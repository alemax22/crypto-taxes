#!/usr/bin/env python3
"""
Wallet Synchronization Service
Application Service for orchestrating wallet synchronization following DDD principles

This service coordinates wallet synchronization while ensuring state persistence
at critical points, making the synchronization status visible to all processes.
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

# Add parent directory to path to import config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wallets.wallet import Wallet
from wallets.wallet_enums import WalletSyncStatus
from wallets.wallet_repository import PostgresWalletRepository, WalletRepository

logger = logging.getLogger(__name__)


class WalletSynchronizationService:
    """
    Application Service for wallet synchronization.

    This service orchestrates the synchronization process while ensuring that
    state changes are persisted immediately, making them visible to other processes.

    Responsibilities:
    - Coordinate synchronization workflow
    - Persist state changes at critical points
    - Handle concurrency checks
    - Manage error handling and state recovery
    """

    def __init__(self, repository: Optional[WalletRepository] = None):
        """
        Initialize the synchronization service.

        Args:
            repository: Wallet repository instance. If None, creates a PostgresWalletRepository
        """
        self.repository = repository or PostgresWalletRepository()
        logger.info("WalletSynchronizationService initialized")

    def synchronize_wallet(
        self, wallet: Wallet, start_date: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Synchronize a single wallet with state persistence.

        This method orchestrates the synchronization process while ensuring that
        state changes are persisted immediately to the repository, making them
        visible to other processes.

        Args:
            wallet: Wallet instance to synchronize
            start_date: Start date for synchronization (YYYY-MM-DD format)

        Returns:
            Tuple of (success: bool, error_message: Optional[str])

        Workflow:
        1. Check if sync is already in progress (concurrency check)
        2. Authenticate the wallet
        3. Set status to IN_PROGRESS and persist
        4. Execute wallet._synchronize_transactions() (domain logic)
        5. Update and persist final status (COMPLETED or FAILED)


        TODO: Implement resilency strategy to handle ifninit IN_PROGRESS status and persist it in the repository.
        """
        wallet_id = wallet.id
        wallet_name = wallet.name

        try:
            # Step 1: Concurrency check - load fresh state from repository
            fresh_wallet = self.repository.get_wallet_by_id(wallet_id)
            if (
                fresh_wallet
                and fresh_wallet.sync_status == WalletSyncStatus.IN_PROGRESS
            ):
                logger.warning(
                    f"Synchronization already in progress for wallet {wallet_name} (ID: {wallet_id})"
                )
                return False, "Synchronization already in progress"

            # Step 2: Authenticate wallet
            logger.info(f"Authenticating wallet: {wallet_name}")
            is_authenticated = wallet.authenticate()

            if not is_authenticated:
                error_msg = "Authentication failed"
                logger.error(f"{error_msg} for wallet {wallet_name}")
                wallet.sync_status = WalletSyncStatus.FAILED
                self._persist_wallet_state(wallet, "authentication failed")
                return False, error_msg

            # Step 3: Set status to IN_PROGRESS and persist immediately
            logger.info(f"Starting synchronization for wallet: {wallet_name}")
            wallet.sync_status = WalletSyncStatus.IN_PROGRESS
            self._persist_wallet_state(wallet, "sync started")

            # Step 4: Execute domain synchronization logic
            # Note: The wallet's _synchronize_transactions() method may update its own status,
            # but we will ensure final state is persisted regardless
            success, error = wallet._synchronize_transactions(start_date)

            # Step 5: Ensure final state is persisted
            # The wallet entity may have already updated its status during _synchronize_transactions(),
            # but we ensure it's persisted here
            self._persist_wallet_state(wallet, "sync completed")
            return success, error

        except Exception as e:
            error_msg = f"Unexpected error during synchronization: {str(e)}"
            logger.error(f"{error_msg} for wallet {wallet_name}")

            # Ensure error state is persisted
            # TODO: What id DB is not available?
            wallet.sync_status = WalletSyncStatus.FAILED
            self._persist_wallet_state(wallet, f"sync error: {error_msg}")

            return False, error_msg

    def _persist_wallet_state(self, wallet: Wallet, reason: str = "") -> bool:
        """
        Persist wallet state to repository.

        Args:
            wallet: Wallet instance to persist
            reason: Optional reason for the state change (for logging)

        Returns:
            True if persistence was successful, False otherwise
        """
        try:
            success = self.repository.save_wallet(wallet)
            if success:
                logger.debug(
                    f"Persisted wallet state for {wallet.name}: "
                    f"status={wallet.sync_status.value}, reason={reason}"
                )
            else:
                logger.warning(
                    f"Failed to persist wallet state for {wallet.name}: "
                    f"status={wallet.sync_status.value}, reason={reason}"
                )
            return success
        except Exception as e:
            logger.error(f"Exception while persisting wallet state: {e}")
            return False

    def get_sync_status(
        self, wallet_id: str
    ) -> tuple[Optional[WalletSyncStatus], Optional[datetime]]:
        """
        Get current synchronization status from repository.

        This method queries the repository for the latest state, ensuring
        we see the most up-to-date synchronization status across all processes.

        Args:
            wallet_id: ID of the wallet

        Returns:
            Tuple of (sync_status, updated_datetime) or (None, None) if wallet not found
        """
        wallet = self.repository.get_wallet_by_id(wallet_id)
        if wallet:
            return wallet.sync_status, wallet.updated_datetime
        return None, None
