from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
import shutil
from datetime import datetime
import csv
from flask import Response
import os
from dotenv import load_dotenv
from flask import jsonify

from ml_insights import get_loom_anomalies, forecast_worker_weekly_production

load_dotenv()

def backup_database():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup/powerloom_backup_{timestamp}.db"
    shutil.copy("powerloom.db", backup_file)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "powerloom_secret_key")

last_backup_time = None


def connect_db():
    conn = sqlite3.connect("powerloom.db")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

from functools import wraps
from werkzeug.security import check_password_hash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login_gateway"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in") or session.get("role") != "Admin":
            flash("Admin access is required to view that page.", "danger")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function

from datetime import date, timedelta

@app.route("/")
@login_required
def home():
    global last_backup_time
    now = datetime.now()
    if last_backup_time is None or (now - last_backup_time).total_seconds() > 86400:
        try:
            backup_database()
            last_backup_time = now
        except Exception as e:
            print(f"Error creating auto-backup: {e}")

    conn = connect_db()
    cursor = conn.cursor()

    # ==============================
    # BASIC STATS
    # ==============================

    # Total Workers
    cursor.execute("SELECT COUNT(*) FROM workers")
    total_workers = cursor.fetchone()[0]

    # Active Workers
    cursor.execute("SELECT COUNT(*) FROM workers WHERE active_status='Active'")
    active_workers = cursor.fetchone()[0]

    # Today's Production
    from datetime import date, timedelta
    today = date.today().isoformat()

    cursor.execute("""
        SELECT COALESCE(SUM(output_quantity), 0)
        FROM daily_output
        WHERE date = ?
    """, (today,))
    today_production = cursor.fetchone()[0]

    # This Week Production
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()

    cursor.execute("""
        SELECT COALESCE(SUM(output_quantity), 0)
        FROM daily_output
        WHERE date BETWEEN ? AND ?
    """, (week_start, today))
    week_production = cursor.fetchone()[0]

    # This Week Salary
    cursor.execute("""
        SELECT COALESCE(SUM(d.output_quantity * l.rate_per_unit), 0)
        FROM daily_output d
        JOIN looms l ON d.loom_number = l.loom_number
        WHERE d.date BETWEEN ? AND ?
    """, (week_start, today))
    week_salary = cursor.fetchone()[0]

    # ==============================
    # WEEKLY PRODUCTION TREND (Last 7 Days)
    # ==============================

    cursor.execute("""
        SELECT date, SUM(output_quantity)
        FROM daily_output
        WHERE date >= date('now', '-6 days')
        GROUP BY date
        ORDER BY date
    """)
    weekly_trend = cursor.fetchall()

    if weekly_trend is None:
        weekly_trend = []

    # ==============================
    # ALERT: LOW PRODUCERS TODAY
    # ==============================

    cursor.execute("""
        SELECT worker_name, output_quantity
        FROM daily_output
        WHERE date = ?
    """, (today,))

    today_records = cursor.fetchall()
    alert_workers = []

    if today_records:
        avg_today = sum([r[1] for r in today_records]) / len(today_records)

        for name, qty in today_records:
            if qty < avg_today * 0.5:
                alert_workers.append((name, qty))

    conn.close()

    # ==============================
    # RENDER TEMPLATE
    # ==============================

    return render_template(
        "index.html",
        total_workers=total_workers,
        active_workers=active_workers,
        today_production=today_production,
        week_production=week_production,
        week_salary=week_salary,
        weekly_trend=weekly_trend,
        alert_workers=alert_workers
    )

