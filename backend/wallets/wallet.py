#!/usr/bin/env python3
"""
Generic Wallet Class
Base class for all wallet/exchange implementations
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class Wallet(ABC):
    """
    Abstract base class for wallet/exchange implementations.
    
    This class provides a common interface for different cryptocurrency
    exchanges and wallets, allowing for unified data synchronization
    and management.
    """
    
    def __init__(self, name: str, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize the wallet.
        
        Args:
            name: Name of the wallet/exchange
            api_key: API key for authentication (optional)
            api_secret: API secret for authentication (optional)
        """
        self.name = name
        self.api_key = api_key
        self.api_secret = api_secret
        self.last_sync = None
        self.is_authenticated = False
        
        logger.info(f"Initialized {self.name} wallet")
    
    @abstractmethod
    def synchronize(self, start_date: Optional[str] = None) -> Dict[str, Any]:
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
        """
        return False, None
    
    @abstractmethod
    def get_balance(self) -> pd.DataFrame:
        """
        Get current balance from the local data.
        Pay attention that it does not trigger the synchronization of the data!
        
        Returns:
            DataFrame with asset balances
        """
        return pd.DataFrame()
    
    @abstractmethod
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
    def authenticate(self) -> bool:
        """
        Validate that the wallet has the necessary credentials and that they are valid.
        This method should be used to validate the credentials before attempting to synchronize data.
        In case of API tokens, it should check that they have all the necessary permissions.

        Returns:
            bool: True if credentials are present and valid, False otherwise
        """
        return False
    
    def update_last_sync(self):
        """Update the last synchronization timestamp."""
        self.last_sync = datetime.now()
        logger.info(f"{self.name}: Last sync updated to {self.last_sync}")
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get the current synchronization status.
        
        Returns:
            Dict with sync status information
        """
        return {
            'name': self.name,
            'is_authenticated': self.is_authenticated,
            'last_sync': self.last_sync,
            'has_credentials': self.validate_credentials()
        }
    
    def __str__(self) -> str:
        """String representation of the wallet."""
        return f"{self.name} Wallet (Authenticated: {self.is_authenticated}, Last Sync: {self.last_sync})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the wallet."""
        return f"Wallet(name='{self.name}', authenticated={self.is_authenticated}, last_sync={self.last_sync})" 