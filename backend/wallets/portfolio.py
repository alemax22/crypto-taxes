#!/usr/bin/env python3
"""
Portfolio Management
Handles multiple wallets/exchanges for a user
"""

import os
import csv
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from cryptography.fernet import Fernet

from wallets.wallet import Wallet
from wallets.wallet_kraken import KrakenWallet

logger = logging.getLogger(__name__)

WALLETS_CSV_FILE_PATH = "wallets.csv"
ENCRYPTION_KEY_FILE_PATH = "portfolio_key.key"

class Portfolio:
    """Portfolio class to manage multiple wallets/exchanges."""
    
    def __init__(self):
        """Initialize the portfolio."""
        self.csv_file_path = WALLETS_CSV_FILE_PATH
        self.wallets_data = []
        self.wallet_types = {
            'Kraken': KrakenWallet,
        }
        
        # Encryption key file path
        self.encryption_key_file = ENCRYPTION_KEY_FILE_PATH
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.csv_file_path), exist_ok=True)
        
        # Initialize encryption
        self._initialize_encryption()
        
        # Load existing wallets
        self._load_wallets_from_csv()
        
        logger.info(f"Portfolio initialized with {len(self.wallets_data)} wallets")
    
    def _initialize_encryption(self):
        """Initialize encryption key for API credentials."""
        if not os.path.exists(self.encryption_key_file):
            logger.info("Creating new encryption key for portfolio")
            self._generate_encryption_key()
        else:
            logger.info("Using existing encryption key")
    
    def _generate_encryption_key(self):
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
    
    def _encrypt_api_credentials(self, api_key: str, api_secret: str) -> tuple:
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
    
    def _decrypt_api_credentials(self, encrypted_api_key: str, encrypted_api_secret: str) -> tuple:
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
    
    def _load_wallets_from_csv(self):
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
    
    def _create_csv_file(self):
        """Create a new CSV file with the proper headers."""
        headers = [
            'wallet_id',
            'wallet_type',
            'name',
            'description',
            'api_key',
            'api_secret',
            'is_active',
            'created_date',
            'last_updated',
            'notes'
        ]
        
        try:
            with open(self.csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
            logger.info(f"Created new CSV file: {self.csv_file_path}")
        except Exception as e:
            logger.error(f"Error creating CSV file: {e}")
    
    def _save_wallets_to_csv(self):
        """Save wallet configurations to CSV file."""
        if not self.wallets_data:
            return
        
        headers = [
            'wallet_id',
            'wallet_type',
            'name',
            'description',
            'api_key',
            'api_secret',
            'is_active',
            'created_date',
            'last_updated',
            'notes'
        ]
        
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
                writer = csv.DictWriter(csvfile, fieldnames=headers)
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
        
        wallet_type = wallet_config['wallet_type']
        if wallet_type not in self.wallet_types:
            logger.error(f"Unsupported wallet type: {wallet_type}")
            return None
        
        try:
            # Create wallet instance with decrypted credentials
            wallet_class = self.wallet_types[wallet_type]
            wallet_instance = wallet_class(
                api_key=wallet_config.get('api_key'),
                api_secret=wallet_config.get('api_secret')
            )
            
            # Set additional attributes
            wallet_instance.wallet_id = wallet_id
            wallet_instance.name = wallet_config.get('name', '')
            wallet_instance.description = wallet_config.get('description', '')
            
            logger.info(f"Loaded wallet: {wallet_config.get('name')} ({wallet_type})")
            return wallet_instance
            
        except Exception as e:
            logger.error(f"Error loading wallet {wallet_id}: {e}")
            return None
    
    def add_wallet(self, 
                   wallet_type: str, 
                   name: str, 
                   api_key: str, 
                   api_secret: str, 
                   description: str = "", 
                   notes: str = "") -> Optional[str]:
        """Add a new wallet to the portfolio."""
        if wallet_type not in self.wallet_types:
            logger.error(f"Unsupported wallet type: {wallet_type}")
            return None
        
        # Generate unique wallet ID
        wallet_id = self._generate_wallet_id(wallet_type, name)
        
        # Check if wallet ID already exists
        if self.get_wallet_by_id(wallet_id):
            logger.error(f"Wallet with ID {wallet_id} already exists")
            return None
        
        # Create wallet configuration with plain text credentials (will be encrypted when saved)
        wallet_config = {
            'wallet_id': wallet_id,
            'wallet_type': wallet_type,
            'name': name,
            'description': description,
            'api_key': api_key,
            'api_secret': api_secret,
            'is_active': 'true',
            'created_date': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'notes': notes
        }
        
        try:
            # Test the wallet by creating an instance
            wallet_instance = self.load_wallet(wallet_id)
            if not wallet_instance:
                logger.error("Failed to create wallet instance")
                return None
            
            # Test authentication
            if not wallet_instance.authenticate():
                logger.warning(f"Authentication failed for wallet {name}. Wallet will be added but marked as inactive.")
                wallet_config['is_active'] = 'false'
            
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
    
    def get_active_wallets(self) -> List[Dict[str, Any]]:
        """Get list of active wallets."""
        active_wallets = []
        for wallet in self.wallets_data:
            if wallet.get('is_active', 'false').lower() == 'true':
                safe_wallet = wallet.copy()
                # Remove sensitive data
                safe_wallet.pop('api_key', None)
                safe_wallet.pop('api_secret', None)
                active_wallets.append(safe_wallet)
        
        return active_wallets
    
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
        active_wallets = self.get_active_wallets()
        
        for wallet_config in active_wallets:
            wallet_id = wallet_config['wallet_id']
            wallet_name = wallet_config['name']
            
            try:
                wallet_instance = self.load_wallet(wallet_id)
                if wallet_instance:
                    logger.info(f"Synchronizing wallet: {wallet_name}")
                    sync_result = wallet_instance.synchronize(start_date, end_date)
                    results[wallet_id] = {
                        'name': wallet_name,
                        'success': sync_result['success'],
                        'transactions_fetched': sync_result.get('transactions_fetched', 0),
                        'error': sync_result.get('error')
                    }
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
        # Create base ID from type and name
        base_id = f"{wallet_type.lower()}_{name.lower().replace(' ', '_')}"
        
        # Check if ID already exists and add suffix if needed
        counter = 1
        wallet_id = base_id
        while self.get_wallet_by_id(wallet_id):
            wallet_id = f"{base_id}_{counter}"
            counter += 1
        
        return wallet_id