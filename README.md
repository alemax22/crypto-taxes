# 🇮🇹 Italian Crypto Tax Calculator 2025

A Python script to compute Italian cryptocurrency taxes for 2025 by connecting to Kraken API and downloading user transactions.

## Features

- 🔗 **Kraken API Integration**: Automatically downloads all trading transactions
- 🧮 **Italian Tax Compliance**: Implements 2025 Italian crypto tax regulations
- 📊 **LIFO Method**: Uses Last-In-First-Out method for cost basis calculations
- 💰 **26% Tax Rate**: Applies the correct Italian crypto tax rate for 2025
- 📁 **Parquet Storage**: Efficiently stores transaction data in Parquet format
- 🔄 **Incremental Updates**: Only downloads new transactions since last run
- 🎯 **Asset Normalization**: Handles Kraken's asset naming conventions

## Prerequisites

- Python 3.8 or higher
- Kraken account with API access
- Kraken API key and secret

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd crypto-taxes
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   # Copy the example file
   cp env_example.txt .env
   
   # Edit .env with your Kraken API credentials
   # Get your API credentials from: https://www.kraken.com/u/settings/api
   ```

## Configuration

### Kraken API Setup

1. Log in to your Kraken account
2. Go to [API Settings](https://www.kraken.com/u/settings/api)
3. Create a new API key with the following permissions:
   - **Query Funds**: Required to check balances
   - **Query Open Orders & Trades**: Required to download transaction history
   - **Query Ledgers**: Required to download deposit/withdrawal history

4. Add your API credentials to the `.env` file:
   ```
   KRAKEN_API_KEY=your_api_key_here
   KRAKEN_API_SECRET=your_api_secret_here
   ```

### API Key Encryption

The script uses a local encryption system to secure your API credentials:

1. **Secret Key Generation**: On first run, the script generates a `secret.key` file using Fernet encryption
2. **API Key Encryption**: Your API keys are encrypted using this secret key before being stored
3. **Environment Variables**: Store the encrypted versions of your API keys in the `.env` file

#### Setup Process:

1. **Generate the secret key** (run once):
   ```python
   from kraken import generate_key
   generate_key()
   ```

2. **Encrypt your API keys**:
   ```python
   from kraken import encrypt_message
   
   # Encrypt your actual API key and secret
   encrypted_key = encrypt_message("your_actual_api_key")
   encrypted_secret = encrypt_message("your_actual_api_secret")
   
   print(f"KRAKEN_API_KEY={encrypted_key}")
   print(f"KRAKEN_API_SECRET={encrypted_secret}")
   ```

3. **Add encrypted values to `.env`**:
   ```
   KRAKEN_API_KEY=gAAAAABk...  # Your encrypted API key
   KRAKEN_API_SECRET=gAAAAABk...  # Your encrypted API secret
   ```

#### Security Features:

- **Local Encryption**: The `secret.key` file is stored locally and should never be shared
- **Fernet Encryption**: Uses industry-standard symmetric encryption
- **Automatic Decryption**: The script automatically decrypts keys when needed
- **No Plain Text Storage**: API credentials are never stored in plain text

⚠️ **Important**: Keep your `secret.key` file secure and never commit it to version control!

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KRAKEN_API_KEY` | Your Kraken API key | Required |
| `KRAKEN_API_SECRET` | Your Kraken API secret | Required |

## Usage

### Basic Usage

Run the main script to calculate your 2025 Italian crypto taxes:

```bash
python main.py
```

### What the Script Does

1. **Connects to Kraken API** using your credentials
2. **Downloads transaction history** starting from 2021-01-01
3. **Stores data efficiently** in Parquet format for fast access
4. **Performs incremental updates** by only downloading new transactions
5. **Normalizes asset names** to handle Kraken's naming conventions
6. **Processes trades** by separating buy and sell transactions
7. **Calculates capital gains/losses** using LIFO method
8. **Applies Italian tax rules** with 26% tax rate
9. **Displays results** showing gains by year and total taxes due

### Data Storage

The script uses efficient Parquet storage:
- `kraken_ledger.parquet`: Stores all downloaded transaction data
- Data is automatically updated with new transactions on each run

## Italian Tax Rules 2025

### Crypto Taxation Overview

- **Tax Rate**: 26% on cryptocurrency capital gains
- **Method**: LIFO (Last-In-First-Out) for cost basis calculation
- **Scope**: All crypto-to-fiat and crypto-to-crypto trades

### What's Taxable

- ✅ Capital gains from selling cryptocurrencies
- ✅ Trading profits
- ✅ Crypto-to-crypto exchanges
- ✅ All gains regardless of holding period

### What's Not Taxable

- ❌ Purchases of cryptocurrencies
- ❌ Transfers between your own wallets

## Example Output

```
Total number of transactions: 1247
['spend', 'receive', 'trade', 'staking', 'transfer']
pair_name XBTEUR pair_altname XXBTZEUR
pair_name ETHEUR pair_altname XETHZEUR
...
(892, 5)
                    gain    taxes
year                            
2021   -1234.56  -321.00
2022    5678.90  1476.51
2023    8901.23  2314.32
2024   12345.67  3209.87
2025    2345.67   609.87
```

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Verify your API credentials in the `.env` file
   - Check that your API key has the required permissions
   - Ensure your Kraken account is active

2. **No Transactions Found**
   - The script processes transactions from 2021 onwards
   - Check if you have trading activity in the specified period
   - Verify your API key has "Query Open Orders & Trades" permission

3. **Import Errors**
   - Make sure all dependencies are installed: `pip install -r requirements.txt`
   - Check your Python version (requires 3.8+)

### Getting Help

If you encounter issues:

1. Check the error messages for specific details
2. Verify your Kraken API credentials and permissions
3. Ensure all dependencies are properly installed
4. Check that your `.env` file is in the correct location

## Security Notes

- ⚠️ **Never commit your `.env` file** to version control
- 🔒 **Keep your API credentials secure**
- 📱 **Use API keys with minimal required permissions**
- 🗑️ **Delete API keys if compromised**
- 🔐 **Protect your `secret.key` file** - this is used to decrypt your API credentials
- 🚫 **Never share your `secret.key` file** - it contains the encryption key for your API credentials
- 📁 **Add `secret.key` to your `.gitignore`** to prevent accidental commits

## Legal Disclaimer

This software is provided for educational and informational purposes only. It is not intended to provide tax, legal, or financial advice. Please consult with a qualified tax professional or accountant for your specific tax situation. The authors are not responsible for any errors in tax calculations or compliance issues.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
