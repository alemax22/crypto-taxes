#!/usr/bin/env python3

import logging
import os
import sys
from decimal import Decimal
from typing import List, Optional

import pandas as pd
from sqlalchemy import Column, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import insert

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import Base, SessionLocal, SCHEMA_NAME, engine

logger = logging.getLogger(__name__)


class OHLCVDataORM(Base):
    __tablename__ = "ohlcv_data"
    __table_args__ = (
        UniqueConstraint(
            "asset", "reference_fiat", "timestamp", "interval_minutes",
            name="uq_ohlcv",
        ),
        {"schema": SCHEMA_NAME},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset = Column(String(32), nullable=False, index=True)
    reference_fiat = Column(String(8), nullable=False, index=True)
    timestamp = Column(Integer, nullable=False, index=True)
    interval_minutes = Column(Integer, nullable=False)
    open = Column(Numeric(20, 8), nullable=False)
    high = Column(Numeric(20, 8), nullable=False)
    low = Column(Numeric(20, 8), nullable=False)
    close = Column(Numeric(20, 8), nullable=False)
    vwap = Column(Numeric(20, 8), nullable=True)
    volume = Column(Numeric(30, 8), nullable=True)


class PostgresOHLCVRepository:
    """PostgreSQL-backed persistence for OHLCV candlestick data."""

    def __init__(self):
        try:
            with engine.begin() as conn:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA_NAME}"'))
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            logger.error(f"Failed to initialise OHLCV table: {e}")

    def upsert_records(self, records: List[dict]) -> int:
        """Insert or update a batch of OHLCV records. Returns number of records processed."""
        if not records:
            return 0
        try:
            with SessionLocal() as session:
                stmt = insert(OHLCVDataORM).values(records)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_ohlcv",
                    set_={
                        "open": stmt.excluded.open,
                        "high": stmt.excluded.high,
                        "low": stmt.excluded.low,
                        "close": stmt.excluded.close,
                        "vwap": stmt.excluded.vwap,
                        "volume": stmt.excluded.volume,
                    },
                )
                session.execute(stmt)
                session.commit()
                return len(records)
        except Exception as e:
            logger.error(f"DB error upserting OHLCV records: {e}")
            return 0

    def get_latest_timestamp(
        self, asset: str, reference_fiat: str, interval_minutes: int
    ) -> Optional[int]:
        """Return the Unix timestamp of the most recent candle for the given asset, or None."""
        try:
            with SessionLocal() as session:
                row = (
                    session.query(OHLCVDataORM.timestamp)
                    .filter(
                        OHLCVDataORM.asset == asset,
                        OHLCVDataORM.reference_fiat == reference_fiat,
                        OHLCVDataORM.interval_minutes == interval_minutes,
                    )
                    .order_by(OHLCVDataORM.timestamp.desc())
                    .first()
                )
                return row[0] if row else None
        except Exception as e:
            logger.error(f"DB error getting latest OHLCV timestamp for {asset}: {e}")
            return None

    def get_ohlcv(
        self,
        asset: str,
        reference_fiat: str,
        start_ts: int,
        end_ts: int,
        interval_minutes: int,
    ) -> pd.DataFrame:
        """Return a DataFrame with columns [asset, timestamp, open, high, low, close, vwap, volume]."""
        try:
            with SessionLocal() as session:
                rows = (
                    session.query(OHLCVDataORM)
                    .filter(
                        OHLCVDataORM.asset == asset,
                        OHLCVDataORM.reference_fiat == reference_fiat,
                        OHLCVDataORM.interval_minutes == interval_minutes,
                        OHLCVDataORM.timestamp >= start_ts,
                        OHLCVDataORM.timestamp <= end_ts,
                    )
                    .order_by(OHLCVDataORM.timestamp)
                    .all()
                )
                if not rows:
                    return pd.DataFrame()
                return pd.DataFrame(
                    [
                        {
                            "asset": r.asset,
                            "timestamp": r.timestamp,
                            "open": Decimal(str(r.open)),
                            "high": Decimal(str(r.high)),
                            "low": Decimal(str(r.low)),
                            "close": Decimal(str(r.close)),
                            "vwap": Decimal(str(r.vwap)) if r.vwap else None,
                            "volume": Decimal(str(r.volume)) if r.volume else None,
                        }
                        for r in rows
                    ]
                )
        except Exception as e:
            logger.error(f"DB error fetching OHLCV for {asset}: {e}")
            return pd.DataFrame()

    def get_all_assets(self, reference_fiat: str, interval_minutes: int) -> List[str]:
        """Return the distinct list of assets that have data stored."""
        try:
            with SessionLocal() as session:
                rows = (
                    session.query(OHLCVDataORM.asset)
                    .filter(
                        OHLCVDataORM.reference_fiat == reference_fiat,
                        OHLCVDataORM.interval_minutes == interval_minutes,
                    )
                    .distinct()
                    .all()
                )
                return [r[0] for r in rows]
        except Exception as e:
            logger.error(f"DB error listing OHLCV assets: {e}")
            return []