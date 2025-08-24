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
import uuid

# Add the parent directory to Python path to import backend modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wallets.portfolio import Portfolio
from wallets.wallet_enums import WalletType, WalletSyncStatus


class MockWallet:
    """Mock wallet for testing."""
    
    def __init__(self, name: str, id: str, reference_fiat: str, portfolio_id: str, 
                 description: str = "", api_key: str = None, api_secret: str = None,
                 is_active: bool = False, sync_status: WalletSyncStatus = WalletSyncStatus.NOT_SYNCHRONIZED):
        self.name = name
        self.id = id
        self.reference_fiat = reference_fiat
        self.portfolio_id = portfolio_id
        self.description = description
        self.api_key = api_key
        self.api_secret = api_secret
        self.is_active = is_active
        self.sync_status = sync_status
    
    def get_wallet_type(self):
        return WalletType.KRAKEN
    
    def authenticate(self):
        return self.is_active
    
    def synchronize(self, start_date=None):
        return True, None


@pytest.mark.unit
class TestPortfolioInitialization(unittest.TestCase):
    """Test cases for Portfolio initialization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_portfolio_initialization_default(self):
        """Test portfolio initialization with default parameters."""
        portfolio = Portfolio()
        
        # Verify portfolio ID starts with PF-
        self.assertTrue(portfolio.portfolio_id.startswith("PF-"))
        
        # Verify reference asset is EUR by default
        self.assertEqual(portfolio.reference_asset, "EUR")
        
        # Verify created_datetime is set
        self.assertIsInstance(portfolio.created_datetime, datetime)
        
        # Verify it's a recent datetime
        now = datetime.now(timezone.utc)
        time_diff = abs((now - portfolio.created_datetime).total_seconds())
        self.assertLess(time_diff, 10)  # Should be within 10 seconds
    
    def test_portfolio_initialization_custom(self):
        """Test portfolio initialization with custom parameters."""
        custom_id = "PF-TEST-123"
        custom_asset = "USD"
        custom_datetime = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        portfolio = Portfolio(
            portfolio_id=custom_id,
            reference_asset=custom_asset,
            created_datetime=custom_datetime
        )
        
        self.assertEqual(portfolio.portfolio_id, custom_id)
        self.assertEqual(portfolio.reference_asset, custom_asset)
        self.assertEqual(portfolio.created_datetime, custom_datetime)


@pytest.mark.unit
class TestPortfolioWalletOperations(unittest.TestCase):
    """Test cases for Portfolio wallet operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        
        # Mock the wallet factory and repository
        self.wallet_factory_patcher = patch('wallets.portfolio.WalletFactory')
        self.repository_patcher = patch('wallets.portfolio.PostgresWalletRepository')
        
        self.mock_wallet_factory = self.wallet_factory_patcher.start()
        self.mock_repository = self.repository_patcher.start()
        
        # Create portfolio instance
        self.portfolio = Portfolio(reference_asset="EUR")
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.wallet_factory_patcher.stop()
        self.repository_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_add_wallet_success(self):
        """Test successful wallet addition."""
        # Mock wallet factory
        mock_wallet = MockWallet(
            name="Test Wallet",
            id="KRAKEN-test-uuid",
            reference_fiat="EUR",
            portfolio_id=self.portfolio.portfolio_id,
            is_active=True
        )
        
        self.mock_wallet_factory.return_value.create_wallet.return_value = mock_wallet
        self.mock_repository.return_value.save_wallet.return_value = True
        
        # Add wallet
        wallet_id = self.portfolio.add_wallet(
            wallet_type=WalletType.KRAKEN,
            name="Test Wallet",
            api_key="test_key",
            api_secret="test_secret"
        )
        
        # Verify wallet was created with correct parameters
        self.mock_wallet_factory.return_value.create_wallet.assert_called_with(
            wallet_type=WalletType.KRAKEN,
            name="Test Wallet",
            reference_fiat="EUR",
            portfolio_id=self.portfolio.portfolio_id,
            description="",
            api_key="test_key",
            api_secret="test_secret"
        )
        
        # Verify wallet was saved
        self.mock_repository.return_value.save_wallet.assert_called_once_with(mock_wallet)
        
        # Verify wallet ID is returned
        self.assertIsNotNone(wallet_id)
        self.assertEqual(wallet_id, mock_wallet.id)
    
    def test_add_wallet_unsupported_type(self):
        """Test adding wallet with unsupported type."""
        # Mock wallet factory to return None for unsupported type
        self.mock_wallet_factory.return_value.create_wallet.return_value = None
        
        wallet_id = self.portfolio.add_wallet(
            wallet_type=WalletType.KRAKEN,
            name="Test Wallet"
        )
        
        self.assertIsNone(wallet_id)
    
    def test_add_wallet_authentication_failure(self):
        """Test adding wallet with authentication failure."""
        # Mock wallet that fails authentication
        mock_wallet = MockWallet(
            name="Test Wallet",
            id="KRAKEN-test-uuid",
            reference_fiat="EUR",
            portfolio_id=self.portfolio.portfolio_id,
            is_active=False  # This will cause authenticate() to return False
        )
        
        self.mock_wallet_factory.return_value.create_wallet.return_value = mock_wallet
        
        wallet_id = self.portfolio.add_wallet(
            wallet_type=WalletType.KRAKEN,
            name="Test Wallet"
        )
        
        self.assertIsNone(wallet_id)
    
    def test_remove_wallet_success(self):
        """Test successful wallet removal."""
        # Mock wallet that belongs to the portfolio
        mock_wallet = MockWallet(
            name="Test Wallet",
            id="test-wallet-id",
            reference_fiat="EUR",
            portfolio_id=self.portfolio.portfolio_id
        )
        
        self.mock_repository.return_value.get_wallet_by_id.return_value = mock_wallet
        self.mock_repository.return_value.delete_wallet_by_id.return_value = True
        
        success = self.portfolio.remove_wallet("test-wallet-id")
        
        self.assertTrue(success)
        self.mock_repository.return_value.delete_wallet_by_id.assert_called_once_with("test-wallet-id")
    
    def test_remove_wallet_not_found(self):
        """Test wallet removal when wallet not found."""
        self.mock_repository.return_value.get_wallet_by_id.return_value = None
        
        success = self.portfolio.remove_wallet("non-existent-id")
        
        self.assertFalse(success)
    
    def test_remove_wallet_wrong_portfolio(self):
        """Test wallet removal when wallet belongs to different portfolio."""
        # Mock wallet that belongs to different portfolio
        mock_wallet = MockWallet(
            name="Test Wallet",
            id="test-wallet-id",
            reference_fiat="EUR",
            portfolio_id="different-portfolio-id"
        )
        
        self.mock_repository.return_value.get_wallet_by_id.return_value = mock_wallet
        
        success = self.portfolio.remove_wallet("test-wallet-id")
        
        self.assertFalse(success)
    
    def test_remove_wallet_failure(self):
        """Test wallet removal failure."""
        # Mock wallet that belongs to the portfolio
        mock_wallet = MockWallet(
            name="Test Wallet",
            id="test-wallet-id",
            reference_fiat="EUR",
            portfolio_id=self.portfolio.portfolio_id
        )
        
        self.mock_repository.return_value.get_wallet_by_id.return_value = mock_wallet
        self.mock_repository.return_value.delete_wallet_by_id.return_value = False
        
        success = self.portfolio.remove_wallet("test-wallet-id")
        
        self.assertFalse(success)
    
    def test_list_wallets(self):
        """Test listing wallets."""
        # Mock wallets
        mock_wallets = [
            MockWallet("Wallet 1", "id1", "EUR", self.portfolio.portfolio_id),
            MockWallet("Wallet 2", "id2", "EUR", self.portfolio.portfolio_id)
        ]
        
        self.mock_repository.return_value.get_all_wallets_in_portfolio.return_value = mock_wallets
        
        wallets = self.portfolio.list_wallets()
        
        self.assertEqual(len(wallets), 2)
        self.assertEqual(wallets, mock_wallets)
        self.mock_repository.return_value.get_all_wallets_in_portfolio.assert_called_once_with(
            self.portfolio.portfolio_id
        )
    
    def test_get_wallet_by_id(self):
        """Test getting wallet by ID."""
        mock_wallet = MockWallet("Test Wallet", "test-id", "EUR", self.portfolio.portfolio_id)
        self.mock_repository.return_value.get_wallet_by_id.return_value = mock_wallet
        
        wallet = self.portfolio.get_wallet_by_id("test-id")
        
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet, mock_wallet)
        self.mock_repository.return_value.get_wallet_by_id.assert_called_once_with("test-id")
    
    def test_get_wallet_by_id_not_found(self):
        """Test getting non-existent wallet by ID."""
        self.mock_repository.return_value.get_wallet_by_id.return_value = None
        
        wallet = self.portfolio.get_wallet_by_id("non-existent-id")
        
        self.assertIsNone(wallet)
    
    def test_get_wallet_by_id_wrong_portfolio(self):
        """Test getting wallet that belongs to different portfolio."""
        # Mock wallet that belongs to different portfolio
        mock_wallet = MockWallet(
            name="Test Wallet",
            id="test-id",
            reference_fiat="EUR",
            portfolio_id="different-portfolio-id"
        )
        
        self.mock_repository.return_value.get_wallet_by_id.return_value = mock_wallet
        
        wallet = self.portfolio.get_wallet_by_id("test-id")
        
        self.assertIsNone(wallet)
    
    def test_is_wallet_in_portfolio(self):
        """Test checking if wallet belongs to portfolio."""
        # Wallet in portfolio
        wallet_in_portfolio = MockWallet(
            name="Test Wallet",
            id="test-id",
            reference_fiat="EUR",
            portfolio_id=self.portfolio.portfolio_id
        )
        
        self.assertTrue(self.portfolio.is_wallet_in_portfolio(wallet_in_portfolio))
        
        # Wallet not in portfolio
        wallet_not_in_portfolio = MockWallet(
            name="Test Wallet",
            id="test-id",
            reference_fiat="EUR",
            portfolio_id="different-portfolio-id"
        )
        
        self.assertFalse(self.portfolio.is_wallet_in_portfolio(wallet_not_in_portfolio))


