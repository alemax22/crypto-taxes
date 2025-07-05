#!/usr/bin/env python3
"""
Wallets Package
Provides wallet management functionality for cryptocurrency exchanges
"""

from .wallet import Wallet
from .wallet_kraken import KrakenWallet
from .portfolio import Portfolio

__all__ = [
    'Wallet',
    'KrakenWallet', 
    'Portfolio'
]

__version__ = '1.0.0' 