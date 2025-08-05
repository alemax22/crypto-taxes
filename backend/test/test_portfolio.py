#!/usr/bin/env python3
"""
Unit tests for Portfolio class
Tests the portfolio management functionality including wallet operations, encryption, and synchronization
"""

import unittest
import pytest
from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
import os
import tempfile
import shutil
import csv
from datetime import datetime, timezone
from decimal import Decimal
import uuid

# Add the parent directory to Python path to import backend modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wallets.portfolio import Portfolio
from wallets.wallet import Wallet
from wallets.wallet_kraken import KrakenWallet


class MockWallet(Wallet):
    """Concrete implementation of Wallet for testing."""
    
    def __init__(self, name: str, id: str, reference_fiat: str, description: str = "", 
                 api_key: str = None, api_secret: str = None, **kwargs):
        super().__init__(name, id, reference_fiat, description, api_key, api_secret)
        # For testing, we want wallets to authenticate successfully by default
        # The is_active parameter from the config should not affect authentication
        self._is_active = True
        self._last_sync = kwargs.get('last_sync', None)
        self._sync_status = kwargs.get('sync_status', "not synchronized")
        self.ledger_file = None
    
    def synchronize(self, start_date=None):
        """Mock implementation."""
        return True, None
    
    def authenticate(self):
        """Mock implementation."""
        return self._is_active
    
    def get_sync_status(self):
        """Mock implementation."""
        return self._sync_status, self._last_sync or datetime.now(timezone.utc).isoformat()
    
    def _get_ohlc_data(self, assets_in_portfolio, start_date=None):
        """Mock implementation."""
        return pd.DataFrame()


@pytest.mark.unit
class TestPortfolioInitialization(unittest.TestCase):
    """Test cases for Portfolio initialization and setup."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.wallets_dir = os.path.join(self.test_dir, 'wallets')
        os.makedirs(self.wallets_dir, exist_ok=True)
        
        # Patch the WALLETS_DIR constant
        self.wallets_dir_patcher = patch('wallets.portfolio.WALLETS_DIR', self.wallets_dir)
        self.mock_wallets_dir = self.wallets_dir_patcher.start()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.wallets_dir_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_portfolio_initialization_new_directory(self):
        """Test portfolio initialization with new directory."""
        portfolio = Portfolio()
        
        # Verify directory was created
        self.assertTrue(os.path.exists(self.wallets_dir))
        
        # Verify CSV file was created
        csv_file = os.path.join(self.wallets_dir, "wallets.csv")
        self.assertTrue(os.path.exists(csv_file))
        
        # Verify encryption key was created
        key_file = os.path.join(self.wallets_dir, "portfolio_key.key")
        self.assertTrue(os.path.exists(key_file))
        
        # Verify wallets_data is empty
        self.assertEqual(len(portfolio.wallets_data), 0)
    
    def test_portfolio_initialization_existing_directory(self):
        """Test portfolio initialization with existing directory."""
        # Create existing files
        csv_file = os.path.join(self.wallets_dir, "wallets.csv")
        key_file = os.path.join(self.wallets_dir, "portfolio_key.key")
        
        # Create CSV file with headers
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['wallet_id', 'wallet_type', 'name', 'description', 'api_key', 
                           'api_secret', 'is_active', 'created_datetime', 'updated_datetime', 
                           'reference_fiat', 'sync_status'])
        
        # Create encryption key
        with open(key_file, 'wb') as f:
            f.write(b'test_key_32_bytes_long_for_fernet')
        
        portfolio = Portfolio()
        
        # Verify files still exist
        self.assertTrue(os.path.exists(csv_file))
        self.assertTrue(os.path.exists(key_file))
        self.assertEqual(len(portfolio.wallets_data), 0)


@pytest.mark.unit
class TestPortfolioEncryption(unittest.TestCase):
    """Test cases for Portfolio encryption functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.wallets_dir = os.path.join(self.test_dir, 'wallets')
        os.makedirs(self.wallets_dir, exist_ok=True)
        
        self.wallets_dir_patcher = patch('wallets.portfolio.WALLETS_DIR', self.wallets_dir)
        self.mock_wallets_dir = self.wallets_dir_patcher.start()
        
        self.portfolio = Portfolio()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.wallets_dir_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_encrypt_decrypt_api_credentials(self):
        """Test encryption and decryption of API credentials."""
        api_key = "test_api_key_123"
        api_secret = "test_api_secret_456"
        
        # Encrypt credentials
        encrypted_key, encrypted_secret = self.portfolio._encrypt_api_credentials(api_key, api_secret)
        
        # Verify encrypted values are different from original
        self.assertNotEqual(encrypted_key, api_key)
        self.assertNotEqual(encrypted_secret, api_secret)
        
        # Decrypt credentials
        decrypted_key, decrypted_secret = self.portfolio._decrypt_api_credentials(encrypted_key, encrypted_secret)
        
        # Verify decrypted values match original
        self.assertEqual(decrypted_key, api_key)
        self.assertEqual(decrypted_secret, api_secret)
    
    def test_encrypt_decrypt_empty_credentials(self):
        """Test encryption and decryption of empty credentials."""
        api_key = ""
        api_secret = ""
        
        encrypted_key, encrypted_secret = self.portfolio._encrypt_api_credentials(api_key, api_secret)
        decrypted_key, decrypted_secret = self.portfolio._decrypt_api_credentials(encrypted_key, encrypted_secret)
        
        self.assertEqual(decrypted_key, api_key)
        self.assertEqual(decrypted_secret, api_secret)
    
    def test_encrypt_decrypt_special_characters(self):
        """Test encryption and decryption of credentials with special characters."""
        api_key = "test@key#123$%^&*()"
        api_secret = "secret!@#$%^&*()_+-=[]{}|;':\",./<>?"
        
        encrypted_key, encrypted_secret = self.portfolio._encrypt_api_credentials(api_key, api_secret)
        decrypted_key, decrypted_secret = self.portfolio._decrypt_api_credentials(encrypted_key, encrypted_secret)
        
        self.assertEqual(decrypted_key, api_key)
        self.assertEqual(decrypted_secret, api_secret)


