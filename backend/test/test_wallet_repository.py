#!/usr/bin/env python3
"""
Unit tests for PostgresWalletRepository using an in-memory SQLite database.
Class-based style to match existing tests.
"""

import os
import sys
import shutil
import tempfile
import unittest
import hashlib
import base64
import pytest

# Ensure backend modules can be imported (same pattern as other tests)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import wallets.wallet_repository as wr
from wallets.wallet_enums import WalletType
from wallets.wallet_factory import WalletFactory
import config as app_config
from wallets.wallet_enums import WalletSyncStatus
from datetime import datetime

@pytest.mark.integration
class TestWalletRepository(unittest.TestCase):
	"""Class-based tests for the repository with an isolated SQLite DB."""

	def setUp(self):
		# Temporary wallets dir for Fernet key
		self.temp_dir = tempfile.mkdtemp()
		
		self._original_wallets_dir = getattr(app_config, 'WALLETS_DIR', None)
		app_config.WALLETS_DIR = self.temp_dir

		self.wr = wr

		# Instantiate repository
		self.repo = self.wr.PostgresWalletRepository()

		# Helpers
		self.WalletType = WalletType
		self.factory = WalletFactory()

	def tearDown(self):
		if self._original_wallets_dir is not None:
			app_config.WALLETS_DIR = self._original_wallets_dir

		shutil.rmtree(self.temp_dir, ignore_errors=True)

	def _make_wallet(self, name="INTEGRATIONTEST-W1", portfolio_id="INTEGRATIONTEST-pf1", api_key=None, api_secret=None):
		# Generate realistic, deterministic credentials by default to avoid ID collisions
		if api_key is None:
			seed = f"{portfolio_id}:{name}:api_key".encode("utf-8")
			digest = hashlib.sha256(seed).hexdigest().upper()
			# Kraken-like API key: 32 uppercase alphanumeric chars
			api_key = digest[:32]
		if api_secret is None:
			seed = f"{portfolio_id}:{name}:api_secret".encode("utf-8")
			# 64 bytes derived from SHA-512, then base64 to ~88 chars
			secret_bytes = hashlib.sha512(seed).digest()
			api_secret = base64.b64encode(secret_bytes).decode("ascii")
		return self.factory.create_wallet(
			wallet_type=self.WalletType.KRAKEN,
			name=name,
			reference_fiat="EUR",
			portfolio_id=portfolio_id,
			description="d",
			api_key=api_key,
			api_secret=api_secret,
			is_active=True,
			last_sync=None,
		)

	def test_enum_and_datetime_roundtrip(self):
		# Create wallet with a non-default enum value
		w = self._make_wallet(name="INTEGRATIONTEST-E1", portfolio_id="INTEGRATIONTEST-pfE1")
		w.sync_status = WalletSyncStatus.IN_PROGRESS
		assert self.repo.save_wallet(w)

		# Verify enum round-trip through repository
		got = self.repo.get_wallet_by_id(w.id)
		self.assertIsNotNone(got)
		self.assertEqual(got.sync_status, WalletSyncStatus.IN_PROGRESS)

		# Verify datetime fields are persisted in DB (created_datetime set, updated_datetime may be None)
		with self.wr.SessionLocal() as session:
			orm = session.query(self.wr.WalletORM).filter(self.wr.WalletORM.wallet_id == w.id).one()
			self.assertIsNotNone(orm.created_datetime)
			self.assertTrue(isinstance(orm.created_datetime, datetime))
			self.assertIsNone(orm.updated_datetime)

		# Update and save again; created should remain, updated may still be None without update logic
		w.name = "INTEGRATIONTEST-E1-updated"
		w.sync_status = WalletSyncStatus.COMPLETED
		assert self.repo.save_wallet(w)
		got2 = self.repo.get_wallet_by_id(w.id)
		self.assertEqual(got2.sync_status, WalletSyncStatus.COMPLETED)
		with self.wr.SessionLocal() as session:
			orm2 = session.query(self.wr.WalletORM).filter(self.wr.WalletORM.wallet_id == w.id).one()
			self.assertIsNotNone(orm2.created_datetime)

	def test_null_api_credentials_roundtrip(self):
		# Create wallet with None credentials explicitly (bypass helper to avoid auto-generation)
		w = self.factory.create_wallet(
			wallet_type=self.WalletType.KRAKEN,
			name="INTEGRATIONTEST-N1",
			reference_fiat="EUR",
			portfolio_id="INTEGRATIONTEST-pfN",
			description="no creds",
			api_key=None,
			api_secret=None,
			is_active=True,
			last_sync=None,
		)
		assert self.repo.save_wallet(w)

		# Retrieve and ensure credentials remain None
		got = self.repo.get_wallet_by_id(w.id)
		self.assertIsNotNone(got)
		self.assertIsNone(got.api_key)
		self.assertIsNone(got.api_secret)

		# Verify DB columns are NULL
		with self.wr.SessionLocal() as session:
			orm = session.query(self.wr.WalletORM).filter(self.wr.WalletORM.wallet_id == w.id).one()
			self.assertIsNone(orm.api_key)
			self.assertIsNone(orm.api_secret)

	def test_save_and_get_wallet(self):
		wallet = self._make_wallet(name="INTEGRATIONTEST-Test1", api_key="abc", api_secret="xyz")
		self.assertTrue(self.repo.save_wallet(wallet))
		got = self.repo.get_wallet_by_id(wallet.id)
		self.assertIsNotNone(got)
		self.assertEqual(got.name, "INTEGRATIONTEST-Test1")
		self.assertEqual(got.api_key, "abc")
		self.assertEqual(got.api_secret, "xyz")

	def test_update_wallet(self):
		wallet = self._make_wallet(name="Before")
		self.repo.save_wallet(wallet)
		wallet.name = "After"
		self.assertTrue(self.repo.save_wallet(wallet))
		got = self.repo.get_wallet_by_id(wallet.id)
		self.assertEqual(got.name, "After")

	def test_list_and_delete(self):
		w1 = self._make_wallet(name="INTEGRATIONTEST-A", portfolio_id="INTEGRATIONTEST-pfA")
		w2 = self._make_wallet(name="INTEGRATIONTEST-B", portfolio_id="INTEGRATIONTEST-pfA")
		w3 = self._make_wallet(name="INTEGRATIONTEST-C", portfolio_id="INTEGRATIONTEST-pfB")
		self.repo.save_all_wallets([w1, w2, w3])
		lst = self.repo.get_all_wallets_in_portfolio("INTEGRATIONTEST-pfA")
		names = sorted([w.name for w in lst])
		self.assertEqual(names, ["INTEGRATIONTEST-A", "INTEGRATIONTEST-B"])
		self.assertTrue(self.repo.delete_wallet_by_id(w1.id))
		self.assertIsNone(self.repo.get_wallet_by_id(w1.id))