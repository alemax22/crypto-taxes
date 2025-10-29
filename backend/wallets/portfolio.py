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
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path to import config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wallets.wallet import Wallet
from wallets.wallet_enums import WalletSyncStatus, WalletType
from wallets.wallet_factory import WalletFactory
from wallets.wallet_repository import PostgresWalletRepository

logger = logging.getLogger(__name__)

class Portfolio:
    """Portfolio class representing a portfolio entity that contains multiple wallets."""
    
    def __init__(self, 
                 user_id: str,
                 portfolio_id: str,
                 reference_asset: str,
                 created_datetime: Optional[datetime],
                 updated_datetime: Optional[datetime]):
        """
        Initialize a portfolio.
        
        Args:
            user_id: Unique identifier for the user owning the portfolio.
            portfolio_id: Unique identifier for the portfolio.
            reference_asset: Reference asset for the portfolio (e.g., "EUR", "USD")
            created_datetime: Creation datetime.
            updated_datetime: Last updated datetime.
        """

        self.user_id = user_id
        self.wallet_factory = WalletFactory()
        self.repository = PostgresWalletRepository()
        self.portfolio_id = portfolio_id
        self.reference_asset = reference_asset
        self.created_datetime = created_datetime
        self.updated_datetime = updated_datetime
        
        logger.info(f"Portfolio initialized with ID: {self.portfolio_id}, reference asset: {self.reference_asset}")
    
    def add_wallet(self, 
                   wallet_type: WalletType, 
                   name: str, 
                   api_key: str = None, 
                   api_secret: str = None, 
                   description: str = "") -> Optional[Wallet]:
        """
        Add a new wallet to this portfolio.
        
        Args:
            wallet_type: Type of wallet to create
            name: Name of the wallet
            api_key: API key for authentication
            api_secret: API secret for authentication
            description: Description of the wallet
            
        Returns:
            Wallet instance if successful, None otherwise
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
                
            # Authenticate wallet
            is_wallet_authenticated = wallet_instance.authenticate()
            if not is_wallet_authenticated:
                logger.error(f"Authentication failed for wallet {name}. Wallet will not be added.")
                return None
                    
            # Persist wallet to database
            is_wallet_saved = self.repository.save_wallet(wallet_instance)
            if is_wallet_saved:
                logger.info(f"Added wallet: {name} ({wallet_type}) with ID: {wallet_instance.id} to portfolio {self.portfolio_id}")
                return wallet_instance
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
    
    def list_wallets(self) -> List[Wallet]:
        """
        List all wallets in this portfolio.
        
        Returns:
            List of wallet instances
        """
        wallets = self.repository.get_all_wallets_in_portfolio(self.portfolio_id)
        return wallets
    
    def get_wallet_by_id(self, wallet_id: str) -> Optional[Wallet]:
        """
        Get wallet configuration by ID.
        
        Args:
            wallet_id: ID of the wallet to retrieve
            
        Returns:
            Wallet instance, or None if not found
        """
        wallet = self.repository.get_wallet_by_id(wallet_id)

        if wallet is None:
            logger.info(f"Wallet {wallet_id} not found in portfolio {self.portfolio_id}")
            return None
        elif not self.is_wallet_in_portfolio(wallet):
            logger.error(f"Wallet {wallet_id} does not belong to portfolio {self.portfolio_id}")
            return None
        else:
            logger.info(f"Wallet {wallet_id} found in portfolio {self.portfolio_id}")
        
        return wallet
    
    def _synchronize_single_wallet(self, wallet_instance: Wallet, start_date: Optional[str] = None) -> tuple[str, Dict[str, Any]]:
        """
        Synchronize a single wallet.
        
        Args:
            wallet_instance: Wallet instance to synchronize
            start_date: Start date for synchronization (YYYY-MM-DD format)
            
        Returns:
            Tuple of (wallet_id, result_dict)
        """
        wallet_id = wallet_instance.id
        wallet_name = wallet_instance.name
        
        try:
            # Check if synchronization is already in progress
            if wallet_instance.sync_status == WalletSyncStatus.IN_PROGRESS:
                logger.info(f"Synchronization already in progress for wallet {wallet_name}")
                return wallet_id, {
                    'name': wallet_name,
                    'success': False,
                    'error': 'Synchronization already in progress'
                }
            logger.info(f"Synchronizing wallet: {wallet_name} in portfolio {self.portfolio_id}")
            
            is_wallet_authenticated = wallet_instance.authenticate()
            if is_wallet_authenticated:
                success, error = wallet_instance.synchronize(start_date)
                logger.info(f"Synchronization result for wallet {wallet_name}: {success} {error}")
                result = {
                    'name': wallet_name,
                    'success': success,
                    'error': error
                }
            else:
                logger.error(f"Authentication failed for wallet {wallet_name}. Skipping synchronization.")
                result = {
                    'name': wallet_name,
                    'success': False,
                    'error': 'Authentication failed'
                }
        except Exception as e:
            result = {
                'name': wallet_name,
                'success': False,
                'error': str(e)
            }
        
        return wallet_id, result

    def synchronize_all_wallets(self, start_date: Optional[str] = None, max_workers: Optional[int] = None) -> Dict[str, Any]:
        """
        Synchronize all active wallets in this portfolio in parallel.
        
        Args:
            start_date: Start date for synchronization (YYYY-MM-DD format)
            max_workers: Maximum number of worker threads. If None, uses min(32, os.cpu_count() + 4)
        
        Returns:
            Dictionary with synchronization results for each wallet
        """
        results = {}
        wallets = self.repository.get_all_wallets_in_portfolio(self.portfolio_id)
        
        if not wallets:
            logger.info(f"No wallets found in portfolio {self.portfolio_id}")
            return results
        
        logger.info(f"Starting parallel synchronization of {len(wallets)} wallets in portfolio {self.portfolio_id}")
        
        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            
            # Submit all wallet synchronization tasks
            future_to_wallet = {
                executor.submit(self._synchronize_single_wallet, wallet, start_date): wallet
                for wallet in wallets
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_wallet):
                wallet = future_to_wallet[future]
                try:
                    wallet_id, result = future.result()
                    results[wallet_id] = result
                    logger.info(f"Completed synchronization for wallet {result['name']}: {'Success' if result['success'] else 'Failed'}")
                except Exception as e:
                    wallet_id = wallet.id
                    wallet_name = wallet.name
                    logger.error(f"Unexpected error during synchronization of wallet {wallet_name}: {e}")
                    results[wallet_id] = {
                        'name': wallet_name,
                        'success': False,
                        'error': f'Unexpected error: {str(e)}'
                    }
        
        logger.info(f"Completed parallel synchronization of {len(wallets)} wallets in portfolio {self.portfolio_id}")
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
        format='%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s:%(process)d] - %(message)s'
    )
    
    # Create a new portfolio
    portfolio = Portfolio(user_id="1234567890", portfolio_id="PF-1234567890", reference_asset="EUR")
    print(f"Created portfolio: {portfolio.portfolio_id}")
    
    # Load API credentials
    with open("api.key", "r") as file:
        api_key = file.readline().strip()
        api_secret = file.readline().strip()
    logging.info(f"API key and secret loaded")
    
    # Add a wallet to the portfolio
    wallet = portfolio.add_wallet(
        wallet_type=WalletType.KRAKEN,
        name="Kraken Test Wallet",
        api_key=api_key,
        api_secret=api_secret
    )
    
    if wallet:
        print(f"Added wallet with ID: {wallet.id}")
        print(f"Portfolio wallets: {portfolio.list_wallets()}")
        
        # Synchronize all wallets
        results = portfolio.synchronize_all_wallets()
        print(f"Synchronization results: {results}")
        
        # Remove the wallet
        portfolio.remove_wallet(wallet.id)
        print(f"After removal: {portfolio.list_wallets()}")
    else:
        print("Failed to add wallet")