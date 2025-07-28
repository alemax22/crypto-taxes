#!/usr/bin/env python3
"""
Kraken Wallet Implementation
Specific implementation for Kraken exchange
"""

import os
import sys
import time
import requests
import urllib.parse
import hashlib
import hmac
import base64
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import logging

# Add parent directory to path to import config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wallets.wallet import Wallet

logger = logging.getLogger(__name__)

RESAMPLING_INTERVAL = 60*60*24
EXCEPTION_ASSETS = ["KFEE", "NFT"]

class KrakenWallet(Wallet):
    """
    Kraken exchange wallet implementation.
    
    This class provides specific functionality for interacting with
    the Kraken exchange API, including transaction synchronization
    and balance retrieval.
    """
    
    def __init__(self, reference_fiat: str, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize Kraken wallet.
        
        Args:
            api_key: Kraken API key
            api_secret: Kraken API secret
        """
        super().__init__("Kraken", reference_fiat, api_key, api_secret)
        
        # Kraken-specific settings
        self.base_url = 'https://api.kraken.com'
        self.persistent_data_dir = '/app/persistent_data'
        
        # Data file paths
        self.ledger_file = os.path.join(self.persistent_data_dir, "data", "kraken_ledger.parquet")
        self.ohlc_file = os.path.join(self.persistent_data_dir, "data", "kraken_ohlc.parquet")
        
        logger.info("Kraken wallet initialized")
    
    def authenticate(self) -> bool:
        """
        Authenticate with Kraken API.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """

        self.is_authenticated = False
        
        try:
            if not self.api_key or not self.api_secret:
                logger.error("Kraken: Missing API credentials")
                return self.is_authenticated
            
            # Test authentication by getting balance
            test_start_timestamp = int(datetime.now().timestamp())
            ledger_response = self._get_ledger(test_start_timestamp, ofs=0)
            
            if 'error' in ledger_response and ledger_response['error']:
                logger.error(f"Kraken authentication failed: {ledger_response['error']}")
                return self.is_authenticated
            
            self.is_authenticated = True
            logger.info("Kraken authentication successful")
            return self.is_authenticated
            
        except Exception as e:
            logger.error(f"Kraken authentication error: {str(e)}")
            return self.is_authenticated

    def synchronize(self, start_date: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Synchronize local data with the remote wallet/exchange.
        
        This method should:
        1. Fetch transaction data from the exchange
        2. Update local data files
        3. Return synchronization status and metadata
        
        Args:
            start_date: Start date for data synchronization (YYYY-MM-DD format)
            
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
            self.sync_status = "in progress"
            
            # Check authentication
            if not self.is_authenticated:
                if not self.authenticate():
                    self.sync_status = "failed"
                    return False, "Authentication failed"
            
            self._ensure_data_directories()
            
            # Set default start date if not provided
            if not start_date:
                start_date = "2000-01-01"
            
            logger.info(f"Starting Kraken synchronization from {start_date}")
            
            # Fetch transaction data
            new_transactions_count = self._synchronize_transactions(start_date)
            if new_transactions_count == -1:
                self.sync_status = "failed"
                return False, "Error synchronizing transactions"
            
            # Update last sync timestamp
            self.last_sync = datetime.now()
            self.sync_status = "completed"
            return True, None
            
        except Exception as e:
            logger.error(f"Kraken synchronization error: {str(e)}")
            self.sync_status = "failed"
            return False, str(e)
    
    def get_balance(self) -> pd.DataFrame:
        """
        Get current balance from Kraken.
        
        Returns:
            DataFrame with asset balances
        """
        # TODO: Review implementation
        try:
            if not self.is_authenticated:
                if not self.authenticate():
                    return pd.DataFrame()
            
            balance_response = self._get_balance_raw()
            
            if 'error' in balance_response and balance_response['error']:
                logger.error(f"Error getting Kraken balance: {balance_response['error']}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            balance_data = balance_response['result']
            balance_df = pd.DataFrame.from_dict(balance_data, orient='index', columns=['balance'])
            balance_df = balance_df.reset_index(names=['asset'])
            
            # Normalize asset names
            balance_df = self._normalize_assets_name(balance_df, "asset")
            
            # Convert to decimal
            balance_df['balance'] = balance_df.apply(
                lambda row: self._decimal_from_value(row['balance']), axis=1
            )
            
            return balance_df
            
        except Exception as e:
            logger.error(f"Error getting Kraken balance: {str(e)}")
            return pd.DataFrame()
    
    def get_transactions(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get transaction history from Kraken.
        
        Args:
            start_date: Start date for transaction history (YYYY-MM-DD format)
            end_date: End date for transaction history (YYYY-MM-DD format)
            
        Returns:
            DataFrame with transaction history in common format
        """

        # TODO: Review implementation
        try:
            if not self.is_authenticated:
                if not self.authenticate():
                    return pd.DataFrame()
            
            # Set default start date if not provided
            if not start_date:
                start_date = "2021-01-01"
            
            # Fetch all ledger data
            ledger_df = self._retrieve_ledger_data(start_date)
            
            if ledger_df.empty:
                logger.warning("No transactions found for the specified date range")
                return pd.DataFrame()
            
            # Filter by end date if provided
            if end_date:
                end_timestamp = datetime.strptime(end_date, "%Y-%m-%d")
                ledger_df = ledger_df[ledger_df['date'] <= end_timestamp]
            
            # Normalize asset names
            ledger_df = self._normalize_assets_name(ledger_df, "asset", True)
            
            # Add decimal columns
            ledger_df["decimalamount"] = ledger_df.apply(
                lambda row: self._decimal_from_value(row["amount"]), axis=1
            )
            ledger_df["decimalbalance"] = ledger_df.apply(
                lambda row: self._decimal_from_value(row["balance"]), axis=1
            )
            ledger_df["decimalfee"] = ledger_df.apply(
                lambda row: self._decimal_from_value(row["fee"]), axis=1
            )
            
            return ledger_df
            
        except Exception as e:
            logger.error(f"Error getting Kraken transactions: {str(e)}")
            return pd.DataFrame()
    
    def _ensure_data_directories(self) -> None:
        """Ensure all necessary data directories exist."""
        # Get all unique directory paths from the file paths defined in __init__
        dirs = set()
        
        # Extract directories from ledger_file and ohlc_file
        dirs.add(os.path.dirname(self.ledger_file))
        dirs.add(os.path.dirname(self.ohlc_file))
        
        # Create all directories
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
    
    def _synchronize_transactions(self, start_date: str) -> int:
        """
        Synchronize transaction data with local storage.
        
        Args:
            start_date: Start date for transactions
            
        Returns:
            int: Number of transactions fetched
        """
        start_timestamp = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        try:
            # Load existing data if available
            existing_df = pd.DataFrame()
            if os.path.exists(self.ledger_file):
                try:
                    existing_df = pd.read_parquet(self.ledger_file, engine="fastparquet")
                    existing_df["amount"] = existing_df["amount"].apply(self._decimal_from_value)
                    existing_df["fee"] = existing_df["fee"].apply(self._decimal_from_value)
                    existing_df["asset_price_in_reference_fiat"] = existing_df["asset_price_in_reference_fiat"].apply(self._decimal_from_value)
                    start_timestamp = int(existing_df["datetime"].max().timestamp())
                    logger.info(f"Loaded {len(existing_df)} existing transactions")
                except Exception as e:
                    logger.warning(f"Error loading existing ledger data: {e}")
            
            # Fetch new data
            new_df = self._retrieve_ledger_data(start_timestamp)
            
            if new_df.empty:
                logger.info("No new transactions found")
                return 0
            
            # Transform to common format
            new_df = self._create_transaction_df_with_common_format(new_df)
            
            # Merge with existing data
            if not existing_df.empty:
                # Remove duplicates and merge using transaction_id
                combined_df = pd.concat([new_df, existing_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['transaction_id'], keep='first')
            else:
                combined_df = new_df
            
            combined_parquet_df = combined_df.copy()
            
            # Convert columns to specific types before saving (parquet does not support Decimal)
            combined_df = combined_df.astype({
                'amount': 'string',
                'balance': 'float64',
                'asset_price_in_reference_fiat': 'string',
                'fee': 'string',
                'transaction_id': 'string',
                'correlation_id': 'string',
                'asset': 'string',
                'transaction_type': 'string',
                'transaction_original_type': 'string',
                'asset_original_name': 'string',
                'asset_original_balance': 'string'
            })

            combined_parquet_df.to_csv("combined_df.csv")

            # Save to file
            combined_parquet_df.to_parquet(self.ledger_file, engine="fastparquet", compression="GZIP")
            
            transactions_fetched = len(new_df)
            logger.info(f"Synchronized {transactions_fetched} new transactions")
            
            return transactions_fetched
            
        except Exception as e:
            logger.error(f"Error synchronizing transactions: {str(e)}")
            return -1
    
    def _create_transaction_df_with_common_format(self, df: pd.DataFrame) -> pd.DataFrame:
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
            "asset_original_balance"
        ]

        result_df["datetime"] = pd.to_datetime(result_df["time"], unit='s')
        result_df["transaction_id"] = result_df["transaction_id"].astype(str)
        result_df["correlation_id"] = result_df["refid"].astype(str)
        result_df["transaction_type"] = result_df["type"].apply(self._map_transaction_type)
        result_df["asset_original_name"] = result_df["asset"]
        result_df["asset"] = result_df["asset"].apply(self._normalize_asset_name)
        result_df["amount"] = result_df["amount"].apply(self._decimal_from_value)
        result_df["asset_original_balance"] = result_df["balance"]
        # Calculate running balance per asset (sorted by datetime)
        result_df = result_df.sort_values(["asset", "datetime"])
        result_df["temp_amount"] = result_df["amount"].astype(float)
        result_df["temp_fee"] = result_df["fee"].astype(float)
        result_df["temp_amount_without_fee"] = result_df["temp_amount"] - result_df["temp_fee"]
        result_df["balance"] = result_df.groupby("asset")["temp_amount_without_fee"].cumsum()
        result_df["asset_price_in_reference_fiat"] = Decimal('0')
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
                "earn": "reward",     # Earn rewards
                
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
                "correction": "transfer"
            }
            return type_mapping.get(kraken_type.lower(), "transfer")

    def _normalize_asset_name(self, asset_name: str) -> str:
        asset_name = asset_name.split('.')[0]
        asset_name = asset_name.split('21')[0]
        if asset_name == "ZEUR":
            asset_name = "EUR"
        elif asset_name == "XBT" or asset_name == "XXBT":
            asset_name = "BTC"
        elif asset_name == "XETH":
            asset_name = "ETH"
        elif asset_name == "XXRP":
            asset_name = "XRP"
        return asset_name
    
    def _get_asset_price_in_reference_fiat(self, transactions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute asset_price_in_reference_fiat for transactions using OHLC price data.
        """

        result_df = self._compute_asset_price_in_reference_fiat_from_trades(transactions_df)

        # Get unique assets from transactions for OHLC data
        assets_in_transactions = result_df["asset"].unique().tolist()
        
        # Fetch OHLC data for price calculations of the asset without price in reference fiat
        ohlc_df = self._get_ohlc_data(
            assets_in_portfolio=assets_in_transactions,
        )
        
        result_df = self._compute_asset_price_in_reference_fiat_from_ohlc(result_df, ohlc_df)

        # Assign 1 to the asset_price_in_reference_fiat of the reference asset
        result_df.loc[result_df["asset"] == self.reference_fiat, "asset_price_in_reference_fiat"] = Decimal('1')

        # Check that all transactions have a price
        nan_price_mask = result_df["asset_price_in_reference_fiat"].isna()
        zero_price_mask = result_df["asset_price_in_reference_fiat"] == Decimal('0')
        not_exception_mask = ~result_df["asset"].isin(EXCEPTION_ASSETS)
        filter_mask = (nan_price_mask | zero_price_mask) & not_exception_mask
        if filter_mask.any():
            logger.error("There are transactions without a price:")
            logger.error(result_df[filter_mask])

        # Convert asset_price_in_reference_fiat to decimal
        result_df["asset_price_in_reference_fiat"] = result_df["asset_price_in_reference_fiat"].apply(self._decimal_from_value)

        return result_df

    def _compute_asset_price_in_reference_fiat_from_trades(self, transactions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute asset_price_in_reference_fiat for transactions using OHLC price data.
        """

        # Create a copy to avoid modifying the original
        result_df = transactions_df.copy()

        # Prepare the dataframe for the join
        # Remove all fees
        trades_df = transactions_df[transactions_df["amount"]!=Decimal('0')].copy()
        spend_mask = trades_df["transaction_original_type"]=="spend"
        receive_mask = trades_df["transaction_original_type"]=="receive"
        trade_mask = trades_df["transaction_original_type"]=="trade"
        trades_df = trades_df[spend_mask | receive_mask | trade_mask].set_index("correlation_id")
        
        # There can be multiple trades with the same correlation_id coming from the original asset name (e.g. XETH.S and XETH)
        # We need to sum the amounts and keep the first date and asset
        trades_from_df = trades_df[trades_df["amount"] < 0].groupby("correlation_id").agg({"asset": "first", "amount": "sum", "datetime": "first"})
        trades_to_df = trades_df[trades_df["amount"] >= 0].groupby("correlation_id").agg({"asset": "first", "amount": "sum", "datetime": "first"})

        # Get asset price in reference fiat
        reference_asset_price_df = trades_from_df.join(trades_to_df, how="left", lsuffix="_from", rsuffix="_to", on="correlation_id")
        
        # Initialize the asset_price_in_reference_fiat column
        reference_asset_price_df["asset_price_in_reference_fiat"] = Decimal('0')
        
        # Compute the price of the buy transactions (buying crypto with fiat)
        buy_mask = reference_asset_price_df["asset_from"] == self.reference_fiat
        reference_asset_price_df.loc[buy_mask, "asset_price_in_reference_fiat"] = (
            reference_asset_price_df.loc[buy_mask, "amount_from"] / 
            reference_asset_price_df.loc[buy_mask, "amount_to"] * -1
        )
        
        # Compute the price of the sell transactions (selling crypto for fiat)
        sell_mask = reference_asset_price_df["asset_to"] == self.reference_fiat
        reference_asset_price_df.loc[sell_mask, "asset_price_in_reference_fiat"] = (
            reference_asset_price_df.loc[sell_mask, "amount_to"] / 
            reference_asset_price_df.loc[sell_mask, "amount_from"] * -1
        )
        
        # Check that there are no duplicate correlation_id
        reference_asset_price_df = reference_asset_price_df.reset_index(drop=False, names="correlation_id")
        if reference_asset_price_df["correlation_id"].duplicated().any():
            logger.error("There are duplicate correlation_id in the reference_asset_price_df")
            return pd.DataFrame()
        
        # Copy the price into the asset_price_in_reference_fiat column of the target df
        # Merge the DataFrames based on correlation_id
        result_df = pd.merge(
            result_df,
            reference_asset_price_df[['correlation_id', 'asset_price_in_reference_fiat']], 
            how='left', 
            on='correlation_id',
            suffixes=('', '_new')
        )
        
        # Update the asset_price_in_reference_fiat column with the new values
        # Keep original values where new values are not NaN
        price_mask = result_df['asset_price_in_reference_fiat_new'].notna()
        not_exception_mask = ~result_df["asset"].isin(EXCEPTION_ASSETS)
        mask = price_mask & not_exception_mask
        result_df.loc[mask, 'asset_price_in_reference_fiat'] = result_df.loc[mask, 'asset_price_in_reference_fiat_new']
        
        # Clean up the temporary column
        result_df = result_df.drop(columns=['asset_price_in_reference_fiat_new'])

        return result_df

    def _compute_asset_price_in_reference_fiat_from_ohlc(self, transactions_df: pd.DataFrame, ohlc_df: pd.DataFrame) -> pd.DataFrame:
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
            logger.warning("Cannot calculate fiat prices: missing transaction or OHLC data")
            return transactions_df
        
        # Create a copy to avoid modifying the original
        result_df = transactions_df.copy()
        result_df["ts"] = result_df["datetime"].apply(lambda x: int(x.timestamp()))
        # Resample the timestamp to the nearest minute
        result_df["timestamp"] = result_df["ts"]//RESAMPLING_INTERVAL*RESAMPLING_INTERVAL

        # Reset the OHLC DataFrame index to make it easier to work with
        ohlc_df_reset = ohlc_df.reset_index()
        
        # Find transactions that don't have prices yet
        no_price_mask = result_df["asset_price_in_reference_fiat"] == Decimal('0')
        
        # Merge the DataFrames on both asset and timestamp
        result_df = pd.merge(
            result_df,
            ohlc_df_reset[['timestamp', 'asset', 'price']], 
            how='left',
            on=['asset', 'timestamp'], 
            suffixes=('', '_ohlc')
        )
        
        # Update missing prices with OHLC data
        computed_price_mask = no_price_mask & result_df['price'].notna()
        result_df.loc[computed_price_mask, 'asset_price_in_reference_fiat'] = result_df.loc[computed_price_mask, 'price']
        
        # Clean up the temporary price column
        result_df = result_df.drop(columns=['price'])

        return result_df
    
    def _synchronize_ohlc_data(self, start_date: str) -> bool:
        """
        Synchronize OHLC (price) data.
        
        Args:
            start_date: Start date for OHLC data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get assets from ledger data
            if os.path.exists(self.ledger_file):
                ledger_df = pd.read_parquet(self.ledger_file, engine="fastparquet")
                assets_in_portfolio = ledger_df["assetnorm"].unique()
            else:
                # If no ledger data, use default assets
                assets_in_portfolio = ["XXBT", "XETH", "ZEUR"]
            
            # Fetch OHLC data with persistence
            ohlc_df = self._get_ohlc_data_with_persistence_old(
                assets_in_portfolio=assets_in_portfolio,
                reference_asset="ZEUR",
                exception_assets=EXCEPTION_ASSETS,
                start_date=start_date
            )
            
            if not ohlc_df.empty:
                logger.info(f"OHLC data synchronization successful - {len(ohlc_df)} records")
                return True
            else:
                logger.warning("OHLC data synchronization failed - no data returned")
                return False
                
        except Exception as e:
            logger.error(f"Error synchronizing OHLC data: {str(e)}")
            return False
    
    def _decimal_from_value(self, value: Any) -> Decimal:
        """Convert value to Decimal."""
        return Decimal(value)
    
    def _decimal_sum(self, value1: Any, value2: Any) -> Decimal:
        """Sum two decimal values."""
        return Decimal(value1) + Decimal(value2)
    
    def _get_kraken_signature(self, urlpath: str, data: Dict[str, Any], secret: str) -> str:
        """Generate Kraken API signature."""
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        
        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()
    
    def _kraken_request(self, uri_path: str, data: Dict[str, Any]) -> requests.Response:
        """Make authenticated request to Kraken API."""
        headers = {}
        headers['API-Key'] = self.api_key
        headers['API-Sign'] = self._get_kraken_signature(uri_path, data, self.api_secret)
        res = requests.post((self.base_url + uri_path), headers=headers, data=data)
        return res
    
    def _kraken_public_request(self, uri_path: str) -> requests.Response:
        """Make public request to Kraken API."""
        req = requests.get((self.base_url + uri_path))
        return req
    
    def _get_balance_raw(self, without_count: str = "false") -> Dict[str, Any]:
        """Get raw balance response from Kraken."""
        resp_ledger = self._kraken_request('/0/private/Balance', {
            "nonce": str(int(1_000_000*time.time()))
        })
        return resp_ledger.json()
    
    def _get_ledger(self, start_timestamp: int, ofs: int, without_count: str = "false") -> Dict[str, Any]:
        """Get ledger data from Kraken."""
        resp_ledger = self._kraken_request('/0/private/Ledgers', {
            "nonce": str(int(1_000_000*time.time())),
            "start": start_timestamp,
            "ofs": ofs,
            "without_count": without_count
        })
        return resp_ledger.json()
    
    def _retrieve_ledger_data(self, start_timestamp: int) -> pd.DataFrame:
        """Retrieve all ledger data from Kraken."""
        tx_batch_size = 50
        sleeping_time = 4  # After every call we should sleep 4s to refill entirely the call limit counter
        has_new_transactions = True
        ledger_df = pd.DataFrame([])
        consecutive_error_counter = 0
        iter_num = 0
        total_count = 0
        without_count = "false"
        
        while has_new_transactions:
            response_json = self._get_ledger(start_timestamp, iter_num*tx_batch_size, without_count)
            
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
                    time.sleep(sleeping_time)
                iter_num = iter_num + 1
            else:
                logger.error(f"ERROR {consecutive_error_counter}")
                logger.error(response_json["error"])
                has_new_transactions = consecutive_error_counter < 2
                consecutive_error_counter = consecutive_error_counter + 1
        
        return ledger_df
    
    def _get_ohlc_data_from_kraken(self, pair: str, altname: str, interval: int = 1440, since: Optional[int] = None) -> pd.DataFrame:
        """Get OHLC data for a single pair."""
        if since is not None:
            resp_ohlc_data = self._kraken_public_request('/0/public/OHLC?pair=' + pair + '&interval=' + str(interval) + '&since=' + str(since))
        else:
            resp_ohlc_data = self._kraken_public_request('/0/public/OHLC?pair=' + pair + '&interval=' + str(interval))
        
        resp_ohlc_data_json = resp_ohlc_data.json()
        resp_ohlc_data_df = pd.DataFrame([])
        
        if len(resp_ohlc_data_json["error"]) == 0:
            resp_ohlc_data_df = pd.DataFrame(resp_ohlc_data_json["result"][altname], columns=["timestamp","open","high","low","close","vwap","volume","count"])
            resp_ohlc_data_df = resp_ohlc_data_df.set_index("timestamp")
            
            # Get the 'last' field from the API response
            last_valid_timestamp = resp_ohlc_data_json["result"]["last"]
            
            # Discard all samples after the last valid timestamp
            if not resp_ohlc_data_df.empty:
                resp_ohlc_data_df = resp_ohlc_data_df[resp_ohlc_data_df.index <= last_valid_timestamp]
                logger.info(f"Discarded samples after timestamp {last_valid_timestamp} (kept {len(resp_ohlc_data_df)} valid samples)")
        else:
            logger.error(resp_ohlc_data_json["error"])
        
        return resp_ohlc_data_df
    
    def _create_tradable_asset_matrix(self) -> pd.DataFrame:
        """Create tradable asset matrix."""
        resp_trad_assets = self._kraken_public_request('/0/public/AssetPairs')
        trad_response_json = resp_trad_assets.json()
        
        # Create DataFrame from API response
        tradable_asset_df = pd.DataFrame(trad_response_json["result"]).transpose()
        
        # Select and rename columns for clarity
        tradable_asset_df = tradable_asset_df[["base", "quote", "altname", "wsname"]].copy()
        
        # Normalize asset names using existing method
        tradable_asset_df["base"] = tradable_asset_df["base"].apply(self._normalize_asset_name)
        tradable_asset_df["quote"] = tradable_asset_df["quote"].apply(self._normalize_asset_name)
        
        # Set index for easy lookup
        tradable_asset_df = tradable_asset_df.reset_index(drop=False, names="index")
        tradable_asset_df = tradable_asset_df.set_index(["base", "quote"])

        # Add custom mappings for special cases
        custom_mappings = self._get_custom_asset_mappings()
        if not custom_mappings.empty:
            tradable_asset_df = pd.concat([tradable_asset_df, custom_mappings])
        
        return tradable_asset_df
    
    def _get_custom_asset_mappings(self) -> pd.DataFrame:
        # TODO: find a common patter to handle the token migrations:
        # - MATIC TO POL 1:1 from ...
        # - EOS TO A 1:1 from ...
        """Get custom asset mappings for special cases."""
        custom_mappings = []
        
        # Add MATIC/POL mapping
        custom_mappings.append({
            'index': 'POLEUR',
            'altname': 'POLEUR',
            'wsname': 'POL/EUR'
        })

        custom_index = pd.MultiIndex.from_tuples([('MATIC', 'EUR')], names=['base', 'quote'])
        custom_mappings = pd.DataFrame(custom_mappings, index=custom_index)
        
        return custom_mappings
    
    def _get_ohlc_data(self, assets_in_portfolio: List[str]) -> pd.DataFrame:
        """Get OHLC data with persistence to parquet file."""
        filename = self.ohlc_file
        tradable_asset_df = self._create_tradable_asset_matrix()
        reference_asset = self.reference_fiat
        exception_assets = EXCEPTION_ASSETS

        # Ensure data directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Load existing data
        existing_ohlc_df = pd.DataFrame()
        try:
            existing_ohlc_df = pd.read_parquet(filename, engine="fastparquet")
            logger.info(f"Loaded existing OHLC data: {existing_ohlc_df.shape[0]} records")
        except FileNotFoundError:
            logger.info("No existing OHLC data found")
        
        # Collect new OHLC data
        new_ohlc_data = []
        
        # Log available trading pairs for debugging
        logger.debug(f"Assets in portfolio: {assets_in_portfolio}")
        
        # TODO: how to handle multi fiat portfolio?
        for asset in assets_in_portfolio:
            if (asset not in exception_assets) and (asset != reference_asset):
                try:
                    # Check if the trading pair exists
                    if (asset, reference_asset) not in tradable_asset_df.index:
                        logger.warning(f"No trading pair found for {asset}/{reference_asset}. Skipping OHLC data fetch.")
                        continue
                    
                    pair_data = tradable_asset_df.loc[asset, reference_asset]
                    pair_altname = pair_data["altname"]
                    # Use altname as the index for OHLC data retrieval
                    pair_index = pair_data["index"]
                    
                    # Get the latest timestamp for this asset from existing data
                    latest_timestamp = None
                    if not existing_ohlc_df.empty:
                        asset_data = existing_ohlc_df.xs(asset, level='asset', drop_level=False) if asset in existing_ohlc_df.index.get_level_values('asset') else pd.DataFrame()
                        if not asset_data.empty and 'timestamp' in asset_data.columns:
                            latest_timestamp = asset_data['timestamp'].max()
                            logger.info(f"Latest timestamp for {asset}: {latest_timestamp} ({datetime.fromtimestamp(latest_timestamp)})")
                    
                    # Check if we need to fetch new data (avoid calls for very recent timestamps)
                    current_time = datetime.now().timestamp()
                    min_interval_seconds = 1440 * 60 * 2
                    
                    if latest_timestamp is not None and (current_time - latest_timestamp) < min_interval_seconds:
                        logger.info(f"Skipping {asset} - latest data is too recent (less than 1440 minutes ago)")
                        continue
                    
                    logger.info(f"Fetching data for {asset} ({pair_altname})")
                    
                    # Get OHLC data with daily interval (1440 minutes) and latest timestamp
                    ohlc_df = self._get_ohlc_data_from_kraken(pair_altname, pair_index, interval=1440, since=latest_timestamp)
                    
                    logger.info(f"Fetched {ohlc_df.shape[0]} rows")
                    
                    # TODO copy implementation from arbitrage scripts to get and align OHLC data, then from this function always retrieve the local copy of the data
                    if not ohlc_df.empty:
                        # Reset index to get timestamp as column
                        ohlc_df = ohlc_df.reset_index()
                        ohlc_df["datetime"] = pd.to_datetime(ohlc_df["timestamp"], unit='s').dt.normalize()
                        
                        # Convert close price to Decimal and create records
                        for _, row in ohlc_df.iterrows():
                            price = self._decimal_from_value(row["close"])
                            new_ohlc_data.append({
                                'date': row["datetime"],
                                'crypto': asset,
                                'price': price,
                                'timestamp': row["timestamp"]
                            })
                    
                    # Sleep to avoid rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error fetching data for {asset}: {e}")
                    continue
        
        # Create new DataFrame
        if new_ohlc_data:
            new_ohlc_df = pd.DataFrame(new_ohlc_data)
            new_ohlc_df = new_ohlc_df.rename(columns={'crypto': 'asset'})
            new_ohlc_df = new_ohlc_df.set_index(['date', 'asset'])
            logger.info(f"Fetched {len(new_ohlc_data)} new OHLC records")
        else:
            new_ohlc_df = pd.DataFrame()
            logger.info("No new OHLC data fetched")
        
        # Merge with existing data
        if not existing_ohlc_df.empty and not new_ohlc_df.empty:
            # Combine existing and new data
            combined_df = pd.concat([existing_ohlc_df, new_ohlc_df])
            # Remove duplicates (keep the newest instance)
            combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
            logger.info(f"Combined data: {combined_df.shape[0]} records and deleted {existing_ohlc_df.shape[0] + new_ohlc_df.shape[0] - combined_df.shape[0]} duplicates")
        elif not existing_ohlc_df.empty:
            combined_df = existing_ohlc_df
        elif not new_ohlc_df.empty:
            combined_df = new_ohlc_df
        else:
            # Create empty DataFrame with proper structure
            combined_df = pd.DataFrame(columns=['price', 'timestamp'])
            combined_df.index = pd.MultiIndex.from_tuples([], names=['date', 'asset'])
        
        # Save to parquet file (with timestamp included)
        if not combined_df.empty:
            combined_df.to_parquet(filename, engine="fastparquet", compression="GZIP")
            logger.info(f"Saved OHLC data to {filename}")
        
        logger.info(f"Combined data: {combined_df.shape[0]} records")
        return combined_df
    
    def _normalize_assets_name(self, df: pd.DataFrame, asset_column_name: str, log_message: bool = False) -> pd.DataFrame:
        """
        Normalize asset names in a DataFrame using Kraken API data.
        
        Args:
            df: DataFrame containing asset data
            asset_column_name: Name of the column containing asset identifiers
            log_message: Whether to print debug messages
        
        Returns:
            DataFrame with normalized asset names in 'assetnorm' column
        """
        # Get all assets keys in the portfolio
        assets_in_portfolio = df[asset_column_name].unique()
        if log_message:
            logger.info("All assets:")
            logger.info(assets_in_portfolio)
        
        # Create a copy of the DataFrame to avoid modifying the original
        df_copy = df.copy()
        
        # Initialize assetnorm column from the asset column
        df_copy["assetnorm"] = df_copy[asset_column_name]
        
        # Apply basic normalization rules
        df_copy = self._apply_basic_normalization_rules(df_copy)
        
        # Normalized asset list
        assets_in_portfolio = df_copy["assetnorm"].unique()
        if log_message:
            logger.info("Normalized assets:")
            logger.info(assets_in_portfolio)
        
        return df_copy
    
    def _apply_basic_normalization_rules(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply basic normalization rules to asset names.
        """
        df["assetnorm"] = df["assetnorm"].str.split('.').str[0]
        df["assetnorm"] = df["assetnorm"].str.split('21').str[0]
        df.loc[(df["assetnorm"]=="EUR"),["assetnorm"]] = "ZEUR"
        df.loc[(df["assetnorm"]=="XBT"),["assetnorm"]] = "XXBT"
        df.loc[(df["assetnorm"]=="ETH"),["assetnorm"]] = "XETH"
        
        return df
    

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # read api key and secret from file api.key which contains the api key and api secret one per line
    with open("api.key", "r") as file:
        api_key = file.readline().strip()
        api_secret = file.readline().strip()
    wallet = KrakenWallet(reference_fiat="EUR", api_key=api_key, api_secret=api_secret)
    wallet.authenticate()
    wallet.synchronize(start_date="2020-01-01")