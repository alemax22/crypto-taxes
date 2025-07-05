# Wallets Module

This module provides a secure way to manage multiple cryptocurrency exchange wallets with automatic encryption of API credentials.

## Features

- **Secure Storage**: API keys are automatically encrypted when stored in CSV files
- **Multiple Exchanges**: Support for different exchange types (currently Kraken)
- **Portfolio Management**: Centralized management of multiple wallets
- **Automatic Decryption**: Credentials are automatically decrypted when loaded into memory

## Quick Start

### 1. Install Dependencies

```bash
pip install cryptography pandas requests
```

### 2. Basic Usage

```python
from wallets.portfolio import Portfolio

# Initialize portfolio
portfolio = Portfolio()

# Add a wallet
wallet_id = portfolio.add_wallet(
    wallet_type="Kraken",
    name="My Kraken Account",
    api_key="your_api_key",
    api_secret="your_api_secret",
    description="Main trading account"
)

# List all wallets
wallets = portfolio.list_wallets()
for wallet in wallets:
    print(f"Name: {wallet['name']}, Type: {wallet['wallet_type']}")

# Load and use a wallet
wallet_instance = portfolio.load_wallet(wallet_id)
if wallet_instance and wallet_instance.authenticate():
    balance = wallet_instance.get_balance()
    transactions = wallet_instance.get_transactions()
```

### 3. Run Tests

```bash
# From the backend directory
python test_wallets.py
```

## File Structure

```
wallets/
├── __init__.py          # Package initialization
├── wallet.py           # Abstract Wallet class
├── wallet_kraken.py    # Kraken-specific implementation
├── portfolio.py        # Portfolio management class
└── example_usage.py    # Example usage script
```

## Security

- API credentials are encrypted using Fernet (symmetric encryption)
- Encryption key is stored separately from the wallet data
- Credentials are only decrypted when loaded into memory
- CSV files contain encrypted data only

## API Reference

### Portfolio Class

- `add_wallet()`: Add a new wallet to the portfolio
- `list_wallets()`: List all wallets (without sensitive data)
- `load_wallet()`: Load a wallet instance for use
- `remove_wallet()`: Remove a wallet from the portfolio
- `get_wallet_summary()`: Get portfolio statistics

### Wallet Class

- `authenticate()`: Authenticate with the exchange
- `get_balance()`: Get current balance
- `get_transactions()`: Get transaction history
- `synchronize()`: Sync data with the exchange

## Example Workflow

1. **Initialize Portfolio**: Creates encryption key and CSV file
2. **Add Wallets**: Add exchange wallets with API credentials
3. **Load Wallets**: Load wallet instances for use
4. **Authenticate**: Verify API credentials work
5. **Fetch Data**: Get balances, transactions, etc.
6. **Synchronize**: Keep local data up to date

## Error Handling

The module includes comprehensive error handling:
- Invalid API credentials are detected during authentication
- Failed wallets are marked as inactive
- Encryption/decryption errors are logged
- Network errors are handled gracefully

## Data Storage

- **CSV File**: `wallets.csv` - Contains encrypted wallet configurations
- **Encryption Key**: `portfolio_key.key` - Separate file for security
- **Data Directory**: Exchange-specific data is stored in organized folders 