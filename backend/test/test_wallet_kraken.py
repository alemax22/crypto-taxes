#!/usr/bin/env python3
"""
Unit tests for KrakenWallet class
Tests the Kraken wallet implementation with mocked API calls
"""

import unittest
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import pandas as pd
import json
import os
import tempfile
import shutil
import time
from datetime import datetime, timedelta
from decimal import Decimal

# Add the parent directory to Python path to import backend modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wallets.wallet_kraken import KrakenWallet, EXCEPTION_ASSETS
from config import RESAMPLING_INTERVAL_IN_SECONDS

@pytest.mark.unit
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
        self.wallet = KrakenWallet("My Kraken Wallet Name", "KRAKEN-1", "EUR", "My Kraken Wallet Description", self.test_api_key, self.test_api_secret)
        
        # Override ledger file path for testing (keep filename, change base folder)
        self.wallet.ledger_file = os.path.join(self.persistent_data_dir, "data", "kraken_ledger.parquet")
        
        # Also override OHLC file path for testing (keep filename, change base folder)
        self.wallet.ohlc_file = os.path.join(self.persistent_data_dir, "data", "kraken_ohlc.parquet")
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_init(self):
        """Test wallet initialization."""
        self.assertEqual(self.wallet.name, "My Kraken Wallet Name")
        self.assertEqual(self.wallet.id, "KRAKEN-1")
        self.assertEqual(self.wallet.reference_fiat, "EUR")
        self.assertEqual(self.wallet.description, "My Kraken Wallet Description")
        self.assertEqual(self.wallet.api_key, self.test_api_key)
        self.assertEqual(self.wallet.api_secret, self.test_api_secret)
        self.assertFalse(self.wallet.is_active)
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
        self.assertTrue(self.wallet.is_active)
        
        # Verify the method was called
        mock_get_ledger.assert_called_once()
    
    @patch('wallets.wallet_kraken.requests.post')
    def test_authenticate_failure_missing_credentials(self, mock_post):
        """Test authentication failure with missing credentials."""
        # Test with missing credentials
        wallet1 = KrakenWallet("My Kraken Wallet Name", "KRAKEN-1", "EUR", "My Kraken Wallet Description")
        result1 = wallet1.authenticate()
        self.assertFalse(result1)
        self.assertFalse(wallet1.is_active)

        # Test with missing API key
        wallet2 = KrakenWallet("My Kraken Wallet Name", "KRAKEN-1", "EUR", "My Kraken Wallet Description", api_key=None, api_secret="test_api_secret_67890")
        result2 = wallet2.authenticate()
        self.assertFalse(result2)
        self.assertFalse(wallet2.is_active)

        # Test with missing API secret
        wallet3 = KrakenWallet("My Kraken Wallet Name", "KRAKEN-1", "EUR", "My Kraken Wallet Description", api_key="test_api_key_12345", api_secret=None)
        result3 = wallet3.authenticate()
        self.assertFalse(result3)
        self.assertFalse(wallet3.is_active)

        # Verify no API call was made
        mock_post.assert_not_called()

    @patch('wallets.wallet_kraken.requests.post')
    def test_authenticate_failure_empty_credentials(self, mock_post):
        """Test authentication failure with empty string credentials."""
        # Test with empty API key
        wallet1 = KrakenWallet("My Kraken Wallet Name", "KRAKEN-1", "EUR", "My Kraken Wallet Description", api_key="", api_secret="test_secret")
        result1 = wallet1.authenticate()
        self.assertFalse(result1)
        self.assertFalse(wallet1.is_active)
        
        # Test with empty API secret
        wallet2 = KrakenWallet("My Kraken Wallet Name", "KRAKEN-1", "EUR", "My Kraken Wallet Description", api_key="test_key", api_secret="")
        result2 = wallet2.authenticate()
        self.assertFalse(result2)
        self.assertFalse(wallet2.is_active)
        
        # Test with both empty
        wallet3 = KrakenWallet("My Kraken Wallet Name", "KRAKEN-1", "EUR", "My Kraken Wallet Description", api_key="", api_secret="")
        result3 = wallet3.authenticate()
        self.assertFalse(result3)
        self.assertFalse(wallet3.is_active)

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
        self.assertFalse(self.wallet.is_active)
    
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

    @patch.object(time, 'sleep')
    @patch.object(KrakenWallet, '_get_tradable_assets_info')
    @patch.object(KrakenWallet, '_get_ohlc_data')
    @patch.object(KrakenWallet, '_get_ledger')
    def test_synchronize_full_ledger_success(self, mock_get_ledger, mock_ohlc_data, mock_get_tradable_assets_info, mock_sleep):
        """Test successful synchronization with multiple ledger calls and asset mapping verification."""
        
        # Mock sleep to avoid waiting for rate limiting as we are not performing any API calls
        mock_sleep.return_value = None

        start_timestamp = 1640995200

        # Mock authentication first
        mock_get_ledger.return_value = {
            'error': [],
            'result': {'ledger': {}, 'count': 0}
        }
        
        # Authenticate the wallet
        self.wallet.authenticate()
        self.assertTrue(self.wallet.is_active)
        
        # Reset mock to clear authentication call
        mock_get_ledger.reset_mock()
        
        # Mock asset matrix to return test data
        mock_get_tradable_assets_info.return_value = self._simulate_tradable_assets_info()
        
        # Mock OHLC data to return test data to avoid complex price calculations
        mock_ohlc_data.return_value = self._simulate_ohlc_data(start_timestamp, 170)

        # Configure mock to return different data for each call
        def mock_get_ledger_side_effect(start_timestamp, ofs, without_count="false"):
            # Load data from anonymized JSON files
            json_files = [
                'data/_get_ledger_0.json',
                'data/_get_ledger_1.json',
                'data/_get_ledger_2.json',
                'data/_get_ledger_3.json'
            ]
            
            # Determine which file to use based on offset
            file_index = ofs // 50
            if file_index >= len(json_files):
                # Return empty data if we've exhausted all files
                return {
                    'error': [],
                    'result': {
                        'ledger': {},
                        'count': 0
                    }
                }
            
            # Load the appropriate JSON file
            import json
            with open(os.path.join(os.path.dirname(__file__), json_files[file_index]), 'r') as f:
                file_data = json.load(f)
            
            ledger_data = file_data['result']['ledger']
            
            if without_count == "false":
                # First call - return total count
                return {
                    'error': [],
                    'result': {
                        'ledger': ledger_data,
                        'count': 178  # Total count from all files
                    }
                }
            else:
                # Subsequent calls - return data without count
                return {
                    'error': [],
                    'result': {
                        'ledger': ledger_data
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
        
        # Verify that _get_ledger was called exactly 4 times (for 178 transactions in batches of 50)
        self.assertEqual(mock_get_ledger.call_count, 4)
        
        # Verify the calls were made with correct parameters
        for i, call in enumerate(mock_get_ledger.call_args_list):
            args, kwargs = call
            self.assertEqual(args[0], start_timestamp)
            
            # Check offset and without_count parameters
            expected_ofs = [0, 50, 100, 150][i]
            expected_without_count = ["false", "true", "true", "true"][i]
            self.assertEqual(args[1], expected_ofs)  # ofs
            self.assertEqual(args[2], expected_without_count)  # without_count
        
        # Verify that the ledger file was created and contains the expected data
        self.assertTrue(os.path.exists(self.wallet.ledger_file))
        
        # Load the saved data and verify asset mapping
        saved_df = self.wallet._retrieve_local_ledger_data()

        # Verify we have all 178 transactions from the JSON files
        self.assertEqual(len(saved_df), 178)
        
        # Verify asset mapping was done correctly
        self._verify_asset_mapping(saved_df)
        
        # Verify transaction type mapping
        self._verify_transaction_type_mapping(saved_df)
        
        # Verify required columns are present (basic ones that should be there)
        basic_columns = ["datetime", 
                         "correlation_id",
                         "transaction_id", 
                         "transaction_type",
                         "asset",
                         "amount",
                         "balance",
                         "asset_price_in_reference_fiat",
                         "fee",
                         "transaction_original_type",
                         "asset_original_name",
                         "asset_original_balance"]
        for col in basic_columns:
            self.assertIn(col, saved_df.columns)

        # Verify that all the rows have a price in reference fiat
        nan_price_mask = saved_df["asset_price_in_reference_fiat"].isna()
        zero_price_mask = saved_df["asset_price_in_reference_fiat"] == Decimal('0')
        not_exception_mask = ~saved_df["asset"].isin(EXCEPTION_ASSETS)
        filter_mask = (nan_price_mask | zero_price_mask) & not_exception_mask
        self.assertFalse(filter_mask.any(), "There are transactions without a price: " + str(saved_df[filter_mask].shape))

        # Check that the balance column has always positive values
        self.assertTrue((saved_df["balance"] >= 0).all(), "Balance column should have positive values")

    def _simulate_ohlc_data(self, start_timestamp, num_days):
        assets_list = [
            {'asset': 'BTC', 'price': 50000.0},
            {'asset': 'ETH', 'price': 3000.0},
            {'asset': '1INCH', 'price': 3.0},
            {'asset': 'EOS', 'price': 10.0},
            {'asset': 'SOL', 'price': 130.0},
            {'asset': 'LUNA', 'price': 60.0},
            {'asset': 'UNI', 'price': 30.0},
            {'asset': 'UST', 'price': 0.90},
            {'asset': 'KSM', 'price': 250.0},
            {'asset': 'DOT', 'price': 10.0},
            {'asset': 'ATOM', 'price': 10.0},
            {'asset': 'ADA', 'price': 2.5}
        ]
        num_assets = len(assets_list)
        aligned_start_timestamp = (start_timestamp // RESAMPLING_INTERVAL_IN_SECONDS) * RESAMPLING_INTERVAL_IN_SECONDS
        timestamps_list = [aligned_start_timestamp + (i // num_assets) * RESAMPLING_INTERVAL_IN_SECONDS for i in range(num_days * num_assets)]
        dates_list = [datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d') for timestamp in timestamps_list]
        test_ohlc_data = pd.DataFrame({
            'asset': [asset['asset'] for asset in assets_list] * num_days,
            'price': [asset['price'] for asset in assets_list] * num_days,
            'timestamp': timestamps_list,
            'date': dates_list,
        })
        test_ohlc_data = test_ohlc_data.set_index(['date', 'asset'])
        return test_ohlc_data
    
    def _simulate_tradable_assets_info(self):
        """Read tradable assets info from file trad_response_json.json"""
        with open(os.path.join(os.path.dirname(__file__), "data", "_get_tradable_assets_info.json"), "r") as file:
            trad_response_json = json.load(file)
        return trad_response_json
    
    def _verify_asset_mapping(self, df):
        """Verify that asset mapping was done correctly based on actual JSON data."""
        # Check that required columns exist
        self.assertIn("asset", df.columns, "asset column should exist")
        self.assertIn("asset_original_name", df.columns, "asset_original_name column should exist")
        
        # Get unique assets from both columns
        original_assets = sorted(df["asset_original_name"].unique())
        normalized_assets = sorted(df["asset"].unique())
        
        # Define expected original assets from JSON files
        expected_original_assets = [
            "1INCH", "ADA", "ADA.S", "ATOM", "ATOM.S", "DOT", "DOT.S", 
            "EOS", "EUR.HOLD", "KSM", "KSM.S", "LUNA", "LUNA.S", 
            "SOL", "SOL.S", "UNI", "UST", "XETH", "XXBT", "ZEUR"
        ]
        
        # Define expected normalized assets based on _normalize_asset_name function
        expected_normalized_assets = [
            "1INCH", "ADA", "ATOM", "BTC", "DOT", "EOS", "ETH", "EUR", "KSM", "LUNA", 
            "SOL", "UNI", "UST"
        ]
        
        # Verify all expected original assets are present
        for asset in expected_original_assets:
            self.assertIn(asset, original_assets, 
                         f"Expected original asset {asset} not found in data")
        
        # Verify all expected normalized assets are present
        for asset in expected_normalized_assets:
            self.assertIn(asset, normalized_assets, 
                         f"Expected normalized asset {asset} not found in data")
        
        # Verify specific normalization mappings
        normalization_mappings = {
            # Staking assets (.S) -> base assets
            "ADA.S": "ADA",
            "ATOM.S": "ATOM", 
            "DOT.S": "DOT",
            "KSM.S": "KSM",
            "LUNA.S": "LUNA",
            "SOL.S": "SOL",
            # Special Kraken asset mappings
            "ZEUR": "EUR",
            "XXBT": "BTC",
            "XETH": "ETH",
            "EUR.HOLD": "EUR",
            # Assets that should remain unchanged
            "1INCH": "1INCH",
            "ADA": "ADA",
            "ATOM": "ATOM",
            "DOT": "DOT",
            "EOS": "EOS",
            "KSM": "KSM",
            "LUNA": "LUNA",
            "SOL": "SOL",
            "UNI": "UNI",
            "UST": "UST"
        }
        
        # Verify each mapping
        for original, expected in normalization_mappings.items():
            if original in original_assets:
                # Get all rows with this original asset
                original_rows = df[df["asset_original_name"] == original]
                # Check that all rows have the expected normalized asset
                for _, row in original_rows.iterrows():
                    self.assertEqual(row["asset"], expected,
                                   f"Asset {original} should normalize to {expected}, but got {row['asset']}")
    
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
                if kraken_type in df["transaction_original_type"].values:
                    # Find rows with the original transaction type
                    original_rows = df[df["transaction_original_type"] == kraken_type]
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
        expected_types = ["trade", "deposit", "withdrawal", "staking"]
        for tx_type in expected_types:
            self.assertIn(tx_type, df["transaction_original_type"].values, f"Transaction type {tx_type} should be present in the data")

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2) 