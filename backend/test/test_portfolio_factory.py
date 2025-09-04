#!/usr/bin/env python3
"""
Unit tests for PortfolioFactory
Verifies portfolio creation and data reconstruction functionality
"""

import unittest
import pytest
import os
import sys
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Add the parent directory to Python path to import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wallets.portfolio_factory import PortfolioFactory
from wallets.portfolio import Portfolio

@pytest.mark.unit
class TestPortfolioFactory(unittest.TestCase):
    def setUp(self):
        self.factory = PortfolioFactory()
        self.patches = []

        wallet_repository_patch = patch('wallets.wallet_repository.PostgresWalletRepository.__new__')
        wallet_repository = wallet_repository_patch.start()
        wallet_repository.return_value = MagicMock()
        self.patches.append(wallet_repository_patch)
    
    def tearDown(self):
        for patch in self.patches:
            patch.stop()

    def test_create_portfolio_success(self):
        """Test successful portfolio creation with all parameters."""
        user_id = "TEST-USER-123"
        reference_asset = "USD"
        portfolio_id = "PF-TEST-123"
        created_datetime = datetime.now(timezone.utc)

        portfolio = self.factory.create_portfolio(
            user_id=user_id,
            reference_asset=reference_asset,
            portfolio_id=portfolio_id,
            created_datetime=created_datetime
        )

        self.assertIsNotNone(portfolio)
        self.assertIsInstance(portfolio, Portfolio)
        self.assertEqual(portfolio.user_id, user_id)
        self.assertEqual(portfolio.portfolio_id, portfolio_id)
        self.assertEqual(portfolio.reference_asset, reference_asset)
        self.assertEqual(portfolio.created_datetime, created_datetime)

    def test_create_portfolio_with_defaults(self):
        """Test portfolio creation with minimal parameters using defaults."""
        user_id = "TEST-USER-456"

        portfolio = self.factory.create_portfolio(user_id=user_id)

        self.assertIsNotNone(portfolio)
        self.assertIsInstance(portfolio, Portfolio)
        self.assertEqual(portfolio.user_id, user_id)
        self.assertEqual(portfolio.reference_asset, "EUR")  # Default value
        self.assertIsNotNone(portfolio.portfolio_id)  # Should be generated
        self.assertTrue(portfolio.portfolio_id.startswith("PF-"))
        self.assertIsNotNone(portfolio.created_datetime)  # Should be set to current time
        self.assertIsNone(portfolio.updated_datetime)  # Should be None for new portfolios

    def test_create_portfolio_generates_id_when_not_provided(self):
        """Test that portfolio ID is generated when not provided."""
        user_id = "TEST-USER-789"

        portfolio1 = self.factory.create_portfolio(user_id=user_id)
        portfolio2 = self.factory.create_portfolio(user_id=user_id)

        self.assertIsNotNone(portfolio1.portfolio_id)
        self.assertIsNotNone(portfolio2.portfolio_id)
        self.assertTrue(portfolio1.portfolio_id.startswith("PF-"))
        self.assertTrue(portfolio2.portfolio_id.startswith("PF-"))
        # IDs should be different since they're generated
        self.assertNotEqual(portfolio1.portfolio_id, portfolio2.portfolio_id)

    def test_create_portfolio_preserves_provided_id(self):
        """Test that provided portfolio ID is preserved."""
        user_id = "TEST-USER-101"
        provided_id = "PF-CUSTOM-999"
        custom_datetime = datetime(2023, 1, 1, tzinfo=timezone.utc)

        portfolio = self.factory.create_portfolio(
            user_id=user_id,
            portfolio_id=provided_id,
            created_datetime=custom_datetime
        )

        self.assertEqual(portfolio.portfolio_id, provided_id)
        self.assertEqual(portfolio.created_datetime, custom_datetime)

    def test_create_portfolio_handles_exception(self):
        """Test that exceptions during portfolio creation are handled gracefully."""
        with patch('wallets.portfolio_factory.Portfolio') as mock_portfolio_class:
            mock_portfolio_class.side_effect = Exception("Test exception")

            portfolio = self.factory.create_portfolio(user_id="TEST-USER-999")

            self.assertIsNone(portfolio)

    def test_create_portfolio_from_raw_data_success(self):
        """Test successful portfolio creation from raw data."""
        raw_data = {
            'user_id': 'TEST-USER-123',
            'portfolio_id': 'PF-RAW-123',
            'reference_asset': 'GBP',
            'created_datetime': '2023-01-15T10:30:00+00:00',
            'updated_datetime': '2023-01-15T11:30:00+00:00'
        }

        portfolio = self.factory.create_portfolio_from_raw_data(raw_data)

        self.assertIsNotNone(portfolio)
        self.assertIsInstance(portfolio, Portfolio)
        self.assertEqual(portfolio.user_id, 'TEST-USER-123')
        self.assertEqual(portfolio.portfolio_id, 'PF-RAW-123')
        self.assertEqual(portfolio.reference_asset, 'GBP')
        self.assertEqual(portfolio.created_datetime.isoformat(), '2023-01-15T10:30:00+00:00')
        self.assertEqual(portfolio.updated_datetime.isoformat(), '2023-01-15T11:30:00+00:00')

    def test_create_portfolio_from_raw_data_happy_path(self):
        """Test portfolio creation from raw data with missing optional fields."""
        raw_data = {
            'user_id': 'TEST-USER-456',
            'portfolio_id': 'PF-DEFAULT-456',
            'created_datetime': '2023-01-15T10:30:00+00:00',
            'updated_datetime': '2023-01-15T11:30:00+00:00',
            'reference_asset': 'GBP'
        }

        portfolio = self.factory.create_portfolio_from_raw_data(raw_data)

        self.assertIsNotNone(portfolio)
        self.assertIsInstance(portfolio, Portfolio)
        self.assertEqual(portfolio.user_id, 'TEST-USER-456')
        self.assertEqual(portfolio.portfolio_id, 'PF-DEFAULT-456')
        self.assertEqual(portfolio.reference_asset, 'GBP')
        self.assertEqual(portfolio.created_datetime.isoformat(), '2023-01-15T10:30:00+00:00')
        self.assertEqual(portfolio.updated_datetime.isoformat(), '2023-01-15T11:30:00+00:00')

    def test_create_portfolio_from_raw_data_missing_user_id(self):
        """Test that missing user_id returns None."""
        raw_data = {
            'portfolio_id': 'PF-NO-USER',
            'reference_asset': 'USD'
            # Missing user_id
        }

        portfolio = self.factory.create_portfolio_from_raw_data(raw_data)

        self.assertIsNone(portfolio)

    def test_create_portfolio_from_raw_data_invalid_datetime(self):
        """Test handling of invalid datetime format."""
        raw_data = {
            'user_id': 'TEST-USER-789',
            'portfolio_id': 'PF-INVALID-DATE',
            'created_datetime': 'invalid-datetime-format',
            'updated_datetime': 'invalid-datetime-format'
        }

        portfolio = self.factory.create_portfolio_from_raw_data(raw_data)

        self.assertIsNone(portfolio)

    def test_create_portfolio_from_raw_data_missing_portfolio_id(self):
        """Test that missing portfolio_id returns None."""
        raw_data = {
            'user_id': 'TEST-USER-111',
            'reference_asset': 'USD'
        }

        portfolio = self.factory.create_portfolio_from_raw_data(raw_data)

        self.assertIsNone(portfolio)
    
    def test_create_portfolio_from_raw_data_missing_reference_asset(self):
        """Test that missing reference_asset returns None."""
        raw_data = {
            'user_id': 'TEST-USER-111',
            'portfolio_id': 'PF-MISSING-REFERENCE-ASSET'
        }
    
        portfolio = self.factory.create_portfolio_from_raw_data(raw_data)

        self.assertIsNone(portfolio)

    def test_create_portfolio_from_raw_data_missing_created_datetime(self):
        """Test that missing created_datetime returns None."""
        raw_data = {
            'user_id': 'TEST-USER-111',
            'portfolio_id': 'PF-MISSING-CREATED-DATETIME'
        }
    
        portfolio = self.factory.create_portfolio_from_raw_data(raw_data)

        self.assertIsNone(portfolio)

    def test_create_portfolio_from_raw_data_missing_updated_datetime(self):
        """Test that missing updated_datetime returns None."""
        raw_data = {
            'user_id': 'TEST-USER-111',
            'portfolio_id': 'PF-MISSING-UPDATED-DATETIME'
        }
    
        portfolio = self.factory.create_portfolio_from_raw_data(raw_data)

        self.assertIsNone(portfolio)

    def test_create_portfolio_from_raw_data_handles_exception(self):
        """Test that exceptions during raw data processing are handled gracefully."""
        with patch('wallets.portfolio_factory.Portfolio') as mock_portfolio_class:
            mock_portfolio_class.side_effect = Exception("Test exception")

            raw_data = {
                'user_id': 'TEST-USER-999',
                'portfolio_id': 'PF-EXCEPTION'
            }

            portfolio = self.factory.create_portfolio_from_raw_data(raw_data)

            self.assertIsNone(portfolio)

    def test_create_portfolio_from_raw_data_with_z_timezone(self):
        """Test handling of datetime with Z timezone indicator."""
        raw_data = {
            'user_id': 'TEST-USER-101',
            'portfolio_id': 'PF-Z-TIMEZONE',
            'reference_asset': 'USD',
            'created_datetime': '2023-06-20T15:45:30Z',
            'updated_datetime': '2023-06-20T15:45:30Z'
        }

        portfolio = self.factory.create_portfolio_from_raw_data(raw_data)

        self.assertIsNotNone(portfolio)
        self.assertIsInstance(portfolio, Portfolio)
        # Should parse Z timezone correctly
        self.assertEqual(portfolio.created_datetime.isoformat(), '2023-06-20T15:45:30+00:00')
        self.assertEqual(portfolio.updated_datetime.isoformat(), '2023-06-20T15:45:30+00:00')
        self.assertEqual(portfolio.reference_asset, 'USD')

    def test_create_portfolio_from_raw_data_empty_user_id(self):
        """Test that empty user_id returns None."""
        raw_data = {
            'user_id': '',
            'portfolio_id': 'PF-EMPTY-USER'
        }

        portfolio = self.factory.create_portfolio_from_raw_data(raw_data)

        self.assertIsNone(portfolio)

    def test_create_portfolio_from_raw_data_none_user_id(self):
        """Test that None user_id returns None."""
        raw_data = {
            'user_id': None,
            'portfolio_id': 'PF-NONE-USER'
        }

        portfolio = self.factory.create_portfolio_from_raw_data(raw_data)

        self.assertIsNone(portfolio)


if __name__ == '__main__':
    unittest.main(verbosity=2)
