#!/usr/bin/env python3
"""
Unit tests for base Wallet class
Tests the base wallet implementation methods
"""

import os
import shutil

# Add the parent directory to Python path to import backend modules
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import RESAMPLING_INTERVAL_IN_SECONDS
from wallets.wallet import Wallet


class MockWallet(Wallet):
    """Concrete implementation of Wallet for testing abstract methods."""

    def __init__(
        self,
        name: str,
        id: str,
        reference_fiat: str,
        portfolio_id: str = "test_portfolio",
        description: str = "",
        api_key: str = None,
        api_secret: str = None,
    ):
        super().__init__(
            name, id, reference_fiat, portfolio_id, description, api_key, api_secret
        )
        self.ledger_file = None  # Will be set in tests

    def _synchronize(self, start_date=None):
        """Mock implementation."""
        return True, None

    def authenticate(self):
        """Mock implementation."""
        return True

    def _get_ohlc_data(self, assets_in_portfolio, start_date=None):
        """Mock implementation."""
        return pd.DataFrame()


@pytest.mark.unit
class TestWalletBaseMethods(unittest.TestCase):
    """Test cases for base Wallet class methods."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        self.persistent_data_dir = os.path.join(self.test_dir, "persistent_data")
        os.makedirs(self.persistent_data_dir, exist_ok=True)

        # Create test wallet instance
        self.wallet = MockWallet(
            "My Mock Wallet Name",
            "MOCK-1",
            "EUR",
            "test_portfolio",
            "My Mock Wallet Description",
        )

        # Set up ledger file path
        self.wallet.ledger_file = os.path.join(
            self.persistent_data_dir, "test_ledger.parquet"
        )

    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_wallet_initialization_created_datetime_is_set(self):
        """Test that created_datetime is set."""
        self.assertIsNotNone(self.wallet.created_datetime)

    def test_wallet_initialization_updated_datetime_is_not_set(self):
        """Test that updated_datetime is set."""
        self.assertIsNone(self.wallet.updated_datetime)

    def test_retrieve_local_ledger_data_file_not_exists(self):
        """Test _retrieve_local_ledger_data when file doesn't exist."""
        # Ensure file doesn't exist
        if os.path.exists(self.wallet.ledger_file):
            os.remove(self.wallet.ledger_file)

        # Call the method
        result = self.wallet._retrieve_local_ledger_data()

        # Verify results
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

    def test_retrieve_local_ledger_data_file_exists_with_valid_data(self):
        """Test _retrieve_local_ledger_data with valid parquet file."""
        # Create test data with all required columns
        test_data = {
            "datetime": [
                datetime(2022, 1, 1, 12, 0, 0),
                datetime(2022, 1, 2, 12, 0, 0),
            ],
            "transaction_id": ["tx1", "tx2"],
            "correlation_id": ["corr1", "corr2"],
            "transaction_type": ["trade", "deposit"],
            "asset": ["BTC", "ETH"],
            "amount": ["0.1", "1.5"],
            "balance": [0.1, 1.5],
            "asset_price_in_reference_fiat": ["50000.0", "3000.0"],
            "fee": ["0.001", "0.0"],
            "transaction_original_type": ["trade", "deposit"],
            "asset_original_name": ["XXBT", "XETH"],
            "asset_original_balance": ["0.1", "1.5"],
        }

        test_df = pd.DataFrame(test_data)

        # Save test data to parquet file
        test_df.to_parquet(
            self.wallet.ledger_file, engine="fastparquet", compression="GZIP"
        )

        # Call the method
        result = self.wallet._retrieve_local_ledger_data()

        # Verify results
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty)
        self.assertEqual(len(result), 2)

        # Verify all required columns are present
        required_columns = [
            "datetime",
            "transaction_id",
            "correlation_id",
            "transaction_type",
            "asset",
            "amount",
            "balance",
            "asset_price_in_reference_fiat",
            "fee",
            "transaction_original_type",
            "asset_original_name",
            "asset_original_balance",
        ]

        for col in required_columns:
            self.assertIn(col, result.columns, f"Required column '{col}' is missing")

        # Verify data types
        self.assertIsInstance(result["datetime"].iloc[0], datetime)
        self.assertIsInstance(result["transaction_id"].iloc[0], str)
        self.assertIsInstance(result["correlation_id"].iloc[0], str)
        self.assertIsInstance(result["transaction_type"].iloc[0], str)
        self.assertIsInstance(result["asset"].iloc[0], str)
        self.assertIsInstance(result["amount"].iloc[0], Decimal)
        self.assertIsInstance(result["balance"].iloc[0], float)
        self.assertIsInstance(result["asset_price_in_reference_fiat"].iloc[0], Decimal)
        self.assertIsInstance(result["fee"].iloc[0], Decimal)
        self.assertIsInstance(result["transaction_original_type"].iloc[0], str)
        self.assertIsInstance(result["asset_original_name"].iloc[0], str)
        self.assertIsInstance(result["asset_original_balance"].iloc[0], str)

        # Verify Decimal conversion worked correctly
        self.assertEqual(result["amount"].iloc[0], Decimal("0.1"))
        self.assertEqual(
            result["asset_price_in_reference_fiat"].iloc[0], Decimal("50000.0")
        )
        self.assertEqual(result["fee"].iloc[0], Decimal("0.001"))

    def test_retrieve_local_ledger_data_file_exists_with_missing_columns(self):
        """Test _retrieve_local_ledger_data with parquet file missing required columns."""
        # Create test data with missing columns
        test_data = {
            "datetime": [datetime(2022, 1, 1, 12, 0, 0)],
            "transaction_id": ["tx1"],
            "asset": ["BTC"],
            "amount": ["0.1"],
            # Missing: correlation_id, transaction_type, balance, etc.
        }

        test_df = pd.DataFrame(test_data)

        # Save test data to parquet file
        test_df.to_parquet(
            self.wallet.ledger_file, engine="fastparquet", compression="GZIP"
        )

        # Call the method
        result = self.wallet._retrieve_local_ledger_data()

        # Verify results - should return empty DataFrame since required columns are missing
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
        # When required columns are missing, the parquet read will fail and return empty DataFrame

    def test_retrieve_local_ledger_data_file_exists_with_invalid_data(self):
        """Test _retrieve_local_ledger_data with invalid parquet file."""
        # Create a corrupted/invalid parquet file
        with open(self.wallet.ledger_file, "w") as f:
            f.write("This is not a valid parquet file")

        # Call the method
        result = self.wallet._retrieve_local_ledger_data()

        # Verify results - should return empty DataFrame due to error
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

    def test_retrieve_local_ledger_data_with_none_values(self):
        """Test _retrieve_local_ledger_data with None values in Decimal columns."""
        # Create test data with None values
        test_data = {
            "datetime": [datetime(2022, 1, 1, 12, 0, 0)],
            "transaction_id": ["tx1"],
            "correlation_id": ["corr1"],
            "transaction_type": ["trade"],
            "asset": ["BTC"],
            "amount": [None],  # None value
            "balance": [0.1],
            "asset_price_in_reference_fiat": [None],  # None value
            "fee": [None],  # None value
            "transaction_original_type": ["trade"],
            "asset_original_name": ["XXBT"],
            "asset_original_balance": ["0.1"],
        }

        test_df = pd.DataFrame(test_data)

        # Save test data to parquet file
        test_df.to_parquet(
            self.wallet.ledger_file, engine="fastparquet", compression="GZIP"
        )

        # Call the method
        result = self.wallet._retrieve_local_ledger_data()

        # Verify results - current implementation handles None values gracefully
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

    def test_retrieve_local_ledger_data_with_numeric_strings(self):
        """Test _retrieve_local_ledger_data with numeric strings in Decimal columns."""
        # Create test data with numeric strings
        test_data = {
            "datetime": [datetime(2022, 1, 1, 12, 0, 0)],
            "transaction_id": ["tx1"],
            "correlation_id": ["corr1"],
            "transaction_type": ["trade"],
            "asset": ["BTC"],
            "amount": ["0.123456789"],  # String representation
            "balance": [0.1],
            "asset_price_in_reference_fiat": ["50000.50"],  # String representation
            "fee": ["0.001"],  # String representation
            "transaction_original_type": ["trade"],
            "asset_original_name": ["XXBT"],
            "asset_original_balance": ["0.1"],
        }

        test_df = pd.DataFrame(test_data)

        # Save test data to parquet file
        test_df.to_parquet(
            self.wallet.ledger_file, engine="fastparquet", compression="GZIP"
        )

        # Call the method
        result = self.wallet._retrieve_local_ledger_data()

        # Verify results
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty)
        self.assertEqual(len(result), 1)

        # Verify string values are converted to correct Decimal values
        self.assertEqual(result["amount"].iloc[0], Decimal("0.123456789"))
        self.assertEqual(
            result["asset_price_in_reference_fiat"].iloc[0], Decimal("50000.50")
        )
        self.assertEqual(result["fee"].iloc[0], Decimal("0.001"))

    def test_retrieve_local_ledger_data_with_invalid_strings(self):
        """Test _retrieve_local_ledger_data with invalid strings in Decimal columns."""
        # Create test data with invalid strings
        test_data = {
            "datetime": [datetime(2022, 1, 1, 12, 0, 0)],
            "transaction_id": ["tx1"],
            "correlation_id": ["corr1"],
            "transaction_type": ["trade"],
            "asset": ["BTC"],
            "amount": ["invalid_number"],  # Invalid string
            "balance": [0.1],
            "asset_price_in_reference_fiat": ["not_a_number"],  # Invalid string
            "fee": ["abc"],  # Invalid string
            "transaction_original_type": ["trade"],
            "asset_original_name": ["XXBT"],
            "asset_original_balance": ["0.1"],
        }

        test_df = pd.DataFrame(test_data)

        # Save test data to parquet file
        test_df.to_parquet(
            self.wallet.ledger_file, engine="fastparquet", compression="GZIP"
        )

        # Call the method
        result_df = self.wallet._retrieve_local_ledger_data()

        # Verify results - should return empty DataFrame due to error
        self.assertIsInstance(result_df, pd.DataFrame)
        self.assertTrue(result_df.empty)

    def test_retrieve_local_ledger_data_column_filtering(self):
        """Test _retrieve_local_ledger_data only loads required columns."""
        # Create test data with extra columns
        test_data = {
            "datetime": [datetime(2022, 1, 1, 12, 0, 0)],
            "transaction_id": ["tx1"],
            "correlation_id": ["corr1"],
            "transaction_type": ["trade"],
            "asset": ["BTC"],
            "amount": ["0.1"],
            "balance": [0.1],
            "asset_price_in_reference_fiat": ["50000.0"],
            "fee": ["0.001"],
            "transaction_original_type": ["trade"],
            "asset_original_name": ["XXBT"],
            "asset_original_balance": ["0.1"],
            "extra_column_1": ["extra_value_1"],  # Extra column
            "extra_column_2": ["extra_value_2"],  # Extra column
            "unused_column": ["unused_value"],  # Extra column
        }

        test_df = pd.DataFrame(test_data)

        # Save test data to parquet file
        test_df.to_parquet(
            self.wallet.ledger_file, engine="fastparquet", compression="GZIP"
        )

        # Call the method
        result = self.wallet._retrieve_local_ledger_data()

        # Verify results
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty)
        self.assertEqual(len(result), 1)

        # Verify only required columns are present (no extra columns)
        required_columns = [
            "datetime",
            "transaction_id",
            "correlation_id",
            "transaction_type",
            "asset",
            "amount",
            "balance",
            "asset_price_in_reference_fiat",
            "fee",
            "transaction_original_type",
            "asset_original_name",
            "asset_original_balance",
        ]

        for col in required_columns:
            self.assertIn(col, result.columns, f"Required column '{col}' is missing")

        # Verify extra columns are not present
        extra_columns = ["extra_column_1", "extra_column_2", "unused_column"]
        for col in extra_columns:
            self.assertNotIn(
                col, result.columns, f"Extra column '{col}' should not be present"
            )

    def test_save_local_ledger_data_column_filtering(self):
        """Test _save_local_ledger_data only saves required columns."""
        # Create test data with extra columns
        test_data = {
            "datetime": [datetime(2022, 1, 1, 12, 0, 0)],
            "transaction_id": ["tx1"],
            "correlation_id": ["corr1"],
            "transaction_type": ["trade"],
            "asset": ["BTC"],
            "amount": ["0.1"],
            "balance": [0.1],
            "asset_price_in_reference_fiat": ["50000.0"],
            "fee": ["0.001"],
            "transaction_original_type": ["trade"],
            "asset_original_name": ["XXBT"],
            "asset_original_balance": ["0.1"],
            "extra_column_1": ["extra_value_1"],  # Extra column
            "extra_column_2": ["extra_value_2"],  # Extra column
            "unused_column": ["unused_value"],  # Extra column
        }

        test_df = pd.DataFrame(test_data)

        # Call the save method
        self.wallet._save_local_ledger_data(test_df)

        # Verify the file was created
        self.assertTrue(os.path.exists(self.wallet.ledger_file))

        # Read back the saved data
        saved_df = pd.read_parquet(self.wallet.ledger_file, engine="fastparquet")

        # Verify only required columns are present in saved file
        required_columns = [
            "datetime",
            "transaction_id",
            "correlation_id",
            "transaction_type",
            "asset",
            "amount",
            "balance",
            "asset_price_in_reference_fiat",
            "fee",
            "transaction_original_type",
            "asset_original_name",
            "asset_original_balance",
        ]

        for col in required_columns:
            self.assertIn(
                col,
                saved_df.columns,
                f"Required column '{col}' is missing in saved file",
            )

        # Verify extra columns are not present in saved file
        extra_columns = ["extra_column_1", "extra_column_2", "unused_column"]
        for col in extra_columns:
            self.assertNotIn(
                col,
                saved_df.columns,
                f"Extra column '{col}' should not be present in saved file",
            )

    def test_get_balance_not_synchronized(self):
        """Test get_balance when wallet has not been synchronized."""
        # Ensure wallet is not synchronized
        self.wallet.updated_datetime = None

        # Call the method
        result = self.wallet.get_balance()

        # Verify results
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

    def test_get_balance_no_ledger_data(self):
        """Test get_balance when wallet is synchronized but no ledger data exists."""
        # Set wallet as synchronized
        self.wallet.updated_datetime = datetime.now()

        # Ensure no ledger file exists
        if os.path.exists(self.wallet.ledger_file):
            os.remove(self.wallet.ledger_file)

        # Call the method
        result = self.wallet.get_balance()

        # Verify results
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

    @patch.object(MockWallet, "_get_ohlc_data")
    def test_get_balance_with_valid_data(self, mock_get_ohlc_data):
        """Test get_balance with valid ledger data."""
        # Set wallet as synchronized
        self.wallet.updated_datetime = datetime.now()

        # Create test ledger data with multiple transactions for same assets
        datetime_list = [
            datetime(2022, 1, 1, 12, 6, 9, tzinfo=timezone.utc),
            datetime(2022, 1, 2, 12, 18, 6, tzinfo=timezone.utc),
            datetime(
                2022, 1, 3, 12, 3, 45, tzinfo=timezone.utc
            ),  # Latest transaction for BTC
            datetime(2022, 1, 1, 12, 7, 0, tzinfo=timezone.utc),
            datetime(
                2022, 1, 2, 12, 23, 59, tzinfo=timezone.utc
            ),  # Latest transaction for ETH
        ]
        asset_list = ["BTC", "BTC", "BTC", "ETH", "ETH"]
        asset_price_in_reference_fiat_list = [
            "50000.0",
            "51000.0",
            "52000.0",
            "3000.0",
            "3100.0",
        ]
        test_data = {
            "datetime": datetime_list,
            "transaction_id": ["tx1", "tx2", "tx3", "tx4", "tx5"],
            "correlation_id": ["corr1", "corr2", "corr3", "corr4", "corr5"],
            "transaction_type": ["trade", "trade", "trade", "trade", "trade"],
            "asset": asset_list,
            "amount": ["0.1", "0.2", "0.3", "1.0", "2.0"],
            "balance": [0.1, 0.3, 0.6, 1.0, 3.0],  # Cumulative balances
            "asset_price_in_reference_fiat": asset_price_in_reference_fiat_list,
            "fee": ["0.001", "0.001", "0.001", "0.01", "0.01"],
            "transaction_original_type": ["trade", "trade", "trade", "trade", "trade"],
            "asset_original_name": ["XXBT", "XXBT", "XXBT", "XETH", "XETH"],
            "asset_original_balance": ["0.1", "0.3", "0.6", "1.0", "3.0"],
        }

        test_df = pd.DataFrame(test_data)

        # Save test data to parquet file
        test_df.to_parquet(
            self.wallet.ledger_file, engine="fastparquet", compression="GZIP"
        )

        timestamp_now_for_mock = (
            datetime.now().timestamp() - 2 * RESAMPLING_INTERVAL_IN_SECONDS
        )
        mock_get_ohlc_data.return_value = self._simulate_ohlc_data(
            timestamp_now_for_mock, 3
        )

        # Call the method
        result = self.wallet.get_balance()

        # Verify results
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty)
        self.assertEqual(len(result), 2)  # Should have 2 assets

        # Verify required columns are present
        required_columns = [
            "asset",
            "balance",
            "balance_in_reference_fiat",
            "asset_price_in_reference_fiat",
            "timestamp",
        ]
        for col in required_columns:
            self.assertIn(col, result.columns, f"Required column '{col}' is missing")

        # Verify data types
        self.assertIsInstance(result["asset"].iloc[0], str)
        self.assertIsInstance(result["balance"].iloc[0], float)
        self.assertIsInstance(result["balance_in_reference_fiat"].iloc[0], float)
        self.assertIsInstance(result["asset_price_in_reference_fiat"].iloc[0], Decimal)

        # Verify that latest balances are used (not cumulative)
        btc_row = result[result["asset"] == "BTC"].iloc[0]
        eth_row = result[result["asset"] == "ETH"].iloc[0]

        self.assertEqual(btc_row["balance"], 0.6)  # Latest balance for BTC
        self.assertEqual(eth_row["balance"], 3.0)  # Latest balance for ETH

        # Verify price calculations
        self.assertEqual(btc_row["asset_price_in_reference_fiat"], Decimal("150000.0"))
        self.assertEqual(eth_row["asset_price_in_reference_fiat"], Decimal("10000.0"))

        # Verify balance in reference fiat calculations
        expected_btc_balance_fiat = 0.6 * 150000.0
        expected_eth_balance_fiat = 3.0 * 10000.0
        self.assertEqual(
            btc_row["balance_in_reference_fiat"], round(expected_btc_balance_fiat, 2)
        )
        self.assertEqual(
            eth_row["balance_in_reference_fiat"], round(expected_eth_balance_fiat, 2)
        )

    def _simulate_ohlc_data(self, start_timestamp, num_days):
        assets_list = [
            {"asset": "BTC", "price": 150000.0},
            {"asset": "ETH", "price": 10000.0},
        ]
        num_assets = len(assets_list)
        aligned_start_timestamp = (
            start_timestamp // RESAMPLING_INTERVAL_IN_SECONDS
        ) * RESAMPLING_INTERVAL_IN_SECONDS
        timestamps_list = [
            aligned_start_timestamp + (i // num_assets) * RESAMPLING_INTERVAL_IN_SECONDS
            for i in range(num_days * num_assets)
        ]
        dates_list = [
            datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
            for timestamp in timestamps_list
        ]
        test_ohlc_data = pd.DataFrame(
            {
                "asset": [asset["asset"] for asset in assets_list] * num_days,
                "price": [asset["price"] for asset in assets_list] * num_days,
                "timestamp": timestamps_list,
                "date": dates_list,
            }
        )
        test_ohlc_data = test_ohlc_data.set_index(["date", "asset"])
        return test_ohlc_data


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)
