from sqlalchemy import Column, String, Numeric, DateTime, Boolean, Integer, Text, Enum, ForeignKey
from sqlalchemy.sql import func
from src.database import Base
import enum

class TradeStatus(enum.Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    EXCEPTION = "EXCEPTION"

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    uti = Column(String(100), unique=True, nullable=False, index=True)   # UTI bleibt Pflicht
    reporting_counterparty = Column(String(50), nullable=True)   # geändert
    counterparty = Column(String(50), nullable=True)             # geändert
    trade_date = Column(DateTime, nullable=True)                 # geändert
    notional = Column(Numeric(20, 2), nullable=True)             # geändert
    product_type = Column(String(50), nullable=True)             # geändert
    status = Column(Enum(TradeStatus), default=TradeStatus.PENDING)
    ingested_at = Column(DateTime, server_default=func.now())
    reporting_due_date = Column(DateTime, nullable=True)         # optional
    hash_key = Column(String(64), nullable=True)                 # optional

class ValidationRule(enum.Enum):
    MISSING_FIELD = "MISSING_FIELD"
    DUPLICATE_TRADE = "DUPLICATE_TRADE"
    UTI_FORMAT = "UTI_FORMAT"
    REPORTING_COMPLETENESS = "REPORTING_COMPLETENESS"
    RECONCILIATION_MISMATCH = "RECONCILIATION_MISMATCH"

class ValidationResult(Base):
    __tablename__ = "validation_results"
    
    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False)
    rule_type = Column(Enum(ValidationRule), nullable=False)
    passed = Column(Boolean, nullable=False)
    message = Column(Text)
    checked_at = Column(DateTime, server_default=func.now())

class ExceptionLog(Base):
    __tablename__ = "exceptions"
    
    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, ForeignKey("trades.id"))
    rule_type = Column(Enum(ValidationRule))
    description = Column(Text)
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime)