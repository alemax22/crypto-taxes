#!/usr/bin/env python3
"""
Portfolio Management
Handles multiple wallets/exchanges for a user
"""

import os
import csv
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from cryptography.fernet import Fernet
import sys
import uuid
from enum import Enum

# Add parent directory to path to import config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from wallets.wallet import Wallet
from wallets.wallet_kraken import KrakenWallet
from wallets.wallet_enums import WalletType, WalletSyncStatus
from wallets.wallet_factory import WalletFactory
from config import WALLETS_DIR

logger = logging.getLogger(__name__)

WALLETS_CSV_FILE_NAME = "wallets.csv"
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
WALLET_CONFIG_COLUMNS = [
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
    
    def __init__(self):
        """Initialize the portfolio."""
        self.csv_file_path = os.path.join(WALLETS_DIR, WALLETS_CSV_FILE_NAME)
        self.wallets_data = []
        
        # Initialize wallet factory
        self.wallet_factory = WalletFactory()

        # Encryption key file path
        self.encryption_key_file = os.path.join(WALLETS_DIR, PORTFOLIO_ENCRYPTION_KEY_FILE_NAME)
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.csv_file_path), exist_ok=True)
        
        # Initialize encryption
        self._initialize_encryption()
        
        # Load existing wallets
        self._load_wallets()
        
        logger.info(f"Portfolio initialized with {len(self.wallets_data)} wallets")
    
    def _initialize_encryption(self) -> None:
        """Initialize encryption key for API credentials."""
        if not os.path.exists(self.encryption_key_file):
            logger.info("Creating new encryption key for portfolio")
            self._generate_encryption_key()
        else:
            logger.info("Using existing encryption key")
    
    def _generate_encryption_key(self) -> None:
        """Generate a new encryption key and save it."""
        try:
            key = Fernet.generate_key()
            with open(self.encryption_key_file, "wb") as key_file:
                key_file.write(key)
            logger.info("Encryption key generated successfully")
        except Exception as e:
            logger.error(f"Error generating encryption key: {e}")
            raise
    
    def _load_encryption_key(self) -> bytes:
        """Load the encryption key from file."""
        try:
            with open(self.encryption_key_file, "rb") as key_file:
                return key_file.read()
        except Exception as e:
            logger.error(f"Error loading encryption key: {e}")
            raise
    
    def _encrypt_api_credentials(self, api_key: str, api_secret: str) -> tuple[str, str]:
        """
        Encrypt API credentials.
        
        Args:
            api_key: API key to encrypt
            api_secret: API secret to encrypt
            
        Returns:
            Tuple of (encrypted_api_key, encrypted_api_secret)
        """
        try:
            key = self._load_encryption_key()
            f = Fernet(key)
            
            encrypted_key = f.encrypt(api_key.encode())
            encrypted_secret = f.encrypt(api_secret.encode())
            
            return encrypted_key.decode(), encrypted_secret.decode()
        except Exception as e:
            logger.error(f"Error encrypting API credentials: {e}")
            raise
    
    def _decrypt_api_credentials(self, encrypted_api_key: str, encrypted_api_secret: str) -> tuple[str, str]:
        """
        Decrypt API credentials.
        
        Args:
            encrypted_api_key: Encrypted API key
            encrypted_api_secret: Encrypted API secret
            
        Returns:
            Tuple of (api_key, api_secret)
        """
        try:
            key = self._load_encryption_key()
            f = Fernet(key)
            
            api_key = f.decrypt(encrypted_api_key.encode()).decode()
            api_secret = f.decrypt(encrypted_api_secret.encode()).decode()
            
            return api_key, api_secret
        except Exception as e:
            logger.error(f"Error decrypting API credentials: {e}")
            raise
    
    def _load_wallets(self) -> None:
        """Load wallet configurations from CSV file."""
        if not os.path.exists(self.csv_file_path):
            logger.info(f"CSV file {self.csv_file_path} does not exist. Creating new file.")
            self._create_csv_file()
            return
        
        try:
            with open(self.csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                raw_wallets = list(reader)
                
                # Decrypt API credentials for each wallet
                self.wallets_data = []
                for wallet in raw_wallets:
                    try:
                        if wallet.get('api_key') and wallet.get('api_secret'):
                            api_key, api_secret = self._decrypt_api_credentials(
                                wallet['api_key'], 
                                wallet['api_secret']
                            )
                            wallet['api_key'] = api_key
                            wallet['api_secret'] = api_secret
                    except Exception as e:
                        logger.warning(f"Failed to decrypt credentials for wallet {wallet.get('wallet_id')}: {e}")
                        # Keep the wallet but mark it as inactive
                        wallet['is_active'] = 'false'
                    
                    self.wallets_data.append(wallet)
                
                logger.info(f"Loaded {len(self.wallets_data)} wallets from CSV")
        except Exception as e:
            logger.error(f"Error loading wallets from CSV: {e}")
            self.wallets_data = []
    
    def _create_csv_file(self) -> None:
        """Create a new CSV file with the proper headers."""
        
        try:
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=WALLET_CONFIG_COLUMNS)
                writer.writeheader()
            logger.info(f"Created new CSV file: {self.csv_file_path}")
        except Exception as e:
            logger.error(f"Error creating CSV file: {e}")
    
    def _save_wallets_to_csv(self) -> None:
        """Save wallet configurations to CSV file."""
        
        try:
            # Create a copy of wallets data with encrypted credentials
            encrypted_wallets = []
            for wallet in self.wallets_data:
                encrypted_wallet = wallet.copy()
                
                # Encrypt API credentials before saving
                if wallet.get('api_key') and wallet.get('api_secret'):
                    try:
                        encrypted_key, encrypted_secret = self._encrypt_api_credentials(
                            wallet['api_key'], 
                            wallet['api_secret']
                        )
                        encrypted_wallet['api_key'] = encrypted_key
                        encrypted_wallet['api_secret'] = encrypted_secret
                    except Exception as e:
                        logger.error(f"Failed to encrypt credentials for wallet {wallet.get('wallet_id')}: {e}")
                        # Skip this wallet if encryption fails
                        continue
                
                encrypted_wallets.append(encrypted_wallet)
            
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=WALLET_CONFIG_COLUMNS)
                writer.writeheader()
                writer.writerows(encrypted_wallets)
            logger.info(f"Saved {len(encrypted_wallets)} wallets to CSV")
        except Exception as e:
            logger.error(f"Error saving wallets to CSV: {e}")
    
    def list_wallets(self) -> List[Dict[str, Any]]:
        """List all wallets in the portfolio."""
        # Return a copy without sensitive data
        safe_wallets = []
        for wallet in self.wallets_data:
            safe_wallet = wallet.copy()
            # Remove sensitive data
            safe_wallet.pop('api_key', None)
            safe_wallet.pop('api_secret', None)
            safe_wallets.append(safe_wallet)
        
        return safe_wallets
    
    def get_wallet_by_id(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get wallet configuration by ID."""
        for wallet in self.wallets_data:
            if wallet['wallet_id'] == wallet_id:
                return wallet.copy()
        return None
    
    def load_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Load a wallet instance by ID."""
        wallet_config = self.get_wallet_by_id(wallet_id)

        if not wallet_config:
            logger.error(f"Wallet with ID {wallet_id} not found")
            return None
        
        return self._load_wallet_from_config(wallet_config)
    
    def _load_wallet_from_config(self, wallet_config: Dict[str, Any]) -> Optional[Wallet]:
        """Load a wallet instance from a wallet configuration."""
        try:
            # Use the factory to create wallet instance
            wallet_instance = self.wallet_factory.create_wallet_from_data(wallet_config)
            
            if wallet_instance:
                logger.info(f"Loaded wallet: {wallet_config.get('name')} ({wallet_config.get('wallet_type')})")
            
            return wallet_instance
            
        except Exception as e:
            logger.error(f"Error loading wallet {wallet_config.get('wallet_id', 'unknown')}: {e}")
            return None
    
    def add_wallet(self, 
                   wallet_type: WalletType, 
                   name: str, 
                   reference_fiat: str,
                   api_key: str = None, 
                   api_secret: str = None, 
                   description: str = "",
                   portfolio_id: str = "default_portfolio") -> Optional[str]:
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
        
        # Generate unique wallet ID
        wallet_id = self._generate_wallet_id(wallet_type.value, name)
        
        # Create wallet configuration with plain text credentials (will be encrypted when saved)
        wallet_config = {
            'wallet_id': wallet_id,
            'wallet_type': wallet_type.value,
            'name': name,
            'description': description,
            'api_key': api_key,
            'api_secret': api_secret,
            'is_active': False,
            'created_datetime': datetime.now(timezone.utc).isoformat(),
            'updated_datetime': None,
            'reference_fiat': reference_fiat,
            'sync_status': WalletSyncStatus.NOT_SYNCHRONIZED.value,
            'portfolio_id': portfolio_id,
        }
        
        try:
            # Test the wallet by creating an instance
            wallet_instance = self._load_wallet_from_config(wallet_config)
            if not wallet_instance:
                logger.error("Failed to create wallet instance")
                return None
            
            # Test authentication
            if wallet_instance.authenticate():
                wallet_config['is_active'] = True
            else:
                logger.error(f"Authentication failed for wallet {name}. Wallet will not be added.")
                return None
            
            # Add to portfolio
            self.wallets_data.append(wallet_config)
            self._save_wallets_to_csv()
            
            logger.info(f"Added wallet: {name} ({wallet_type}) with ID: {wallet_id}")
            return wallet_id
            
        except Exception as e:
            logger.error(f"Error adding wallet: {e}")
            return None
    
    def remove_wallet(self, wallet_id: str) -> bool:
        """Remove a wallet from the portfolio."""
        # Find and remove the wallet
        for i, wallet in enumerate(self.wallets_data):
            if wallet['wallet_id'] == wallet_id:
                removed_wallet = self.wallets_data.pop(i)
                self._save_wallets_to_csv()
                logger.info(f"Removed wallet: {removed_wallet.get('name')} ({wallet_id})")
                return True
        
        logger.error(f"Wallet with ID {wallet_id} not found")
        return False
    
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

        for wallet_config in self.wallets_data:
            wallet_id = wallet_config['wallet_id']
            wallet_name = wallet_config['name']
            
            try:
                wallet_instance = self.load_wallet(wallet_id)
                if wallet_instance:
                    logger.info(f"Synchronizing wallet: {wallet_name}")
                    # Check if wallet is active
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
                    _, wallet_updated_datetime = wallet_instance.get_sync_status()
                    wallet_config['updated_datetime'] = wallet_updated_datetime.isoformat()
                    wallet_config['is_active'] = is_active
                else:
                    results[wallet_id] = {
                        'name': wallet_name,
                        'success': False,
                        'error': 'Failed to load wallet instance'
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