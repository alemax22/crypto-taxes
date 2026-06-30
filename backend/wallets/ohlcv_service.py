#!/usr/bin/env python3

import logging
import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

import pandas as pd
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    OHLCV_DEFAULT_ASSETS,
    OHLCV_INITIAL_LOAD_START_DATE,
    OHLCV_INTERVAL_MINUTES,
    RESAMPLING_INTERVAL_IN_SECONDS,
)
from wallets.ohlcv_repository import PostgresOHLCVRepository

logger = logging.getLogger(__name__)

KRAKEN_BASE_URL = "https://api.kraken.com"
KRAKEN_OHLC_MAX_CANDLES = 720
KRAKEN_REQUEST_DELAY = 2.0  # seconds between Kraken API calls


class OHLCVService:
    """
    Manages OHLCV candlestick data sourced from the Kraken public API.

    Supports two modes:
    - Initial historical backfill: paginates from OHLCV_INITIAL_LOAD_START_DATE
      (first time data is requested for an asset).
    - Progressive update: fetches only candles newer than the latest stored timestamp.

    Both are handled automatically by load() based on what is already in the database.
    """

    _ASSET_NAME_MAP = {
        "ZEUR": "EUR",
        "XBT": "BTC",
        "XXBT": "BTC",
        "XETH": "ETH",
        "XXRP": "XRP",
    }

    def __init__(self, repository: Optional[PostgresOHLCVRepository] = None):
        self._repository = repository or PostgresOHLCVRepository()

    def _normalize_asset_name(self, name: str) -> str:
        name = name.split(".")[0].split("21")[0]
        return self._ASSET_NAME_MAP.get(name, name)

    def _get_tradable_asset_matrix(self) -> pd.DataFrame:
        """
        Fetch all tradable pairs from Kraken and return a DataFrame indexed by
        (base_asset, quote_asset) with columns [index, altname, wsname].
        'index' is the Kraken internal pair key used to read the OHLC response;
        'altname' is the human-readable name used in the query parameter.
        """
        resp = requests.get(f"{KRAKEN_BASE_URL}/0/public/AssetPairs", timeout=30)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data["result"]).transpose()
        df = df[["base", "quote", "altname", "wsname"]].copy()
        df["base"] = df["base"].apply(self._normalize_asset_name)
        df["quote"] = df["quote"].apply(self._normalize_asset_name)
        df = df.reset_index(drop=False, names="index").set_index(["base", "quote"])

        # Handle token migrations: MATIC was renamed to POL 1:1
        custom_idx = pd.MultiIndex.from_tuples([("MATIC", "EUR")], names=["base", "quote"])
        custom_df = pd.DataFrame(
            [{"index": "POLEUR", "altname": "POLEUR", "wsname": "POL/EUR"}],
            index=custom_idx,
        )
        return pd.concat([df, custom_df])

    def _fetch_ohlcv_page(
        self, query_pair: str, result_key: str, since: int
    ) -> tuple[List[dict], Optional[int]]:
        """
        Fetch one page of daily OHLCV candles from Kraken starting at `since`.
        Returns (records, last_valid_timestamp).  Returns ([], None) on error.
        """
        url = (
            f"{KRAKEN_BASE_URL}/0/public/OHLC"
            f"?pair={query_pair}&interval={OHLCV_INTERVAL_MINUTES}&since={since}"
        )
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if data["error"]:
            logger.error(f"Kraken OHLC error for {query_pair}: {data['error']}")
            return [], None

        last_ts: int = data["result"]["last"]
        records = [
            {
                "timestamp": int(row[0]),
                "open": str(row[1]),
                "high": str(row[2]),
                "low": str(row[3]),
                "close": str(row[4]),
                "vwap": str(row[5]),
                "volume": str(row[6]),
            }
            for row in data["result"][result_key]
            if int(row[0]) <= last_ts
        ]
        return records, last_ts

    def _load_asset(
        self,
        asset: str,
        reference_fiat: str,
        tradable_df: pd.DataFrame,
        since: int,
    ) -> Dict:
        """
        Paginate through Kraken OHLCV data from `since` to the present,
        upserting every page into the repository as it arrives.
        """
        if (asset, reference_fiat) not in tradable_df.index:
            logger.warning(f"No trading pair {asset}/{reference_fiat} on Kraken, skipping")
            return {"asset": asset, "status": "skipped", "records_saved": 0}

        pair_data = tradable_df.loc[asset, reference_fiat]
        if isinstance(pair_data, pd.DataFrame):
            pair_data = pair_data.iloc[0]
        query_pair = pair_data["altname"]
        result_key = pair_data["index"]
        total_saved = 0

        while True:
            try:
                raw_records, last_ts = self._fetch_ohlcv_page(query_pair, result_key, since)
            except Exception as e:
                logger.error(f"Error fetching OHLCV page for {asset}: {e}")
                return {"asset": asset, "status": "error", "records_saved": total_saved}

            if last_ts is None:
                return {"asset": asset, "status": "error", "records_saved": total_saved}

            if raw_records:
                db_records = [
                    {
                        "asset": asset,
                        "reference_fiat": reference_fiat,
                        "interval_minutes": OHLCV_INTERVAL_MINUTES,
                        **r,
                    }
                    for r in raw_records
                ]
                saved = self._repository.upsert_records(db_records)
                total_saved += saved
                logger.info(f"{asset}: stored {saved} candles (cumulative {total_saved})")

            # Fewer than max candles returned means we have reached the current end
            if len(raw_records) < KRAKEN_OHLC_MAX_CANDLES:
                break

            since = raw_records[-1]["timestamp"]
            time.sleep(KRAKEN_REQUEST_DELAY)

        return {"asset": asset, "status": "ok", "records_saved": total_saved}

    def load(self, assets: List[str], reference_fiat: str) -> Dict[str, Dict]:
        """
        Load OHLCV data for the given assets.

        For each asset the service checks the most recent candle stored in the database:
        - No data → full historical backfill starting from OHLCV_INITIAL_LOAD_START_DATE.
        - Data present but stale (older than 2 intervals) → progressive fetch from latest timestamp.
        - Data present and fresh → skip.
        """
        tradable_df = self._get_tradable_asset_matrix()
        results: Dict[str, Dict] = {}
        min_update_interval = RESAMPLING_INTERVAL_IN_SECONDS * 2

        for asset in assets:
            latest_ts = self._repository.get_latest_timestamp(
                asset, reference_fiat, OHLCV_INTERVAL_MINUTES
            )
            current_ts = int(datetime.now(timezone.utc).timestamp())

            if latest_ts is not None and (current_ts - latest_ts) < min_update_interval:
                logger.info(f"{asset}: data is up-to-date, skipping")
                results[asset] = {"asset": asset, "status": "up_to_date", "records_saved": 0}
                continue

            if latest_ts is None:
                since = int(
                    OHLCV_INITIAL_LOAD_START_DATE.replace(tzinfo=timezone.utc).timestamp()
                )
                logger.info(
                    f"{asset}: no data found, starting historical load from "
                    f"{OHLCV_INITIAL_LOAD_START_DATE.date()}"
                )
            else:
                since = latest_ts
                logger.info(
                    f"{asset}: progressive update from "
                    f"{datetime.fromtimestamp(latest_ts, tz=timezone.utc).date()}"
                )

            results[asset] = self._load_asset(asset, reference_fiat, tradable_df, since)
            time.sleep(KRAKEN_REQUEST_DELAY)

        return results

    def get_price_dataframe(
        self,
        assets: List[str],
        reference_fiat: str,
        start_ts: int,
        end_ts: int,
    ) -> pd.DataFrame:
        """
        Return a DataFrame with columns [asset, timestamp, price] for the given time range.
        Used by KrakenWallet to assign fiat prices to transactions.
        """
        frames = []
        for asset in assets:
            df = self._repository.get_ohlcv(
                asset, reference_fiat, start_ts, end_ts, OHLCV_INTERVAL_MINUTES
            )
            if not df.empty:
                df = df[["asset", "timestamp", "close"]].rename(columns={"close": "price"})
                frames.append(df)
        if not frames:
            return pd.DataFrame(columns=["asset", "timestamp", "price"])
        result = pd.concat(frames, ignore_index=True)
        result["price"] = result["price"].apply(lambda v: Decimal(str(v)))
        return result