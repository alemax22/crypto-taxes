#!/usr/bin/env python3
"""
Portfolio Management
Handles portfolio entities that contain multiple wallets/exchanges
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import sys
import uuid
from enum import Enum

# Add parent directory to path to import config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wallets.wallet import Wallet
from wallets.wallet_enums import WalletType, WalletSyncStatus
from wallets.wallet_factory import WalletFactory
from wallets.wallet_repository import PostgresWalletRepository

logger = logging.getLogger(__name__)

class Portfolio:
    """Portfolio class representing a portfolio entity that contains multiple wallets."""
    
    def __init__(self, 
                 portfolio_id: Optional[str] = None,
                 reference_asset: str = "EUR",
                 created_datetime: Optional[datetime] = None):
        """
        Initialize a portfolio.
        
        Args:
            portfolio_id: Unique identifier for the portfolio. If None, generates a new one with PF- prefix
            reference_asset: Reference asset for the portfolio (e.g., "EUR", "USD")
            created_datetime: Creation datetime. If None, uses current UTC time
        """
        self.wallet_factory = WalletFactory()
        self.repository = PostgresWalletRepository()
        
        # Generate portfolio ID if not provided
        if portfolio_id is None:
            self.portfolio_id = f"PF-{str(uuid.uuid4())}"
        else:
            self.portfolio_id = portfolio_id
            
        self.reference_asset = reference_asset
        self.created_datetime = created_datetime or datetime.now(timezone.utc)
        
        logger.info(f"Portfolio initialized with ID: {self.portfolio_id}, reference asset: {self.reference_asset}")
    
    def add_wallet(self, 
                   wallet_type: WalletType, 
                   name: str, 
                   api_key: str = None, 
                   api_secret: str = None, 
                   description: str = "") -> Optional[str]:
        """
        Add a new wallet to this portfolio.
        
        Args:
            wallet_type: Type of wallet to create
            name: Name of the wallet
            api_key: API key for authentication
            api_secret: API secret for authentication
            description: Description of the wallet
            skip_auth: Skip authentication check (for testing)
            
        Returns:
            Wallet ID if successful, None otherwise
        """
    
        try:
            wallet_instance = self.wallet_factory.create_wallet(
                wallet_type=wallet_type,
                name=name,
                reference_fiat=self.reference_asset,
                portfolio_id=self.portfolio_id,
                description=description,
                api_key=api_key,
                api_secret=api_secret,
            )
            
            if not wallet_instance:
                logger.error("Failed to create wallet instance")
                return None
                
            # Test authentication
            if not wallet_instance.authenticate():
                logger.error(f"Authentication failed for wallet {name}. Wallet will not be added.")
                return None
                    
            # Persist wallet
            if self.repository.save_wallet(wallet_instance):
                logger.info(f"Added wallet: {name} ({wallet_type}) with ID: {wallet_instance.id} to portfolio {self.portfolio_id}")
                return wallet_instance.id
            else:
                logger.error("Failed to persist wallet")
                return None
                
        except Exception as e:
            logger.error(f"Error adding wallet: {e}")
            return None
    
    def remove_wallet(self, wallet_id: str) -> bool:
        """
        Remove a wallet from this portfolio.
        
        Args:
            wallet_id: ID of the wallet to remove
            
        Returns:
            True if successful, False otherwise
        """
        wallet = self.get_wallet_by_id(wallet_id)
        if wallet is None or not self.is_wallet_in_portfolio(wallet):
            logger.error(f"Wallet {wallet_id} does not belong to portfolio {self.portfolio_id}")
            return False
        success = self.repository.delete_wallet_by_id(wallet_id)
        if success:
            logger.info(f"Removed wallet {wallet_id} from portfolio {self.portfolio_id}")
        else:
            logger.error(f"Failed to remove wallet {wallet_id} from portfolio {self.portfolio_id}")
        return success
    
    def list_wallets(self) -> List[Dict[str, Any]]:
        """
        List all wallets in this portfolio.
        
        Returns:
            List of wallet dictionaries (without sensitive data)
        """
        wallets = self.repository.get_all_wallets_in_portfolio(self.portfolio_id)
        return wallets
    
    def get_wallet_by_id(self, wallet_id: str) -> Optional[Wallet]:
        """
        Get wallet configuration by ID.
        
        Args:
            wallet_id: ID of the wallet to retrieve
            
        Returns:
            Wallet dictionary with sensitive data, or None if not found
        """
        wallet = self.repository.get_wallet_by_id(wallet_id)

        if wallet is not None and not self.is_wallet_in_portfolio(wallet):
            logger.error(f"Wallet {wallet_id} does not belong to portfolio {self.portfolio_id}")
            return None

        return wallet
    
    def synchronize_all_wallets(self, start_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronize all active wallets in this portfolio.
        
        Args:
            start_date: Start date for synchronization (YYYY-MM-DD format)
            
        Returns:
            Dictionary with synchronization results for each wallet
        """
        results = {}
        
        # TODO: Parallelize the synchronization

        wallets = self.repository.get_all_wallets_in_portfolio(self.portfolio_id)
        for wallet_instance in wallets:
            wallet_id = wallet_instance.id
            wallet_name = wallet_instance.name
            
            try:
                logger.info(f"Synchronizing wallet: {wallet_name} in portfolio {self.portfolio_id}")
                is_active = wallet_instance.authenticate()
                if is_active:
                    success, error = wallet_instance.synchronize(start_date)
                    logging.info(f"Synchronization result for wallet {wallet_name}: {success} {error}")
                    results[wallet_id] = {
                        'name': wallet_name,
                        'success': success,
                        'error': error
                    }
                else:
                    logger.error(f"Authentication failed for wallet {wallet_name}. Skipping synchronization.")
                    results[wallet_id] = {
                        'name': wallet_name,
                        'success': False,
                        'error': 'Authentication failed'
                    }
            except Exception as e:
                results[wallet_id] = {
                    'name': wallet_name,
                    'success': False,
                    'error': str(e)
                }
        
        return results

    def is_wallet_in_portfolio(self, wallet: Wallet) -> bool:
        """
        Check if a wallet is in a portfolio.
        
        Args:
            portfolio: Portfolio instance
            wallet_id: ID of the wallet to check
        """
        return wallet.portfolio_id == self.portfolio_id

if __name__ == "__main__":  # pragma: no cover
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create a new portfolio
    portfolio = Portfolio(reference_asset="EUR")
    print(f"Created portfolio: {portfolio.to_dict()}")
    
    # Load API credentials
    with open("api.key", "r") as file:
        api_key = file.readline().strip()
        api_secret = file.readline().strip()
    logging.info(f"API key and secret loaded")
    
    # Add a wallet to the portfolio
    wallet_id = portfolio.add_wallet(
        wallet_type=WalletType.KRAKEN,
        name="Kraken Ale",
        api_key=api_key,
        api_secret=api_secret
    )
    
    if wallet_id:
        print(f"Added wallet with ID: {wallet_id}")
        print(f"Portfolio wallets: {portfolio.list_wallets()}")
        
        # Synchronize all wallets
        results = portfolio.synchronize_all_wallets()
        print(f"Synchronization results: {results}")
        
        # Remove the wallet
        portfolio.remove_wallet(wallet_id)
        print(f"After removal: {portfolio.list_wallets()}")
    else:
        print("Failed to add wallet")