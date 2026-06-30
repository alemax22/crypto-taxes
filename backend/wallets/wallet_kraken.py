#!/usr/bin/env python3
"""
Kraken Wallet Implementation
Specific implementation for Kraken exchange
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

# Add parent directory to path to import config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    OHLCV_INITIAL_LOAD_START_DATE,
    RESAMPLING_INTERVAL_IN_SECONDS,
    WALLETS_DIR,
)
from wallets.wallet import Wallet
from wallets.wallet_enums import WalletSyncStatus

logger = logging.getLogger(__name__)

EXCEPTION_ASSETS = ["KFEE", "NFT"]
TX_BATCH_SIZE = 50
KRAKEN_SLEEPING_TIME = 4  # seconds after every call to refill the call limit counter


class KrakenWallet(Wallet):
    """
    Kraken exchange wallet implementation.

    This class provides specific functionality for interacting with
    the Kraken exchange API, including transaction synchronization
    and balance retrieval.
    """

    def __init__(
        self,
        name: str,
        id: str,
        reference_fiat: str,
        portfolio_id: str,
        description: str = "",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        is_active: bool = False,
        created_datetime: Optional[datetime] = None,
        updated_datetime: Optional[datetime] = None,
        sync_status: WalletSyncStatus = WalletSyncStatus.NOT_SYNCHRONIZED,
    ):
        """
        Initialize Kraken wallet.

        Args:
            name: Name of the wallet
            id: ID of the wallet
            reference_fiat: Reference fiat currency
            portfolio_id: ID of the portfolio this wallet belongs to
            description: Description of the wallet (optional)
            api_key: Kraken API key (optional)
            api_secret: Kraken API secret (optional)
            is_active: Whether the wallet is active (optional)
            created_datetime: When the wallet was created (optional)
            updated_datetime: Last synchronization/update timestamp (optional)
            sync_status: Status of the synchronization process (optional)
        """
        super().__init__(
            name,
            id,
            reference_fiat,
            portfolio_id,
            description,
            api_key,
            api_secret,
            is_active,
            created_datetime,
            updated_datetime,
            sync_status,
        )

        # Kraken-specific settings
        self.base_url = "https://api.kraken.com"

        # Data file paths
        self.ledger_file = os.path.join(WALLETS_DIR, "kraken_ledger.parquet")
        self.ohlc_file = os.path.join(WALLETS_DIR, "kraken_ohlc.parquet")

        logger.info("Kraken wallet initialized")

    def authenticate(self) -> bool:
        """
        Authenticate with Kraken API.

        Returns:
            bool: True if authentication successful, False otherwise
        """

        self.is_active = False

        try:
            if not self.api_key or not self.api_secret:
                logger.error("Kraken: Missing API credentials")
                return self.is_active

            # Test authentication by getting balance
            test_start_timestamp = int(datetime.now().timestamp())
            ledger_response_json = self._get_ledger(test_start_timestamp, ofs=0)

            if "error" in ledger_response_json and ledger_response_json["error"]:
                logger.error(
                    f"Kraken authentication failed: {ledger_response_json['error']}"
                )
                return self.is_active

            self.is_active = True
            logger.info("Kraken authentication successful")
            return self.is_active

        except Exception as e:
            logger.error(f"Kraken authentication error: {str(e)}")
            return self.is_active

    def _synchronize(
        self, start_date: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Synchronize local data with the remote wallet/exchange.

        This method should:
        1. Fetch transaction data from the exchange
        2. Update local data files
        3. Return synchronization status and metadata

        Args:
            start_date: Start date for data synchronization (YYYY-MM-DD format in GMT timezone)

        Returns:
            bool: True if synchronization was successful, False otherwise
            error: Error message if synchronization failed, None otherwise

        The output dataframe should have the following columns:
        - datetime: datetime
        - transaction_id: str
        - correlation_id: str
        - transaction_type: str
            - deposit:
                - reward
                - deposit
            - trade:
                - crypto -> crypto
                - crypto -> fiat
                - fiat -> crypto
            - withdrawal
            - transfer (from another wallet)
        - asset: str
        - amount: decimal
        - balance: float
        - asset_price_in_reference_fiat: decimal
        - fee: decimal
        - transaction_original_type: str (value coming from the exchange)
        - asset_original_name: str (value coming from the exchange)
        - asset_original_balance: str (value coming from the exchange)

        """
        try:
            self.sync_status = WalletSyncStatus.IN_PROGRESS

            # Check authentication
            if not self.is_active:
                if not self.authenticate():
                    self.sync_status = WalletSyncStatus.FAILED
                    return False, "Authentication failed"

            self._ensure_data_directories()

            # Set default start date if not provided
            if not start_date:
                start_date = "2000-01-01"

            logger.info(f"Starting Kraken synchronization from {start_date}")

            # Fetch transaction data
            new_transactions_count = self._synchronize_transactions_internal(start_date)
            if new_transactions_count == -1:
                self.sync_status = "failed"
                return False, "Error synchronizing transactions"

            # Update last sync timestamp
            self.updated_datetime = datetime.now(timezone.utc)
            self.sync_status = WalletSyncStatus.COMPLETED
            return True, None

        except Exception as e:
            logger.error(f"Kraken synchronization error: {str(e)}")
            self.sync_status = WalletSyncStatus.FAILED
            return False, str(e)

    def _ensure_data_directories(self) -> None:
        """Ensure all necessary data directories exist."""
        os.makedirs(os.path.dirname(self.ledger_file), exist_ok=True)

    def _synchronize_transactions_internal(self, start_date: str) -> int:
        """
        Synchronize transaction data with local storage.

        Args:
            start_date: Start date for transactions

        Returns:
            int: Total number of transactions
        """
        try:
            # Load existing data if available
            existing_df = self._retrieve_local_ledger_data()

            if existing_df.empty:
                start_timestamp = int(
                    datetime.strptime(start_date, "%Y-%m-%d")
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                )
            else:
                start_timestamp = int(existing_df["datetime"].max().timestamp())

            logger.info(
                f"Synchronizing transactions from {datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d %H:%M:%S')} to {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Fetch new data
            new_df = self._retrieve_kraken_ledger_data(start_timestamp)

            if new_df.empty:
                logger.info("No new transactions found")
                return 0

            # Transform to common format
            new_df = self._create_transaction_df_with_common_format(new_df)

            # Merge with existing data
            if not existing_df.empty:
                # Remove duplicates and merge using transaction_id
                combined_df = pd.concat([new_df, existing_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(
                    subset=["transaction_id"], keep="first"
                )
            else:
                combined_df = new_df

            # Save to local file
            self._save_local_ledger_data(combined_df)

            transactions_fetched = len(new_df)
            total_transactions = len(combined_df)
            logger.info(f"Synchronized {transactions_fetched} new transactions")
            logger.info(f"Total transactions: {total_transactions}")

            return total_transactions

        except Exception as e:
            logger.error(f"Error synchronizing transactions: {str(e)}")
            return -1

    def _create_transaction_df_with_common_format(
        self, df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Create a transaction dataframe with common format.

        Transform Kraken API ledger data into the standardized format with only
        the required columns as specified in the synchronize function.

        Args:
            df: DataFrame containing raw Kraken ledger data
            start_date: Start date for transactions

        Returns:
            DataFrame with standardized columns:
            - datetime: datetime
            - transaction_id: str
            - correlation_id: str
            - transaction_type: str
            - asset: str
            - amount: decimal
            - balance: float
            - asset_price_in_reference_fiat: decimal
            - fee: decimal
            - transaction_original_type: str
            - asset_original_name: str
            - asset_original_balance: str
        """

        # Create a copy to avoid modifying the original
        result_df = df.copy()
        result_df = result_df.reset_index(drop=False, names="transaction_id")

        required_columns = [
            "datetime",
            "correlation_id",
            "transaction_id",
            "transaction_type",
            "asset",
            "amount",
            "balance",
            "asset_price_in_reference_fiat",
            "fee",
            "transaction_original_type",
            "asset_original_name",
            "asset_original_balance",
        ]

        result_df["datetime"] = pd.to_datetime(result_df["time"], unit="s")
        result_df["transaction_id"] = result_df["transaction_id"].astype(str)
        result_df["correlation_id"] = result_df["refid"].astype(str)
        result_df["transaction_type"] = result_df["type"].apply(
            self._map_transaction_type
        )
        result_df["asset_original_name"] = result_df["asset"]
        result_df["asset"] = result_df["asset"].apply(self._normalize_asset_name)
        result_df["amount"] = result_df["amount"].apply(self._decimal_from_value)
        result_df["asset_original_balance"] = result_df["balance"]

        # Calculate running balance per asset (sorted by datetime)
        result_df = result_df.sort_values(["asset", "datetime"])
        result_df["temp_amount"] = result_df["amount"].astype(float)
        result_df["temp_fee"] = result_df["fee"].astype(float)
        result_df["temp_amount_without_fee"] = (
            result_df["temp_amount"] - result_df["temp_fee"]
        )
        result_df["balance"] = result_df.groupby("asset")[
            "temp_amount_without_fee"
        ].cumsum()
        result_df["asset_price_in_reference_fiat"] = Decimal("0")
        result_df["fee"] = result_df["fee"].apply(self._decimal_from_value)
        result_df["transaction_original_type"] = result_df["type"]

        result_df = self._get_asset_price_in_reference_fiat(result_df)

        # Return only the required columns
        return result_df[required_columns]

    def _map_transaction_type(self, kraken_type: str) -> str:
        """Map Kraken transaction types to standardized types."""
        type_mapping = {
            # Deposits
            "deposit": "deposit",
            "staking": "reward",  # Staking rewards
            "earn": "reward",  # Earn rewards
            # Trades
            "trade": "trade",
            "margin trade": "trade",
            # Withdrawals
            "withdrawal": "withdrawal",
            "withdraw": "withdrawal",
            # Transfers
            "transfer": "transfer",
            "margin transfer": "transfer",
            # Fees
            "fee": "fee",
            "margin fee": "fee",
            # Other
            "adjustment": "transfer",
            "rollover": "transfer",
            "settled": "transfer",
            "correction": "transfer",
        }
        return type_mapping.get(kraken_type.lower(), "transfer")

    def _normalize_asset_name(self, asset_name: str) -> str:
        asset_name = asset_name.split(".")[0]
        asset_name = asset_name.split("21")[0]
        if asset_name == "ZEUR":
            asset_name = "EUR"
        elif asset_name == "XBT" or asset_name == "XXBT":
            asset_name = "BTC"
        elif asset_name == "XETH":
            asset_name = "ETH"
        elif asset_name == "XXRP":
            asset_name = "XRP"
        return asset_name

    def _get_asset_price_in_reference_fiat(
        self, transactions_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compute asset_price_in_reference_fiat for transactions using OHLC price data.
        """

        result_df = self._compute_asset_price_in_reference_fiat_from_trades(
            transactions_df
        )

        # Get unique assets from transactions for OHLC data
        assets_in_transactions = result_df["asset"].unique().tolist()

        # Fetch OHLC data for price calculations of the asset without price in reference fiat
        ohlc_df = self._get_ohlc_data(
            assets_in_portfolio=assets_in_transactions,
        )

        result_df = self._compute_asset_price_in_reference_fiat_from_ohlc(
            result_df, ohlc_df
        )

        # Assign 1 to the asset_price_in_reference_fiat of the reference asset
        result_df.loc[
            result_df["asset"] == self.reference_fiat, "asset_price_in_reference_fiat"
        ] = Decimal("1")

        # Check that all transactions have a price
        nan_price_mask = result_df["asset_price_in_reference_fiat"].isna()
        zero_price_mask = result_df["asset_price_in_reference_fiat"] == Decimal("0")
        not_exception_mask = ~result_df["asset"].isin(EXCEPTION_ASSETS)
        filter_mask = (nan_price_mask | zero_price_mask) & not_exception_mask
        if filter_mask.any():
            logger.error("There are transactions without a price:")
            logger.error(result_df[filter_mask])

        # Convert asset_price_in_reference_fiat to decimal
        result_df["asset_price_in_reference_fiat"] = result_df[
            "asset_price_in_reference_fiat"
        ].apply(self._decimal_from_value)

        return result_df

    def _compute_asset_price_in_reference_fiat_from_trades(
        self, transactions_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Compute asset_price_in_reference_fiat for transactions using OHLC price data.
        """

        # Create a copy to avoid modifying the original
        result_df = transactions_df.copy()

        # Prepare the dataframe for the join
        # Remove all fees
        trades_df = transactions_df[transactions_df["amount"] != Decimal("0")].copy()
        spend_mask = trades_df["transaction_original_type"] == "spend"
        receive_mask = trades_df["transaction_original_type"] == "receive"
        trade_mask = trades_df["transaction_original_type"] == "trade"
        trades_df = trades_df[spend_mask | receive_mask | trade_mask].set_index(
            "correlation_id"
        )

        # There can be multiple trades with the same correlation_id coming from the original asset name (e.g. XETH.S and XETH)
        # We need to sum the amounts and keep the first date and asset
        trades_from_df = (
            trades_df[trades_df["amount"] < 0]
            .groupby("correlation_id")
            .agg({"asset": "first", "amount": "sum", "datetime": "first"})
        )
        trades_to_df = (
            trades_df[trades_df["amount"] >= 0]
            .groupby("correlation_id")
            .agg({"asset": "first", "amount": "sum", "datetime": "first"})
        )

        # Get asset price in reference fiat
        reference_asset_price_df = trades_from_df.join(
            trades_to_df,
            how="left",
            lsuffix="_from",
            rsuffix="_to",
            on="correlation_id",
        )

        # Initialize the asset_price_in_reference_fiat column
        reference_asset_price_df["asset_price_in_reference_fiat"] = Decimal("0")

        # Compute the price of the buy transactions (buying crypto with fiat)
        buy_mask = reference_asset_price_df["asset_from"] == self.reference_fiat
        reference_asset_price_df.loc[buy_mask, "asset_price_in_reference_fiat"] = (
            reference_asset_price_df.loc[buy_mask, "amount_from"]
            / reference_asset_price_df.loc[buy_mask, "amount_to"]
            * -1
        )

        # Compute the price of the sell transactions (selling crypto for fiat)
        sell_mask = reference_asset_price_df["asset_to"] == self.reference_fiat
        reference_asset_price_df.loc[sell_mask, "asset_price_in_reference_fiat"] = (
            reference_asset_price_df.loc[sell_mask, "amount_to"]
            / reference_asset_price_df.loc[sell_mask, "amount_from"]
            * -1
        )

        # Check that there are no duplicate correlation_id
        reference_asset_price_df = reference_asset_price_df.reset_index(
            drop=False, names="correlation_id"
        )
        if reference_asset_price_df["correlation_id"].duplicated().any():
            logger.error(
                "There are duplicate correlation_id in the reference_asset_price_df"
            )
            return pd.DataFrame()

        # Copy the price into the asset_price_in_reference_fiat column of the target df
        # Merge the DataFrames based on correlation_id
        result_df = pd.merge(
            result_df,
            reference_asset_price_df[
                ["correlation_id", "asset_price_in_reference_fiat"]
            ],
            how="left",
            on="correlation_id",
            suffixes=("", "_new"),
        )

        # Update the asset_price_in_reference_fiat column with the new values
        # Keep original values where new values are not NaN
        price_mask = result_df["asset_price_in_reference_fiat_new"].notna()
        not_exception_mask = ~result_df["asset"].isin(EXCEPTION_ASSETS)
        mask = price_mask & not_exception_mask
        result_df.loc[mask, "asset_price_in_reference_fiat"] = result_df.loc[
            mask, "asset_price_in_reference_fiat_new"
        ]

        # Clean up the temporary column
        result_df = result_df.drop(columns=["asset_price_in_reference_fiat_new"])

        return result_df

    def _compute_asset_price_in_reference_fiat_from_ohlc(
        self, transactions_df: pd.DataFrame, ohlc_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate asset_price_in_reference_fiat for transactions using OHLC price data.

        Args:
            transactions_df: DataFrame with transactions in common format
            ohlc_df: DataFrame with OHLC price data

        Returns:
            DataFrame with calculated asset_price_in_reference_fiat values
        """
        # TODO: review implementation and improve performance
        if transactions_df.empty or ohlc_df.empty:
            logger.warning(
                "Cannot calculate fiat prices: missing transaction or OHLC data"
            )
            return transactions_df

        # Create a copy to avoid modifying the original
        result_df = transactions_df.copy()
        result_df["ts"] = result_df["datetime"].apply(lambda x: int(x.timestamp()))
        # Resample the timestamp to the nearest minute
        result_df["timestamp"] = (
            result_df["ts"] // RESAMPLING_INTERVAL_IN_SECONDS
        ) * RESAMPLING_INTERVAL_IN_SECONDS

        # Reset the OHLC DataFrame index to make it easier to work with
        ohlc_df_reset = ohlc_df.reset_index()

        # Find transactions that don't have prices yet
        no_price_mask = result_df["asset_price_in_reference_fiat"] == Decimal("0")

        # Merge the DataFrames on both asset and timestamp
        result_df = pd.merge(
            result_df,
            ohlc_df_reset[["timestamp", "asset", "price"]],
            how="left",
            on=["asset", "timestamp"],
            suffixes=("", "_ohlc"),
        )

        # Update missing prices with OHLC data
        computed_price_mask = no_price_mask & result_df["price"].notna()
        result_df.loc[computed_price_mask, "asset_price_in_reference_fiat"] = (
            result_df.loc[computed_price_mask, "price"]
        )

        # Clean up the temporary price column
        result_df = result_df.drop(columns=["price"])

        return result_df

    def _get_kraken_signature(
        self, urlpath: str, data: Dict[str, Any], secret: str
    ) -> str:
        """Generate Kraken API signature."""
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data["nonce"]) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()

        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    def _kraken_request(self, uri_path: str, data: Dict[str, Any]) -> requests.Response:
        """Make authenticated request to Kraken API."""
        headers = {}
        headers["API-Key"] = self.api_key
        headers["API-Sign"] = self._get_kraken_signature(
            uri_path, data, self.api_secret
        )
        res = requests.post((self.base_url + uri_path), headers=headers, data=data)
        return res

    def _kraken_public_request(self, uri_path: str) -> requests.Response:
        """Make public request to Kraken API."""
        req = requests.get((self.base_url + uri_path))
        return req

    # TODO: TO be used to compare the balance with the local one, or delete it!
    def _get_balance_raw(self, without_count: str = "false") -> Dict[str, Any]:
        """Get raw balance response from Kraken."""
        resp_ledger = self._kraken_request(
            "/0/private/Balance", {"nonce": str(int(1_000_000 * time.time()))}
        )
        return resp_ledger.json()

    def _get_ledger(
        self, start_timestamp: int, ofs: int = 0, without_count: str = "false"
    ) -> Dict[str, Any]:
        """Get ledger data from Kraken."""
        nonce = str(int(1_000_000 * time.time()))
        logger.info(f"Nonce: {nonce}")
        resp_ledger = self._kraken_request(
            "/0/private/Ledgers",
            {
                "nonce": nonce,
                "start": start_timestamp,
                "ofs": ofs,
                "without_count": without_count,
            },
        )
        return resp_ledger.json()

    def _get_tradable_assets_info(self) -> Dict[str, Any]:
        """Get tradable assets info from Kraken."""
        resp_trad_assets = self._kraken_public_request("/0/public/AssetPairs")
        trad_response_json = resp_trad_assets.json()
        return trad_response_json

    def _retrieve_kraken_ledger_data(self, start_timestamp: int) -> pd.DataFrame:
        """Retrieve all ledger data from Kraken."""
        has_new_transactions = True
        ledger_df = pd.DataFrame([])
        consecutive_error_counter = 0
        iter_num = 0
        total_count = 0
        without_count = "false"

        while has_new_transactions:
            response_json = self._get_ledger(
                start_timestamp, iter_num * TX_BATCH_SIZE, without_count
            )

            # Get the total counter
            if without_count == "false":
                total_count = response_json["result"]["count"]
                without_count = "true"

            # Check if there were some errors
            if len(response_json["error"]) == 0:
                consecutive_error_counter = 0
                resp_ledger_json = response_json["result"]["ledger"]
                partial_ledger_df = pd.DataFrame(resp_ledger_json).transpose()
                ledger_df = pd.concat([ledger_df, partial_ledger_df])
                has_new_transactions = (ledger_df.shape[0]) < total_count
                logger.info(f"Call C-{iter_num} performed")
                if has_new_transactions:
                    logger.info("Now Sleeping...")
                    time.sleep(KRAKEN_SLEEPING_TIME)
                iter_num = iter_num + 1
            else:
                logger.error(f"ERROR {consecutive_error_counter}")
                logger.error(response_json["error"])
                has_new_transactions = consecutive_error_counter < 2
                consecutive_error_counter = consecutive_error_counter + 1

        return ledger_df

    def _get_ohlc_data(
        self, assets_in_portfolio: List[str], start_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Return OHLC price data from PostgreSQL for the given assets.
        Triggers a progressive Kraken fetch for any asset whose data is stale or absent.
        On first call for an asset this performs a full historical backfill from 2020.
        """
        from wallets.ohlcv_service import OHLCVService

        assets_to_load = [
            a for a in assets_in_portfolio
            if a not in EXCEPTION_ASSETS and a != self.reference_fiat
        ]

        if not assets_to_load:
            empty = pd.DataFrame(columns=["price", "timestamp"])
            empty.index = pd.MultiIndex.from_tuples([], names=["date", "asset"])
            return empty

        service = OHLCVService()
        service.load(assets_to_load, self.reference_fiat)

        start_ts = int(
            OHLCV_INITIAL_LOAD_START_DATE.replace(tzinfo=timezone.utc).timestamp()
        )
        end_ts = int(datetime.now(timezone.utc).timestamp())

        price_df = service.get_price_dataframe(
            assets_to_load, self.reference_fiat, start_ts, end_ts
        )

        if price_df.empty:
            empty = pd.DataFrame(columns=["price", "timestamp"])
            empty.index = pd.MultiIndex.from_tuples([], names=["date", "asset"])
            return empty

        price_df["date"] = pd.to_datetime(price_df["timestamp"], unit="s").dt.normalize()
        return price_df.set_index(["date", "asset"])[["price", "timestamp"]]


if __name__ == "__main__":  # pragma: no cover
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s:%(process)d] - %(message)s",
    )
    # read api key and secret from file api.key which contains the api key and api secret one per line
    with open("api.key", "r") as file:
        api_key = file.readline().strip()
        api_secret = file.readline().strip()
    wallet = KrakenWallet(reference_fiat="EUR", api_key=api_key, api_secret=api_secret)
    wallet.authenticate()
    wallet._synchronize(start_date="2020-01-01")
    result_df = wallet.get_balance()