@pytest.mark.unit
class TestPortfolioWalletManagement(unittest.TestCase):
    """Test cases for Portfolio wallet management operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.wallets_dir = os.path.join(self.test_dir, 'wallets')
        os.makedirs(self.wallets_dir, exist_ok=True)
        
        self.wallets_dir_patcher = patch('wallets.portfolio.WALLETS_DIR', self.wallets_dir)
        self.mock_wallets_dir = self.wallets_dir_patcher.start()
        
        # Create portfolio and mock wallet types
        self.portfolio = Portfolio()
        self.portfolio.wallet_types = {'Kraken': MockWallet}
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.wallets_dir_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_generate_wallet_id(self):
        """Test wallet ID generation."""
        wallet_id = self.portfolio._generate_wallet_id("Kraken", "Test Wallet")
        
        # Verify format
        self.assertTrue(wallet_id.startswith("KRAKEN-"))
        self.assertTrue(len(wallet_id) > len("KRAKEN-"))
        
        # Verify uniqueness
        wallet_id2 = self.portfolio._generate_wallet_id("Kraken", "Test Wallet")
        self.assertNotEqual(wallet_id, wallet_id2)
    
    def test_add_wallet_success(self):
        """Test successful wallet addition."""
        wallet_id = self.portfolio.add_wallet(
            wallet_type="Kraken",
            name="Test Wallet",
            reference_fiat="EUR",
            api_key="test_key",
            api_secret="test_secret",
            description="Test description"
        )
        
        # Verify wallet was added
        self.assertIsNotNone(wallet_id)
        self.assertEqual(len(self.portfolio.wallets_data), 1)
        
        # Verify wallet data
        wallet = self.portfolio.wallets_data[0]
        self.assertEqual(wallet['wallet_id'], wallet_id)
        self.assertEqual(wallet['wallet_type'], "Kraken")
        self.assertEqual(wallet['name'], "Test Wallet")
        self.assertEqual(wallet['reference_fiat'], "EUR")
        self.assertEqual(wallet['api_key'], "test_key")
        self.assertEqual(wallet['api_secret'], "test_secret")
        self.assertEqual(wallet['description'], "Test description")
        self.assertTrue(wallet['is_active'])
        self.assertEqual(wallet['sync_status'], "not synchronized")
    
    def test_add_wallet_unsupported_type(self):
        """Test adding wallet with unsupported type."""
        wallet_id = self.portfolio.add_wallet(
            wallet_type="Unsupported",
            name="Test Wallet",
            reference_fiat="EUR"
        )
        
        # Verify wallet was not added
        self.assertIsNone(wallet_id)
        self.assertEqual(len(self.portfolio.wallets_data), 0)
    
    @patch.object(MockWallet, 'authenticate', return_value=False)
    def test_add_wallet_authentication_failure(self, mock_authenticate):
        """Test adding wallet with authentication failure."""
        wallet_id = self.portfolio.add_wallet(
            wallet_type="Kraken",
            name="Test Wallet",
            reference_fiat="EUR",
            api_key="test_key",
            api_secret="test_secret"
        )
        
        # Verify wallet was not added
        self.assertIsNone(wallet_id)
        self.assertEqual(len(self.portfolio.wallets_data), 0)
    
    def test_list_wallets(self):
        """Test listing wallets without sensitive data."""
        # Add a wallet
        wallet_id = self.portfolio.add_wallet(
            wallet_type="Kraken",
            name="Test Wallet",
            reference_fiat="EUR",
            api_key="test_key",
            api_secret="test_secret"
        )
        
        # List wallets
        wallets = self.portfolio.list_wallets()
        
        # Verify wallet is listed but without sensitive data
        self.assertEqual(len(wallets), 1)
        wallet = wallets[0]
        self.assertEqual(wallet['wallet_id'], wallet_id)
        self.assertEqual(wallet['name'], "Test Wallet")
        self.assertNotIn('api_key', wallet)
        self.assertNotIn('api_secret', wallet)
    
    def test_get_wallet_by_id(self):
        """Test getting wallet by ID."""
        # Add a wallet
        wallet_id = self.portfolio.add_wallet(
            wallet_type="Kraken",
            name="Test Wallet",
            reference_fiat="EUR",
            api_key="test_key",
            api_secret="test_secret"
        )
        
        # Get wallet by ID
        wallet = self.portfolio.get_wallet_by_id(wallet_id)
        
        # Verify wallet data
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet['wallet_id'], wallet_id)
        self.assertEqual(wallet['name'], "Test Wallet")
        self.assertEqual(wallet['api_key'], "test_key")
        self.assertEqual(wallet['api_secret'], "test_secret")
    
    def test_get_wallet_by_id_not_found(self):
        """Test getting wallet by non-existent ID."""
        wallet = self.portfolio.get_wallet_by_id("non-existent-id")
        self.assertIsNone(wallet)
    
    def test_load_wallet(self):
        """Test loading wallet instance."""
        # Add a wallet
        wallet_id = self.portfolio.add_wallet(
            wallet_type="Kraken",
            name="Test Wallet",
            reference_fiat="EUR",
            api_key="test_key",
            api_secret="test_secret"
        )
        
        # Load wallet instance
        wallet_instance = self.portfolio.load_wallet(wallet_id)
        
        # Verify wallet instance
        self.assertIsNotNone(wallet_instance)
        self.assertIsInstance(wallet_instance, MockWallet)
        self.assertEqual(wallet_instance.name, "Test Wallet")
        self.assertEqual(wallet_instance.id, wallet_id)
    
    def test_load_wallet_not_found(self):
        """Test loading non-existent wallet."""
        wallet_instance = self.portfolio.load_wallet("non-existent-id")
        self.assertIsNone(wallet_instance)
    
    def test_remove_wallet(self):
        """Test removing wallet."""
        # Add a wallet
        wallet_id = self.portfolio.add_wallet(
            wallet_type="Kraken",
            name="Test Wallet",
            reference_fiat="EUR",
            api_key="test_key",
            api_secret="test_secret"
        )
        
        # Verify wallet was added
        self.assertEqual(len(self.portfolio.wallets_data), 1)
        
        # Remove wallet
        result = self.portfolio.remove_wallet(wallet_id)
        
        # Verify removal was successful
        self.assertTrue(result)
        self.assertEqual(len(self.portfolio.wallets_data), 0)
    
    def test_remove_wallet_not_found(self):
        """Test removing non-existent wallet."""
        result = self.portfolio.remove_wallet("non-existent-id")
        self.assertFalse(result)


@pytest.mark.unit
class TestPortfolioSynchronization(unittest.TestCase):
    """Test cases for Portfolio synchronization functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.wallets_dir = os.path.join(self.test_dir, 'wallets')
        os.makedirs(self.wallets_dir, exist_ok=True)
        
        self.wallets_dir_patcher = patch('wallets.portfolio.WALLETS_DIR', self.wallets_dir)
        self.mock_wallets_dir = self.wallets_dir_patcher.start()
        
        # Create portfolio and mock wallet types
        self.portfolio = Portfolio()
        self.portfolio.wallet_types = {'Kraken': MockWallet}
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.wallets_dir_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_synchronize_all_wallets_no_wallets(self):
        """Test synchronization with no wallets."""
        results = self.portfolio.synchronize_all_wallets()
        self.assertEqual(results, {})
    
    def test_synchronize_all_wallets_success(self):
        """Test successful synchronization of all wallets."""
        # Add a wallet
        wallet_id = self.portfolio.add_wallet(
            wallet_type="Kraken",
            name="Test Wallet",
            reference_fiat="EUR",
            api_key="test_key",
            api_secret="test_secret"
        )
        
        # Synchronize all wallets
        results = self.portfolio.synchronize_all_wallets()
        
        # Verify results
        self.assertIn(wallet_id, results)
        result = results[wallet_id]
        self.assertEqual(result['name'], "Test Wallet")
        self.assertTrue(result['success'])
        self.assertIsNone(result['error'])
    
    def test_synchronize_all_wallets_authentication_failure(self):
        """Test synchronization with authentication failure."""
        # Create a wallet with authentication failure
        wallet_id = self.portfolio._generate_wallet_id("Kraken", "Test Wallet")
        wallet_config = {
            'wallet_id': wallet_id,
            'wallet_type': 'Kraken',
            'name': 'Test Wallet',
            'description': '',
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'is_active': False,
            'created_datetime': datetime.now(timezone.utc).isoformat(),
            'updated_datetime': None,
            'reference_fiat': 'EUR',
            'sync_status': 'not synchronized',
        }
        self.portfolio.wallets_data.append(wallet_config)
        
        # Mock authentication failure
        with patch.object(MockWallet, 'authenticate', return_value=False):
            results = self.portfolio.synchronize_all_wallets()
        
        # Verify results
        self.assertIn(wallet_id, results)
        result = results[wallet_id]
        self.assertEqual(result['name'], "Test Wallet")
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Authentication failed")
    
    def test_synchronize_all_wallets_load_failure(self):
        """Test synchronization with wallet load failure."""
        # Add a wallet with invalid configuration
        wallet_id = self.portfolio._generate_wallet_id("Kraken", "Test Wallet")
        wallet_config = {
            'wallet_id': wallet_id,
            'wallet_type': 'InvalidType',  # This will cause load failure
            'name': 'Test Wallet',
            'description': '',
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'is_active': False,
            'created_datetime': datetime.now(timezone.utc).isoformat(),
            'updated_datetime': None,
            'reference_fiat': 'EUR',
            'sync_status': 'not synchronized',
        }
        self.portfolio.wallets_data.append(wallet_config)
        
        # Synchronize all wallets
        results = self.portfolio.synchronize_all_wallets()
        
        # Verify results
        self.assertIn(wallet_id, results)
        result = results[wallet_id]
        self.assertEqual(result['name'], "Test Wallet")
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Failed to load wallet instance")
    
    def test_synchronize_all_wallets_with_date_range(self):
        """Test synchronization with date range parameters."""
        # Add a wallet
        wallet_id = self.portfolio.add_wallet(
            wallet_type="Kraken",
            name="Test Wallet",
            reference_fiat="EUR",
            api_key="test_key",
            api_secret="test_secret"
        )
        
        # Synchronize with date range
        start_date = "2023-01-01"
        end_date = "2023-12-31"
        results = self.portfolio.synchronize_all_wallets(start_date, end_date)
        
        # Verify results
        self.assertIn(wallet_id, results)
        result = results[wallet_id]
        self.assertTrue(result['success'])


