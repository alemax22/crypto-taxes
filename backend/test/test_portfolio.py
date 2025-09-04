#!/usr/bin/env python3
"""
Unit tests for the new Portfolio class
Tests the portfolio entity functionality including wallet operations and synchronization
"""

import unittest
import pytest
from unittest.mock import patch, MagicMock
import os
import tempfile
import shutil
from datetime import datetime, timezone

# Add the parent directory to Python path to import backend modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wallets.portfolio import Portfolio
from wallets.wallet_enums import WalletType
from wallets.wallet_kraken import KrakenWallet

@pytest.mark.unit
class TestPortfolioInitialization(unittest.TestCase):
    """Test cases for Portfolio initialization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.patches = []

        wallet_repository_patch = patch('wallets.wallet_repository.PostgresWalletRepository.__new__')
        wallet_repository = wallet_repository_patch.start()
        wallet_repository.return_value = MagicMock()
        self.patches.append(wallet_repository_patch)
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        for patch in self.patches:
            patch.stop()
    
    def test_portfolio_initialization_required_parameters(self):
        """Test portfolio initialization with all required parameters."""

        custom_datetime = datetime(2023, 1, 1, tzinfo=timezone.utc)
        portfolio = Portfolio(
            user_id="TEST_USER_ID",
            portfolio_id="PF-TEST-123",
            reference_asset="EUR",
            created_datetime=custom_datetime,
            updated_datetime=None
        )
        
        # Verify portfolio ID
        self.assertEqual(portfolio.portfolio_id, "PF-TEST-123")
        
        # Verify reference asset
        self.assertEqual(portfolio.reference_asset, "EUR")
        
        # Verify created_datetime
        self.assertEqual(portfolio.created_datetime, custom_datetime)

        # Verify updated_datetime
        self.assertIsNone(portfolio.updated_datetime)
    
    def test_portfolio_initialization_custom(self):
        """Test portfolio initialization with custom parameters."""
        custom_id = "PF-TEST-123"
        custom_asset = "USD"
        custom_datetime = datetime(2023, 1, 1, tzinfo=timezone.utc)

        portfolio = Portfolio(
            user_id="TEST_USER_ID",
            portfolio_id=custom_id,
            reference_asset=custom_asset,
            created_datetime=custom_datetime,
            updated_datetime=None
        )
        
        self.assertEqual(portfolio.portfolio_id, custom_id)
        self.assertEqual(portfolio.reference_asset, custom_asset)
        self.assertEqual(portfolio.created_datetime, custom_datetime)

# TODO: Review all the tests as they MUST not rely on the integration with the database
@pytest.mark.unit
class TestPortfolioWalletOperations(unittest.TestCase):
    """Test cases for Portfolio wallet operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Store patches for cleanup
        self.patches = []
        self.test_dir = tempfile.mkdtemp()
        
        # Create portfolio instance
        mock_repository_patch = patch('wallets.wallet_repository.PostgresWalletRepository.__new__')
        mock_repository = mock_repository_patch.start()
        mock_repository.return_value = MagicMock()
        self.patches.append(mock_repository_patch)
        self.portfolio = Portfolio(
            user_id="TEST_USER_ID",
            portfolio_id="PF-TEST-123",
            reference_asset="EUR",
            created_datetime=datetime.now(timezone.utc),
            updated_datetime=None
        )
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        for patch in self.patches:
            patch.stop()
    
    @patch('wallets.wallet_kraken.KrakenWallet.authenticate')
    def test_add_wallet_success(self, mock_authenticate):
        """Test successful wallet addition."""
        mock_authenticate.return_value = True
        self.portfolio.repository.save_wallet = MagicMock(return_value=True)

        # Add wallet
        wallet = self.portfolio.add_wallet(
            wallet_type=WalletType.KRAKEN,
            name="Test Wallet",
            api_key="test_key",
            api_secret="test_secret"
        )

        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.name, "Test Wallet")
        self.assertEqual(wallet.api_key, "test_key")
        self.assertEqual(wallet.api_secret, "test_secret")
        self.assertEqual(wallet.portfolio_id, self.portfolio.portfolio_id)
        self.assertEqual(wallet.get_wallet_type(), WalletType.KRAKEN)
        self.assertEqual(wallet.reference_fiat, "EUR")
        self.portfolio.repository.save_wallet.assert_called_once_with(wallet)
    
    def test_add_wallet_unsupported_type(self):
        """Test adding wallet with unsupported type."""
        
        wallet = self.portfolio.add_wallet(
            wallet_type="UNSUPPORTED",
            name="Test Wallet"
        )
        
        self.assertIsNone(wallet)
        self.portfolio.repository.save_wallet.assert_not_called()
    
    @patch('wallets.wallet_kraken.KrakenWallet.authenticate')
    def test_add_wallet_authentication_failure(self, mock_authenticate):
        """Test adding wallet with authentication failure."""
        # Mock wallet that fails authentication
        mock_authenticate.return_value = False
        
        wallet = self.portfolio.add_wallet(
            wallet_type=WalletType.KRAKEN,
            name="Test Wallet"
        )
        
        self.assertIsNone(wallet)
        self.portfolio.repository.save_wallet.assert_not_called()
    
    def test_delete_wallet_success(self):
        """Test successful wallet removal."""
        # Mock wallet that belongs to the portfolio
        mock_wallet = KrakenWallet(
            name="Test Wallet",
            id="TEST-KRAKEN-fre6gfe4f4g4e6gfuegfu46uhw3uinkv",
            reference_fiat="EUR",
            portfolio_id=self.portfolio.portfolio_id
        )
        self.portfolio.repository.get_wallet_by_id = MagicMock(return_value=mock_wallet)
        self.portfolio.repository.delete_wallet_by_id = MagicMock(return_value=True)
        
        success = self.portfolio.remove_wallet(mock_wallet.id)
        
        self.assertTrue(success)
        self.portfolio.repository.delete_wallet_by_id.assert_called_once_with(mock_wallet.id)
    
    def test_remove_wallet_not_found(self):
        """Test wallet removal when wallet not found."""
        self.portfolio.repository.get_wallet_by_id = MagicMock(return_value=None)
        
        success = self.portfolio.remove_wallet("TEST-KRAKEN-non-existent-id")
        
        self.assertFalse(success)
        self.portfolio.repository.delete_wallet_by_id.assert_not_called()
    
    def test_remove_wallet_wrong_portfolio(self):
        """Test wallet removal when wallet belongs to different portfolio."""
        # Mock wallet that belongs to different portfolio
        mock_wallet = KrakenWallet(
            name="Test Wallet",
            id="TEST-KRAKEN-fre6gfe4f4g4e6gfuegfu46uhw3uinkv",
            reference_fiat="EUR",
            portfolio_id="TEST_PF-different-portfolio-id"
        )
        self.portfolio.repository.get_wallet_by_id = MagicMock(return_value=mock_wallet)
        
        success = self.portfolio.remove_wallet(mock_wallet.id)
        
        self.assertFalse(success)
        self.portfolio.repository.delete_wallet_by_id.assert_not_called()
    
    def test_remove_wallet_failure(self):
        """Test wallet removal failure."""
        # Mock wallet that belongs to the portfolio
        mock_wallet = KrakenWallet(
            name="Test Wallet",
            id="TEST-KRAKEN-fre6gfe4f4g4e6gfuegfu46uhw3uinkv",
            reference_fiat="EUR",
            portfolio_id=self.portfolio.portfolio_id
        )
        self.portfolio.repository.get_wallet_by_id = MagicMock(return_value=mock_wallet)
        self.portfolio.repository.delete_wallet_by_id = MagicMock(return_value=False)
        
        success = self.portfolio.remove_wallet(mock_wallet.id)
        
        self.assertFalse(success)
    
    def test_list_wallets(self):
        """Test listing wallets."""
        # Mock wallets
        wallet_1 = KrakenWallet(
            "Wallet 1", 
            "TEST-KRAKEN-fre6gfe4f4g4e6gfuegfu46uhw3uinkv", 
            "EUR", 
            self.portfolio.portfolio_id,
            is_active=True
        )
        wallet_2 = KrakenWallet(
            "Wallet 2", 
            "TEST-KRAKEN-fre6g4gASFs4e6gfue43gdfgfd5qzFSD", "EUR", self.portfolio.portfolio_id
        )

        self.portfolio.repository.get_all_wallets_in_portfolio = MagicMock(return_value=[
            wallet_1,
            wallet_2
        ])
        
        wallets = self.portfolio.list_wallets()
        
        self.assertEqual(len(wallets), 2)
        self.assertEqual(wallets, [
            wallet_1,
            wallet_2
        ])
        self.portfolio.repository.get_all_wallets_in_portfolio.assert_called_once_with(
            self.portfolio.portfolio_id
        )
    
    def test_get_wallet_by_id(self):
        """Test getting wallet by ID."""
        mock_wallet = KrakenWallet(
            "Test Wallet", 
            "TEST-KRAKEN-fre6gfe4f4g4e6gfuegfu46uhw3uinkv", 
            "EUR", 
            self.portfolio.portfolio_id,
            is_active=True
        )
        self.portfolio.repository.get_wallet_by_id = MagicMock(return_value=mock_wallet)
        
        wallet = self.portfolio.get_wallet_by_id(mock_wallet.id)
        
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet, mock_wallet)
        self.portfolio.repository.get_wallet_by_id.assert_called_once_with(mock_wallet.id)
    
    def test_get_wallet_by_id_wrong_portfolio(self):
        """Test getting wallet by ID when wallet belongs to different portfolio."""
        mock_wallet = KrakenWallet(
            "Test Wallet", 
            "TEST-KRAKEN-fre6gfe4f4g4e6gfuegfu46uhw3uinkv", 
            "EUR", 
            "TEST_PF-different-portfolio-id",
            is_active=True
        )
        self.portfolio.repository.get_wallet_by_id = MagicMock(return_value=mock_wallet)
        
        wallet = self.portfolio.get_wallet_by_id(mock_wallet.id)
        
        self.assertIsNone(wallet)

    def test_get_wallet_by_id_not_found(self):
        """Test getting non-existent wallet by ID."""
        self.portfolio.repository.get_wallet_by_id = MagicMock(return_value=None)
        
        wallet = self.portfolio.get_wallet_by_id("TEST-KRAKEN-non-existent-id")
        
        self.assertIsNone(wallet)
    
    def test_is_wallet_in_portfolio(self):
        """Test checking if wallet belongs to portfolio."""
        # Wallet in portfolio
        wallet_in_portfolio = KrakenWallet(
            name="Test Wallet",
            id="TEST-KRAKEN-fre6gfe4f4g4e6gfuegfu46uhw3uinkv",
            reference_fiat="EUR",
            portfolio_id=self.portfolio.portfolio_id
        )
        
        self.assertTrue(self.portfolio.is_wallet_in_portfolio(wallet_in_portfolio))
        
        # Wallet not in portfolio
        wallet_not_in_portfolio = KrakenWallet(
            name="Test Wallet",
            id="TEST-KRAKEN-fre6gfe4f4g4e6gfuegfu46uhw3uinkv",
            reference_fiat="EUR",
            portfolio_id="TEST-PF-different-portfolio-id"
        )
        
        self.assertFalse(self.portfolio.is_wallet_in_portfolio(wallet_not_in_portfolio))


