#!/usr/bin/env python3
"""
Unit tests for WalletFactory ID generation
Verifies determinism and sensitivity to each input parameter
"""

import unittest
import pytest
import re
import os
import sys

# Add the parent directory to Python path to import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wallets.wallet_enums import WalletType
from wallets.wallet_factory import WalletFactory


@pytest.mark.unit
class TestWalletFactoryIdGeneration(unittest.TestCase):
    def setUp(self):
        self.factory = WalletFactory()

    def test_deterministic_id_generation(self):
        """Same inputs should always produce the same ID."""
        wallet_type = WalletType.KRAKEN
        # Use a realistic UUID-like portfolio identifier
        portfolio_id = "550e8400-e29b-41d4-a716-446655440000"
        # Use a realistic 32-character API key (exchange-style)
        api_key = "Z8Y7X6W5V4U3T2S1R0Q9P8O7N6M5L4K"

        id_1 = self.factory._generate_wallet_id(wallet_type, portfolio_id, api_key)
        id_2 = self.factory._generate_wallet_id(wallet_type, portfolio_id, api_key)

        # IDs must be identical for the same inputs
        self.assertEqual(id_1, id_2)

        # Format: WalletType.value-<36 hex chars>
        self.assertTrue(
            re.match(rf"^{wallet_type.value}-[0-9a-f]{{36}}$", id_1) is not None,
            f"ID format invalid: {id_1}"
        )

    def test_id_changes_when_inputs_change(self):
        """Changing any single input while keeping the other two equal should change the ID."""
        base = self.factory._generate_wallet_id(
            WalletType.KRAKEN,
            "4b825dc6-8b3e-4eec-bb42-00c04f60b9ae",
            "A1B2C3D4E5F6G7H8J9K1L2M3N4O5P6Q"
        )

        # Change only portfolio_id
        changed_portfolio = self.factory._generate_wallet_id(
            WalletType.KRAKEN,
            "a902f21b-3d84-4a7e-a1f2-7a6c9e5b3d1f",
            "A1B2C3D4E5F6G7H8J9K1L2M3N4O5P6Q"
        )
        self.assertNotEqual(base, changed_portfolio)

        # Change only api_key
        changed_api = self.factory._generate_wallet_id(
            WalletType.KRAKEN,
            "4b825dc6-8b3e-4eec-bb42-00c04f60b9ae",
            "Q6P5O4N3M2L1K9J8H7G6F5E4D3C2B1A0"
        )
        self.assertNotEqual(base, changed_api)

        # Change only wallet_type: use a lightweight stand-in with a different .value
        class _DummyType:
            def __init__(self, value):
                self.value = value

        changed_type = self.factory._generate_wallet_id(
            _DummyType("BinanceWallet"),
            "4b825dc6-8b3e-4eec-bb42-00c04f60b9ae",
            "A1B2C3D4E5F6G7H8J9K1L2M3N4O5P6Q"
        )
        self.assertNotEqual(base, changed_type)

    def test_create_wallet_generates_deterministic_id(self):
        """Factory.create_wallet should create a Kraken wallet with deterministic ID when id is not provided."""
        wallet_type = WalletType.KRAKEN
        portfolio_id = "b3a1f4e2-7c9d-4e5b-8a1f-223344556677"
        api_key = "Z8Y7X6W5V4U3T2S1R0Q9P8O7N6M5L4K"

        wallet = self.factory.create_wallet(
            wallet_type=wallet_type,
            name="Primary Kraken",
            reference_fiat="EUR",
            portfolio_id=portfolio_id,
            description="Kraken spot account",
            api_key=api_key,
            api_secret="SECRET_1234567890"
        )

        self.assertIsNotNone(wallet)
        # Verify it created a KrakenWallet instance
        from wallets.wallet_kraken import KrakenWallet
        self.assertIsInstance(wallet, KrakenWallet)

        # Verify deterministic ID
        expected_id = self.factory._generate_wallet_id(wallet_type, portfolio_id, api_key)
        self.assertEqual(wallet.id, expected_id)
        self.assertTrue(wallet.id.startswith(wallet_type.value + "-"))

        # Verify key fields
        self.assertEqual(wallet.name, "Primary Kraken")
        self.assertEqual(wallet.reference_fiat, "EUR")
        self.assertEqual(wallet.portfolio_id, portfolio_id)
        self.assertEqual(wallet.api_key, api_key)

    def test_create_wallet_from_raw_generates_deterministic_id(self):
        """Factory.create_wallet_from_raw_data should build a Kraken wallet and deterministically set the ID when missing."""
        wallet_type = WalletType.KRAKEN
        portfolio_id = "550e8400-e29b-41d4-a716-446655440000"
        api_key = "A1B2C3D4E5F6G7H8J9K1L2M3N4O5P6Q"

        raw = {
            "wallet_type": wallet_type.value,
            "name": "Kraken Raw",
            "reference_fiat": "EUR",
            "portfolio_id": portfolio_id,
            "description": "From raw payload",
            "api_key": api_key,
            "api_secret": "RAW_SECRET",
            # Intentionally omit 'wallet_id' to force generation
        }

        wallet = self.factory.create_wallet_from_raw_data(raw)

        self.assertIsNotNone(wallet)
        from wallets.wallet_kraken import KrakenWallet
        self.assertIsInstance(wallet, KrakenWallet)

        expected_id = self.factory._generate_wallet_id(wallet_type, portfolio_id, api_key)
        self.assertEqual(wallet.id, expected_id)
        self.assertTrue(wallet.id.startswith(wallet_type.value + "-"))
        self.assertEqual(wallet.name, "Kraken Raw")
        self.assertEqual(wallet.reference_fiat, "EUR")
        self.assertEqual(wallet.portfolio_id, portfolio_id)
        self.assertEqual(wallet.api_key, api_key)

    def test_create_wallet_preserves_provided_id(self):
        """Factory.create_wallet should not override a provided ID."""
        wallet_type = WalletType.KRAKEN
        portfolio_id = "11111111-2222-3333-4444-555555555555"
        api_key = "1234567890ABCDEFGHIJKLMNOPQRSTUV"
        provided_id = "KRAKEN-EXTERNAL-123"

        wallet = self.factory.create_wallet(
            wallet_type=wallet_type,
            name="Kraken With ID",
            reference_fiat="EUR",
            portfolio_id=portfolio_id,
            id=provided_id,
            api_key=api_key,
            api_secret="SECRET"
        )

        self.assertIsNotNone(wallet)
        from wallets.wallet_kraken import KrakenWallet
        self.assertIsInstance(wallet, KrakenWallet)
        self.assertEqual(wallet.id, provided_id)

        # Ensure it did not silently regenerate a deterministic one
        deterministic_id = self.factory._generate_wallet_id(wallet_type, portfolio_id, api_key)
        self.assertNotEqual(wallet.id, deterministic_id)

    def test_create_wallet_from_raw_preserves_provided_id(self):
        """Factory.create_wallet_from_raw_data should not override 'wallet_id' if provided in raw data."""
        wallet_type = WalletType.KRAKEN
        portfolio_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        api_key = "ZYXWVUTSRQPONMLKJIHGFEDCBA098765"
        provided_id = "KRAKEN-CUSTOM-999"

        raw = {
            "wallet_type": wallet_type.value,
            "name": "Kraken Raw With ID",
            "reference_fiat": "EUR",
            "portfolio_id": portfolio_id,
            "wallet_id": provided_id,
            "api_key": api_key,
            "api_secret": "RAWSECRET",
        }

        wallet = self.factory.create_wallet_from_raw_data(raw)

        self.assertIsNotNone(wallet)
        from wallets.wallet_kraken import KrakenWallet
        self.assertIsInstance(wallet, KrakenWallet)
        self.assertEqual(wallet.id, provided_id)

        deterministic_id = self.factory._generate_wallet_id(wallet_type, portfolio_id, api_key)
        self.assertNotEqual(wallet.id, deterministic_id)


if __name__ == '__main__':
    unittest.main(verbosity=2)


