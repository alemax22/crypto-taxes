#!/usr/bin/env python3
"""
Unit tests for KrakenWallet class
Tests the Kraken wallet implementation with mocked API calls
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import pandas as pd
import json
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from decimal import Decimal
import time # Added for nonce generation

# Add the parent directory to Python path to import backend modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wallets.kraken_wallet import KrakenWallet


class TestKrakenWallet(unittest.TestCase):
    """Test cases for KrakenWallet class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.persistent_data_dir = os.path.join(self.test_dir, 'persistent_data')
        
        # Mock API credentials
        self.test_api_key = "test_api_key_12345"
        self.test_api_secret = "test_api_secret_67890"
        
        # Create test wallet instance
        self.wallet = KrakenWallet(self.test_api_key, self.test_api_secret)
        
        # Override persistent data directory for testing
        self.wallet.persistent_data_dir = self.persistent_data_dir
        
        # Create test data directories
        os.makedirs(os.path.join(self.persistent_data_dir, 'data'), exist_ok=True)
        os.makedirs(os.path.join(self.persistent_data_dir, 'config'), exist_ok=True)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_init(self):
        """Test wallet initialization."""
        self.assertEqual(self.wallet.name, "Kraken")
        self.assertEqual(self.wallet.api_key, self.test_api_key)
        self.assertEqual(self.wallet.api_secret, self.test_api_secret)
        self.assertFalse(self.wallet.is_authenticated)
        self.assertIsNone(self.wallet.last_sync)
    
    @patch.object(KrakenWallet, '_get_ledger')
    def test_authenticate_success(self, mock_get_ledger):
        """Test successful authentication."""
        # Mock successful ledger response
        mock_get_ledger.return_value = {
            'error': [],
            'result': {
                'ledger': {
                    'test_ref_id': {
                        'refid': 'test_ref_id',
                        'time': 1640995200,
                        'type': 'trade',
                        'aclass': 'currency',
                        'asset': 'XXBT',
                        'amount': '0.1',
                        'fee': '0.0001',
                        'balance': '1.0'
                    }
                },
                'count': 1
            }
        }
        
        # Test authentication
        result = self.wallet.authenticate()
        
        # Verify results
        self.assertTrue(result)
        self.assertTrue(self.wallet.is_authenticated)
        
        # Verify the method was called
        mock_get_ledger.assert_called_once()
    
    @patch('wallets.kraken_wallet.requests.post')
    def test_authenticate_failure_missing_credentials(self, mock_post):
        """Test authentication failure with missing credentials."""
        # Create wallet without credentials
        wallet = KrakenWallet()
        
        # Test authentication
        result = wallet.authenticate()
        
        # Verify results
        self.assertFalse(result)
        self.assertFalse(wallet.is_authenticated)
        
        # Verify no API call was made
        mock_post.assert_not_called()
    
    @patch.object(KrakenWallet, '_get_ledger')
    def test_authenticate_failure_api_error(self, mock_get_ledger):
        """Test authentication failure with API error."""
        # Mock API error response
        mock_get_ledger.return_value = {
            'error': ['API:Invalid key']
        }
        
        # Test authentication
        result = self.wallet.authenticate()
        
        # Verify results
        self.assertFalse(result)
        self.assertFalse(self.wallet.is_authenticated)
    
    @patch.object(KrakenWallet, '_get_balance_raw')
    @patch.object(KrakenWallet, 'authenticate')
    def test_get_balance_success(self, mock_authenticate, mock_get_balance_raw):
        """Test successful balance retrieval."""
        # Mock authentication to succeed
        mock_authenticate.return_value = True
        self.wallet.is_authenticated = True
        
        # Mock successful balance response
        mock_get_balance_raw.return_value = {
            'error': [],
            'result': {
                'XXBT': '1.5',
                'XETH': '10.0',
                'ZEUR': '5000.0'
            }
        }
        
        # Test balance retrieval
        balance_df = self.wallet.get_balance()
        
        # Verify results
        self.assertIsInstance(balance_df, pd.DataFrame)
        self.assertEqual(len(balance_df), 3)
        
        # Check specific assets
        btc_row = balance_df[balance_df['asset'] == 'XXBT'].iloc[0]
        self.assertEqual(btc_row['balance'], Decimal('1.5'))
        
        # Verify the method was called
        mock_get_balance_raw.assert_called_once()
    
    @patch.object(KrakenWallet, '_get_balance_raw')
    @patch.object(KrakenWallet, 'authenticate')
    def test_get_balance_failure(self, mock_authenticate, mock_get_balance_raw):
        """Test balance retrieval failure."""
        # Mock authentication to succeed
        mock_authenticate.return_value = True
        self.wallet.is_authenticated = True
        
        # Mock API error response
        mock_get_balance_raw.return_value = {
            'error': ['API:Invalid key']
        }
        
        # Test balance retrieval
        balance_df = self.wallet.get_balance()
        
        # Verify results
        self.assertTrue(balance_df.empty)
    
    @patch('wallets.kraken_wallet.pd.read_parquet')
    @patch.object(KrakenWallet, '_retrieve_all_ledger_data')
    @patch.object(KrakenWallet, 'authenticate')
    def test_get_transactions_success(self, mock_authenticate, mock_retrieve_ledger, mock_read_parquet):
        """Test successful transaction retrieval."""
        # Mock authentication to succeed
        mock_authenticate.return_value = True
        self.wallet.is_authenticated = True
        
        # Mock existing ledger data
        mock_ledger_data = pd.DataFrame({
            'refid': ['ref1', 'ref2'],
            'time': [1640995200, 1640995300],
            'type': ['trade', 'deposit'],
            'asset': ['XXBT', 'XETH'],
            'amount': ['0.1', '1.0'],
            'fee': ['0.0001', '0.0'],
            'balance': ['1.0', '10.0'],
            'assetnorm': ['XXBT', 'XETH']
        })
        mock_retrieve_ledger.return_value = mock_ledger_data
        
        # Test transaction retrieval
        transactions_df = self.wallet.get_transactions()
        
        # Verify results
        self.assertIsInstance(transactions_df, pd.DataFrame)
        self.assertEqual(len(transactions_df), 2)
        self.assertIn('decimalamount', transactions_df.columns)
        self.assertIn('decimalbalance', transactions_df.columns)
        self.assertIn('decimalfee', transactions_df.columns)
    
    @patch('wallets.kraken_wallet.pd.read_parquet')
    def test_get_transactions_no_data(self, mock_read_parquet):
        """Test transaction retrieval with no data."""
        # Mock empty ledger data
        mock_read_parquet.side_effect = FileNotFoundError()
        
        # Test transaction retrieval
        transactions_df = self.wallet.get_transactions()
        
        # Verify results
        self.assertTrue(transactions_df.empty)
    
    @patch.object(KrakenWallet, '_synchronize_ohlc_data')
    @patch.object(KrakenWallet, '_synchronize_balance')
    @patch.object(KrakenWallet, '_synchronize_transactions')
    @patch.object(KrakenWallet, '_get_ledger')
    def test_synchronize_success(self, mock_get_ledger, mock_sync_transactions, mock_sync_balance, mock_sync_ohlc):
        """Test successful synchronization."""
        # Mock authentication
        mock_get_ledger.return_value = {
            'error': [],
            'result': {'ledger': {}, 'count': 0}
        }
        
        # Mock synchronization methods
        mock_sync_transactions.return_value = 5  # 5 transactions fetched
        mock_sync_balance.return_value = True
        mock_sync_ohlc.return_value = True
        
        # Test synchronization
        result = self.wallet.synchronize(start_date="2022-01-01")
        
        # Verify results
        self.assertTrue(result['success'])
        self.assertEqual(result['transactions_fetched'], 5)
        self.assertTrue(result['balance_updated'])
        self.assertTrue(result['ohlc_updated'])
        self.assertIsNotNone(result['last_sync'])
        self.assertIsNone(result['error'])
    
    @patch.object(KrakenWallet, '_get_ledger')
    def test_synchronize_authentication_failure(self, mock_get_ledger):
        """Test synchronization with authentication failure."""
        # Mock authentication failure
        mock_get_ledger.return_value = {
            'error': ['API:Invalid key']
        }
        
        # Test synchronization
        result = self.wallet.synchronize(start_date="2022-01-01")
        
        # Verify results
        self.assertFalse(result['success'])
        self.assertEqual(result['transactions_fetched'], 0)
        self.assertFalse(result['balance_updated'])
        self.assertIsNotNone(result['error'])
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('wallets.kraken_wallet.json.load')
    def test_load_credentials_from_storage_success(self, mock_json_load, mock_file):
        """Test successful credential loading from storage."""
        # Mock file content
        mock_json_load.return_value = {
            'KRAKEN_API_KEY': 'encrypted_key',
            'KRAKEN_API_SECRET': 'encrypted_secret'
        }
        
        # Mock decryption
        with patch.object(self.wallet, '_decrypt_message') as mock_decrypt:
            mock_decrypt.side_effect = ['decrypted_key', 'decrypted_secret']
            
            # Test credential loading
            result = self.wallet.load_credentials_from_storage()
            
            # Verify results
            self.assertTrue(result)
            self.assertEqual(self.wallet.api_key, 'decrypted_key')
            self.assertEqual(self.wallet.api_secret, 'decrypted_secret')
    
    def test_load_credentials_from_storage_missing_files(self):
        """Test credential loading with missing files."""
        # Test with missing files
        result = self.wallet.load_credentials_from_storage()
        
        # Verify results
        self.assertFalse(result)
    
    def test_decimal_from_value(self):
        """Test decimal conversion."""
        # Test string value
        result = self.wallet._decimal_from_value("1.5")
        self.assertEqual(result, Decimal('1.5'))
        
        # Test float value
        result = self.wallet._decimal_from_value(2.75)
        self.assertEqual(result, Decimal('2.75'))
        
        # Test integer value
        result = self.wallet._decimal_from_value(10)
        self.assertEqual(result, Decimal('10'))
    
    def test_decimal_sum(self):
        """Test decimal summation."""
        result = self.wallet._decimal_sum("1.5", "2.5")
        self.assertEqual(result, Decimal('4.0'))
        
        result = self.wallet._decimal_sum(Decimal('1.5'), Decimal('2.5'))
        self.assertEqual(result, Decimal('4.0'))
    
    @patch('cryptography.fernet.Fernet')
    def test_decrypt_message(self, mock_fernet):
        """Test message decryption."""
        # Mock Fernet
        mock_fernet_instance = Mock()
        mock_fernet_instance.decrypt.return_value = b'decrypted_message'
        mock_fernet.return_value = mock_fernet_instance
        
        # Mock file read
        with patch('builtins.open', mock_open(read_data=b'secret_key')):
            result = self.wallet._decrypt_message('encrypted_message')
            
            # Verify results
            self.assertEqual(result, 'decrypted_message')
    
    def test_normalize_assets_name(self):
        """Test asset name normalization."""
        # Create test DataFrame with assetnorm column
        df = pd.DataFrame({
            'asset': ['EUR', 'XBT', 'ETH', 'BTC.21', 'MATIC.21'],
            'assetnorm': ['EUR', 'XBT', 'ETH', 'BTC.21', 'MATIC.21']  # Add the required column
        })
        
        # Test normalization
        result = self.wallet._normalize_assets_name(df, 'asset')
        
        # Verify results
        self.assertIn('assetnorm', result.columns)
        self.assertEqual(result.loc[0, 'assetnorm'], 'ZEUR')
        self.assertEqual(result.loc[1, 'assetnorm'], 'XXBT')
        self.assertEqual(result.loc[2, 'assetnorm'], 'XETH')
        self.assertEqual(result.loc[3, 'assetnorm'], 'BTC')  # Fixed: BTC.21 -> BTC
        self.assertEqual(result.loc[4, 'assetnorm'], 'MATIC')
    
    @patch('wallets.kraken_wallet.requests.get')
    def test_get_ohlc_data_success(self, mock_get):
        """Test successful OHLC data retrieval."""
        # Mock successful OHLC response
        mock_response = Mock()
        mock_response.json.return_value = {
            'error': [],
            'result': {
                'XXBTZEUR': [
                    [1640995200, 50000, 51000, 49000, 50500, 50250, 100, 50],
                    [1641081600, 50500, 52000, 50000, 51500, 51250, 150, 75]
                ],
                'last': 1641081600
            }
        }
        mock_get.return_value = mock_response
        
        # Test OHLC data retrieval
        result = self.wallet._get_ohlc_data('XXBTZEUR', 'XXBTZEUR')
        
        # Verify results
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn('open', result.columns)
        self.assertIn('high', result.columns)
        self.assertIn('low', result.columns)
        self.assertIn('close', result.columns)
    
    @patch('wallets.kraken_wallet.requests.get')
    def test_get_ohlc_data_error(self, mock_get):
        """Test OHLC data retrieval with error."""
        # Mock error response
        mock_response = Mock()
        mock_response.json.return_value = {
            'error': ['Invalid pair']
        }
        mock_get.return_value = mock_response
        
        # Test OHLC data retrieval
        result = self.wallet._get_ohlc_data('INVALID', 'INVALID')
        
        # Verify results
        self.assertTrue(result.empty)
    
    def test_ensure_data_directories(self):
        """Test data directory creation."""
        # Remove existing directories
        test_dirs = [
            os.path.join(self.persistent_data_dir, 'data'),
            os.path.join(self.persistent_data_dir, 'logs'),
            os.path.join(self.persistent_data_dir, 'config')
        ]
        
        for dir_path in test_dirs:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
        
        # Test directory creation
        self.wallet._ensure_data_directories()
        
        # Verify directories were created
        for dir_path in test_dirs:
            self.assertTrue(os.path.exists(dir_path))
    
    def test_totimestamp(self):
        """Test timestamp conversion."""
        result = self.wallet._totimestamp("2022-01-01")
        # Note: This depends on timezone. Let's use a more flexible approach
        expected_2022_01_01 = 1640995200  # Unix timestamp for 2022-01-01 UTC
        # Allow for timezone differences (within 24 hours)
        self.assertGreaterEqual(result, expected_2022_01_01 - 86400)
        self.assertLessEqual(result, expected_2022_01_01 + 86400)
    
    @patch('wallets.kraken_wallet.requests.post')
    def test_kraken_request(self, mock_post):
        """Test Kraken API request."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {'result': 'test'}
        mock_post.return_value = mock_response
        
        # Test request with proper data including nonce
        test_data = {
            'param': 'value',
            'nonce': str(int(1_000_000*time.time()))  # Add required nonce
        }
        
        # Use a properly encoded API secret for testing
        self.wallet.api_secret = "dGVzdF9hcGlfc2VjcmV0X2Zvcl90ZXN0aW5n"  # base64 encoded "test_api_secret_for_testing"
        
        result = self.wallet._kraken_request('/test', test_data)
        
        # Verify results
        self.assertEqual(result, mock_response)
        mock_post.assert_called_once()
    
    @patch('wallets.kraken_wallet.requests.get')
    def test_kraken_public_request(self, mock_get):
        """Test Kraken public API request."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {'result': 'test'}
        mock_get.return_value = mock_response
        
        # Test request
        result = self.wallet._kraken_public_request('/test')
        
        # Verify results
        self.assertEqual(result, mock_response)
        mock_get.assert_called_once()