@pytest.mark.unit
class TestPortfolioSynchronization(unittest.TestCase):
    """Test cases for Portfolio synchronization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        
        # Mock the wallet factory and repository
        self.wallet_factory_patcher = patch('wallets.portfolio.WalletFactory')
        self.repository_patcher = patch('wallets.portfolio.PostgresWalletRepository')
        
        self.mock_wallet_factory = self.wallet_factory_patcher.start()
        self.mock_repository = self.repository_patcher.start()
        
        # Create portfolio instance
        self.portfolio = Portfolio(reference_asset="EUR")
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.wallet_factory_patcher.stop()
        self.repository_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_synchronize_all_wallets_success(self):
        """Test successful synchronization of all wallets."""
        # Mock wallets
        mock_wallet1 = MockWallet("Wallet 1", "id1", "EUR", self.portfolio.portfolio_id, is_active=True)
        mock_wallet2 = MockWallet("Wallet 2", "id2", "EUR", self.portfolio.portfolio_id, is_active=True)
        
        self.mock_repository.return_value.get_all_wallets_in_portfolio.return_value = [mock_wallet1, mock_wallet2]
        
        results = self.portfolio.synchronize_all_wallets()
        
        self.assertEqual(len(results), 2)
        self.assertTrue(results['id1']['success'])
        self.assertTrue(results['id2']['success'])
        self.assertIsNone(results['id1']['error'])
        self.assertIsNone(results['id2']['error'])
    
    def test_synchronize_all_wallets_authentication_failure(self):
        """Test synchronization with authentication failure."""
        # Mock wallet that fails authentication
        mock_wallet = MockWallet("Wallet 1", "id1", "EUR", self.portfolio.portfolio_id, is_active=False)
        
        self.mock_repository.return_value.get_all_wallets_in_portfolio.return_value = [mock_wallet]
        
        results = self.portfolio.synchronize_all_wallets()
        
        self.assertEqual(len(results), 1)
        self.assertFalse(results['id1']['success'])
        self.assertEqual(results['id1']['error'], 'Authentication failed')
    
    def test_synchronize_all_wallets_synchronization_failure(self):
        """Test synchronization with sync failure."""
        # Mock wallet that fails synchronization
        mock_wallet = MockWallet("Wallet 1", "id1", "EUR", self.portfolio.portfolio_id, is_active=True)
        
        # Override synchronize method to return failure
        def mock_synchronize(start_date=None):
            return False, "Sync failed"
        
        mock_wallet.synchronize = mock_synchronize
        
        self.mock_repository.return_value.get_all_wallets_in_portfolio.return_value = [mock_wallet]
        
        results = self.portfolio.synchronize_all_wallets()
        
        self.assertEqual(len(results), 1)
        self.assertFalse(results['id1']['success'])
        self.assertEqual(results['id1']['error'], 'Sync failed')
    
    def test_synchronize_all_wallets_exception(self):
        """Test synchronization with exception."""
        # Mock wallet that raises exception
        mock_wallet = MockWallet("Wallet 1", "id1", "EUR", self.portfolio.portfolio_id, is_active=True)
        
        # Override authenticate method to raise exception
        def mock_authenticate():
            raise Exception("Authentication error")
        
        mock_wallet.authenticate = mock_authenticate
        
        self.mock_repository.return_value.get_all_wallets_in_portfolio.return_value = [mock_wallet]
        
        results = self.portfolio.synchronize_all_wallets()
        
        self.assertEqual(len(results), 1)
        self.assertFalse(results['id1']['success'])
        self.assertEqual(results['id1']['error'], 'Authentication error')


if __name__ == '__main__':
    unittest.main()
