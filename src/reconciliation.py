# src/reconciliation.py
import pandas as pd
from sqlalchemy.orm import Session
from src.models import Trade, ValidationResult, ValidationRule, ExceptionLog, TradeStatus
from datetime import datetime

def reconcile_with_external_report(db: Session, external_csv_path: str):
    """
    Reconciliation check: compare internal trades against an external report (e.g., TRADE repo)
    Handles None values gracefully.
    """
    ext_df = pd.read_csv(external_csv_path)  # expects columns: uti, reported_notional, reported_counterparty
    ext_dict = ext_df.set_index('uti').to_dict(orient='index')
    
    trades = db.query(Trade).all()
    mismatches = 0
    for trade in trades:
        # Wenn trade.uti None ist, können wir nicht abgleichen
        if trade.uti is None or trade.uti not in ext_dict:
            # Optional: als Exception loggen (UTI fehlt oder nicht im externen Report)
            msg = f"Trade UTI {trade.uti} not found in external report" if trade.uti else "Trade has no UTI, cannot reconcile"
            result = ValidationResult(
                trade_id=trade.id,
                rule_type=ValidationRule.RECONCILIATION_MISMATCH,
                passed=False,
                message=msg
            )
            db.add(result)
            exception = ExceptionLog(
                trade_id=trade.id,
                rule_type=ValidationRule.RECONCILIATION_MISMATCH,
                description=msg
            )
            db.add(exception)
            mismatches += 1
            continue
        
        ext = ext_dict[trade.uti]
        mismatched_fields = []
        
        # Notional vergleichen (None vermeiden)
        internal_notional = float(trade.notional) if trade.notional is not None else None
        external_notional = float(ext.get('reported_notional', 0)) if ext.get('reported_notional') is not None else None
        
        if internal_notional is None and external_notional is not None:
            mismatched_fields.append(f"notional missing internally (external={external_notional})")
        elif internal_notional is not None and external_notional is None:
            mismatched_fields.append(f"notional missing externally (internal={internal_notional})")
        elif internal_notional is not None and external_notional is not None and internal_notional != external_notional:
            mismatched_fields.append(f"notional (internal={internal_notional}, external={external_notional})")
        
        # Counterparty vergleichen (None vermeiden)
        internal_cpty = trade.counterparty
        external_cpty = ext.get('reported_counterparty')
        if internal_cpty is None and external_cpty is not None:
            mismatched_fields.append(f"counterparty missing internally (external={external_cpty})")
        elif internal_cpty is not None and external_cpty is None:
            mismatched_fields.append(f"counterparty missing externally (internal={internal_cpty})")
        elif internal_cpty is not None and external_cpty is not None and internal_cpty != external_cpty:
            mismatched_fields.append(f"counterparty (internal={internal_cpty}, external={external_cpty})")
        
        passed = len(mismatched_fields) == 0
        msg = f"Reconciliation mismatch: {', '.join(mismatched_fields)}" if mismatched_fields else "Reconciliation passed"
        
        result = ValidationResult(
            trade_id=trade.id,
            rule_type=ValidationRule.RECONCILIATION_MISMATCH,
            passed=passed,
            message=msg
        )
        db.add(result)
        if not passed:
            exception = ExceptionLog(
                trade_id=trade.id,
                rule_type=ValidationRule.RECONCILIATION_MISMATCH,
                description=msg
            )
            db.add(exception)
            # Trade status bereits EXCEPTION? Falls nicht, setzen wir es auf EXCEPTION
            if trade.status != TradeStatus.EXCEPTION:
                trade.status = TradeStatus.EXCEPTION
            mismatches += 1
    db.commit()
    print(f"Reconciliation complete. {mismatches} mismatches found.")


def check_reporting_completeness(db: Session):
    """
    Reporting completeness: trades older than reporting due date must be validated/reported.
    Handles None in reporting_due_date.
    """
    now = datetime.utcnow()
    # Nur Trades mit reporting_due_date not None und < now
    late_trades = db.query(Trade).filter(
        Trade.reporting_due_date < now,
        Trade.status != TradeStatus.VALIDATED
    ).all()
    
    for trade in late_trades:
        msg = f"Trade not validated by due date {trade.reporting_due_date}"
        result = ValidationResult(
            trade_id=trade.id,
            rule_type=ValidationRule.REPORTING_COMPLETENESS,
            passed=False,
            message=msg
        )
        db.add(result)
        exception = ExceptionLog(
            trade_id=trade.id,
            rule_type=ValidationRule.REPORTING_COMPLETENESS,
            description=msg
        )
        db.add(exception)
        if trade.status != TradeStatus.EXCEPTION:
            trade.status = TradeStatus.EXCEPTION
    db.commit()
    print(f"Reporting completeness: {len(late_trades)} late trades flagged.")