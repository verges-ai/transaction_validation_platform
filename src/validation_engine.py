# src/validation_engine.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.models import Trade, ValidationResult, ValidationRule, ExceptionLog, TradeStatus
import re
from datetime import datetime

def validate_missing_fields_batch(db: Session, trade_ids):
    """Identifiziert Trades mit fehlenden Pflichtfeldern (ein SQL-Aufruf)"""
    trades = db.query(Trade).filter(Trade.id.in_(trade_ids)).all()
    missing_list = []
    for trade in trades:
        missing = []
        if not trade.uti: missing.append("uti")
        if not trade.reporting_counterparty: missing.append("reporting_counterparty")
        if not trade.counterparty: missing.append("counterparty")
        if not trade.trade_date: missing.append("trade_date")
        if not trade.notional: missing.append("notional")
        if not trade.product_type: missing.append("product_type")
        if missing:
            missing_list.append((trade, missing))
    # Ergebnisse speichern
    for trade, missing in missing_list:
        msg = f"Missing fields: {', '.join(missing)}"
        vr = ValidationResult(trade_id=trade.id, rule_type=ValidationRule.MISSING_FIELD, passed=False, message=msg)
        db.add(vr)
        exc = ExceptionLog(trade_id=trade.id, rule_type=ValidationRule.MISSING_FIELD, description=msg)
        db.add(exc)
        trade.status = TradeStatus.EXCEPTION
    db.commit()
    return len(missing_list)

def validate_duplicates_batch(db: Session, trade_ids):
    """Findet Duplikate basierend auf hash_key (effizient mit GROUP BY)"""
    from sqlalchemy import func
    # Finde alle hash_keys, die mehr als einmal vorkommen
    dup_hashes = db.query(Trade.hash_key, func.count(Trade.id).label('cnt'))\
                   .filter(Trade.hash_key.isnot(None), Trade.id.in_(trade_ids))\
                   .group_by(Trade.hash_key).having(func.count(Trade.id) > 1).all()
    duplicate_count = 0
    for hkey, _ in dup_hashes:
        dup_trades = db.query(Trade).filter(Trade.hash_key == hkey).order_by(Trade.id).all()
        # Erste Trade als Original, alle weiteren als Duplikate markieren
        for i, trade in enumerate(dup_trades):
            if i == 0:
                continue  # Original
            msg = f"Duplicate of trade ID {dup_trades[0].id}"
            vr = ValidationResult(trade_id=trade.id, rule_type=ValidationRule.DUPLICATE_TRADE, passed=False, message=msg)
            db.add(vr)
            exc = ExceptionLog(trade_id=trade.id, rule_type=ValidationRule.DUPLICATE_TRADE, description=msg)
            db.add(exc)
            trade.status = TradeStatus.EXCEPTION
            duplicate_count += 1
    db.commit()
    return duplicate_count

def validate_uti_format_batch(db: Session, trade_ids):
    pattern = re.compile(r'^[A-Z0-9]{16,52}$')
    trades = db.query(Trade).filter(Trade.id.in_(trade_ids), Trade.uti.isnot(None)).all()
    invalid = 0
    for trade in trades:
        if not pattern.match(trade.uti):
            msg = f"Invalid UTI format: {trade.uti}"
            vr = ValidationResult(trade_id=trade.id, rule_type=ValidationRule.UTI_FORMAT, passed=False, message=msg)
            db.add(vr)
            exc = ExceptionLog(trade_id=trade.id, rule_type=ValidationRule.UTI_FORMAT, description=msg)
            db.add(exc)
            trade.status = TradeStatus.EXCEPTION
            invalid += 1
    db.commit()
    return invalid

def run_all_validations(db: Session, batch_size=5000):
    """Validiert Trades in Batches, um Speicher und Zeit zu sparen"""
    # Alle Trade-IDs holen (nur IDs, nicht ganze Objekte)
    all_ids = [id for (id,) in db.query(Trade.id).filter(Trade.status == TradeStatus.PENDING).all()]
    print(f"Starte Validierung für {len(all_ids)} Trades im Batch-Modus...")
    
    total_missing = 0
    total_dupes = 0
    total_uti = 0
    
    for i in range(0, len(all_ids), batch_size):
        batch_ids = all_ids[i:i+batch_size]
        missing = validate_missing_fields_batch(db, batch_ids)
        dupes = validate_duplicates_batch(db, batch_ids)
        uti = validate_uti_format_batch(db, batch_ids)
        total_missing += missing
        total_dupes += dupes
        total_uti += uti
        print(f"Batch {i//batch_size + 1}: {len(batch_ids)} Trades – Missing: {missing}, Dupes: {dupes}, UTI: {uti}")
    
    # Trades ohne Exception auf VALIDATED setzen
    db.query(Trade).filter(Trade.status == TradeStatus.PENDING).update({Trade.status: TradeStatus.VALIDATED})
    db.commit()
    
    print(f"\n✅ Validierung abgeschlossen.")
    print(f"   - Fehlende Felder: {total_missing}")
    print(f"   - Duplikate: {total_dupes}")
    print(f"   - Ungültige UTIs: {total_uti}")
    print(f"   - Gültige Trades: {len(all_ids) - total_missing - total_dupes - total_uti}")