@app.route("/add-worker", methods=["GET", "POST"])
@admin_required
def add_worker():
    if request.method == "POST":
        name = request.form["worker_name"].strip()
        phone = request.form["phone"].strip()

        # PHONE NUMBER VALIDATION
        if not phone.isdigit() or len(phone) != 10:
            flash("Phone number must contain exactly 10 digits.", "danger")
            return redirect(url_for("add_worker"))

        conn = connect_db()
        cursor = conn.cursor()

        # Check duplicate
        cursor.execute("SELECT COUNT(*) FROM workers WHERE worker_name=?", (name,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            flash(f"Worker '{name}' already exists.", "danger")
            return redirect(url_for("add_worker"))

        cursor.execute(
            "INSERT INTO workers VALUES (?, ?, ?)",
            (name, phone, "Active")
        )

        conn.commit()
        conn.close()

        flash(f"Worker '{name}' added successfully.", "success")
        return redirect(url_for("add_worker"))

    return render_template("add_worker.html")

@app.route("/add-loom", methods=["GET", "POST"])
@admin_required
def add_loom():
    if request.method == "POST":
        loom_number = request.form.get("loom_number")
        rate = request.form.get("rate")

        # Basic validation
        if not loom_number or not rate:
            flash("Loom number and rate are required.", "danger")
            return redirect(url_for("add_loom"))

        conn = connect_db()
        cursor = conn.cursor()

        # Check duplicate
        cursor.execute("SELECT COUNT(*) FROM looms WHERE loom_number=?", (loom_number,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            flash(f"Loom {loom_number} already exists.", "danger")
            return redirect(url_for("add_loom"))

        cursor.execute(
            "INSERT INTO looms (loom_number, rate_per_unit, status) VALUES (?, ?, ?)",
            (loom_number, rate, "Active")
        )

        conn.commit()
        conn.close()

        flash(f"Loom {loom_number} added successfully.", "success")
        return redirect(url_for("add_loom"))

    return render_template("add_loom.html")



@app.route("/daily-entry", methods=["GET", "POST"])
@login_required
def daily_entry():
    conn = connect_db()
    cursor = conn.cursor()

    if request.method == "POST":
        worker = request.form.get("worker_name")
        loom = request.form.get("loom_number")
        date = request.form.get("date")
        shift = request.form.get("shift")
        output = request.form.get("output")

        # REQUIRED FIELD CHECK
        if not output or not output.isdigit():
            conn.close()
            flash("Output quantity is required and must be a number.", "danger")
            return redirect(url_for("daily_entry"))

        # 🔴 OUTPUT VALIDATION (CRITICAL FIX)
        if not output or not output.isdigit():
            conn.close()
            return (
                "Output quantity is required and must be a number.<br><br>"
                "<a href='/daily-entry'>Back</a>"
            )

        output = int(output)

        # DUPLICATE ENTRY CHECK
        cursor.execute(
            """
            SELECT COUNT(*) FROM daily_output
            WHERE worker_name=? AND date=? AND shift=?
            """,
            (worker, date, shift)
        )

        if cursor.fetchone()[0] > 0:
            conn.close()
            flash("Duplicate entry not allowed for this worker, date and shift.", "danger")
            return redirect(url_for("daily_entry"))

        # Parse and validate run_time
        run_time = request.form.get("run_time")
        try:
            run_time = float(run_time) if run_time else 12.0
            if run_time < 0 or run_time > 24:
                run_time = 12.0
        except ValueError:
            run_time = 12.0

        # INSERT DAILY OUTPUT
        cursor.execute(
            """
            INSERT INTO daily_output
            (worker_name, loom_number, date, shift, output_quantity, run_time_hours)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (worker, loom, date, shift, output, run_time)
        )

        conn.commit()
        conn.close()
        flash(f"Daily output record for {worker} (Loom {loom}) added successfully.", "success")
        return redirect(url_for("daily_entry"))
    
    # GET REQUEST → LOAD DROPDOWNS
    cursor.execute("SELECT worker_name FROM workers WHERE active_status='Active'")
    workers = cursor.fetchall()

    cursor.execute("SELECT loom_number FROM looms WHERE status='Active'")
    looms = cursor.fetchall()

    conn.close()
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("daily_entry.html", workers=workers, looms=looms, today_date=today)
@app.route("/weekly-salary", methods=["GET", "POST"])
@admin_required
def weekly_salary():
    conn = connect_db()
    cursor = conn.cursor()

    # ALWAYS define variables first
    worker = None
    start = None
    end = None
    records = []
    total = 0
    outstanding_loan_balance = 0.0
    applied_deduction = 0.0
    deduction_id = None
    net_total = 0.0
    total_meters = 0
    incentive_bonus = 0.0
    achieved_target_threshold = None

    # Fetch active workers
    cursor.execute("SELECT worker_name FROM workers WHERE active_status='Active' ORDER BY worker_name")
    workers = cursor.fetchall()

    if request.method == "POST":
        worker = request.form.get("worker_name")
        start = request.form.get("start_date")
        end = request.form.get("end_date")
    else:
        worker = request.args.get("worker_name")
        start = request.args.get("start_date")
        end = request.args.get("end_date")

    if worker and start and end:
        cursor.execute("""
            SELECT d.date,
                   d.loom_number,
                   d.output_quantity,
                   l.rate_per_unit,
                   (d.output_quantity * l.rate_per_unit) AS daily_pay
            FROM daily_output d
            JOIN looms l ON d.loom_number = l.loom_number
            WHERE d.worker_name = ?
            AND d.date BETWEEN ? AND ?
            ORDER BY d.date ASC
        """, (worker, start, end))

        records = cursor.fetchall()
        total = sum(r[4] for r in records)
        
        # Calculate total meters and target incentive
        total_meters = sum(r[2] for r in records)
        incentive_bonus, achieved_target_threshold = calculate_incentive(total_meters)

        # Get outstanding loans for the worker
        cursor.execute("""
            SELECT COALESCE(SUM(amount - repaid_amount), 0)
            FROM loans
            WHERE worker_name = ? AND status = 'Active'
        """, (worker,))
        outstanding_loan_balance = cursor.fetchone()[0]

        # Get applied salary deduction repayment for this date range
        cursor.execute("""
            SELECT repayment_id, COALESCE(SUM(amount), 0)
            FROM loan_repayments
            WHERE worker_name = ?
              AND salary_start_date = ?
              AND salary_end_date = ?
              AND repayment_type = 'Salary Deduction'
            GROUP BY repayment_id
        """, (worker, start, end))
        
        repayment_rows = cursor.fetchall()
        if repayment_rows:
            deduction_id = repayment_rows[0][0]
            applied_deduction = sum(r[1] for r in repayment_rows)
        else:
            deduction_id = None
            applied_deduction = 0.0

        net_total = total + incentive_bonus - applied_deduction

    conn.close()

    return render_template(
        "weekly_salary.html",
        workers=workers,
        records=records,
        total=total,
        selected_worker=worker,
        start=start,
        end=end,
        outstanding_loan_balance=outstanding_loan_balance,
        applied_deduction=applied_deduction,
        deduction_id=deduction_id,
        net_total=net_total,
        total_meters=total_meters,
        incentive_bonus=incentive_bonus,
        achieved_target_threshold=achieved_target_threshold
    )


@app.route("/worker-production", methods=["GET", "POST"])
@admin_required
def worker_production():
    conn = connect_db()
    cursor = conn.cursor()

    records = []
    forecasts = {}
    start = end = None

    if request.method == "POST":
        start = request.form.get("start_date")
        end = request.form.get("end_date")

        cursor.execute("""
            SELECT worker_name,
                   COALESCE(SUM(output_quantity), 0) AS total_output
            FROM daily_output
            WHERE date BETWEEN ? AND ?
            GROUP BY worker_name
            ORDER BY worker_name
        """, (start, end))

        records = cursor.fetchall()
        
        try:
            from datetime import datetime
            datetime.strptime(start, "%Y-%m-%d")
            for record in records:
                worker_name = record[0]
                forecast = forecast_worker_weekly_production("powerloom.db", worker_name, start)
                forecasts[worker_name] = forecast
        except Exception as e:
            print("Forecast error:", e)

    conn.close()
    return render_template(
        "worker_production.html",
        records=records,
        start=start,
        end=end,
        forecasts=forecasts
    )

@app.route("/worker-salary-report", methods=["GET", "POST"])
@admin_required
def worker_salary_report():
    conn = connect_db()
    cursor = conn.cursor()

    records = []
    start = end = None

    if request.method == "POST":
        start = request.form.get("start_date")
        end = request.form.get("end_date")

        cursor.execute("""
            SELECT d.worker_name,
                   COALESCE(SUM(d.output_quantity * l.rate_per_unit), 0) AS total_salary
            FROM daily_output d
            JOIN looms l ON d.loom_number = l.loom_number
            WHERE d.date BETWEEN ? AND ?
            GROUP BY d.worker_name
            ORDER BY d.worker_name
        """, (start, end))

        records = cursor.fetchall()

    conn.close()
    return render_template(
        "worker_salary_report.html",
        records=records,
        start=start,
        end=end
    )

@app.route('/view-workers')
@admin_required
def view_workers():
    status = request.args.get('status', 'Active')
    search = request.args.get('search', '')

    conn = sqlite3.connect('powerloom.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = "SELECT * FROM workers WHERE active_status=?"
    params = [status]

    if search:
        query += " AND (worker_name LIKE ? OR phone LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    cursor.execute(query, params)
    workers = cursor.fetchall()

    conn.close()

    return render_template(
        'view_workers.html',
        workers=workers,
        current_status=status,
        search=search
    )





@app.route("/delete-worker", methods=["POST"])
@admin_required
def delete_worker():
    worker_name = request.form["worker_name"]

    conn = connect_db()
    cursor = conn.cursor()

    # CHECK IF SALARY / DAILY OUTPUT RECORDS EXIST
    cursor.execute(
        "SELECT COUNT(*) FROM daily_output WHERE worker_name=?",
        (worker_name,)
    )
    count = cursor.fetchone()[0]

    if count > 0:
        conn.close()
        flash("Cannot delete worker. Salary records exist.", "danger")
        return redirect(url_for("view_workers"))

    # SAFE TO DELETE (SOFT DELETE)
    cursor.execute(
        "UPDATE workers SET active_status='Inactive' WHERE worker_name=?",
        (worker_name,)
    )

    conn.commit()
    conn.close()

    flash(f"Worker '{worker_name}' deactivated successfully.", "success")
    return redirect("/view-workers")


@app.route('/deactivate_worker/<worker_name>')
@admin_required
def deactivate_worker(worker_name):
    conn = sqlite3.connect('powerloom.db')
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE workers SET active_status='Inactive' WHERE worker_name=?",
        (worker_name,)
    )

    conn.commit()
    conn.close()

    flash(f"Worker '{worker_name}' deactivated successfully.", "success")
    return redirect('/view-workers?status=Active')



@app.route('/activate_worker/<worker_name>')
@admin_required
def activate_worker(worker_name):
    conn = sqlite3.connect('powerloom.db')
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE workers SET active_status='Active' WHERE worker_name=?",
        (worker_name,)
    )

    conn.commit()
    conn.close()

    flash(f"Worker '{worker_name}' activated successfully.", "success")
    return redirect('/view-workers?status=Inactive')

@app.route("/edit-worker/<worker_name>", methods=["GET", "POST"])
@admin_required
def edit_worker(worker_name):
    conn = connect_db()
    cursor = conn.cursor()

    if request.method == "POST":
        new_name = request.form["new_name"]
        phone = request.form["phone"]

        # Phone validation
        if not phone.isdigit() or len(phone) != 10:
            conn.close()
            return "Invalid phone number.<br><a href='/view-workers'>Back</a>"

        # Update workers table
        cursor.execute(
            "UPDATE workers SET worker_name=?, phone=? WHERE worker_name=?",
            (new_name, phone, worker_name)
        )

        # Update dependent records
        cursor.execute(
            "UPDATE daily_output SET worker_name=? WHERE worker_name=?",
            (new_name, worker_name)
        )

        conn.commit()
        conn.close()
        flash(f"Worker '{new_name}' updated successfully.", "success")
        return redirect("/view-workers")


    cursor.execute(
        "SELECT phone FROM workers WHERE worker_name=?",
        (worker_name,)
    )
    phone = cursor.fetchone()[0]

    conn.close()
    return render_template(
        "edit_worker.html",
        worker_name=worker_name,
        phone=phone
    )


@app.route('/view-looms')
@admin_required
def view_looms():
    status = request.args.get('status', 'Active')

    conn = sqlite3.connect('powerloom.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM looms WHERE status=?",
        (status,)
    )
    looms = cursor.fetchall()

    conn.close()

    return render_template(
        'view_looms.html',
        looms=looms,
        current_status=status
    )


@app.route('/deactivate_loom/<int:loom_number>')
@admin_required
def deactivate_loom(loom_number):
    conn = sqlite3.connect('powerloom.db')
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE looms SET status='Inactive' WHERE loom_number=?",
        (loom_number,)
    )

    conn.commit()
    conn.close()

    flash(f"Loom {loom_number} deactivated successfully.", "success")
    return redirect('/view-looms?status=Active')



@app.route('/activate_loom/<int:loom_number>')
@admin_required
def activate_loom(loom_number):
    conn = sqlite3.connect('powerloom.db')
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE looms SET status='Active' WHERE loom_number=?",
        (loom_number,)
    )

    conn.commit()
    conn.close()

    flash(f"Loom {loom_number} activated successfully.", "success")
    return redirect('/view-looms?status=Inactive')






@app.route("/delete-loom", methods=["POST"])
@admin_required
def delete_loom():
    loom_number = request.form["loom_number"]

    conn = connect_db()
    cursor = conn.cursor()

    # Check if loom is used
    cursor.execute(
        "SELECT COUNT(*) FROM daily_output WHERE loom_number=?",
        (loom_number,)
    )
    count = cursor.fetchone()[0]

    if count > 0:
        conn.close()
        flash("Cannot delete loom. Production records exist.", "danger")
        return redirect(url_for("view_looms"))

    # SOFT DELETE (THIS IS THE KEY LINE)
    cursor.execute(
        "UPDATE looms SET status='Inactive' WHERE loom_number=?",
        (loom_number,)
    )

    conn.commit()
    conn.close()

    flash(f"Loom {loom_number} deactivated successfully.", "success")
    return redirect("/view-looms")

@app.route("/edit-loom/<int:loom_number>", methods=["GET", "POST"])
@admin_required
def edit_loom(loom_number):
    conn = connect_db()
    cursor = conn.cursor()

    if request.method == "POST":
        new_loom = request.form["new_loom"]
        rate = request.form["rate"]

        # Update looms table
        cursor.execute(
            "UPDATE looms SET loom_number=?, rate_per_unit=? WHERE loom_number=?",
            (new_loom, rate, loom_number)
        )

        # Update dependent records
        cursor.execute(
            "UPDATE daily_output SET loom_number=? WHERE loom_number=?",
            (new_loom, loom_number)
        )

        conn.commit()
        conn.close()
        flash(f"Loom {new_loom} updated successfully.", "success")
        return redirect(url_for("view_looms"))

    cursor.execute(
        "SELECT rate_per_unit FROM looms WHERE loom_number=?",
        (loom_number,)
    )
    rate = cursor.fetchone()[0]

    conn.close()
    return render_template(
        "edit_loom.html",
        loom_number=loom_number,
        rate=rate
    )

@app.route("/daily-history", methods=["GET", "POST"])
@login_required
def daily_history():
    conn = connect_db()
    cursor = conn.cursor()

    # Fetch workers for dropdown
    cursor.execute("SELECT worker_name FROM workers WHERE active_status='Active'")
    workers = cursor.fetchall()

    # Read filters (POST preferred; GET fallback)
    worker = request.form.get("worker_name") or request.args.get("worker_name")
    date = request.form.get("date") or request.args.get("date")

    query = """
        SELECT record_id, date, worker_name, loom_number, shift, output_quantity, run_time_hours
        FROM daily_output
        WHERE 1=1
    """
    params = []

    if worker:
        query += " AND worker_name = ?"
        params.append(worker)

    if date:
        query += " AND date = ?"
        params.append(date)

    query += " ORDER BY date DESC"

    cursor.execute(query, params)
    records = cursor.fetchall()

    conn.close()
    return render_template(
        "daily_history.html",
        records=records,
        workers=workers,
        selected_worker=worker,
        selected_date=date
    )

@app.route("/edit-entry/<int:record_id>", methods=["GET", "POST"])
@admin_required
def edit_entry(record_id):
    conn = connect_db()
    cursor = conn.cursor()

    if request.method == "POST":
        worker = request.form.get("worker_name")
        loom = request.form.get("loom_number")
        date = request.form.get("date")
        shift = request.form.get("shift")
        output = request.form.get("output")

        # Basic validations
        if not output or not output.isdigit():
            conn.close()
            flash("Output quantity must be a positive number.", "danger")
            return redirect(url_for("edit_entry", record_id=record_id))

        output = int(output)

        # Parse and validate run_time
        run_time = request.form.get("run_time")
        try:
            run_time = float(run_time) if run_time else 12.0
            if run_time < 0 or run_time > 24:
                run_time = 12.0
        except ValueError:
            run_time = 12.0

        # Update record
        cursor.execute(
            """
            UPDATE daily_output
            SET worker_name=?, loom_number=?, date=?, shift=?, output_quantity=?, run_time_hours=?
            WHERE record_id=?
            """,
            (worker, loom, date, shift, output, run_time, record_id)
        )
        conn.commit()
        conn.close()
        flash("Daily output record updated successfully.", "success")
        return redirect(url_for("daily_history"))

    # Fetch existing record details
    cursor.execute("SELECT * FROM daily_output WHERE record_id = ?", (record_id,))
    record = cursor.fetchone()

    # Load dropdowns
    cursor.execute("SELECT worker_name FROM workers WHERE active_status='Active'")
    workers = cursor.fetchall()

    cursor.execute("SELECT loom_number FROM looms WHERE status='Active'")
    looms = cursor.fetchall()

    conn.close()

    if not record:
        flash("Record not found.", "danger")
        return redirect(url_for("daily_history"))

    # record is a tuple: (record_id, date, worker_name, loom_number, shift, output_quantity)
    return render_template("edit_entry.html", record=record, workers=workers, looms=looms)


@app.route("/delete-entry/<int:record_id>", methods=["POST"])
@admin_required
def delete_entry(record_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM daily_output WHERE record_id = ?", (record_id,))
    conn.commit()
    conn.close()

    flash("Daily output record deleted successfully.", "success")
    return redirect(url_for("daily_history"))


@app.route("/print-payslip/<worker_name>/<start_date>/<end_date>")
@admin_required
def print_payslip(worker_name, start_date, end_date):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT d.date,
               d.loom_number,
               d.output_quantity,
               l.rate_per_unit,
               (d.output_quantity * l.rate_per_unit) AS daily_pay,
               d.run_time_hours
        FROM daily_output d
        JOIN looms l ON d.loom_number = l.loom_number
        WHERE d.worker_name = ?
        AND d.date BETWEEN ? AND ?
        ORDER BY d.date ASC
    """, (worker_name, start_date, end_date))

    records = cursor.fetchall()
    total = sum(r[4] for r in records)

    # Calculate total meters and target incentive
    total_meters = sum(r[2] for r in records)
    incentive_bonus, achieved_target_threshold = calculate_incentive(total_meters)

    # Query if there was a salary deduction for this pay period
    cursor.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM loan_repayments
        WHERE worker_name = ?
          AND salary_start_date = ?
          AND salary_end_date = ?
          AND repayment_type = 'Salary Deduction'
    """, (worker_name, start_date, end_date))
    applied_deduction = cursor.fetchone()[0]

    # Query remaining outstanding loan balance for the worker
    cursor.execute("""
        SELECT COALESCE(SUM(amount - repaid_amount), 0)
        FROM loans
        WHERE worker_name = ? AND status = 'Active'
    """, (worker_name,))
    remaining_balance = cursor.fetchone()[0]

    net_total = total + incentive_bonus - applied_deduction
    conn.close()

    today_str = datetime.now().strftime("%Y-%m-%d")

    return render_template(
        "print_payslip.html",
        worker_name=worker_name,
        start=start_date,
        end=end_date,
        records=records,
        total=total,
        applied_deduction=applied_deduction,
        net_total=net_total,
        remaining_balance=remaining_balance,
        date=today_str,
        total_meters=total_meters,
        incentive_bonus=incentive_bonus,
        achieved_target_threshold=achieved_target_threshold
    )


@app.route("/analytics")
@admin_required
def analytics():

    import statistics

    conn = connect_db()
    cur = conn.cursor()

    # 🔥 1️⃣ Top Performing Workers
    cur.execute("""
        SELECT worker_name, SUM(output_quantity) as total
        FROM daily_output
        GROUP BY worker_name
        ORDER BY total DESC
        LIMIT 5
    """)
    top_workers = cur.fetchall()

    # 🔥 2️⃣ Monthly Production Trend
    cur.execute("""
        SELECT date,
             SUM(output_quantity)
            FROM daily_output
            GROUP BY date
        ORDER BY date
    """)
    monthly_trend = cur.fetchall()

    # 🔥 3️⃣ Loom Efficiency
    cur.execute("""
        SELECT daily_output.loom_number,
               SUM(daily_output.output_quantity) as actual,
               looms.expected_daily_production
        FROM daily_output
        JOIN looms ON looms.loom_number = daily_output.loom_number
        GROUP BY daily_output.loom_number
    """)

    loom_data = cur.fetchall()
    loom_efficiency = []

    for loom in loom_data:
        loom_number = loom[0]
        actual = loom[1] or 0
        expected_monthly = (loom[2] or 0) * 30

        if expected_monthly > 0:
            efficiency = round((actual / expected_monthly) * 100, 2)
        else:
            efficiency = 0

        loom_efficiency.append((loom_number, efficiency))

    # 🔥 4️⃣ Worker Consistency Category
    cur.execute("""
        SELECT worker_name, output_quantity
        FROM daily_output
    """)

    data = cur.fetchall()
    worker_dict = {}

    for name, qty in data:
        worker_dict.setdefault(name, []).append(qty)

    consistency_data = []

    for name, productions in worker_dict.items():

        if len(productions) > 1:
            mean = statistics.mean(productions)
            std_dev = statistics.stdev(productions)

            if mean > 0:
                cv = (std_dev / mean) * 100

                if cv < 10:
                    category = "Excellent"
                elif cv < 25:
                    category = "Good"
                elif cv < 50:
                    category = "Average"
                else:
                    category = "Poor"
            else:
                category = "No Production"
        else:
            category = "Insufficient Data"

        consistency_data.append((name, category))

    conn.close()

    return render_template(
        "analytics.html",
        top_workers=top_workers,
        monthly_trend=monthly_trend,
        loom_efficiency=loom_efficiency,
        consistency_data=consistency_data
    )

@app.route("/api/loom_alerts")
@admin_required
def loom_alerts():
    anomalous_looms = get_loom_anomalies("powerloom.db")
    return jsonify({"anomalous_looms": anomalous_looms})


@app.route("/export-production")
@admin_required
def export_production():

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT worker_name, loom_number, date, shift, output_quantity
        FROM daily_output
        ORDER BY date
    """)

    rows = cursor.fetchall()
    conn.close()

    import io
    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Worker Name", "Loom", "Date", "Shift", "Output"])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in rows:
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition":"attachment;filename=production_report.csv"}
    )

@app.route("/export-salary")
@admin_required
def export_salary():

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT d.worker_name,
               SUM(d.output_quantity * l.rate_per_unit) AS total_salary
        FROM daily_output d
        JOIN looms l ON d.loom_number = l.loom_number
        GROUP BY d.worker_name
    """)

    rows = cursor.fetchall()
    conn.close()

    import io
    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Worker Name", "Total Salary"])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for row in rows:
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition":"attachment;filename=salary_report.csv"}
    )

def calculate_incentive(total_meters):
    if not total_meters or total_meters <= 0:
        return 0.0, None
        
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT target_quantity, bonus_amount
        FROM incentive_targets
        WHERE target_type = 'Weekly'
        ORDER BY target_quantity DESC
    """)
    targets = cursor.fetchall()
    conn.close()
    
    for qty, bonus in targets:
        if total_meters >= qty:
            return bonus, qty
            
    return 0.0, None

@app.route("/targets", methods=["GET", "POST"])
@admin_required
def targets_dashboard():
    conn = connect_db()
    cursor = conn.cursor()
    
    if request.method == "POST":
        qty = request.form.get("target_quantity")
        bonus = request.form.get("bonus_amount")
        
        if not qty or not bonus:
            flash("Target quantity and bonus amount are required.", "danger")
            return redirect(url_for("targets_dashboard"))
            
        try:
            qty = int(qty)
            bonus = float(bonus)
            if qty <= 0 or bonus <= 0:
                raise ValueError
        except ValueError:
            flash("Threshold and bonus must be positive numbers.", "danger")
            return redirect(url_for("targets_dashboard"))
            
        try:
            cursor.execute("""
                INSERT INTO incentive_targets (target_quantity, bonus_amount)
                VALUES (?, ?)
            """, (qty, bonus))
            conn.commit()
            flash("Production target tier added successfully.", "success")
        except sqlite3.IntegrityError:
            flash("A target tier with this threshold already exists.", "danger")
            
        conn.close()
        return redirect(url_for("targets_dashboard"))
        
    cursor.execute("SELECT target_id, target_quantity, bonus_amount FROM incentive_targets ORDER BY target_quantity ASC")
    targets = cursor.fetchall()
    conn.close()
    return render_template("targets.html", targets=targets)

@app.route("/targets/delete/<int:target_id>", methods=["POST"])
@admin_required
def targets_delete(target_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM incentive_targets WHERE target_id = ?", (target_id,))
    conn.commit()
    conn.close()
    flash("Production target tier deleted successfully.", "success")
    return redirect(url_for("targets_dashboard"))


@app.route("/loans", methods=["GET"])
@admin_required
def loans_dashboard():
    conn = connect_db()
    cursor = conn.cursor()
    
    # 1. Fetch active workers for the loan issue dropdown
    cursor.execute("SELECT worker_name FROM workers WHERE active_status='Active' ORDER BY worker_name")
    workers = cursor.fetchall()
    
    # 2. Fetch workers who currently have active loans to populate the repayment dropdown
    cursor.execute("""
        SELECT worker_name, SUM(amount - repaid_amount) AS outstanding
        FROM loans
        WHERE status = 'Active'
        GROUP BY worker_name
        HAVING outstanding > 0
        ORDER BY worker_name
    """)
    workers_with_loans = cursor.fetchall()
    
    # 3. Fetch all active loans
    cursor.execute("""
        SELECT loan_id, worker_name, amount, date_given, description, repaid_amount, status
        FROM loans
        WHERE status = 'Active'
        ORDER BY date_given DESC
    """)
    active_loans = cursor.fetchall()
    
    # 4. Fetch all repayments
    cursor.execute("""
        SELECT repayment_id, loan_id, worker_name, amount, repayment_date, repayment_type, salary_start_date, salary_end_date, notes
        FROM loan_repayments
        ORDER BY repayment_date DESC, repayment_id DESC
    """)
    repayments = cursor.fetchall()
    
    conn.close()
    
    today_date = datetime.now().strftime("%Y-%m-%d")
    return render_template(
        "loans.html",
        workers=workers,
        workers_with_loans=workers_with_loans,
        active_loans=active_loans,
        repayments=repayments,
        today_date=today_date
    )

@app.route("/loans/issue", methods=["POST"])
@admin_required
def loans_issue():
    worker_name = request.form.get("worker_name")
    amount = request.form.get("amount")
    date_given = request.form.get("date")
    description = request.form.get("description")
    
    if not worker_name or not amount or not date_given:
        flash("Worker name, amount, and date are required.", "danger")
        return redirect(url_for("loans_dashboard"))
        
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Amount must be a positive number.", "danger")
        return redirect(url_for("loans_dashboard"))
        
    conn = connect_db()
    cursor = conn.cursor()
    
    # Verify worker exists and is active
    cursor.execute("SELECT active_status FROM workers WHERE worker_name = ?", (worker_name,))
    worker = cursor.fetchone()
    if not worker:
        conn.close()
        flash("Selected worker does not exist.", "danger")
        return redirect(url_for("loans_dashboard"))
        
    cursor.execute("""
        INSERT INTO loans (worker_name, amount, date_given, description)
        VALUES (?, ?, ?, ?)
    """, (worker_name, amount, date_given, description))
    
    conn.commit()
    conn.close()
    
    flash(f"Advance of ₹{amount:.2f} issued to {worker_name} successfully.", "success")
    return redirect(url_for("loans_dashboard"))

@app.route("/loans/repay", methods=["POST"])
@admin_required
def loans_repay():
    worker_name = request.form.get("worker_name")
    amount = request.form.get("amount")
    repayment_date = request.form.get("date")
    notes = request.form.get("notes")
    
    if not worker_name or not amount or not repayment_date:
        flash("Worker name, amount, and date are required.", "danger")
        return redirect(url_for("loans_dashboard"))
        
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Amount must be a positive number.", "danger")
        return redirect(url_for("loans_dashboard"))
        
    conn = connect_db()
    cursor = conn.cursor()
    
    # Get all active loans for this worker, ordered by date_given ascending (FIFO repayment)
    cursor.execute("""
        SELECT loan_id, amount, repaid_amount
        FROM loans
        WHERE worker_name = ? AND status = 'Active'
        ORDER BY date_given ASC, loan_id ASC
    """, (worker_name,))
    active_loans = cursor.fetchall()
    
    total_outstanding = sum(l[1] - l[2] for l in active_loans)
    
    if total_outstanding == 0:
        conn.close()
        flash(f"{worker_name} does not have any active loans.", "danger")
        return redirect(url_for("loans_dashboard"))
        
    if amount > total_outstanding:
        conn.close()
        flash(f"Repayment amount (₹{amount}) exceeds total outstanding debt (₹{total_outstanding}).", "danger")
        return redirect(url_for("loans_dashboard"))
        
    remaining_repayment = amount
    
    # Process repayment across worker's active loans (FIFO)
    for loan in active_loans:
        if remaining_repayment <= 0:
            break
            
        loan_id, loan_amt, repaid_amt = loan
        outstanding = loan_amt - repaid_amt
        
        repay_to_this_loan = min(remaining_repayment, outstanding)
        new_repaid_amount = repaid_amt + repay_to_this_loan
        new_status = 'Paid' if new_repaid_amount >= loan_amt else 'Active'
        
        # Update loan
        cursor.execute("""
            UPDATE loans
            SET repaid_amount = ?, status = ?
            WHERE loan_id = ?
        """, (new_repaid_amount, new_status, loan_id))
        
        # Record repayment transaction
        cursor.execute("""
            INSERT INTO loan_repayments (loan_id, worker_name, amount, repayment_date, repayment_type, notes)
            VALUES (?, ?, ?, ?, 'Direct Cash', ?)
        """, (loan_id, worker_name, repay_to_this_loan, repayment_date, notes))
        
        remaining_repayment -= repay_to_this_loan
        
    conn.commit()
    conn.close()
    
    flash(f"Recorded cash repayment of ₹{amount} for {worker_name}.", "success")
    return redirect(url_for("loans_dashboard"))

@app.route("/loans/delete/<int:loan_id>", methods=["POST"])
@admin_required
def loans_delete(loan_id):
    conn = connect_db()
    cursor = conn.cursor()
    
    # Check if there are any repayments associated with this loan
    cursor.execute("SELECT COUNT(*) FROM loan_repayments WHERE loan_id = ?", (loan_id,))
    repayment_count = cursor.fetchone()[0]
    
    if repayment_count > 0:
        conn.close()
        flash("Cannot delete loan. Repayment records already exist for this loan.", "danger")
        return redirect(url_for("loans_dashboard"))
        
    cursor.execute("DELETE FROM loans WHERE loan_id = ?", (loan_id,))
    conn.commit()
    conn.close()
    
    flash("Loan record deleted successfully.", "success")
    return redirect(url_for("loans_dashboard"))

@app.route("/loans/repayment/delete/<int:repayment_id>", methods=["POST"])
@admin_required
def repayment_delete(repayment_id):
    conn = connect_db()
    cursor = conn.cursor()
    
    # Fetch repayment details
    cursor.execute("SELECT loan_id, amount FROM loan_repayments WHERE repayment_id = ?", (repayment_id,))
    repayment = cursor.fetchone()
    
    if not repayment:
        conn.close()
        flash("Repayment record not found.", "danger")
        return redirect(url_for("loans_dashboard"))
        
    loan_id, amount = repayment
    
    # Update the loan's repaid amount and restore to active
    cursor.execute("SELECT amount, repaid_amount FROM loans WHERE loan_id = ?", (loan_id,))
    loan = cursor.fetchone()
    
    if loan:
        loan_amt, repaid_amt = loan
        new_repaid = max(0.0, repaid_amt - amount)
        cursor.execute("""
            UPDATE loans
            SET repaid_amount = ?, status = 'Active'
            WHERE loan_id = ?
        """, (new_repaid, loan_id))
        
    # Delete the repayment record
    cursor.execute("DELETE FROM loan_repayments WHERE repayment_id = ?", (repayment_id,))
    
    conn.commit()
    conn.close()
    
    flash("Repayment reverted successfully.", "success")
    return redirect(url_for("loans_dashboard"))

@app.route("/weekly-salary/deduct", methods=["POST"])
@admin_required
def weekly_salary_deduct():
    worker_name = request.form.get("worker_name")
    amount = request.form.get("amount")
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    
    if not worker_name or not amount or not start_date or not end_date:
        flash("Missing required parameters to apply deduction.", "danger")
        return redirect(url_for("weekly_salary"))
        
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Deduction amount must be a positive number.", "danger")
        return redirect(url_for("weekly_salary", worker_name=worker_name, start_date=start_date, end_date=end_date))
        
    conn = connect_db()
    cursor = conn.cursor()
    
    # Check if a deduction is already applied for this period
    cursor.execute("""
        SELECT COUNT(*) FROM loan_repayments
        WHERE worker_name = ?
          AND salary_start_date = ?
          AND salary_end_date = ?
          AND repayment_type = 'Salary Deduction'
    """, (worker_name, start_date, end_date))
    
    if cursor.fetchone()[0] > 0:
        conn.close()
        flash("A salary deduction is already applied for this week.", "danger")
        return redirect(url_for("weekly_salary", worker_name=worker_name, start_date=start_date, end_date=end_date))
        
    # Fetch active loans for the worker (FIFO)
    cursor.execute("""
        SELECT loan_id, amount, repaid_amount
        FROM loans
        WHERE worker_name = ? AND status = 'Active'
        ORDER BY date_given ASC, loan_id ASC
    """, (worker_name,))
    active_loans = cursor.fetchall()
    
    total_outstanding = sum(l[1] - l[2] for l in active_loans)
    if total_outstanding == 0:
        conn.close()
        flash("Worker has no outstanding loans to deduct from.", "danger")
        return redirect(url_for("weekly_salary", worker_name=worker_name, start_date=start_date, end_date=end_date))
        
    if amount > total_outstanding:
        amount = total_outstanding  # Cap at outstanding balance
        
    remaining = amount
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    for loan in active_loans:
        if remaining <= 0:
            break
            
        loan_id, loan_amt, repaid_amt = loan
        outstanding = loan_amt - repaid_amt
        
        deduct_from_this_loan = min(remaining, outstanding)
        new_repaid = repaid_amt + deduct_from_this_loan
        new_status = 'Paid' if new_repaid >= loan_amt else 'Active'
        
        cursor.execute("""
            UPDATE loans
            SET repaid_amount = ?, status = ?
            WHERE loan_id = ?
        """, (new_repaid, new_status, loan_id))
        
        cursor.execute("""
            INSERT INTO loan_repayments (loan_id, worker_name, amount, repayment_date, repayment_type, salary_start_date, salary_end_date)
            VALUES (?, ?, ?, ?, 'Salary Deduction', ?, ?)
        """, (loan_id, worker_name, deduct_from_this_loan, today_str, start_date, end_date))
        
        remaining -= deduct_from_this_loan
        
    conn.commit()
    conn.close()
    
    flash(f"Successfully deducted ₹{amount} from {worker_name}'s salary.", "success")
    return redirect(f"/weekly-salary?worker_name={worker_name}&start_date={start_date}&end_date={end_date}")

@app.route("/weekly-salary/remove-deduction", methods=["POST"])
@admin_required
def weekly_salary_remove_deduction():
    repayment_id = request.form.get("repayment_id")
    worker_name = request.form.get("worker_name")
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    
    if not repayment_id:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT repayment_id FROM loan_repayments
            WHERE worker_name = ?
              AND salary_start_date = ?
              AND salary_end_date = ?
              AND repayment_type = 'Salary Deduction'
        """, (worker_name, start_date, end_date))
        row = cursor.fetchone()
        if row:
            repayment_id = row[0]
        conn.close()
        
    if not repayment_id:
        flash("Deduction record not found.", "danger")
        return redirect(f"/weekly-salary?worker_name={worker_name}&start_date={start_date}&end_date={end_date}")
        
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT repayment_id, loan_id, amount
        FROM loan_repayments
        WHERE worker_name = ?
          AND salary_start_date = ?
          AND salary_end_date = ?
          AND repayment_type = 'Salary Deduction'
    """, (worker_name, start_date, end_date))
    repayments = cursor.fetchall()
    
    for rep in repayments:
        rep_id, loan_id, amount = rep
        
        cursor.execute("SELECT amount, repaid_amount FROM loans WHERE loan_id = ?", (loan_id,))
        loan = cursor.fetchone()
        if loan:
            loan_amt, repaid_amt = loan
            new_repaid = max(0.0, repaid_amt - amount)
            cursor.execute("""
                UPDATE loans
                SET repaid_amount = ?, status = 'Active'
                WHERE loan_id = ?
            """, (new_repaid, loan_id))
            
        cursor.execute("DELETE FROM loan_repayments WHERE repayment_id = ?", (rep_id,))
        
    conn.commit()
    conn.close()
    
    flash("Salary deduction removed successfully.", "success")
    return redirect(f"/weekly-salary?worker_name={worker_name}&start_date={start_date}&end_date={end_date}")

@app.route("/login")
def login_gateway():
    return render_template("login_gateway.html")

@app.route("/login/admin", methods=["GET", "POST"])
def login_admin():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, role FROM users WHERE username = ? AND role = 'Admin'", (username,))
        row = cursor.fetchone()
        conn.close()

        if row and check_password_hash(row[0], password):
            session["logged_in"] = True
            session["role"] = "Admin"
            return redirect("/")
        else:
            flash("Invalid Admin username or password.", "danger")
            return redirect(url_for("login_admin"))

    return render_template("login.html", role_title="Admin")

@app.route("/login/supervisor", methods=["GET", "POST"])
def login_supervisor():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, role FROM users WHERE username = ? AND role = 'Supervisor'", (username,))
        row = cursor.fetchone()
        conn.close()

        if row and check_password_hash(row[0], password):
            session["logged_in"] = True
            session["role"] = "Supervisor"
            return redirect("/")
        else:
            flash("Invalid Supervisor username or password.", "danger")
            return redirect(url_for("login_supervisor"))

    return render_template("login.html", role_title="Supervisor")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_gateway"))



if __name__ == "__main__":
    backup_database()
    app.run(debug=True)
