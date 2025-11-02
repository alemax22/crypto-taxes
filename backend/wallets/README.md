# Wallets Module

This module provides a secure way to manage multiple cryptocurrency exchange wallets with automatic encryption of API credentials.

## Features

- **Secure Storage**: API keys are automatically encrypted when stored in the database
- **Multiple Exchanges**: Support for different exchange types (currently Kraken)
- **Portfolio Management**: Centralized management of multiple wallets within portfolios
- **Automatic Decryption**: Credentials are automatically decrypted when loaded into memory

## Quick Start

### 1. Install Dependencies

```bash
pip install cryptography pandas requests sqlalchemy psycopg2-binary
```

### 2. Basic Usage

```python
from wallets.portfolio import Portfolio
from wallets.wallet_enums import WalletType

# Initialize portfolio (creates a new portfolio entity)
portfolio = Portfolio(reference_asset="EUR")

# Add a wallet to the portfolio
wallet_id = portfolio.add_wallet(
    wallet_type=WalletType.KRAKEN,
    name="My Kraken Account",
    api_key="your_api_key",
    api_secret="your_api_secret",
    description="Main trading account"
)

# List all wallets in the portfolio
wallets = portfolio.list_wallets()
for wallet in wallets:
    print(f"Name: {wallet['name']}, Type: {wallet['wallet_type']}")

# Load and use a wallet
wallet_instance = portfolio.load_wallet(wallet_id)
if wallet_instance and wallet_instance.authenticate():
    balance = wallet_instance.get_balance()
    transactions = wallet_instance.get_transactions()

# Synchronize all wallets in the portfolio
results = portfolio.synchronize_all_wallets()
print(f"Synchronization results: {results}")

# Get portfolio information
portfolio_info = portfolio.to_dict()
print(f"Portfolio ID: {portfolio_info['portfolio_id']}")
print(f"Reference Asset: {portfolio_info['reference_asset']}")
print(f"Wallet Count: {portfolio_info['wallet_count']}")
```

### 3. Run Tests

```bash
# From the backend directory
python -m pytest test/test_portfolio_new.py -v
```

## File Structure

```
wallets/
├── __init__.py              # Package initialization
├── wallet.py               # Abstract Wallet class
├── wallet_kraken.py        # Kraken-specific implementation
├── portfolio.py            # Portfolio management class
├── wallet_factory.py       # Factory for creating wallets
├── wallet_repository.py    # Database repository for wallets
├── wallet_enums.py         # Enums for wallet types and status
└── README.md              # This file
```

## Portfolio Entity

The Portfolio class represents a portfolio entity with the following properties:

- **portfolio_id**: Unique identifier starting with "PF-" followed by a UUID
- **reference_asset**: Reference asset for the portfolio (e.g., "EUR", "USD")
- **created_datetime**: When the portfolio was created

## Security

- API credentials are encrypted using Fernet (symmetric encryption)
- Encryption key is stored separately from the wallet data
- Credentials are only decrypted when loaded into memory
- Database contains encrypted data only

## API Reference

### Portfolio Class

#### Initialization
```python
Portfolio(portfolio_id=None, reference_asset="EUR", created_datetime=None)
```

#### Methods
- `add_wallet()`: Add a new wallet to the portfolio
- `list_wallets()`: List all wallets (without sensitive data)
- `get_wallet_by_id()`: Get wallet configuration by ID
- `load_wallet()`: Load a wallet instance for use
- `remove_wallet()`: Remove a wallet from the portfolio
- `synchronize_all_wallets()`: Synchronize all wallets in the portfolio
- `to_dict()`: Convert portfolio to dictionary representation

### Wallet Class

- `authenticate()`: Authenticate with the exchange
- `get_balance()`: Get current balance
- `get_transactions()`: Get transaction history
- `synchronize()`: Sync data with the exchange

## Example Workflow

1. **Create Portfolio**: Initialize a new portfolio entity with reference asset
2. **Add Wallets**: Add exchange wallets with API credentials to the portfolio
3. **Load Wallets**: Load wallet instances for use
4. **Authenticate**: Verify API credentials work
5. **Fetch Data**: Get balances, transactions, etc.
6. **Synchronize**: Keep local data up to date for all wallets in the portfolio

## Error Handling

The module includes comprehensive error handling:
- Invalid API credentials are detected during authentication
- Failed wallets are marked as inactive
- Encryption/decryption errors are logged
- Network errors are handled gracefully
- Portfolio operations are scoped to the specific portfolio

## Data Storage

- **Database**: PostgreSQL with encrypted wallet configurations
- **Encryption Key**: Stored securely for credential encryption
- **Data Directory**: Exchange-specific data is stored in organized folders

## Database Schema

The portfolio system uses a database-backed approach:
- Wallets are stored in a `wallets` table with encrypted credentials
- Each wallet belongs to a specific portfolio via `portfolio_id`
- Portfolio information is managed by the Portfolio class 