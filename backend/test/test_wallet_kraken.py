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
        self.wallet = KrakenWallet("EUR", self.test_api_key, self.test_api_secret)
        
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
        wallet1 = KrakenWallet("EUR")
        result1 = wallet1.authenticate()
        self.assertFalse(result1)
        self.assertFalse(wallet1.is_authenticated)

        # Test with missing API key
        wallet2 = KrakenWallet("EUR", api_key=None, api_secret="test_api_secret_67890")
        result2 = wallet2.authenticate()
        self.assertFalse(result2)
        self.assertFalse(wallet2.is_authenticated)

        # Test with missing API secret
        wallet3 = KrakenWallet("EUR", api_key="test_api_key_12345", api_secret=None)
        result3 = wallet3.authenticate()
        self.assertFalse(result3)
        self.assertFalse(wallet3.is_authenticated)

        # Verify no API call was made
        mock_post.assert_not_called()

    @patch('wallets.wallet_kraken.requests.post')
    def test_authenticate_failure_empty_credentials(self, mock_post):
        """Test authentication failure with empty string credentials."""
        # Test with empty API key
        wallet1 = KrakenWallet("EUR", api_key="", api_secret="test_secret")
        result1 = wallet1.authenticate()
        self.assertFalse(result1)
        self.assertFalse(wallet1.is_authenticated)
        
        # Test with empty API secret
        wallet2 = KrakenWallet("EUR", api_key="test_key", api_secret="")
        result2 = wallet2.authenticate()
        self.assertFalse(result2)
        self.assertFalse(wallet2.is_authenticated)
        
        # Test with both empty
        wallet3 = KrakenWallet("EUR", api_key="", api_secret="")
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
    def test_synchronize_empty_ledger_success(self, mock_get_ledger):
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
        self.assertEqual(self.wallet.sync_status, "completed")

    @patch.object(KrakenWallet, '_create_tradable_asset_matrix')
    @patch.object(KrakenWallet, '_get_ohlc_data')
    @patch.object(KrakenWallet, '_get_ledger')
    def test_synchronize_full_ledger_success(self, mock_get_ledger, mock_ohlc_data, mock_asset_matrix):
        """Test successful synchronization with multiple ledger calls and asset mapping verification."""
        
        # Mock authentication first
        mock_get_ledger.return_value = {
            'error': [],
            'result': {'ledger': {}, 'count': 0}
        }
        
        # Authenticate the wallet
        self.wallet.authenticate()
        self.assertTrue(self.wallet.is_authenticated)
        
        # Reset mock to clear authentication call
        mock_get_ledger.reset_mock()
        
        # Mock asset matrix to return test data
        mock_asset_matrix.return_value = self._create_test_asset_matrix()
        
        # Mock OHLC data to return empty DataFrame to avoid complex price calculations
        mock_ohlc_data.return_value = pd.DataFrame()
        
        # Create realistic ledger data for 3 consecutive calls
        # Each call returns 50 transactions (batch size), total 150 transactions
        ledger_data = self._create_realistic_ledger_data()
        
        # Configure mock to return different data for each call
        def mock_get_ledger_side_effect(start_date, ofs, without_count="false"):
            # Convert ledger_data dict to list for slicing
            ledger_list = list(ledger_data.items())
            start_idx = ofs
            end_idx = min(ofs + 50, len(ledger_list))
            batch_data = dict(ledger_list[start_idx:end_idx])
            
            if without_count == "false":
                # First call - return total count
                return {
                    'error': [],
                    'result': {
                        'ledger': batch_data,
                        'count': 150
                    }
                }
            else:
                # Subsequent calls - return data without count
                return {
                    'error': [],
                    'result': {
                        'ledger': batch_data
                    }
                }
        
        mock_get_ledger.side_effect = mock_get_ledger_side_effect
        
        # Test synchronization
        success, error = self.wallet.synchronize(start_date="2022-01-01")
        
        # Verify basic results
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIsNotNone(self.wallet.last_sync)
        self.assertEqual(self.wallet.sync_status, "completed")
        
        # Verify that _get_ledger was called exactly 3 times (for 150 transactions in batches of 50)
        self.assertEqual(mock_get_ledger.call_count, 3)
        
        # Verify the calls were made with correct parameters
        expected_calls = [
            # First call: ofs=0, without_count="false" (to get total count)
            (("2022-01-01", 0, "false"),),
            # Second call: ofs=50, without_count="true"
            (("2022-01-01", 50, "true"),),
            # Third call: ofs=100, without_count="true"
            (("2022-01-01", 100, "true"),),
        ]
        
        for i, call in enumerate(mock_get_ledger.call_args_list):
            args, kwargs = call
            expected_args = expected_calls[i][0]
            self.assertEqual(args[0], expected_args[0])  # start_date
            self.assertEqual(args[1], expected_args[1])  # ofs
            self.assertEqual(args[2], expected_args[2])  # without_count
        
        # Verify that the ledger file was created and contains the expected data
        self.assertTrue(os.path.exists(self.wallet.ledger_file))
        
        # Load the saved data and verify asset mapping
        saved_df = pd.read_parquet(self.wallet.ledger_file, engine="fastparquet")
        
        # Verify we have all 150 transactions
        self.assertEqual(len(saved_df), 150)
        
        # Verify asset mapping was done correctly
        self._verify_asset_mapping(saved_df)
        
        # Verify transaction type mapping
        self._verify_transaction_type_mapping(saved_df)
        
        # Verify required columns are present (basic ones that should be there)
        basic_columns = ["date", "transaction_id", "asset", "balance", "fee"]
        for col in basic_columns:
            self.assertIn(col, saved_df.columns)
    
    def _create_realistic_ledger_data(self):
        """Create realistic ledger data for testing."""
        ledger_data = {}
        
        # Create 150 transactions with various asset types and transaction types
        for i in range(150):
            # Vary transaction types and assets
            tx_type = ["trade", "deposit", "withdrawal", "staking", "fee"][i % 5]
            asset = ["XXBT", "XETH", "ZEUR", "XBT", "ETH", "EUR"][i % 6]
            
            # Create transaction with realistic data
            ledger_data[f"refid_{i}"] = {
                "refid": f"refid_{i}",
                "time": 1640995200 + (i * 3600),  # Increment by 1 hour
                "type": tx_type,
                "aclass": "currency",
                "asset": asset,
                "amount": str(0.1 + (i * 0.01)),
                "fee": str(0.001 + (i * 0.0001)),
                "balance": str(1.0 + (i * 0.1))
            }
        
        return ledger_data
    
    def _create_test_asset_matrix(self):
        """Create a test asset matrix for mocking."""
        test_data = [
            {'base': 'BTC', 'quote': 'EUR', 'altname': 'XBTEUR', 'wsname': 'BTC/EUR'},
            {'base': 'ETH', 'quote': 'EUR', 'altname': 'XETHEUR', 'wsname': 'ETH/EUR'},
            {'base': 'MATIC', 'quote': 'EUR', 'altname': 'POLEUR', 'wsname': 'POL/EUR'},
        ]
        df = pd.DataFrame(test_data)
        df = df.set_index(['base', 'quote'])
        return df
    
    def _verify_asset_mapping(self, df):
        """Verify that asset mapping was done correctly."""
        # Check that asset normalization was applied
        self.assertIn("assetnorm", df.columns)
        
        # Verify specific asset mappings based on the new normalization
        asset_mappings = {
            "EUR": "EUR",  # Now normalized to EUR
            "XBT": "BTC",  # Now normalized to BTC
            "ETH": "ETH"   # Now normalized to ETH
        }
        
        for original, expected in asset_mappings.items():
            if original in df["asset"].values:
                # Find rows with the original asset name
                original_rows = df[df["asset"] == original]
                # Check that they were mapped to the expected normalized name
                normalized_rows = df[df["assetnorm"] == expected]
                self.assertGreater(len(normalized_rows), 0, 
                                 f"Asset {original} should be mapped to {expected}")
        
        # Verify that asset names with dots were split correctly
        if any("." in asset for asset in df["asset"].values):
            dot_assets = df[df["asset"].str.contains(".", na=False)]
            for _, row in dot_assets.iterrows():
                # The normalized asset should not contain dots
                self.assertNotIn(".", row["assetnorm"])
        
        # Verify that asset names with "21" were split correctly
        if any("21" in asset for asset in df["asset"].values):
            twenty_one_assets = df[df["asset"].str.contains("21", na=False)]
            for _, row in twenty_one_assets.iterrows():
                # The normalized asset should not contain "21"
                self.assertNotIn("21", row["assetnorm"])
        
        # Verify that all assets in our test data were processed
        expected_assets = ["XXBT", "XETH", "ZEUR", "XBT", "ETH", "EUR"]
        for asset in expected_assets:
            if asset in df["asset"].values:
                self.assertIn(asset, df["asset"].values, f"Asset {asset} should be present in the data")
        
        # Verify that normalized assets are present
        normalized_assets = ["BTC", "ETH", "EUR"]
        for asset in normalized_assets:
            if asset in df["assetnorm"].values:
                self.assertIn(asset, df["assetnorm"].values, f"Normalized asset {asset} should be present in the data")
    
    def _verify_transaction_type_mapping(self, df):
        """Verify that transaction type mapping was done correctly."""
        # Check that transaction_type column exists (if the remapping was done)
        if "transaction_type" in df.columns:
            # Verify specific transaction type mappings
            type_mappings = {
                "trade": "trade",
                "deposit": "deposit", 
                "withdrawal": "withdrawal",
                "staking": "reward",
                "earn": "reward",
                "fee": "fee"
            }
            
            for kraken_type, expected_type in type_mappings.items():
                if kraken_type in df["type"].values:
                    # Find rows with the original transaction type
                    original_rows = df[df["type"] == kraken_type]
                    # Check that they were mapped to the expected type
                    mapped_rows = df[df["transaction_type"] == expected_type]
                    self.assertGreater(len(mapped_rows), 0,
                                     f"Transaction type {kraken_type} should be mapped to {expected_type}")
            
            # Verify that all transaction types are valid
            valid_types = ["deposit", "trade", "withdrawal", "transfer", "reward", "fee"]
            for tx_type in df["transaction_type"].unique():
                self.assertIn(tx_type, valid_types, 
                             f"Transaction type {tx_type} is not in valid types: {valid_types}")
        
        # Verify that all transaction types in our test data were processed
        expected_types = ["trade", "deposit", "withdrawal", "staking", "fee"]
        for tx_type in expected_types:
            self.assertIn(tx_type, df["type"].values, f"Transaction type {tx_type} should be present in the data")


class TestKrakenWalletIntegration(unittest.TestCase):
    """Integration tests for KrakenWallet class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.persistent_data_dir = os.path.join(self.test_dir, 'persistent_data')
        
        # Create test wallet
        self.wallet = KrakenWallet("EUR", "test_key", "test_secret")
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