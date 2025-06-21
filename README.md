# 🇮🇹 Italian Crypto Tax Calculator 2025

A Python script to compute Italian cryptocurrency taxes for 2025 by connecting to Kraken API and downloading user transactions.

## Features

- 🔗 **Kraken API Integration**: Automatically downloads all trading transactions
- 🧮 **Italian Tax Compliance**: Implements 2025 Italian crypto tax regulations
- 📊 **FIFO Method**: Uses First-In-First-Out method for cost basis calculations
- 💰 **€2000 Exemption**: Applies the Italian crypto gains exemption threshold
- 📈 **Holding Period Analysis**: Distinguishes between short-term (≤12 months) and long-term gains
- 📁 **CSV Export**: Saves detailed tax reports and transaction data
- 🎯 **26% Tax Rate**: Applies the correct Italian crypto tax rate for 2025

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

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KRAKEN_API_KEY` | Your Kraken API key | Required |
| `KRAKEN_API_SECRET` | Your Kraken API secret | Required |
| `TAX_YEAR` | Tax year for calculations | 2025 |
| `EXEMPTION_THRESHOLD` | Exemption threshold in EUR | 2000 |

## Usage

### Basic Usage

Run the main script to calculate your 2025 Italian crypto taxes:

```bash
python main.py
```

### What the Script Does

1. **Connects to Kraken API** using your credentials
2. **Downloads all transactions** from the past 2 years
3. **Filters transactions** for the 2025 tax year
4. **Calculates capital gains/losses** using FIFO method
5. **Applies Italian tax rules**:
   - €2000 exemption threshold
   - 26% tax rate on crypto gains
   - Holding period analysis
6. **Displays results** in a formatted report
7. **Saves data** to CSV files for record keeping

### Output Files

The script generates two CSV files with timestamps:

- `tax_results_YYYYMMDD_HHMMSS.csv`: Complete tax calculation results
- `transactions_YYYYMMDD_HHMMSS.csv`: All downloaded transactions

## Italian Tax Rules 2025

### Crypto Taxation Overview

- **Tax Rate**: 26% on cryptocurrency capital gains
- **Exemption**: €2000 per year (no tax on gains up to this amount)
- **Holding Period**: No distinction between short-term and long-term gains in 2025
- **Method**: FIFO (First-In-First-Out) for cost basis calculation

### What's Taxable

- ✅ Capital gains from selling cryptocurrencies
- ✅ Trading profits
- ✅ Crypto-to-crypto exchanges
- ✅ Mining rewards (if applicable)

### What's Not Taxable

- ❌ Purchases of cryptocurrencies
- ❌ Transfers between your own wallets
- ❌ Gains below €2000 threshold

## Example Output

```
🇮🇹 Italian Crypto Tax Calculator for 2025
==================================================
✅ Kraken API connection established

📥 Downloading transaction history...
📅 Fetching transactions from 2023-01-01 to present...
📊 Processed 1,247 transactions:
   - Trades: 892
   - Ledger entries: 355
✅ Downloaded 1,247 transactions

🧮 Calculating Italian crypto taxes...
🔍 Analyzing transactions for tax year 2025...
📅 Found 156 transactions for tax year 2025
✅ Tax calculation completed

==================================================
📊 ITALIAN CRYPTO TAX RESULTS FOR 2025
==================================================

💰 Total Capital Gains: €8,450.00
📈 Total Capital Losses: €1,200.00
⚖️  Net Capital Gains: €7,250.00

💸 Taxable Amount: €5,250.00
🏛️  Total Tax Due: €1,365.00

📋 Tax Breakdown:
   26% on crypto gains: €1,365.00

📅 Holding Period Analysis:
   Short-term gains (≤12 months): €4,800.00
   Long-term gains (>12 months): €2,450.00

💾 Results saved to:
   - tax_results_20250115_143022.csv
   - transactions_20250115_143022.csv

🎉 Tax calculation process completed successfully!
```

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Verify your API credentials in the `.env` file
   - Check that your API key has the required permissions
   - Ensure your Kraken account is active

2. **No Transactions Found**
   - The script only processes transactions from the specified tax year
   - Check if you have trading activity in 2025
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

## Legal Disclaimer

This software is provided for educational and informational purposes only. It is not intended to provide tax, legal, or financial advice. Please consult with a qualified tax professional or accountant for your specific tax situation. The authors are not responsible for any errors in tax calculations or compliance issues.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
