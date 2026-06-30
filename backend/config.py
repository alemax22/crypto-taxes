"""
Configuration file for Italian Crypto Tax Calculator 2025
Contains tax rates, thresholds, and other settings.
"""
import os
from datetime import datetime

# RESAMPLING INTERVAL
RESAMPLING_INTERVAL_IN_SECONDS = 60*60*24  # 1 day in seconds

# OHLCV settings
OHLCV_INTERVAL_MINUTES = 1440  # daily candles
OHLCV_INITIAL_LOAD_START_DATE = datetime(2020, 1, 1)
OHLCV_DEFAULT_ASSETS = [
    "BTC", "ETH", "XRP", "LTC", "ADA", "DOT", "LINK", "UNI",
    "SOL", "MATIC", "ATOM", "XLM", "ALGO", "VET", "AAVE",
    "TRX", "XTZ", "EOS", "KSM", "1INCH",
]

# REQUIRED COLUMNS FOR TRANSACTIONS
TRANSACTION_REQUIRED_COLUMNS = [
    "datetime", "transaction_id", "correlation_id", "transaction_type",
    "asset", "amount", "balance", "asset_price_in_reference_fiat", "fee",
    "transaction_original_type", "asset_original_name", "asset_original_balance"
]

PERSISTENT_DATA_DIR = "/app/persistent_data"
WALLETS_DIR = os.path.join(PERSISTENT_DATA_DIR, "wallets")

# TO BE REMOVED  ####################################################################################
# # Tax year
TAX_YEAR = 2025

# Italian crypto tax rates for 2025
ITALIAN_TAX_RATES = {
    'short_term': 0.26,  # 26% for gains held ≤12 months
    'long_term': 0.26,   # 26% for gains held >12 months
    'withholding': 0.26  # 26% withholding tax on crypto income
}

# Exemption threshold for crypto gains (€2000)
EXEMPTION_THRESHOLD = 2000

# Minimum holding period for long-term gains (in days)
LONG_TERM_HOLDING_PERIOD = 365



# Tax calculation settings
TAX_CALCULATION_SETTINGS = {
    'fifo_method': True,  # Use FIFO method for cost basis
    'include_fees': True,  # Include trading fees in calculations
    'round_to_cents': True,  # Round amounts to 2 decimal places
    'currency': 'EUR'  # Default currency for calculations
}

# File output settings
OUTPUT_SETTINGS = {
    'include_timestamps': True,
    'csv_encoding': 'utf-8',
    'date_format': '%Y-%m-%d %H:%M:%S'
} 