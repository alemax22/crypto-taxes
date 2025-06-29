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


class KrakenWallet(Wallet):
    """
    Kraken exchange wallet implementation.
    
    This class provides specific functionality for interacting with
    the Kraken exchange API, including transaction synchronization
    and balance retrieval.
    """
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize Kraken wallet.
        
        Args:
            api_key: Kraken API key
            api_secret: Kraken API secret
        """
        super().__init__("Kraken", api_key, api_secret)
        
        # Kraken-specific settings
        self.base_url = 'https://api.kraken.com'
        self.persistent_data_dir = '/app/persistent_data'
        
        # Data file paths
        self.ledger_file = os.path.join(self.persistent_data_dir, "data", "kraken_ledger.parquet")
        self.ohlc_file = os.path.join(self.persistent_data_dir, "data", "kraken_ohlc.parquet")
        self.api_keys_file = os.path.join(self.persistent_data_dir, "config", "kraken_api_keys.json")
        self.secret_key_file = os.path.join(self.persistent_data_dir, "config", "secret.key")
        
        logger.info("Kraken wallet initialized")
    
    # ============================================================================
    # AUTHENTICATION METHODS
    # ============================================================================
    
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
            test_start_date = datetime.now() - timedelta(days=1)
            ledger_response = self._get_ledger(test_start_date, ofs=0)
            
            if 'error' in ledger_response and ledger_response['error']:
                logger.error(f"Kraken authentication failed: {ledger_response['error']}")
                return self.is_authenticated
            
            self.is_authenticated = True
            logger.info("Kraken authentication successful")
            return self.is_authenticated
            
        except Exception as e:
            logger.error(f"Kraken authentication error: {str(e)}")
            return self.is_authenticated
    
    def load_credentials_from_storage(self) -> bool:
        """
        Load credentials from persistent storage.
        
        Returns:
            bool: True if credentials loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(self.api_keys_file):
                logger.warning("API keys file not found")
                return False
            
            if not os.path.exists(self.secret_key_file):
                logger.warning("Secret key file not found")
                return False
            
            # Load encrypted credentials
            with open(self.api_keys_file, 'r') as f:
                api_data = json.load(f)
            
            encrypted_key = api_data.get("KRAKEN_API_KEY")
            encrypted_secret = api_data.get("KRAKEN_API_SECRET")
            
            if not encrypted_key or not encrypted_secret:
                logger.warning("Encrypted credentials not found in file")
                return False
            
            # Decrypt credentials
            self.api_key = self._decrypt_message(encrypted_key, self.secret_key_file)
            self.api_secret = self._decrypt_message(encrypted_secret, self.secret_key_file)
            
            logger.info("Credentials loaded from storage successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading credentials from storage: {str(e)}")
            return False
    
    # ============================================================================
    # CORE WALLET METHODS
    # ============================================================================
    
    def synchronize(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronize local data with Kraken exchange.
        
        Args:
            start_date: Start date for data synchronization (YYYY-MM-DD format)
            end_date: End date for data synchronization (YYYY-MM-DD format)
            
        Returns:
            Dict containing synchronization results
        """
        try:
            if not self.is_authenticated:
                if not self.authenticate():
                    return {
                        'success': False,
                        'transactions_fetched': 0,
                        'balance_updated': False,
                        'last_sync': None,
                        'error': 'Authentication failed'
                    }
            
            # Ensure data directories exist
            self._ensure_data_directories()
            
            # Set default start date if not provided
            if not start_date:
                start_date = "2021-01-01"
            
            logger.info(f"Starting Kraken synchronization from {start_date}")
            
            # Fetch transaction data
            transactions_fetched = self._synchronize_transactions(start_date, end_date)
            
            # Update balance
            balance_updated = self._synchronize_balance()
            
            # Update OHLC data
            ohlc_updated = self._synchronize_ohlc_data(start_date)
            
            # Update last sync timestamp
            self.update_last_sync()
            
            return {
                'success': True,
                'transactions_fetched': transactions_fetched,
                'balance_updated': balance_updated,
                'ohlc_updated': ohlc_updated,
                'last_sync': self.last_sync,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Kraken synchronization error: {str(e)}")
            return {
                'success': False,
                'transactions_fetched': 0,
                'balance_updated': False,
                'last_sync': None,
                'error': str(e)
            }
    
    def get_balance(self) -> pd.DataFrame:
        """
        Get current balance from Kraken.
        
        Returns:
            DataFrame with asset balances
        """
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
            DataFrame with transaction history
        """
        try:
            if not self.is_authenticated:
                if not self.authenticate():
                    return pd.DataFrame()
            
            # Set default start date if not provided
            if not start_date:
                start_date = "2021-01-01"
            
            # Fetch all ledger data
            ledger_df = self._retrieve_all_ledger_data(start_date)
            
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
    
    # ============================================================================
    # PRIVATE HELPER METHODS
    # ============================================================================
    
    def _ensure_data_directories(self):
        """Ensure all necessary data directories exist."""
        dirs = [
            os.path.join(self.persistent_data_dir, 'data'),
            os.path.join(self.persistent_data_dir, 'logs'),
            os.path.join(self.persistent_data_dir, 'config')
        ]
        for dir_path in dirs:
            os.makedirs(dir_path, exist_ok=True)
    
    def _synchronize_transactions(self, start_date: str, end_date: Optional[str] = None) -> int:
        """
        Synchronize transaction data with local storage.
        
        Args:
            start_date: Start date for transactions
            end_date: End date for transactions
            
        Returns:
            int: Number of transactions fetched
        """
        try:
            # Load existing data if available
            existing_df = pd.DataFrame()
            if os.path.exists(self.ledger_file):
                try:
                    existing_df = pd.read_parquet(self.ledger_file, engine="fastparquet")
                    logger.info(f"Loaded {len(existing_df)} existing transactions")
                except Exception as e:
                    logger.warning(f"Error loading existing ledger data: {e}")
            
            # Fetch new data
            new_df = self._retrieve_all_ledger_data(start_date)
            
            if new_df.empty:
                logger.info("No new transactions found")
                return 0
            
            # Merge with existing data
            if not existing_df.empty:
                # Remove duplicates and merge
                combined_df = pd.concat([new_df, existing_df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=['refid'], keep='first')
            else:
                combined_df = new_df
            
            # Save to file
            combined_df.to_parquet(self.ledger_file, engine="fastparquet", compression="GZIP")
            
            transactions_fetched = len(new_df)
            logger.info(f"Synchronized {transactions_fetched} new transactions")
            
            return transactions_fetched
            
        except Exception as e:
            logger.error(f"Error synchronizing transactions: {str(e)}")
            return 0
    
    def _synchronize_balance(self) -> bool:
        """
        Synchronize balance data.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Balance is fetched on-demand, so just verify we can get it
            balance_df = self.get_balance()
            if not balance_df.empty:
                logger.info("Balance synchronization successful")
                return True
            else:
                logger.warning("Balance synchronization failed - no data returned")
                return False
                
        except Exception as e:
            logger.error(f"Error synchronizing balance: {str(e)}")
            return False
    
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
            ohlc_df = self._get_ohlc_data_with_persistence(
                assets_in_portfolio=assets_in_portfolio,
                reference_asset="ZEUR",
                exception_assets=["KFEE", "NFT"],
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
    
    # ============================================================================
    # KRAKEN API METHODS (moved from kraken.py)
    # ============================================================================
    
    def _decimal_from_value(self, value):
        """Convert value to Decimal."""
        return Decimal(value)
    
    def _decimal_sum(self, value1, value2):
        """Sum two decimal values."""
        return Decimal(value1) + Decimal(value2)
    
    def _decrypt_message(self, encrypted_message, key_path="secret.key"):
        """Decrypt a message using the key stored at the specified path."""
        from cryptography.fernet import Fernet
        key = open(key_path, "rb").read()
        f = Fernet(key)
        decrypted_message = f.decrypt(encrypted_message.encode() if isinstance(encrypted_message, str) else encrypted_message)
        return decrypted_message.decode()
    
    def _get_kraken_signature(self, urlpath, data, secret):
        """Generate Kraken API signature."""
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        
        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()
    
    def _kraken_request(self, uri_path, data):
        """Make authenticated request to Kraken API."""
        headers = {}
        headers['API-Key'] = self.api_key
        headers['API-Sign'] = self._get_kraken_signature(uri_path, data, self.api_secret)
        res = requests.post((self.base_url + uri_path), headers=headers, data=data)
        return res
    
    def _kraken_public_request(self, uri_path):
        """Make public request to Kraken API."""
        req = requests.get((self.base_url + uri_path))
        return req
    
    def _totimestamp(self, date):
        """Convert datetime to timestamp."""
        unix = datetime.strptime(date, "%Y-%m-%d").timetuple()
        unix_int = np.int32(time.mktime(unix))
        return unix_int
    
    def _get_balance_raw(self, without_count="false"):
        """Get raw balance response from Kraken."""
        resp_ledger = self._kraken_request('/0/private/Balance', {
            "nonce": str(int(1_000_000*time.time()))
        })
        return resp_ledger.json()
    
    def _get_ledger(self, start_date, ofs, without_count="false"):
        """Get ledger data from Kraken."""
        start_timestamp = self._totimestamp(start_date)
        resp_ledger = self._kraken_request('/0/private/Ledgers', {
            "nonce": str(int(1_000_000*time.time())),
            "start": start_timestamp,
            "ofs": ofs,
            "without_count": without_count
        })
        return resp_ledger.json()
    
    def _retrieve_all_ledger_data(self, start_date):
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
            response_json = self._get_ledger(start_date, iter_num*tx_batch_size, without_count)
            
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
        
        # Add date column
        ledger_df["date"] = pd.to_datetime(ledger_df["time"], unit='s')
        return ledger_df
    
    def _get_ohlc_data(self, pair, altname, interval=1440, since=None):
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
    
    def _create_tradable_asset_matrix(self):
        """Create tradable asset matrix."""
        resp_trad_assets = self._kraken_public_request('/0/public/AssetPairs')
        trad_response_json = resp_trad_assets.json()
        tradable_asset_df = pd.DataFrame(trad_response_json["result"]).transpose()
        tradable_asset_df = tradable_asset_df[["base","quote","altname","wsname"]]
        tradable_asset_df = tradable_asset_df.reset_index()
        tradable_asset_df = tradable_asset_df.set_index(["base","quote"])
        return tradable_asset_df
    
    def _get_ohlc_data_with_persistence(self, assets_in_portfolio, reference_asset="ZEUR", exception_assets=["KFEE","NFT"], start_date="2021-01-01"):
        """Get OHLC data with persistence to parquet file."""
        filename = self.ohlc_file
        tradable_asset_pair = self._create_tradable_asset_matrix()
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Add MATIC/POL mapping
        new_row_data = {
            'altname': 'POLEUR',
            'index': 'POLEUR',
            'wsname': 'POL/EUR'
        }
        new_index = pd.MultiIndex.from_tuples([('MATIC', 'ZEUR')], names=['base', 'quote'])
        new_row_df = pd.DataFrame([new_row_data], index=new_index)
        tradable_asset_pair = pd.concat([tradable_asset_pair, new_row_df])
        
        # Load existing data
        existing_ohlc_df = pd.DataFrame()
        try:
            existing_ohlc_df = pd.read_parquet(filename, engine="fastparquet")
            logger.info(f"Loaded existing OHLC data: {existing_ohlc_df.shape[0]} records")
        except FileNotFoundError:
            logger.info("No existing OHLC data found")
        
        # Collect new OHLC data
        new_ohlc_data = []
        
        for asset in assets_in_portfolio:
            if (asset not in exception_assets) and (asset != reference_asset):
                try:
                    pair_name = tradable_asset_pair.loc[asset, reference_asset].loc["altname"]
                    pair_altname = tradable_asset_pair.loc[asset, reference_asset].loc["index"]
                    
                    # Get the latest timestamp for this asset from existing data
                    latest_timestamp = None
                    if not existing_ohlc_df.empty:
                        asset_data = existing_ohlc_df.xs(asset, level='crypto', drop_level=False) if asset in existing_ohlc_df.index.get_level_values('crypto') else pd.DataFrame()
                        if not asset_data.empty and 'timestamp' in asset_data.columns:
                            latest_timestamp = asset_data['timestamp'].max()
                            logger.info(f"Latest timestamp for {asset}: {latest_timestamp} ({datetime.fromtimestamp(latest_timestamp)})")
                    
                    # Check if we need to fetch new data (avoid calls for very recent timestamps)
                    current_time = datetime.now().timestamp()
                    min_interval_seconds = 1440 * 60 * 2
                    
                    if latest_timestamp is not None and (current_time - latest_timestamp) < min_interval_seconds:
                        logger.info(f"Skipping {asset} - latest data is too recent (less than 1440 minutes ago)")
                        continue
                    
                    logger.info(f"Fetching data for {asset} ({pair_name})")
                    
                    # Get OHLC data with daily interval (1440 minutes) and latest timestamp
                    ohlc_df = self._get_ohlc_data(pair_name, pair_altname, interval=1440, since=latest_timestamp)
                    
                    logger.info(f"Fetched {ohlc_df.shape[0]} rows")
                    
                    if not ohlc_df.empty:
                        # Reset index to get timestamp as column
                        ohlc_df = ohlc_df.reset_index()
                        ohlc_df["date"] = pd.to_datetime(ohlc_df["timestamp"], unit='s').dt.normalize()
                        
                        # Convert close price to Decimal and create records
                        for _, row in ohlc_df.iterrows():
                            price = self._decimal_from_value(row["close"])
                            new_ohlc_data.append({
                                'date': row["date"],
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
            new_ohlc_df = new_ohlc_df.set_index(['date', 'crypto'])
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
            combined_df.index = pd.MultiIndex.from_tuples([], names=['date', 'crypto'])
        
        # Save to parquet file (with timestamp included)
        if not combined_df.empty:
            combined_df.to_parquet(filename, engine="fastparquet", compression="GZIP")
            logger.info(f"Saved OHLC data to {filename}")
        
        logger.info(f"Combined data: {combined_df.shape[0]} records")
        return combined_df
    
    def _normalize_assets_name(self, df, asset_column_name, log_message=False):
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
        
        # Apply basic normalization rules
        df = self._apply_basic_normalization_rules(df)
        
        # Normalized asset list
        assets_in_portfolio = df["assetnorm"].unique()
        if log_message:
            logger.info("Normalized assets:")
            logger.info(assets_in_portfolio)
        
        return df
    
    def _apply_basic_normalization_rules(self, df):
        """
        Apply basic normalization rules to asset names.
        """
        df["assetnorm"] = df["assetnorm"].str.split('.').str[0]
        df["assetnorm"] = df["assetnorm"].str.split('21').str[0]
        df.loc[(df["assetnorm"]=="EUR"),["assetnorm"]] = "ZEUR"
        df.loc[(df["assetnorm"]=="XBT"),["assetnorm"]] = "XXBT"
        df.loc[(df["assetnorm"]=="ETH"),["assetnorm"]] = "XETH"
        
        return df