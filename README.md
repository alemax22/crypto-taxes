# Italian Crypto Tax Calculator 2025

A comprehensive web application for calculating Italian crypto taxes according to 2025 regulations, with support for Kraken API integration.

## Features

- **Automated Tax Calculation**: Computes crypto taxes according to Italian 2025 regulations
- **Kraken API Integration**: Direct connection to Kraken for transaction data
- **Secure API Key Management**: Encrypted storage of API credentials with persistence
- **Interactive Dashboard**: Real-time visualization of tax data and portfolio balance
- **Transaction History**: Detailed view of all trading activities
- **Tax Summary**: Year-by-year breakdown of gains, losses, and taxes
- **Portfolio Balance**: Current holdings across all assets
- **Docker Support**: Fully containerized application for easy deployment

## API Key Management

The application includes a secure API key management system:

- **Encrypted Storage**: API credentials are encrypted using the application's encryption system
- **Persistence**: Credentials persist across application restarts
- **Validation**: Automatic testing of API credentials before saving
- **User Interface**: Easy-to-use web interface for configuration

### Required Kraken API Permissions

Your Kraken API key needs the following permissions:
- **Query Funds** - To check balances
- **Query Open Orders & Trades** - To download transaction history  
- **Query Ledgers** - To download deposit/withdrawal history

## Quick Start with Docker

### Prerequisites

- Docker Desktop installed and running
- Kraken API credentials (optional for initial setup)

### Running the Application

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd crypto-taxes
   ```

2. **Start the application**:
   
   **On Windows:**
   ```cmd
   run-docker.bat
   ```
   
   **On Linux/Mac:**
   ```bash
   ./run-docker.sh
   ```

3. **Access the application**:
   Open your browser and navigate to `http://localhost:5000`

4. **Configure API credentials**:
   - Click "Configure API Credentials" on the dashboard
   - Enter your Kraken API key and secret
   - The credentials will be encrypted and saved securely

5. **Calculate taxes**:
   - Once credentials are configured, click "Calculate Taxes"
   - The application will fetch your data from Kraken and compute taxes

## Manual Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend development)
- Kraken API credentials

### Backend Setup

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up encryption**:
   ```bash
   python setup_encryption.py
   ```

3. **Configure environment variables**:
   Create a `.env` file with your Kraken API credentials:
   ```
   KRAKEN_API_KEY=your_api_key_here
   KRAKEN_API_SECRET=your_api_secret_here
   ```

### Frontend Setup

1. **Install Node.js dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Build the frontend**:
   ```bash
   npm run build
   ```

### Running the Application

1. **Start the Flask backend**:
   ```bash
   python app.py
   ```

2. **Access the application**:
   Open your browser and navigate to `http://localhost:5000`

## API Endpoints

### Authentication & Configuration
- `GET /api/check-credentials` - Check if API credentials are configured
- `POST /api/setup-credentials` - Set up encrypted API credentials

### Data & Calculations
- `POST /api/calculate-taxes` - Calculate crypto taxes
- `GET /api/transactions` - Get transaction history
- `GET /api/balance` - Get current portfolio balance
- `GET /api/health` - Health check endpoint

## Data Persistence

The application stores data in the following locations:
- **Transaction data**: `data/kraken_ledger.parquet`
- **OHLC data**: `kraken_historical_ohlc_data/`
- **API credentials**: `.env` (encrypted)
- **Logs**: `logs/`

## Tax Calculation Details

The application implements Italian crypto tax regulations for 2025:

- **Tax Rate**: 26% on capital gains
- **2024 Franchigia**: €2,000 deductible threshold for 2024
- **FIFO Method**: First-in, first-out for cost basis calculation
- **Year-end Balances**: Automatic calculation of year-end positions

## Security Features

- **Encrypted API Storage**: Credentials encrypted using Fernet encryption
- **Secure Environment**: Docker containerization for isolation
- **No Plain Text**: API secrets never stored in plain text
- **Persistent Security**: Encryption key stored in `secret.key`

## Troubleshooting

### Common Issues

1. **Docker not running**: Ensure Docker Desktop is started
2. **Port conflicts**: Check if port 5000 is available
3. **API errors**: Verify Kraken API credentials and permissions
4. **Data not loading**: Check internet connection and API status

### Logs

View application logs:
```bash
docker-compose logs -f
```

### Reset Data

To reset all data and start fresh:
```bash
docker-compose down
rm -rf data/ logs/ .env
docker-compose up --build -d
```

## Development

### Project Structure
```
crypto-taxes/
├── app.py                 # Flask backend
├── kraken.py             # Kraken API integration
├── main.py               # Original CLI script
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   └── pages/        # Page components
│   └── public/
├── data/                 # Data storage
├── logs/                 # Application logs
└── docker-compose.yml    # Docker configuration
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This application is for educational and informational purposes. Please consult with a qualified tax professional for official tax advice. The authors are not responsible for any tax-related decisions made using this software.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the error logs
3. Create an issue in the repository
4. Contact the development team
