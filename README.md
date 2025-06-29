# Italian Crypto Tax Calculator 2025

A comprehensive crypto tax calculation tool for Italian residents, specifically designed for 2025 tax regulations. This application connects to the Kraken API, downloads user transactions, and computes taxes according to Italian crypto tax laws.

## Features

- **Kraken API Integration**: Secure connection to Kraken API for transaction data
- **Italian Tax Compliance**: Implements 2025 Italian crypto tax regulations
- **Encrypted Storage**: API credentials encrypted and stored securely
- **Web Interface**: Modern React frontend with real-time data visualization
- **Docker Support**: Fully containerized application
- **Persistent Data**: All data stored in a single Docker volume

## Quick Start with Docker

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd crypto-taxes
   ```

2. **Start the application**:
   ```bash
   docker-compose up --build -d
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
   python backend/setup_encryption.py
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
   python backend/app.py
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

The application uses a single Docker volume for all persistent data:

- **Transaction data**: `/app/persistent_data/data/kraken_ledger.parquet`
- **OHLC data**: `/app/persistent_data/data/kraken_ohlc.parquet`
- **API credentials**: `/app/persistent_data/config/kraken_api_keys.json` (encrypted)
- **Encryption key**: `/app/persistent_data/config/secret.key`
- **Logs**: `/app/persistent_data/logs/`

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
- **Persistent Security**: Encryption key stored in persistent volume

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
docker-compose down -v
docker-compose up --build -d
```

## Development

### Project Structure
```
crypto-taxes/
├── backend/              # Python backend files
│   ├── app.py           # Flask backend
│   ├── kraken.py        # Kraken API integration
│   ├── main.py          # Original CLI script
│   ├── config.py        # Configuration settings
│   ├── setup_encryption.py # Encryption setup
│   └── test_secret_generation.py # Test utilities
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   └── pages/        # Page components
│   └── public/
├── docker-compose.yml    # Docker configuration
└── Dockerfile           # Multi-stage Docker build
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This application is for educational and informational purposes. Please consult with a qualified tax professional for official tax advice. The authors are not responsible for any tax-related decisions made using this software.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the error logs
3. Create an issue in the repository
4. Contact the development team
