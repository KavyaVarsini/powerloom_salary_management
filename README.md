# 🏭 Powerloom Salary & Production Management System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)

An end-to-end web application built for **Jai Krishna Weaving Mills** to streamline daily loom production tracking, automated worker weekly salary calculation, loan advance management, ML-driven yield forecasting, and official printable payslip/PDF generation.

---

## 🌟 Key Features

### 📊 1. Production Dashboard & Analytics
- **Live KPI Tracking**: Real-time stats for Total Workers, Active/Inactive Workers, Today's Output, Weekly Meters Weaved, and Weekly Total Salary.
- **Interactive Visualizations**:
  - **Weekly Production Trend**: Interactive line chart with date ranges.
  - **Top Performing Workers**: Bar charts comparing worker output.
  - **Monthly Production Trend**: Historical line chart for long-term tracking.
  - **Loom Efficiency (%)**: Horizontal bar chart comparing individual loom metrics.
  - **Worker Consistency Classification**: Automatic categorization into *Excellent, Good, Average, Poor, Insufficient Data*.
- **Machine Learning Alerts**: Anomaly detection identifies looms operating below expected benchmarks.

### 👥 2. Master Management (Admin)
- **Worker Management**: Add, view, update, and toggle active/inactive status for mill operators.
- **Loom Management**: Register powerlooms, assign targets, and monitor efficiency.

### ⚙️ 3. Operations & Financial Control
- **Daily Production Log**: Record daily shift entries (date, worker, loom, shift, meters weaved, run hours).
- **Automated Weekly Salary Calculation**: Automated wage calculations per meter weaved, including loan advance deductions and target bonuses.
- **Loan & Advance Management**: Manage worker loans, track payments, and automatically reconcile salary deductions.
- **Production Targets**: Set shift and weekly production targets for incentive tracking.

### 📄 4. Professional Payslips & PDF Exporting
- **Official Mill Letterhead Integration**: Includes GSTIN (`33AAQFJ1452K1Z7`), Contact Numbers, Official Company Title, and Address.
- **High-Resolution Payslips**: Generate clean, printable worker payslips with dual-logo rendering.
- **One-Click PDF Reports**: Export table data (Salary Reports, Production Logs) into formatted PDFs with custom headers and line wrapping.

### 🎨 5. Modern UI/UX & Dark Mode
- **Grouped Sidebar Navigation**: Organised sections for *Overview*, *Masters*, *Operations*, and *Reports & Analytics* with FontAwesome icons.
- **Dual Theme Support**: Dynamic Dark Mode & Light Mode switching with high-contrast chart rendering.
- **Responsive Layout**: Designed for desktops, tablets, and mobile displays.

---

## 🛠️ Technology Stack

- **Backend**: Python, Flask, SQLite / Relational Database
- **Machine Learning**: Scikit-learn, Pandas, NumPy (Yield forecasting & anomaly detection)
- **Frontend**: HTML5, Vanilla CSS3, JavaScript (ES6+), FontAwesome Icons
- **Charts & Reporting**: Chart.js, Vanilla DataTables, jsPDF & jsPDF-AutoTable
- **PDF & Image Processing**: Pillow (PIL), Canvas Data URL handling

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9 or higher installed
- `pip` package manager

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/KavyaVarsini/powerloom_salary_management.git
   cd powerloom_salary_management
   ```

2. **Create a virtual environment** *(optional but recommended)*:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(If `requirements.txt` is missing: `pip install flask pillow scikit-learn pandas numpy`)*

4. **Run the Application**:
   ```bash
   python app.py
   ```

5. **Access the Web App**:
   Open your browser and navigate to `http://127.0.0.1:5000`

---

## 📑 Module Overview

| Module | Description |
| :--- | :--- |
| `Dashboard` | Real-time overview of active/inactive workers, weekly production range, and ML loom alerts |
| `Daily Entry` | Form for logging daily loom production metrics per shift |
| `Weekly Salary` | Automatic weekly salary calculation with loan advance deductions |
| `Production Report` | Detailed metrics and ML weekly forecasts per worker |
| `Salary Report` | Weekly wage breakdown with one-click PDF export |
| `Analytics` | Comprehensive graphical breakdown of loom efficiency and worker consistency |

---

## 📄 License & Attribution

- **Developed for**: **Jai Krishna Weaving Mills**
- Address: 1/501 - A1, Kallimedu Thottam, Nallagoundenpalayam, Paduvampalli (Po), Sulur (Tk.), Coimbatore - 641 659.
