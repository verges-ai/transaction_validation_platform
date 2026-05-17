from src.database import SessionLocal
from src.ingestion import ingest_trades_from_csv_chunked

db = SessionLocal()
ingest_trades_from_csv_chunked(db, "data/large_trades.csv", chunksize=20000)
db.close()