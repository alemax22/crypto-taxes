#!/usr/bin/env python3
"""
Wallet Enums
Shared enums for wallet-related functionality
"""

from enum import Enum


class WalletSyncStatus(Enum):
    """Enumeration of wallet synchronization statuses."""
    NOT_SYNCHRONIZED = "not synchronized"
    IN_PROGRESS = "in progress"
    COMPLETED = "completed"
    FAILED = "failed"


class WalletType(Enum):
    """Enumeration of supported wallet types."""
    KRAKEN = "KrakenWallet"
    # Add more wallet types as needed
    # BINANCE = "BinanceWallet"
    # COINBASE = "CoinbaseWallet"


class TransactionType(Enum):
    """Enumeration of transaction types."""
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRADE = "trade"
    TRANSFER = "transfer"
    REWARD = "reward"
    FEE = "fee"


class AssetType(Enum):
    """Enumeration of asset types."""
    CRYPTO = "crypto"
    FIAT = "fiat"
    TOKEN = "token"
