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
from datetime import datetime

import importlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

# Ensure backend modules can be imported (same pattern as other tests)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.mark.unit
class TestWalletRepository(unittest.TestCase):
	"""Class-based tests for the repository with an isolated SQLite DB."""

	def setUp(self):
		# Temporary wallets dir for Fernet key
		self.temp_dir = tempfile.mkdtemp()
		import config as app_config
		self._original_wallets_dir = getattr(app_config, 'WALLETS_DIR', None)
		app_config.WALLETS_DIR = self.temp_dir

		# Create in-memory SQLite engine and session
		engine = create_engine("sqlite:///:memory:")
		SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

		# Patch db module to use SQLite and no schema
		import db as app_db
		self._original_engine = app_db.engine
		self._original_session_local = app_db.SessionLocal
		self._original_schema = getattr(app_db, 'SCHEMA_NAME', None)
		app_db.engine = engine
		app_db.SessionLocal = SessionLocal
		app_db.SCHEMA_NAME = None

		# Reload repository to bind ORM with patched db
		import wallets.wallet_repository as wr
		importlib.reload(wr)
		self.wr = wr

		# Create tables
		self.wr.Base.metadata.create_all(bind=engine)

		# Patch repository __init__ to avoid schema DDL on SQLite
		self._orig_repo_init = self.wr.PostgresWalletRepository.__init__
		
		def repo_init_no_schema(repo_self):
			# Call base init to set encryption key, etc.
			self.wr.WalletRepository.__init__(repo_self)
			# Ensure tables are present (already created above)
			return None

		self.wr.PostgresWalletRepository.__init__ = repo_init_no_schema

		# Instantiate repository
		self.repo = self.wr.PostgresWalletRepository()

		# Helpers
		self.WalletType = self.wr.wallets.wallet_enums.WalletType
		self.factory = self.wr.wallets.wallet_factory.WalletFactory()

	def tearDown(self):
		# Restore patched attributes
		import config as app_config
		if self._original_wallets_dir is not None:
			app_config.WALLETS_DIR = self._original_wallets_dir
		import db as app_db
		app_db.engine = self._original_engine
		app_db.SessionLocal = self._original_session_local
		app_db.SCHEMA_NAME = self._original_schema
		# Restore methods
		self.wr.PostgresWalletRepository.__init__ = self._orig_repo_init
		# Cleanup temp dir
		shutil.rmtree(self.temp_dir, ignore_errors=True)

	def _make_wallet(self, name="W1", portfolio_id="pf1", api_key="k", api_secret="s"):
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

	def test_save_and_get_wallet(self):
		wallet = self._make_wallet(name="Test1", api_key="abc", api_secret="xyz")
		self.assertTrue(self.repo.save_wallet(wallet))
		got = self.repo.get_wallet_by_id(wallet.id)
		self.assertIsNotNone(got)
		self.assertEqual(got.name, "Test1")
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
		w1 = self._make_wallet(name="A", portfolio_id="pfA")
		w2 = self._make_wallet(name="B", portfolio_id="pfA")
		w3 = self._make_wallet(name="C", portfolio_id="pfB")
		self.repo.save_all_wallets([w1, w2, w3])
		lst = self.repo.get_all_wallets_in_portfolio("pfA")
		names = sorted([w.name for w in lst])
		self.assertEqual(names, ["A", "B"])
		self.assertTrue(self.repo.delete_wallet_by_id(w1.id))
		self.assertIsNone(self.repo.get_wallet_by_id(w1.id))