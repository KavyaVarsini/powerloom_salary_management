import sqlite3
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta

def get_loom_anomalies(db_path="powerloom.db"):
    """
    Analyzes daily output and run time for looms to detect anomalies (potential breakdowns).
    Returns a list of loom numbers flagged as anomalous.
    """
    try:
        conn = sqlite3.connect(db_path)
        query = """
        SELECT loom_number, date, output_quantity, run_time_hours
        FROM daily_output
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty or len(df) < 10:
            return [] # Not enough data

        # Feature engineering: Output per hour
        df['run_time_hours'] = df['run_time_hours'].replace(0, 0.1)
        df['output_per_hour'] = df['output_quantity'] / df['run_time_hours']
        
        features = df[['output_quantity', 'run_time_hours', 'output_per_hour']]
        
        # Fit Isolation Forest
        clf = IsolationForest(contamination=0.05, random_state=42)
        clf.fit(features)
        
        df['anomaly'] = clf.predict(features)
        
        # Sort by date
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date')
        
        latest_records = df.groupby('loom_number').tail(1)
        
        # We only care about anomalies where output is suspiciously LOW
        avg_output = df['output_per_hour'].mean()
        
        anomalous_looms = latest_records[
            (latest_records['anomaly'] == -1) & 
            (latest_records['output_per_hour'] < avg_output)
        ]
        
        return anomalous_looms['loom_number'].tolist()
        
    except Exception as e:
        print(f"Error in get_loom_anomalies: {e}")
        return []

def forecast_worker_weekly_production(db_path, worker_name, week_start_date_str):
    """
    Uses linear regression on current week's production to predict total weekly output.
    week_start_date_str should be 'YYYY-MM-DD'
    Returns: dict with predicted_output, is_on_track for bonuses
    """
    try:
        week_start = datetime.strptime(week_start_date_str, "%Y-%m-%d")
        week_dates = [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        
        conn = sqlite3.connect(db_path)
        
        targets_df = pd.read_sql_query("SELECT target_quantity, bonus_amount FROM incentive_targets ORDER BY target_quantity", conn)
        
        query = """
        SELECT date, SUM(output_quantity) as total_output
        FROM daily_output
        WHERE worker_name = ? AND date BETWEEN ? AND ?
        GROUP BY date
        ORDER BY date
        """
        
        df = pd.read_sql_query(query, conn, params=(worker_name, week_dates[0], week_dates[-1]))
        conn.close()
        
        if df.empty:
            return {"predicted": 0, "message": "No data yet this week.", "target_hit": None, "current_total": 0}
            
        df['date'] = pd.to_datetime(df['date'])
        df['day_index'] = (df['date'] - week_start).dt.days
        
        df['cumulative_output'] = df['total_output'].cumsum()
        current_total = int(df['cumulative_output'].max())
        
        if len(df) < 2:
            daily_avg = df['total_output'].mean()
            predicted_total = int(daily_avg * 7)
            msg = f"Early forecast: {predicted_total} units"
        else:
            X = df[['day_index']]
            y = df['cumulative_output']
            
            model = LinearRegression()
            model.fit(X, y)
            
            # Predict for Sunday (index 6)
            # Ensure output is a scalar and not a NumPy array by wrapping in float() then int()
            prediction_array = model.predict(pd.DataFrame({'day_index': [6]}))
            predicted_total = int(round(float(prediction_array[0])))
            
            # Prevent negative predictions if something weird happens
            predicted_total = max(predicted_total, current_total)
            msg = f"Forecasted week total: {predicted_total} units"
            
        target_hit = None
        for _, row in targets_df.iterrows():
            if predicted_total >= row['target_quantity']:
                target_hit = f"On track for {int(row['target_quantity'])} unit bonus (₹{row['bonus_amount']})"
        
        if not target_hit and not targets_df.empty:
            next_target = targets_df.iloc[0]['target_quantity']
            diff = max(0, int(next_target - current_total))
            target_hit = f"Needs {diff} more units for first bonus."
            
        return {
            "predicted": predicted_total,
            "message": msg,
            "target_hit": target_hit,
            "current_total": current_total
        }
        
    except Exception as e:
        print(f"Error in forecast_worker_weekly_production: {e}")
        return {"predicted": 0, "message": "Forecast unavailable", "target_hit": None, "current_total": 0}