@pytest.mark.unit
class TestPortfolioCSVOperations(unittest.TestCase):
    """Test cases for Portfolio CSV file operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.wallets_dir = os.path.join(self.test_dir, 'wallets')
        os.makedirs(self.wallets_dir, exist_ok=True)
        
        self.wallets_dir_patcher = patch('wallets.portfolio.WALLETS_DIR', self.wallets_dir)
        self.mock_wallets_dir = self.wallets_dir_patcher.start()
        
        # Create portfolio and mock wallet types
        self.portfolio = Portfolio()
        self.portfolio.wallet_types = {'Kraken': MockWallet}
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.wallets_dir_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_create_csv_file(self):
        """Test CSV file creation."""
        csv_file = os.path.join(self.wallets_dir, "wallets.csv")
        
        # Remove existing file if it exists
        if os.path.exists(csv_file):
            os.remove(csv_file)
        
        # Create CSV file
        self.portfolio._create_csv_file()
        
        # Verify file was created
        self.assertTrue(os.path.exists(csv_file))
        
        # Verify headers
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            expected_headers = ['wallet_id', 'wallet_type', 'name', 'description', 'api_key',
                              'api_secret', 'is_active', 'created_datetime', 'updated_datetime',
                              'reference_fiat', 'sync_status']
            self.assertEqual(headers, expected_headers)
    
    def test_save_wallets_to_csv(self):
        """Test saving wallets to CSV."""
        # Add a wallet
        wallet_id = self.portfolio.add_wallet(
            wallet_type="Kraken",
            name="Test Wallet",
            reference_fiat="EUR",
            api_key="test_key",
            api_secret="test_secret"
        )
        
        # Save to CSV
        self.portfolio._save_wallets_to_csv()
        
        # Verify CSV file contains the wallet
        csv_file = os.path.join(self.wallets_dir, "wallets.csv")
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['wallet_id'], wallet_id)
        self.assertEqual(row['wallet_type'], "Kraken")
        self.assertEqual(row['name'], "Test Wallet")
        # API credentials should be encrypted
        self.assertNotEqual(row['api_key'], "test_key")
        self.assertNotEqual(row['api_secret'], "test_secret")
    
    def test_load_wallets_from_csv(self):
        """Test loading wallets from CSV."""
        # Create a wallet and save it
        wallet_id = self.portfolio.add_wallet(
            wallet_type="Kraken",
            name="Test Wallet",
            reference_fiat="EUR",
            api_key="test_key",
            api_secret="test_secret"
        )
        
        # Create a new portfolio instance to load from CSV
        new_portfolio = Portfolio()
        
        # Verify wallet was loaded
        self.assertEqual(len(new_portfolio.wallets_data), 1)
        wallet = new_portfolio.wallets_data[0]
        self.assertEqual(wallet['wallet_id'], wallet_id)
        self.assertEqual(wallet['name'], "Test Wallet")
        self.assertEqual(wallet['api_key'], "test_key")  # Should be decrypted
        self.assertEqual(wallet['api_secret'], "test_secret")  # Should be decrypted
    
    def test_load_wallets_from_csv_with_decryption_failure(self):
        """Test loading wallets from CSV with decryption failure."""
        # Create a wallet and save it
        wallet_id = self.portfolio.add_wallet(
            wallet_type="Kraken",
            name="Test Wallet",
            reference_fiat="EUR",
            api_key="test_key",
            api_secret="test_secret"
        )
        
        # Corrupt the encryption key
        key_file = os.path.join(self.wallets_dir, "portfolio_key.key")
        with open(key_file, 'wb') as f:
            f.write(b'corrupted_key')
        
        # Create a new portfolio instance to load from CSV
        new_portfolio = Portfolio()
        
        # Verify wallet was loaded but marked as inactive
        self.assertEqual(len(new_portfolio.wallets_data), 1)
        wallet = new_portfolio.wallets_data[0]
        self.assertEqual(wallet['wallet_id'], wallet_id)
        self.assertEqual(wallet['is_active'], 'false')


if __name__ == '__main__':
    unittest.main() 