class TestKrakenWalletIntegration(unittest.TestCase):
    """Integration tests for KrakenWallet class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.persistent_data_dir = os.path.join(self.test_dir, 'persistent_data')
        
        # Create test wallet
        self.wallet = KrakenWallet("test_key", "test_secret")
        self.wallet.persistent_data_dir = self.persistent_data_dir
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch.object(KrakenWallet, '_synchronize_ohlc_data')
    @patch.object(KrakenWallet, '_synchronize_balance')
    @patch.object(KrakenWallet, '_synchronize_transactions')
    @patch.object(KrakenWallet, '_get_ledger')
    def test_full_synchronization_workflow(self, mock_get_ledger, mock_sync_transactions, mock_sync_balance, mock_sync_ohlc):
        """Test complete synchronization workflow."""
        # Mock authentication
        mock_get_ledger.return_value = {
            'error': [],
            'result': {'ledger': {}, 'count': 0}
        }
        
        # Mock synchronization methods
        mock_sync_transactions.return_value = 10  # 10 transactions fetched
        mock_sync_balance.return_value = True
        mock_sync_ohlc.return_value = True
        
        # Test synchronization
        result = self.wallet.synchronize(start_date="2022-01-01")
        
        # Verify results
        self.assertTrue(result['success'])
        self.assertEqual(result['transactions_fetched'], 10)
        self.assertTrue(result['balance_updated'])
        self.assertTrue(result['ohlc_updated'])
        
        # Note: File existence checks removed since we're mocking everything
        # and the actual files won't be created in the test environment


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2) 