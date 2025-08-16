#!/usr/bin/env python3
"""
Portfolio Management
Handles multiple wallets/exchanges for a user
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

PORTFOLIO_ENCRYPTION_KEY_FILE_NAME = "portfolio_key.key"

'''
wallet_id: str - unique identifier for the wallet
wallet_type: str - type of the wallet (Kraken, Binance, etc.)
name: str - name of the wallet, given by the user
description: str - description of the wallet (optional)
api_key: str - API key for the wallet
api_secret: str - API secret for the wallet
is_active: bool - whether the wallet is active, wallet method authenticate() must return True. 
                  Even though we don't save inactive wallets, it might happen that a wallet becomes inactive after being added.
created_datetime: datetime - date and time when the wallet was created
updated_datetime: datetime - date and time when the wallet was last updated, updated when wallet method synchronize() is called
reference_fiat: str - reference fiat of the wallet
sync_status: str - status of the synchronization process
    - not synchronized: the wallet has not been synchronized yet
    - in progress: the synchronization is in progress
    - completed: the synchronization has been completed
    - failed: the synchronization has failed
'''
WALLET_CONFIG_COLUMNS: List[str] = [
    'wallet_id',
    'wallet_type',
    'name',
    'description',
    'api_key',
    'api_secret',
    'is_active',
    'created_datetime',
    'updated_datetime',
    'reference_fiat',
    'sync_status',
    'portfolio_id',
]

class Portfolio:
    """Portfolio class to manage multiple wallets/exchanges."""
    
    def __init__(self, portfolio_id: str = "default_portfolio"):
        """Initialize the portfolio (DB-backed)."""
        self.wallet_factory = WalletFactory()
        self.repository = PostgresWalletRepository()
        self.portfolio_id = portfolio_id
        logger.info("Portfolio initialized (DB-backed)")
    
    # DB-backed implementation helpers
    def _wallet_to_dict(self, wallet: Wallet, include_sensitive: bool = True) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            'wallet_id': wallet.id,
            'wallet_type': wallet.get_wallet_type().value,
            'name': wallet.name,
            'description': wallet.description or '',
            'is_active': bool(wallet.is_active),
            'created_datetime': '',
            'updated_datetime': None,
            'reference_fiat': wallet.reference_fiat,
            'sync_status': (wallet.sync_status.value if wallet.sync_status else WalletSyncStatus.NOT_SYNCHRONIZED.value),
            'portfolio_id': wallet.portfolio_id,
        }
        if include_sensitive:
            data['api_key'] = wallet.api_key
            data['api_secret'] = wallet.api_secret
        return data
    
    def list_wallets(self) -> List[Dict[str, Any]]:
        """List all wallets in the portfolio."""
        wallets = self.repository.get_all_wallets_in_portfolio(self.portfolio_id)
        return [self._wallet_to_dict(w, include_sensitive=False) for w in wallets]
    
    def get_wallet_by_id(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get wallet configuration by ID."""
        wallet = self.repository.get_wallet_by_id(wallet_id, self.portfolio_id)
        return self._wallet_to_dict(wallet) if wallet else None
    
    def load_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Load a wallet instance by ID."""
        return self.repository.get_wallet_by_id(wallet_id, self.portfolio_id)
    
    def _load_wallet_from_config(self, wallet_config: Dict[str, Any]) -> Optional[Wallet]:
        """Deprecated in DB-backed implementation."""
        return None
    
    def add_wallet(self, 
                   wallet_type: WalletType, 
                   name: str, 
                   reference_fiat: str,
                   api_key: str = None, 
                   api_secret: str = None, 
                   description: str = "",
                   portfolio_id: str = "default_portfolio",
                   skip_auth: bool = False) -> Optional[str]:
        """Add a new wallet to the portfolio."""
        # Validate wallet type by attempting to create a test instance
        test_wallet = self.wallet_factory.create_wallet(
            wallet_type=wallet_type,
            name="test",
            reference_fiat=reference_fiat,
            portfolio_id=portfolio_id,
            id="test"
        )
        if not test_wallet:
            logger.error(f"Unsupported wallet type: {wallet_type.value}")
            return None
        
        # Generate unique wallet ID (keep previous pattern)
        wallet_id = self._generate_wallet_id(wallet_type.value, name)
        try:
            wallet_instance = self.wallet_factory.create_wallet(
                wallet_type=wallet_type,
                name=name,
                reference_fiat=reference_fiat,
                portfolio_id=portfolio_id,
                id=wallet_id,
                description=description,
                api_key=api_key,
                api_secret=api_secret,
                is_active=False,
                sync_status=WalletSyncStatus.NOT_SYNCHRONIZED,
            )
            if not wallet_instance:
                logger.error("Failed to create wallet instance")
                return None
            # Test authentication unless skipped (for integration tests/dev)
            if not skip_auth:
                if wallet_instance.authenticate():
                    wallet_instance.is_active = True
                else:
                    logger.error(f"Authentication failed for wallet {name}. Wallet will not be added.")
                    return None
            # Persist
            if self.repository.save_wallet(wallet_instance):
                logger.info(f"Added wallet: {name} ({wallet_type}) with ID: {wallet_id}")
                return wallet_id
            logger.error("Failed to persist wallet")
            return None
        except Exception as e:
            logger.error(f"Error adding wallet: {e}")
            return None
    
    def remove_wallet(self, wallet_id: str) -> bool:
        """Remove a wallet from the portfolio."""
        return self.repository.delete_wallet_by_id(wallet_id, self.portfolio_id)
    
    def synchronize_all_wallets(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronize all active wallets.
        
        Args:
            start_date: Start date for synchronization (YYYY-MM-DD format)
            end_date: End date for synchronization (YYYY-MM-DD format)
            
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
                logger.info(f"Synchronizing wallet: {wallet_name}")
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
    
    def _generate_wallet_id(self, wallet_type: str, name: str) -> str:
        """Generate a unique wallet ID."""
        # Create base ID from type and name (remove "Wallet" suffix if present)
        base_name = wallet_type.replace("Wallet", "")
        base_id = f"{base_name.upper()}"
        
        # Generate a random UUID
        uuid_str = str(uuid.uuid4())
        wallet_id = f"{base_id}-{uuid_str}"
        
        return wallet_id

if __name__ == "__main__":  # pragma: no cover
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    with open("api.key", "r") as file:
        api_key = file.readline().strip()
        api_secret = file.readline().strip()
    logging.info(f"API key and secret loaded")
    portfolio = Portfolio()
    logging.info(portfolio.list_wallets())
    wallet_id = portfolio.add_wallet(
        wallet_type=WalletType.KRAKEN,
        name="Kraken Ale",
        reference_fiat="EUR",
        api_key=api_key,
        api_secret=api_secret
    )
    results = portfolio.synchronize_all_wallets()
    logging.info(results)
    portfolio.remove_wallet(wallet_id)
    print(portfolio.list_wallets())