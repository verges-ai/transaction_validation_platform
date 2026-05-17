# dashboard/app.py
import streamlit as st
import plotly.express as px
import pandas as pd
from sqlalchemy import create_engine, text
from src.config import Config

st.set_page_config(page_title="Transaction Reporting Validation", layout="wide")
st.title("📊 Transaction Reporting Validation Platform")

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

@st.cache_data(ttl=60)
def load_metrics():
    with engine.connect() as conn:
        trades = pd.read_sql("SELECT * FROM trades", conn)
        validations = pd.read_sql("SELECT * FROM validation_results", conn)
        exceptions = pd.read_sql("SELECT * FROM exceptions", conn)
    return trades, validations, exceptions

trades_df, validations_df, exceptions_df = load_metrics()

# ==================== KPIs ====================
col1, col2, col3, col4 = st.columns(4)
open_exc = len(exceptions_df[exceptions_df['resolved'] == False])
col1.metric("Total Trades", len(trades_df))
col2.metric("Total Exceptions", len(exceptions_df))
col3.metric("Open Exceptions", open_exc)
pass_rate = (validations_df['passed'].sum() / len(validations_df)) * 100 if len(validations_df) > 0 else 0
col4.metric("Validation Pass Rate", f"{pass_rate:.1f}%")

# ==================== Validierungsdiagramm ====================
st.subheader("Validation Results by Rule")
rule_pass = validations_df.groupby('rule_type')['passed'].mean().reset_index()
fig = px.bar(rule_pass, x='rule_type', y='passed', title="Pass Rate per Rule")
st.plotly_chart(fig, use_container_width=True)

# ==================== Aktive Exceptions (nur unerledigte) ====================
st.subheader("🔴 Active Exceptions (Unresolved)")
st.caption("💡 Die Spalte 'id' ist die Exception-ID – diese gibst du unten im Formular ein, um einen Fehler als erledigt zu markieren.")

# 1. Duplikate
dupes = exceptions_df[(exceptions_df['rule_type'] == 'DUPLICATE_TRADE') & (exceptions_df['resolved'] == False)]
if not dupes.empty:
    st.warning(f"{len(dupes)} unresolved duplicate trades")
    st.dataframe(
        dupes[['id', 'description']],
        hide_index=True,
        use_container_width=True
    )
else:
    st.success("No unresolved duplicate trades")

# 2. Reconciliation-Mismatches
rec = exceptions_df[(exceptions_df['rule_type'] == 'RECONCILIATION_MISMATCH') & (exceptions_df['resolved'] == False)]
if not rec.empty:
    st.error(f"{len(rec)} unresolved reconciliation mismatches")
    st.dataframe(
        rec[['id', 'description']],
        hide_index=True,
        use_container_width=True
    )
else:
    st.success("No unresolved reconciliation mismatches")

# 3. Fehlende Pflichtfelder
missing = exceptions_df[(exceptions_df['rule_type'] == 'MISSING_FIELD') & (exceptions_df['resolved'] == False)]
if not missing.empty:
    st.warning(f"{len(missing)} unresolved missing fields")
    st.dataframe(
        missing[['id', 'description']],
        hide_index=True,
        use_container_width=True
    )
else:
    st.success("No missing field exceptions")

# 4. Verspätete Meldungen
late = exceptions_df[(exceptions_df['rule_type'] == 'REPORTING_COMPLETENESS') & (exceptions_df['resolved'] == False)]
if not late.empty:
    st.warning(f"{len(late)} late trades not yet resolved")
    st.dataframe(
        late[['id', 'description']],
        hide_index=True,
        use_container_width=True
    )
else:
    st.success("All late trades resolved")

# ==================== Exception resolution form ====================
st.subheader("🔧 Mark an Exception as Resolved")
with st.form("resolve_exception"):
    exc_id = st.number_input("Exception ID (from the tables above)", min_value=1, step=1)
    if st.form_submit_button("Mark as Resolved"):
        import psycopg2
        conn = psycopg2.connect(Config.SQLALCHEMY_DATABASE_URI)
        cur = conn.cursor()
        cur.execute(
            "UPDATE exceptions SET resolved = True, resolved_at = NOW() WHERE id = %s AND resolved = False",
            (exc_id,)
        )
        conn.commit()
        updated = cur.rowcount
        cur.close()
        conn.close()
        if updated:
            st.success(f"✅ Exception {exc_id} marked as resolved at {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
            st.rerun()
        else:
            st.error(f"❌ Exception {exc_id} not found or already resolved.")

# ==================== Historie (erledigte Exceptions der letzten 7 Tage) ====================
st.subheader("📜 History – Resolved Exceptions (Last 7 days)")
resolved = exceptions_df[(exceptions_df['resolved'] == True) & (exceptions_df['resolved_at'].notna())]
if not resolved.empty:
    resolved['resolved_at'] = pd.to_datetime(resolved['resolved_at'])
    last_7_days = resolved[resolved['resolved_at'] > pd.Timestamp.now() - pd.Timedelta(days=7)]
    if not last_7_days.empty:
        st.dataframe(
            last_7_days[['id', 'rule_type', 'description', 'resolved_at']],
            hide_index=True,
            use_container_width=True
        )
        st.caption(f"Showing {len(last_7_days)} resolved exceptions from the last 7 days.")
    else:
        st.info("No exceptions resolved in the last 7 days.")
else:
    st.info("No resolved exceptions yet. Use the form above to mark an exception as resolved.")