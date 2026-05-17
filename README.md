# Transaction Reporting Validation Platform

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)](https://www.postgresql.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.25-red)](https://streamlit.io/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**An automated control engine for financial transaction reporting – ensuring accuracy, completeness, and regulatory compliance.**

---

## 📖 Business Context (Why does this matter?)

### The problem
After the 2008 financial crisis, regulators worldwide (e.g., ESMA in Europe) introduced rules like **EMIR** and **MiFID II**. These rules require banks, asset managers, and trading firms to report every single derivatives or securities transaction to central trade repositories within very short deadlines (often **T+1** – by the next day).

**What happens if reporting fails?**  
- Fines up to millions of euros per day  
- Reputational damage  
- Increased regulatory scrutiny  

Yet many firms still rely on manual checks, spreadsheets, or fragmented IT systems. Common issues:
- Missing mandatory fields (e.g., counterparty name)  
- Duplicate submissions of the same trade  
- Invalid unique trade identifiers (UTI)  
- Mismatches between internal records and what was actually reported to the regulator  

### The solution
This platform automates the validation of trade data **before** it is sent to regulators. It acts as a **quality gate**:
- Ingests trade files (e.g., from a trading system)  
- Runs the same checks a regulator would do  
- Flags exceptions immediately  
- Provides a dashboard for operations teams to monitor and fix issues  

**Result:** Faster, cheaper, and more reliable regulatory reporting.

---

## 🎯 Business Case (What value does it create?)

| Metric | Before (manual) | With this platform | Improvement |
|--------|----------------|--------------------|--------------|
| **Time to detect missing fields** | Hours / days | Seconds | **99% faster** |
| **Duplicate trade rate** | ~3-5% (often undetected) | <0.1% after validation | **~95% reduction** |
| **Reconciliation effort** | 2 FTEs full‑time | 0.5 FTE (only exceptions) | **75% cost saving** |
| **Regulatory fine risk** | Moderate to high | Low | **Risk mitigated** |

**Key benefits for stakeholders:**
- **Compliance officers** – Audit trail of all validation checks.  
- **Operations teams** – Single dashboard to prioritize exceptions.  
- **IT / Data managers** – Open‑source, extensible rule engine.  
- **Senior management** – Real‑time quality metrics (pass rates, late trades).

---

## 🚀 Features (What does it do?)

- **Trade Ingestion** – Load large CSV files (100k+ trades) in chunks with duplicate detection.
- **Data Enrichment** – Automatic hash‑based duplicate keys, T+1 reporting due dates.
- **Validation Rules** –  
  ✅ Missing required fields (e.g., counterparty, notional)  
  ✅ Duplicate trades (based on UTI)  
  ✅ UTI format (must be alphanumeric, 16‑52 chars)  
  ✅ Reporting completeness (trades reported after deadline)  
- **Reconciliation** – Compare internal trades against external reports (e.g., trade repositories). Flag notional / counterparty mismatches.
- **Exception Management** – Persist all failures, track resolution status.
- **Operational Dashboard** – Built with Streamlit + Plotly: real‑time KPIs, pass rates, exception trends, and manual resolution.

---

## 🛠️ Tech Stack (For the technical reader)

| Component       | Technology                                |
|----------------|-------------------------------------------|
| Backend         | Python 3.10+, SQLAlchemy ORM              |
| Database        | PostgreSQL 15                             |
| Data Processing | Pandas, NumPy                             |
| Dashboard       | Streamlit, Plotly                         |
| Containerisation| Docker / Docker Compose (optional)        |

---

## 📦 Installation & Setup

### 1. Clone the repository
bash
git clone https://github.com/yourusername/transaction-validation-platform.git
cd transaction-validation-platform

### 2. Set up PostgreSQL (using Docker)
    docker-compose up -d

### 3. Create virtual environment & install dependencies
    python -m venv venv
    source venv/bin/activate      # Linux/Mac
   # or
   venv\Scripts\activate          # Windows

   pip install -r requirements.txt

### 4. Configure environment variables

   Copy .env.example to .env and adjust if needed.

### 5. Create database tables

  python -c "from src.database import engine; from src import models; models.Base.metadata.create_all(bind=engine)"

### 6. Generate sample data (large dataset)  

    Run the data generator to create 150k trades with realistic errors (duplicates, missing fields, invalid UTIs) and an         external report for reconciliation.
    
    python scripts/generate_large_dataset.py

### 7. Run the validation pipeline

   Ingest trades

python -c "from src.database import SessionLocal; from src.ingestion import ingest_trades_from_csv_chunked; db =         SessionLocal(); ingest_trades_from_csv_chunked(db, 'data/large_trades.csv', chunksize=20000); db.close()"

   Run all validations
   
python -c "from src.database import SessionLocal; from src.validation_engine import run_all_validations; run_all_validations(SessionLocal())"   

   Reconcile with external report & check completeness

python -c "from src.database import SessionLocal; from src.reconciliation import reconcile_with_external_report, check_reporting_completeness; db = SessionLocal(); reconcile_with_external_report(db, 'data/large_external_reports.csv'); check_reporting_completeness(db); db.close()"   

### 8. Launch the monitoring dashboard

    python -m streamlit run dashboard/app.py

### 9. Exception management workflow

    - All validation failures are written to exceptions table with rule type and description.

    - Operations team can review exceptions in the dashboard.

    - Each exception can be marked as resolved directly from the Streamlit UI.
    

