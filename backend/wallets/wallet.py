#!/usr/bin/env python3
"""
Generic Wallet Class
Base class for all wallet/exchange implementations
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal, InvalidOperation
import pandas as pd
import logging
import os
import sys
import numpy as np

# Add parent directory to path to import config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import RESAMPLING_INTERVAL_IN_SECONDS
from config import TRANSACTION_REQUIRED_COLUMNS

logger = logging.getLogger(__name__)

class Wallet(ABC):
    """
    Abstract base class for wallet/exchange implementations.
    
    This class provides a common interface for different cryptocurrency
    exchanges and wallets, allowing for unified data synchronization
    and management.
    """
    
    def __init__(self, name: str, reference_fiat: str, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize the wallet.
        
        Args:
            name: Name of the wallet/exchange
            api_key: API key for authentication (optional)
            api_secret: API secret for authentication (optional)
        """
        self.name = name
        self.reference_fiat = reference_fiat
        self.api_key = api_key
        self.api_secret = api_secret
        self.last_sync = None
        self.is_authenticated = False
        # Status of the synchronization process
        # - not synchronized: the wallet has not been synchronized yet
        # - in progress: the synchronization is in progress
        # - completed: the synchronization has been completed
        # - failed: the synchronization has failed
        self.sync_status = "not synchronized"
        
        logger.info(f"Initialized {self.name} wallet")
    
    @abstractmethod
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
        
        Example:

        self.sync_status = "in progress"
        time.sleep(1)
        self.sync_status = "completed"
        self.last_sync = datetime.now()

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
        - balance: float (the balance of the asset at the time of the transaction)
        - asset_price_in_reference_fiat: decimal
        - fee: decimal
        - transaction_original_type: str (value coming from the exchange)
        - asset_original_name: str (value coming from the exchange)
        - asset_original_balance: str (value coming from the exchange)

        """
        return False, None
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Validate that the wallet has the necessary credentials and that they are valid.
        This method should be used to validate the credentials before attempting to synchronize data.
        In case of API tokens, it should check that they have all the necessary permissions.

        Returns:
            bool: True if credentials are present and valid, False otherwise
        """
        return False
    
    def get_balance(self) -> pd.DataFrame:
        """
        Get current balance from the local data.
        Pay attention that it does not trigger the synchronization of the data!
        
        Returns:
            DataFrame with asset balances
            - asset: str
            - balance: float (total balance of the asset)
            - balance_in_reference_fiat: float (total balance of the asset in the reference fiat)
            - asset_price_in_reference_fiat: float (price of the asset in the reference fiat)
            - timestamp: int (timestamp of the ohlc data used to compute the balance in reference fiat)
        """

        balance_df = pd.DataFrame()

        if self.last_sync is not None:
            existing_df = self._retrieve_local_ledger_data()
            if not existing_df.empty:
                existing_df.sort_values(by="datetime", ascending=False, inplace=True)
                balance_df = existing_df.groupby("asset")["balance"].first().reset_index()
                balance_df["timestamp"] = (datetime.now().timestamp() - RESAMPLING_INTERVAL_IN_SECONDS) // RESAMPLING_INTERVAL_IN_SECONDS * RESAMPLING_INTERVAL_IN_SECONDS
                
                # Get unique assets from transactions for OHLC data
                assets_in_transactions = balance_df["asset"].unique().tolist()
                
                # Fetch OHLC data for price calculations of the asset without price in reference fiat
                ohlc_df = self._get_ohlc_data(
                    assets_in_portfolio=assets_in_transactions,
                )

                # Convert price to float
                ohlc_df["price"] = ohlc_df["price"].astype(float)

                # Reset index
                ohlc_df.reset_index(inplace=True)

                # Merge the DataFrames on both asset and timestamp
                balance_df = pd.merge(
                    balance_df,
                    ohlc_df[['timestamp', 'asset', 'price']], 
                    how='left',
                    on=['asset', 'timestamp'], 
                    suffixes=('', '_ohlc')
                )
                
                # Asset price in reference fiat MUST be a Decimal as of our column definition
                balance_df["asset_price_in_reference_fiat"] = balance_df["price"].apply(self._decimal_from_value)
                # The conversion to float is an overhead, but we keep it to maintain consistency in the column definitions
                balance_df["balance_in_reference_fiat"] = balance_df["balance"] * balance_df["asset_price_in_reference_fiat"].astype(float)
                # Convert to float first, then round
                balance_df["balance_in_reference_fiat"] = balance_df["balance_in_reference_fiat"].astype(float).round(2)
                balance_df = balance_df.drop(columns=["price"])
            else:
                logger.warning("No local ledger data found") 
        else:
            logger.warning("Wallet has not been synchronized yet")

        return balance_df
    
    def get_transactions(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get transaction history from the local data.
        Pay attention that it does not trigger the synchronization of the data!
        
        Args:
            start_date: Start date for transaction history (YYYY-MM-DD format)
            end_date: End date for transaction history (YYYY-MM-DD format)
            
        Returns:
            DataFrame with transaction history
        """
        return pd.DataFrame()


    @abstractmethod
    def _get_ohlc_data(self, assets_in_portfolio: List[str], start_date: Optional[str] = None) -> pd.DataFrame:
        """
        Get OHLC data for a list of assets.
        """
        return pd.DataFrame()

    def get_sync_status(self) -> tuple[str, Optional[datetime]]:
        """
        Get the current synchronization status.
        
        Returns:
            Tuple with sync status and last sync timestamp
        """
        return self.sync_status, self.last_sync
    
    def _retrieve_local_ledger_data(self) -> pd.DataFrame:
        """Retrieve local ledger data."""

        result_df = pd.DataFrame(columns=TRANSACTION_REQUIRED_COLUMNS)

        if os.path.exists(self.ledger_file):
            try:
                existing_df = pd.read_parquet(self.ledger_file, engine="fastparquet", columns=TRANSACTION_REQUIRED_COLUMNS)
                
                # Convert columns to Decimal (parquet does not support Decimal)
                existing_df["amount"] = existing_df["amount"].apply(self._decimal_from_value)
                existing_df["fee"] = existing_df["fee"].apply(self._decimal_from_value)
                existing_df["asset_price_in_reference_fiat"] = existing_df["asset_price_in_reference_fiat"].apply(self._decimal_from_value)

                # If the conversion is successful, return the existing dataframe
                result_df = existing_df

                logger.info(f"Loaded {len(existing_df)} existing transactions")
            except Exception as e:
                logger.error(f"Error loading existing ledger data: {e}")
        else:
            logger.info(f"No local ledger data found in {self.ledger_file}")
        return result_df

    def _save_local_ledger_data(self, df: pd.DataFrame) -> None:
        """Save local ledger data to file."""
        
        ledger_parquet_df = df.copy()

        try:   
            # Convert columns to specific types before saving (parquet does not support Decimal)
            ledger_parquet_df = ledger_parquet_df.astype({
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
            
            # Check that the dataframe has all the required columns
            ledger_parquet_df = ledger_parquet_df[TRANSACTION_REQUIRED_COLUMNS]

            # Save to file
            ledger_parquet_df.to_parquet(self.ledger_file, engine="fastparquet", compression="GZIP")
            
        except Exception as e:
            logger.error(f"Error saving local ledger data: {e}")

    def __str__(self) -> str:
        """String representation of the wallet."""
        return f"{self.name} Wallet (Authenticated: {self.is_authenticated}, Last Sync: {self.last_sync})"
    
    def _decimal_from_value(self, value: Any) -> Decimal:
        """Convert value to Decimal."""
        return Decimal(value)
    
    def __repr__(self) -> str:
        """Detailed string representation of the wallet."""
        return f"Wallet(name='{self.name}', authenticated={self.is_authenticated}, last_sync={self.last_sync})" 