@pytest.mark.unit
class TestPortfolioSynchronization(unittest.TestCase):
    """Test cases for Portfolio synchronization."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Store patches for cleanup
        self.patches = []
        self.test_dir = tempfile.mkdtemp()
        
        # Create portfolio instance
        mock_repository_patch = patch('wallets.wallet_repository.PostgresWalletRepository.__new__')
        mock_repository = mock_repository_patch.start()
        mock_repository.return_value = MagicMock()
        self.patches.append(mock_repository_patch)
        self.portfolio = Portfolio(
            user_id="TEST_USER_ID",
            portfolio_id="PF-TEST-SYNC-123",
            reference_asset="EUR",
            created_datetime=datetime.now(timezone.utc),
            updated_datetime=None
        )
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
        for patch in self.patches:
            patch.stop()
    
    def test_synchronize_all_wallets_success(self):
        """Test successful synchronization of all wallets."""
        
        # Mock wallets
        wallet_1 = KrakenWallet(
            "Wallet 1", 
            "TEST-KRAKEN-fre6gfe4f4g4e6gfuegfu46uhw3uinkv", 
            "EUR", self.portfolio.portfolio_id, 
            is_active=True
        )
        wallet_2 = KrakenWallet(
            "Wallet 2", 
            "TEST-KRAKEN-fre6g4gASFs4e6gfue43gdfgfd5qzFSD", 
            "EUR", 
            self.portfolio.portfolio_id, 
            is_active=True
        )
        
        # Mock the authenticate and synchronize methods on the instances
        wallet_1.authenticate = MagicMock(return_value=True)
        wallet_1.synchronize = MagicMock(return_value=(True, None))
        wallet_2.authenticate = MagicMock(return_value=True)
        wallet_2.synchronize = MagicMock(return_value=(True, None))
        
        self.portfolio.repository.get_all_wallets_in_portfolio = MagicMock(return_value=[
            wallet_1,
            wallet_2
        ])
        
        results = self.portfolio.synchronize_all_wallets()

        self.assertEqual(len(results), 2)
        self.assertTrue(results[wallet_1.id]['success'])
        self.assertTrue(results[wallet_2.id]['success'])
        self.assertIsNone(results[wallet_1.id]['error'])
        self.assertIsNone(results[wallet_2.id]['error'])
        wallet_1.synchronize.assert_called_once_with(None)
        wallet_2.synchronize.assert_called_once_with(None)
    
    def test_synchronize_all_wallets_authentication_failure(self):
        """Test synchronization with authentication failure."""
        # Mock wallet that fails authentication
        wallet_1 = KrakenWallet(
            "Wallet 1", 
            "TEST-KRAKEN-fre6gfe4f4g4e6gfuegfu46uhw3uinkv", 
            "EUR", 
            self.portfolio.portfolio_id, 
            is_active=True
        )
        
        # Mock the authenticate and synchronize methods on the instance
        wallet_1.authenticate = MagicMock(return_value=False)
        wallet_1.synchronize = MagicMock(return_value=(True, None))
        
        self.portfolio.repository.get_all_wallets_in_portfolio = MagicMock(return_value=[
            wallet_1
        ])

        results = self.portfolio.synchronize_all_wallets()
        
        self.assertEqual(len(results), 1)
        self.assertFalse(results[wallet_1.id]['success'])
        self.assertEqual(results[wallet_1.id]['error'], 'Authentication failed')
        wallet_1.synchronize.assert_not_called()
    
    def test_synchronize_all_wallets_synchronization_failure(self):
        """Test synchronization with sync failure."""
        # Mock wallet that fails synchronization
        wallet_1 = KrakenWallet(
            "Wallet 1", 
            "TEST-KRAKEN-fre6gfe4f4g4e6gfuegfu46uhw3uinkv", 
            "EUR", 
            self.portfolio.portfolio_id, 
            is_active=True
        )
        
        wallet_1.authenticate = MagicMock(return_value=True)
        wallet_1.synchronize = MagicMock(return_value=(False, 'Sync failed'))
        
        self.portfolio.repository.get_all_wallets_in_portfolio = MagicMock(return_value=[
            wallet_1
        ])
        
        results = self.portfolio.synchronize_all_wallets()
        
        self.assertEqual(len(results), 1)
        self.assertFalse(results[wallet_1.id]['success'])
        self.assertEqual(results[wallet_1.id]['error'], 'Sync failed')
        wallet_1.synchronize.assert_called_once_with(None)
    
    def test_synchronize_all_wallets_exception(self):
        """Test synchronization with exception."""
        # Mock wallet that raises exception
        wallet_1 = KrakenWallet(
            "Wallet 1", 
            "TEST-KRAKEN-fre6gfe4f4g4e6gfuegfu46uhw3uinkv", 
            "EUR", 
            self.portfolio.portfolio_id, 
            is_active=True
        )
        
        # Mock the authenticate method to raise exception and synchronize method
        wallet_1.authenticate = MagicMock(side_effect=Exception("Authentication error"))
        wallet_1.synchronize = MagicMock(return_value=(True, None))
        
        self.portfolio.repository.get_all_wallets_in_portfolio = MagicMock(return_value=[
            wallet_1
        ])
        
        results = self.portfolio.synchronize_all_wallets()
        
        self.assertEqual(len(results), 1)
        self.assertFalse(results[wallet_1.id]['success'])
        self.assertEqual(results[wallet_1.id]['error'], 'Authentication error')
        wallet_1.synchronize.assert_not_called()
    
    def test_synchronize_all_wallets_empty_portfolio(self):
        """Test synchronization with empty portfolio."""
        self.portfolio.repository.get_all_wallets_in_portfolio = MagicMock(return_value=[])
        
        results = self.portfolio.synchronize_all_wallets()
        
        self.assertEqual(len(results), 0)
    
    def test_synchronize_all_wallets_with_start_date(self):
        """Test synchronization with start date parameter."""
        # Mock wallet
        wallet_1 = KrakenWallet(
            "Wallet 1", 
            "TEST-KRAKEN-fre6gfe4f4g4e6gfuegfu46uhw3uinkv", 
            "EUR", 
            self.portfolio.portfolio_id, 
            is_active=True
        )
        
        # Mock the authenticate and synchronize methods on the instance
        wallet_1.authenticate = MagicMock(return_value=True)
        wallet_1.synchronize = MagicMock(return_value=(True, None))
        
        self.portfolio.repository.get_all_wallets_in_portfolio = MagicMock(return_value=[
            wallet_1
        ])
        
        start_date = "2024-01-01"
        results = self.portfolio.synchronize_all_wallets(start_date=start_date)
        
        self.assertEqual(len(results), 1)
        self.assertTrue(results[wallet_1.id]['success'])
        wallet_1.synchronize.assert_called_once_with(start_date)
    
    def test_synchronize_all_wallets_with_max_workers(self):
        """Test synchronization with custom max_workers parameter."""
        # Mock wallets
        wallet_1 = KrakenWallet(
            "Wallet 1", 
            "TEST-KRAKEN-fre6gfe4f4g4e6gfuegfu46uhw3uinkv", 
            "EUR", 
            self.portfolio.portfolio_id, 
            is_active=True
        )
        wallet_2 = KrakenWallet(
            "Wallet 2", 
            "TEST-KRAKEN-fre6g4gASFs4e6gfue43gdfgfd5qzFSD", 
            "EUR", 
            self.portfolio.portfolio_id, 
            is_active=True
        )
        
        # Mock the authenticate and synchronize methods on the instances
        wallet_1.authenticate = MagicMock(return_value=True)
        wallet_1.synchronize = MagicMock(return_value=(True, None))
        wallet_2.authenticate = MagicMock(return_value=True)
        wallet_2.synchronize = MagicMock(return_value=(True, None))
        
        self.portfolio.repository.get_all_wallets_in_portfolio = MagicMock(return_value=[
            wallet_1,
            wallet_2
        ])
        
        results = self.portfolio.synchronize_all_wallets(max_workers=2)
        
        self.assertEqual(len(results), 2)
        self.assertTrue(results[wallet_1.id]['success'])
        self.assertTrue(results[wallet_2.id]['success'])
        wallet_1.synchronize.assert_called_once_with(None)
        wallet_2.synchronize.assert_called_once_with(None)


if __name__ == '__main__':
    unittest.main()
