import pandas as pd
import numpy as np
import random
import hashlib
from datetime import datetime, timedelta
from faker import Faker  # optional: pip install faker

fake = Faker()
Faker.seed(42)
np.random.seed(42)
random.seed(42)

# ==================== KONFIGURATION ====================
NUM_TRADES = 150_000          # 150.000 Trades – groß, aber handhabbar
NUM_EXTERNAL = 145_000        # Externer Report – etwas weniger für Abweichungen
DUPLICATE_RATE = 0.03         # 3% Duplikate
MISSING_FIELD_RATE = 0.02     # 2% fehlende Pflichtfelder
INVALID_UTI_RATE = 0.015      # 1.5% ungültige UTI-Formate
RECONCILIATION_MISMATCH_RATE = 0.04  # 4% Abweichungen zum externen Report
OUTPUT_PATH_TRADES = "data/large_trades.csv"
OUTPUT_PATH_EXTERNAL = "data/large_external_reports.csv"

# ==================== HELPER FUNKTIONEN ====================
def random_date(start, end):
    """Zufallsdatum zwischen start und end"""
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

def generate_valid_uti(counter, prefix="UTI"):
    """Gültige UTI (16-52 Zeichen, alphanumerisch, Grossbuchstaben)"""
    suffix = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=30))
    return f"{prefix}{counter:08d}{suffix[:20]}"

def generate_invalid_uti():
    """Ungültige UTI – zu kurz, Sonderzeichen, Kleinbuchstaben etc."""
    invalid_types = [
        lambda: "SHORT",                           # zu kurz
        lambda: "uti-with-lowercase-12345",        # Kleinbuchstaben + Bindestrich
        lambda: "123456789012345678901234567890123456789012345678901234567890", # zu lang (über 52)
        lambda: "UTI$pecial%Chars!",               # Sonderzeichen
        lambda: "",                                 # leer
        lambda: None                                # None
    ]
    return random.choice(invalid_types)()

def maybe_missing_field(value, rate):
    """Setzt Wert auf None mit Wahrscheinlichkeit rate"""
    if random.random() < rate:
        return None
    return value

# ==================== GENERIERUNG DER TRADES ====================
print(f"Generiere {NUM_TRADES} Trades...")

trade_data = []
base_date = datetime(2024, 1, 1)
end_date = datetime(2025, 6, 1)
counterparties = ["GoldmanSachs", "JPMorgan", "DeutscheBank", "BNPParibas", "HSBC", "UBS", "CreditSuisse", "BankofAmerica", "Citigroup", "MorganStanley"]
clients = [f"Client_{i}" for i in range(1, 501)]  # 500 verschiedene Clients
product_types = ["IRS", "CDS", "FXForward", "EquitySwap", "CommoditySwap", "Bond", "Repo"]

duplicate_map = {}  # UTI -> erste Trade-ID für spätere Duplikate

for i in range(1, NUM_TRADES + 1):
    # Basis-Trade-Daten
    is_duplicate = random.random() < DUPLICATE_RATE and len(duplicate_map) > 0
    if is_duplicate and duplicate_map:
        original_uti = random.choice(list(duplicate_map.keys()))
        uti = original_uti
        trade_date = duplicate_map[original_uti]["trade_date"]
        counterparty = duplicate_map[original_uti]["counterparty"]
        notional = duplicate_map[original_uti]["notional"]
        product_type = duplicate_map[original_uti]["product_type"]
    else:
        uti = generate_valid_uti(i)
        trade_date = random_date(base_date, end_date)
        counterparty = random.choice(clients)
        notional = round(random.uniform(10000, 10_000_000), 2)
        product_type = random.choice(product_types)
        if not is_duplicate:
            duplicate_map[uti] = {
                "trade_date": trade_date,
                "counterparty": counterparty,
                "notional": notional,
                "product_type": product_type
            }
    
    # Fehlerhafte UTIs überschreiben
    if random.random() < INVALID_UTI_RATE:
        uti = generate_invalid_uti()
    
    # Pflichtfelder mit Fehlern versehen
    reporting_counterparty = maybe_missing_field(random.choice(counterparties), MISSING_FIELD_RATE)
    counterparty_field = maybe_missing_field(counterparty, MISSING_FIELD_RATE)
    trade_date_field = maybe_missing_field(trade_date, MISSING_FIELD_RATE)
    notional_field = maybe_missing_field(notional, MISSING_FIELD_RATE)
    product_type_field = maybe_missing_field(product_type, MISSING_FIELD_RATE)
    
    trade_data.append({
        "uti": uti,
        "reporting_counterparty": reporting_counterparty,
        "counterparty": counterparty_field,
        "trade_date": trade_date_field,
        "notional": notional_field,
        "product_type": product_type_field
    })
    
    if i % 10000 == 0:
        print(f"  ... {i} Trades generiert")

trades_df = pd.DataFrame(trade_data)

# ==================== EXTERNEN REPORT GENERIEREN ====================
print(f"\nGeneriere externen Report mit {NUM_EXTERNAL} Einträgen...")

# Basis: eindeutige UTIs aus den Trades (ohne Duplikate)
unique_trades = trades_df.drop_duplicates(subset=["uti"]).copy()
# Entferne Trades mit None-UTI (können nicht abgeglichen werden)
unique_trades = unique_trades[unique_trades["uti"].notna()]
sample_utis = unique_trades["uti"].sample(min(NUM_EXTERNAL, len(unique_trades)), random_state=42)

external_records = []
for uti in sample_utis:
    original_row = unique_trades[unique_trades["uti"] == uti].iloc[0]
    reported_notional = original_row["notional"]
    reported_counterparty = original_row["counterparty"]
    
    # Reconciliation-Mismatch einbauen
    if random.random() < RECONCILIATION_MISMATCH_RATE:
        # Ändere Notional oder Counterparty
        if random.random() < 0.5:
            reported_notional = reported_notional * random.uniform(0.8, 1.2) if reported_notional else 1000000
        else:
            reported_counterparty = f"Wrong_{random.choice(clients)}"
    
    # Falls Originalwerte None waren, müssen wir sie durch sinnvolle Defaults ersetzen
    if pd.isna(reported_notional):
        reported_notional = 1000000
    if pd.isna(reported_counterparty):
        reported_counterparty = "Unknown_Client"
    
    external_records.append({
        "uti": uti,
        "reported_notional": round(reported_notional, 2),
        "reported_counterparty": reported_counterparty
    })

external_df = pd.DataFrame(external_records)

# ==================== SPEICHERN ====================
trades_df.to_csv(OUTPUT_PATH_TRADES, index=False)
external_df.to_csv(OUTPUT_PATH_EXTERNAL, index=False)

print(f"\n✅ Fertig!")
print(f"   - Trades: {len(trades_df):,} Zeilen → {OUTPUT_PATH_TRADES}")
print(f"   - Externer Report: {len(external_df):,} Zeilen → {OUTPUT_PATH_EXTERNAL}")

# Kleine Statistikpip install faker
missing_fields = trades_df.isna().sum().sum()
duplicate_utis = trades_df['uti'].duplicated().sum()
invalid_utis = trades_df['uti'].apply(lambda x: not isinstance(x, str) or len(str(x)) < 16 or len(str(x)) > 52 or not str(x).isalnum() or not str(x).isupper()).sum()
print(f"\n📊 Statistiken:")
print(f"   - Fehlende Felder (gesamt): {missing_fields}")
print(f"   - Duplikate (UTI): {duplicate_utis}")
print(f"   - Ungültige UTIs: {invalid_utis}")