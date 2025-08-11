
#!/usr/bin/env python3
"""
Wallet Repository
Domain-Driven Design repository for wallet persistence and retrieval
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import os
import csv
import logging
from cryptography.fernet import Fernet
import sys
import uuid

# Add parent directory to path to import config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import WALLETS_DIR
from wallets.wallet import Wallet
from wallets.wallet_factory import WalletFactory

logger = logging.getLogger(__name__)

PORTFOLIO_ENCRYPTION_KEY_FILE_NAME = "portfolio_key.key"

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

class WalletRepository(ABC):
    """
    Abstract wallet repository interface.
    
    This interface defines the contract for wallet persistence operations
    in a Domain-Driven Design architecture.
    """
    
    @abstractmethod
    def save_wallet(self, wallet: Wallet) -> bool:
        """
        Save a wallet configuration to the repository.
        
        Args:
            wallet: Wallet instance
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_wallet_by_id(self, wallet_id: str, portfolio_id: str) -> Optional[Wallet]:
        """
        Find a wallet configuration by its ID.
        
        Args:
            wallet_id: Unique identifier of the wallet
            portfolio_id: Unique identifier of the portfolio
        Returns:
            Dict containing wallet configuration or None if not found
        """
        pass
    
    @abstractmethod
    def get_all_wallets_in_portfolio(self, portfolio_id: str) -> List[Wallet]:
        """
        Retrieve all wallet configurations from the repository for a given portfolio.
        
        Args:
            portfolio_id: Unique identifier of the portfolio
            
        Returns:
            List of wallet instances
        """
        pass
    
    @abstractmethod
    def delete_wallet_by_id(self, wallet_id: str, portfolio_id: str) -> bool:
        """
        Delete a wallet from the repository.
        
        Args:
            wallet_id: Unique identifier of the wallet to delete
            portfolio_id: Unique identifier of the portfolio
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        pass

    @abstractmethod
    def save_all_wallets(self, wallet_list: List[Wallet]) -> None:
        """
        Save all wallet data to the repository.
        It does not remove wallets that are not in the list.
        
        Args:
            wallet_list: List of wallet instances
        """
        pass

class CsvWalletRepository(WalletRepository):
    """
    CSV-based implementation of the wallet repository.
    
    This implementation stores wallet configurations in a CSV file
    with encrypted API credentials for security.

    In particular, there will be one file for each portfolio, whose name is PORTFOLIO-ID.csv
    """
    
    def __init__(self):
        """
        Initialize the CSV wallet repository.
        """
        self.wallets_dir = WALLETS_DIR
        self.encryption_key_file = os.path.join(self.wallets_dir, PORTFOLIO_ENCRYPTION_KEY_FILE_NAME)
        
        # Initialize wallet factory
        self.wallet_factory = WalletFactory()
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.wallets_dir), exist_ok=True)
        
        # Initialize encryption
        self._initialize_encryption()
    
    def _initialize_encryption(self) -> None:
        """Initialize encryption key for API credentials."""
        if not os.path.exists(self.encryption_key_file):
            logger.info("Creating new encryption key for wallet repository")
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
    
    def _create_csv_file(self) -> None:
        """Create a new CSV file with the proper headers."""
        try:
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=WALLET_CONFIG_COLUMNS)
                writer.writeheader()
            logger.info(f"Created new CSV file: {self.csv_file_path}")
        except Exception as e:
            logger.error(f"Error creating CSV file: {e}")
            raise
    
    def _load_portfolio_wallets(self, portfolio_id: str) -> List[Wallet]:
        """Load all wallets from CSV file."""
        wallet_list = []
        
        try:
            with open(self.csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                raw_wallets = list(reader)

                # Decrypt API credentials for each wallet and filter out wallets that are not in the portfolio
                for wallet_data in raw_wallets:
                    
                    # Filter out wallets that are not in the portfolio
                    if wallet_data.get('portfolio_id') == portfolio_id:  
                        try:
                            if wallet_data.get('api_key') and wallet_data.get('api_secret'):
                                api_key, api_secret = self._decrypt_api_credentials(
                                    wallet_data['api_key'], 
                                    wallet_data['api_secret']
                                )
                                wallet_data['api_key'] = api_key
                                wallet_data['api_secret'] = api_secret
                        except Exception as e:
                            logger.warning(f"Failed to decrypt credentials for wallet {wallet_data.get('wallet_id')}: {e}")
                            # Keep the wallet but mark it as inactive
                            wallet_data['is_active'] = 'false'
                        
                        # Create a wallet instance from the data
                        wallet = self.wallet_factory.create_wallet_from_raw_data(wallet_data)

                        wallet_list.append(wallet)
                
                logger.info(f"Loaded {len(wallet_list)} wallets from CSV")
        except Exception as e:
            logger.error(f"Error loading wallets from CSV: {e}")
        
        return wallet_list
    
    # TODO: Check the portfolio_id of the wallets in the list
    def _save_all_wallets(self, wallet_list: List[Wallet]) -> None:
        """Save all wallet data to CSV file."""
        try:
            # Create CSV file if it doesn't exist
            if not os.path.exists(self.csv_file_path):
                self._create_csv_file()
            
            logger.info(f"CSV Wallet Repository initialized at {self.csv_file_path}")

            # Convert all wallets to CSV rows with proper mapping
            csv_rows = []
            for wallet in wallet_list:
                # Determine wallet type from the wallet class name
                wallet_type = wallet.__class__.__name__
                
                # Prepare wallet data for CSV
                wallet_data = {
                    'wallet_id': wallet.id,
                    'wallet_type': wallet_type,
                    'name': wallet.name,
                    'description': wallet.description or '',
                    'api_key': '',  # Will be encrypted just before writing
                    'api_secret': '',  # Will be encrypted just before writing
                    'is_active': str(wallet.is_active).lower(),
                    'created_datetime': '',  # Not available in Wallet class
                    'updated_datetime': '',  # Not available in Wallet class
                    'reference_fiat': wallet.reference_fiat,
                    'sync_status': wallet.sync_status.value if wallet.sync_status else 'not_synchronized',
                    'portfolio_id': wallet.portfolio_id,
                }
                
                # Encrypt API credentials just before adding to CSV rows
                if wallet.api_key and wallet.api_secret:
                    try:
                        encrypted_key, encrypted_secret = self._encrypt_api_credentials(
                            wallet.api_key, 
                            wallet.api_secret
                        )
                        wallet_data['api_key'] = encrypted_key
                        wallet_data['api_secret'] = encrypted_secret
                    except Exception as e:
                        logger.error(f"Failed to encrypt credentials for wallet {wallet.id}: {e}")
                        # Skip this wallet if encryption fails
                        continue
                
                csv_rows.append(wallet_data)
            
            # Write to CSV file
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=WALLET_CONFIG_COLUMNS)
                writer.writeheader()
                writer.writerows(csv_rows)
            
            logger.info(f"Saved {len(csv_rows)} wallets to CSV")
        except Exception as e:
            logger.error(f"Error saving wallets to CSV: {e}")
            raise
    
    def save_wallet(self, wallet: Wallet) -> bool:
        """
        Save a wallet configuration to the repository.
        
        Args:
            wallet: Wallet instance
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            # Load existing wallets (convert to Wallet instances)
            existing_wallets = self._load_all_wallets(wallet.portfolio_id)
            
            # Check if wallet already exists
            existing_index = None
            for i, existing_wallet in enumerate(existing_wallets):
                if existing_wallet.id == wallet.id:
                    existing_index = i
                    break
            
            if existing_index is not None:
                # Update existing wallet
                existing_wallets[existing_index] = wallet
                logger.info(f"Updated existing wallet: {wallet.name}")
            else:
                # Add new wallet
                existing_wallets.append(wallet)
                logger.info(f"Added new wallet: {wallet.name}")
            
            # Save all wallets
            self._save_all_wallets(existing_wallets)
            return True
        
        except Exception as e:
            logger.error(f"Error saving wallet: {e}")
            return False
    
    def find_wallet_by_id(self, wallet_id: str) -> Optional[Wallet]:
        """
        Find a wallet configuration by its ID.
        
        Args:
            wallet_id: Unique identifier of the wallet
            
        Returns:
            Wallet instance or None if not found
        """
        try:
            # Load all wallets from all portfolios
            all_wallets = []
            for portfolio_id in self._get_portfolio_ids():
                wallets = self._load_all_wallets(portfolio_id)
                all_wallets.extend(wallets)
            
            for wallet in all_wallets:
                if wallet.id == wallet_id:
                    return wallet
            
            logger.warning(f"Wallet with ID {wallet_id} not found")
            return None
            
        except Exception as e:
            logger.error(f"Error finding wallet by ID: {e}")
            return None
    
    def find_all_wallets(self, portfolio_id: str) -> List[Wallet]:
        """
        Retrieve all wallet configurations from the repository.
        
        Args:
            portfolio_id: Unique identifier of the portfolio
            
        Returns:
            List of wallet instances
        """
        try:
            return self._load_all_wallets(portfolio_id)
        except Exception as e:
            logger.error(f"Error finding all wallets: {e}")
            return []
    
    def update_wallet(self, wallet: Wallet) -> bool:
        """
        Update an existing wallet configuration.
        
        Args:
            wallet: Wallet instance to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Load existing wallets
            existing_wallets = self._load_all_wallets(wallet.portfolio_id)
            
            # Find and update the wallet
            for i, existing_wallet in enumerate(existing_wallets):
                if existing_wallet.id == wallet.id:
                    existing_wallets[i] = wallet
                    
                    # Save all wallets
                    self._save_all_wallets(existing_wallets)
                    logger.info(f"Updated wallet: {wallet.name}")
                    return True
            
            logger.warning(f"Wallet with ID {wallet.id} not found for update")
            return False
            
        except Exception as e:
            logger.error(f"Error updating wallet: {e}")
            return False
    
    def delete_wallet_by_id(self, wallet_id: str) -> bool:
        """
        Delete a wallet configuration from the repository.
        
        Args:
            wallet_id: Unique identifier of the wallet to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            # Find the wallet first to get its portfolio_id
            wallet = self.find_wallet_by_id(wallet_id)
            if not wallet:
                logger.warning(f"Wallet with ID {wallet_id} not found for deletion")
                return False
            
            # Load existing wallets from the same portfolio
            existing_wallets = self._load_all_wallets(wallet.portfolio_id)
            
            # Find and remove the wallet
            for i, existing_wallet in enumerate(existing_wallets):
                if existing_wallet.id == wallet_id:
                    removed_wallet = existing_wallets.pop(i)
                    
                    # Save remaining wallets
                    self._save_all_wallets(existing_wallets)
                    logger.info(f"Deleted wallet: {removed_wallet.name}")
                    return True
            
            logger.warning(f"Wallet with ID {wallet_id} not found for deletion")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting wallet: {e}")
            return False