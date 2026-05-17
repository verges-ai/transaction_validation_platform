# src/ingestion.py
import pandas as pd
import hashlib
from sqlalchemy.orm import Session
from src.models import Trade, TradeStatus
from datetime import datetime, timedelta

def compute_hash_key(row):
    """Deterministischer Hash für Duplikaterkennung"""
    if pd.isna(row['uti']) or pd.isna(row['trade_date']) or pd.isna(row['counterparty']):
        return None
    data = f"{row['uti']}|{row['trade_date']}|{row['counterparty']}"
    return hashlib.sha256(data.encode()).hexdigest()

def ingest_trades_from_csv_chunked(db: Session, csv_path: str, chunksize=10000):
    """
    Lädt große CSV-Datei in Chunks, um Speicher zu sparen.
    Entfernt Duplikate innerhalb eines Chunks vor dem Einfügen.
    """
    total_ingested = 0
    for chunk in pd.read_csv(csv_path, chunksize=chunksize):
        # Datum konvertieren
        chunk['trade_date'] = pd.to_datetime(chunk['trade_date'], errors='coerce')
        # Hash Key berechnen
        chunk['hash_key'] = chunk.apply(compute_hash_key, axis=1)
        # Reporting due date (T+1)
        chunk['reporting_due_date'] = chunk['trade_date'] + timedelta(days=1)
        
        # Entferne Duplikate innerhalb des Chunks (behalte ersten Vorkommen)
        chunk = chunk.drop_duplicates(subset=['uti'], keep='first')
        
        trades_to_add = []
        for _, row in chunk.iterrows():
            # Überspringe Zeilen ohne UTI (können wir nicht eindeutig zuordnen)
            if pd.isna(row['uti']):
                continue
            
            # Prüfe, ob die UTI bereits in der Datenbank existiert
            existing = db.query(Trade).filter_by(uti=row['uti']).first()
            if not existing:
                trade = Trade(
                    uti=row['uti'],
                    reporting_counterparty=row['reporting_counterparty'] if pd.notna(row['reporting_counterparty']) else None,
                    counterparty=row['counterparty'] if pd.notna(row['counterparty']) else None,
                    trade_date=row['trade_date'] if pd.notna(row['trade_date']) else None,
                    notional=row['notional'] if pd.notna(row['notional']) else None,
                    product_type=row['product_type'] if pd.notna(row['product_type']) else None,
                    status=TradeStatus.PENDING,
                    reporting_due_date=row['reporting_due_date'] if pd.notna(row['reporting_due_date']) else None,
                    hash_key=row['hash_key']
                )
                trades_to_add.append(trade)
        
        if trades_to_add:
            db.bulk_save_objects(trades_to_add)
            db.commit()
            total_ingested += len(trades_to_add)
        print(f"Chunk verarbeitet, {len(trades_to_add)} neue Trades hinzugefügt. Gesamt: {total_ingested}")
    
    print(f"✅ Ingestion abgeschlossen. Insgesamt {total_ingested} Trades importiert.")