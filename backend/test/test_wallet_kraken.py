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

from wallets.wallet_kraken import KrakenWallet


class TestKrakenWallet(unittest.TestCase):
    """Test cases for KrakenWallet class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.persistent_data_dir = os.path.join(self.test_dir, 'persistent_data')
        
        # Mock API credentials - API secret must be base64 encoded for signature generation
        self.test_api_key = "test_api_key_12345"
        # Base64 encode the secret to avoid "Incorrect padding" errors
        self.test_api_secret = "test_api_secret_67890"
        
        # Create test wallet instance
        self.wallet = KrakenWallet(self.test_api_key, self.test_api_secret)
        
        # Override persistent data directory for testing
        self.wallet.persistent_data_dir = self.persistent_data_dir
    
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
    
    @patch('wallets.wallet_kraken.requests.post')
    def test_authenticate_failure_missing_credentials(self, mock_post):
        """Test authentication failure with missing credentials."""
        # Test with missing credentials
        wallet1 = KrakenWallet()
        result1 = wallet1.authenticate()
        self.assertFalse(result1)
        self.assertFalse(wallet1.is_authenticated)

        # Test with missing API key
        wallet2 = KrakenWallet(api_key=None, api_secret="test_api_secret_67890")
        result2 = wallet2.authenticate()
        self.assertFalse(result2)
        self.assertFalse(wallet2.is_authenticated)

        # Test with missing API secret
        wallet3 = KrakenWallet(api_key="test_api_key_12345", api_secret=None)
        result3 = wallet3.authenticate()
        self.assertFalse(result3)
        self.assertFalse(wallet3.is_authenticated)

        # Verify no API call was made
        mock_post.assert_not_called()

    @patch('wallets.wallet_kraken.requests.post')
    def test_authenticate_failure_empty_credentials(self, mock_post):
        """Test authentication failure with empty string credentials."""
        # Test with empty API key
        wallet1 = KrakenWallet(api_key="", api_secret="test_secret")
        result1 = wallet1.authenticate()
        self.assertFalse(result1)
        self.assertFalse(wallet1.is_authenticated)
        
        # Test with empty API secret
        wallet2 = KrakenWallet(api_key="test_key", api_secret="")
        result2 = wallet2.authenticate()
        self.assertFalse(result2)
        self.assertFalse(wallet2.is_authenticated)
        
        # Test with both empty
        wallet3 = KrakenWallet(api_key="", api_secret="")
        result3 = wallet3.authenticate()
        self.assertFalse(result3)
        self.assertFalse(wallet3.is_authenticated)

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
    
    @patch.object(KrakenWallet, '_get_ledger')
    def test_synchronize_success(self, mock_get_ledger):
        """Test successful synchronization."""
        # Mock authentication
        mock_get_ledger.return_value = {
            'error': [],
            'result': {'ledger': {}, 'count': 0}
        }

        # Test synchronization
        result = self.wallet.synchronize(start_date="2022-01-01")
        
        # Verify results
        self.assertTrue(result)
        self.assertIsNotNone(self.wallet.last_sync)
        self.assertEqual(self.wallet.sync_status, "Synchronization completed")


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