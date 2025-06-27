#!/usr/bin/env python3
"""
Flask API for Italian Crypto Tax Calculator 2025
Provides endpoints for tax calculation and transaction data retrieval.
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import os
import json
import logging
from decimal import Decimal

import kraken

app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def save_encrypted_credentials(api_key, api_secret):
    """
    Save encrypted API credentials to kraken_api_keys.json
    """
    try:
        # Check if secret.key exists, if not generate it
        if not os.path.exists('secret.key'):
            logger.info("Secret key file not found. Generating new encryption key...")
            kraken.generate_key()
            logger.info("New encryption key generated successfully")
        
        # Encrypt the credentials
        encrypted_key = kraken.encrypt_message(api_key)
        encrypted_secret = kraken.encrypt_message(api_secret)
        
        # Store in JSON file
        api_file = 'kraken_api_keys.json'
        api_data = {
            "KRAKEN_API_KEY": encrypted_key.decode() if isinstance(encrypted_key, bytes) else encrypted_key,
            "KRAKEN_API_SECRET": encrypted_secret.decode() if isinstance(encrypted_secret, bytes) else encrypted_secret
        }
        with open(api_file, 'w') as f:
            json.dump(api_data, f)
        
        return True
    except Exception as e:
        logger.error(f"Error saving encrypted credentials: {str(e)}")
        return False

def load_encrypted_credentials():
    """
    Load encrypted API credentials from kraken_api_keys.json
    """
    api_file = 'kraken_api_keys.json'
    if not os.path.exists(api_file):
        return None, None
    with open(api_file, 'r') as f:
        api_data = json.load(f)
    return api_data.get("KRAKEN_API_KEY"), api_data.get("KRAKEN_API_SECRET")

def test_kraken_credentials(api_key, api_secret):
    """
    Test if the provided Kraken API credentials are valid
    """
    try:
        # Try to get balance (this will test the credentials)
        response = kraken.get_balance(api_key, api_secret)
        
        return True
    except Exception as e:
        logger.error(f"Error testing Kraken credentials: {str(e)}")
        return False

@app.route('/api/setup-credentials', methods=['POST'])
def setup_credentials():
    """
    API endpoint to set up Kraken API credentials
    """
    try:
        data = request.get_json()
        api_key = data.get('api_key', '').strip()
        api_secret = data.get('api_secret', '').strip()
        
        if not api_key or not api_secret:
            return jsonify({
                'success': False, 
                'error': 'API key and secret are required'
            }), 400
        
        # Test the credentials first
        logger.info("Testing Kraken API credentials...")
        if not test_kraken_credentials(api_key, api_secret):
            return jsonify({
                'success': False, 
                'error': 'Invalid API credentials. Please check your API key and secret.'
            }), 400
        
        # Save the encrypted credentials
        logger.info("Saving encrypted credentials...")
        if save_encrypted_credentials(api_key, api_secret):
            return jsonify({
                'success': True,
                'message': 'API credentials saved successfully and encrypted'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to save credentials'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in setup_credentials: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/check-credentials', methods=['GET'])
def check_credentials():
    """
    API endpoint to check if credentials are configured
    """
    try:
        encrypted_key, encrypted_secret = load_encrypted_credentials()
        if not encrypted_key or not encrypted_secret:
            return jsonify({
                'success': True,
                'configured': False,
                'message': 'No API credentials configured'
            })
        # Try to decrypt and use the credentials
        try:
            api_key = kraken.decrypt_message(encrypted_key)
            api_secret = kraken.decrypt_message(encrypted_secret)
            # Optionally, test with a lightweight Kraken call here
            return jsonify({
                'success': True,
                'configured': True,
                'message': 'API credentials are configured and valid'
            })
        except Exception as e:
            return jsonify({
                'success': True,
                'configured': False,
                'message': 'API credentials are configured but invalid'
            })
    except Exception as e:
        logger.error(f"Error in check_credentials: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def calculate_taxes_api():
    """
    Main function to calculate crypto taxes - converted from main.py
    """
    try:
        reference_asset = "ZEUR"
        exception_assets = ["KFEE","NFT"]
        encrypted_key, encrypted_secret = load_encrypted_credentials()
        api_key = kraken.decrypt_message(encrypted_key)
        api_sec = kraken.decrypt_message(encrypted_secret)
        start_date = "2021-01-01"
        
        response = kraken.get_ledger(start_date, 0, api_key, api_sec)
        logger.info(f"Total number of transactions: {response['result']['count']}")
        
        # Get all ledger data
        start_timestamp = datetime.strptime(start_date, "%Y-%m-%d")
        filename = "data/kraken_ledger.parquet"
        ledger_df = pd.DataFrame([])
        
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        # Read data from file
        try:
            ledger_df = pd.read_parquet(filename, engine="fastparquet")
            if ledger_df.shape[0] > 0:
                ledger_df = ledger_df[ledger_df["date"] > start_date]
                start_timestamp = ledger_df.iloc[0].loc["date"]
                start_date = str(start_timestamp)[:10]
        except FileNotFoundError:
            logger.info("No existing ledger file found, starting fresh")

        ledger_df_delta = kraken.retrieve_all_ledger_data(start_date, api_key, api_sec)
        ledger_df_delta = ledger_df_delta.loc[ledger_df_delta["date"] > start_timestamp]
        
        # Ensure both DataFrames have the same structure before concatenation
        if ledger_df.empty:
            ledger_df = ledger_df_delta
        elif ledger_df_delta.empty:
            pass
        else:
            all_columns = list(set(ledger_df.columns) | set(ledger_df_delta.columns))
            
            for col in all_columns:
                if col not in ledger_df.columns:
                    ledger_df[col] = None
                if col not in ledger_df_delta.columns:
                    ledger_df_delta[col] = None
            
            ledger_df = ledger_df[all_columns]
            ledger_df_delta = ledger_df_delta[all_columns]
            ledger_df = pd.concat([ledger_df_delta, ledger_df], ignore_index=False)
            
        # Write back to file
        ledger_df.to_parquet(filename, engine="fastparquet", compression="GZIP")
        
        # Create columns with decimal value
        ledger_df["decimalamount"] = ledger_df.apply(lambda row: kraken.decimal_from_value(row["amount"]), axis=1)
        ledger_df["decimalbalance"] = ledger_df.apply(lambda row: kraken.decimal_from_value(row["balance"]), axis=1)
        ledger_df["decimalfee"] = ledger_df.apply(lambda row: kraken.decimal_from_value(row["fee"]), axis=1)
        ledger_df["justdate"] = ledger_df['date'].dt.normalize()
        
        ledger_df = kraken.normalize_assets_name(ledger_df, "asset", True)
        assets_in_portfolio = ledger_df["assetnorm"].unique()
        operation_types = ledger_df["type"].unique()
        
        # Trades processing
        ledger_df_trade = ledger_df[ledger_df["assetnorm"]!="KFEE"]
        ledger_df_trade = ledger_df_trade[(ledger_df_trade["type"]=="spend")|(ledger_df_trade["type"]=="receive")|(ledger_df_trade["type"]=="trade")].set_index("refid")
        ledger_df_from = ledger_df_trade[ledger_df_trade["decimalamount"] < 0]
        ledger_df_to = ledger_df_trade[ledger_df_trade["decimalamount"] >= 0]
        ledger_df_trade = ledger_df_from.join(ledger_df_to, how="left", lsuffix="_from", rsuffix="_to")
        ledger_df_trade = ledger_df_trade.sort_values(by=['date_from'], ascending=False)

        # Check consistency
        if ledger_df_trade.index.duplicated().any():
            logger.warning("There are duplicate indexes in trade data")
        else:
            logger.info("No duplicate indexes found")

        # Reformat the dataframe
        ledger_df_trade = ledger_df_trade[["date_to","decimalamount_from","decimalamount_to","assetnorm_from","assetnorm_to", "justdate_to"]]
        
        # All sell
        ledger_df_trade_sell = ledger_df_trade[ledger_df_trade["assetnorm_to"] == reference_asset]
        ledger_df_trade_sell = ledger_df_trade_sell.rename(columns={'justdate_to': 'date', 'decimalamount_to': 'total', 'decimalamount_from': 'quantity', 'assetnorm_from': 'cryptocur', 'date_to': 'datetime'})
        ledger_df_trade_sell = ledger_df_trade_sell[["date","total","quantity","cryptocur","datetime"]]

        # All buy
        ledger_df_trade_buy = ledger_df_trade[ledger_df_trade["assetnorm_from"] == reference_asset]
        ledger_df_trade_buy = ledger_df_trade_buy.rename(columns={'justdate_to': 'date', 'decimalamount_from': 'total', 'decimalamount_to': 'quantity', 'assetnorm_to': 'cryptocur', 'date_to': 'datetime'})
        ledger_df_trade_buy = ledger_df_trade_buy[["date","total","quantity","cryptocur","datetime"]]

        # Compute price
        ledger_df_trade_final = pd.concat([ledger_df_trade_sell, ledger_df_trade_buy], ignore_index=False)
        ledger_df_trade_final["price"] = ledger_df_trade_final["total"]/ledger_df_trade_final["quantity"]*-1
        ledger_df_trade_final.sort_values(by=['datetime'], ascending=False, inplace=True)

        # Get OHLC data
        logger.info("Fetching OHLC data with persistence...")
        OHLC_df = kraken.get_ohlc_data_with_persistence(
            assets_in_portfolio=assets_in_portfolio,
            reference_asset=reference_asset,
            exception_assets=exception_assets,
            start_date=start_date
        )
        
        # Get balance data
        balance_df = kraken.get_balance_dataframe(api_key, api_sec)
        balance_df = balance_df.reset_index(names=['asset'])
        balance_df = kraken.normalize_assets_name(balance_df, "asset")
        balance_df["balance"] = balance_df.apply(lambda row: kraken.decimal_from_value(row["balance"]), axis=1)
        balance_df = balance_df[["balance","assetnorm"]]
        balance_df = balance_df.groupby(['assetnorm']).sum()

        # Calculate year-end balances
        kraken.calculate_year_end_balances(ledger_df, OHLC_df, reference_asset, exception_assets)

        # Compute taxes
        ledger_out_df3, gains_final_df = kraken.compute_taxes(ledger_df_trade_final)
        
        # Group by year and asset for tax calculation
        gains_by_year_asset = gains_final_df.groupby(['year','asset']).sum()
        gains_by_year = gains_final_df.groupby(['year']).sum()

        # Apply taxes with 2024 franchigia
        gains_by_year["taxes"] = gains_by_year.apply(
            lambda row: kraken.calculate_taxes_with_franchigia(row["gain"], row.name) if row.name == 2024 
            else row["gain"] * Decimal(0.26), 
            axis=1
        )
        
        # Convert DataFrames to JSON-serializable format
        def decimal_to_float(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            return obj
        
        # Convert gains data
        gains_by_year_json = gains_by_year.reset_index().to_dict('records')
        gains_by_year_asset_json = gains_by_year_asset.reset_index().to_dict('records')
        
        # Convert transaction data
        ledger_df_trade_final_json = ledger_df_trade_final.reset_index().to_dict('records')
        
        # Convert balance data
        balance_df_json = balance_df.reset_index().to_dict('records')
        
        # Apply decimal conversion
        for record in gains_by_year_json:
            for key, value in record.items():
                record[key] = decimal_to_float(value)
        
        for record in gains_by_year_asset_json:
            for key, value in record.items():
                record[key] = decimal_to_float(value)
        
        for record in ledger_df_trade_final_json:
            for key, value in record.items():
                record[key] = decimal_to_float(value)
        
        for record in balance_df_json:
            for key, value in record.items():
                record[key] = decimal_to_float(value)
        
        return {
            'success': True,
            'gains_by_year': gains_by_year_json,
            'gains_by_year_asset': gains_by_year_asset_json,
            'transactions': ledger_df_trade_final_json,
            'balance': balance_df_json,
            'total_transactions': len(ledger_df_trade_final_json),
            'assets_in_portfolio': list(assets_in_portfolio),
            'operation_types': list(operation_types)
        }
        
    except Exception as e:
        logger.error(f"Error in calculate_taxes_api: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/api/calculate-taxes', methods=['POST'])
def calculate_taxes_endpoint():
    """
    API endpoint to calculate crypto taxes
    """
    try:
        logger.info("Calculating taxes...")
        result = calculate_taxes_api()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in calculate_taxes_endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    """
    API endpoint to get transaction data
    """
    try:
        filename = "data/kraken_ledger.parquet"
        if os.path.exists(filename):
            ledger_df = pd.read_parquet(filename, engine="fastparquet")
            transactions = ledger_df.to_dict('records')
            return jsonify({'success': True, 'transactions': transactions})
        else:
            return jsonify({'success': False, 'error': 'No transaction data found'})
    except Exception as e:
        logger.error(f"Error in get_transactions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/balance', methods=['GET'])
def get_balance():
    """
    API endpoint to get current balance
    """
    try:
        logger.info("get_balance")
        encrypted_key, encrypted_secret = load_encrypted_credentials()
        api_key = kraken.decrypt_message(encrypted_key)
        api_sec = kraken.decrypt_message(encrypted_secret)
        balance_df = kraken.get_balance_dataframe(api_key, api_sec)
        balance_df = balance_df.reset_index(names=['asset'])
        balance_df = kraken.normalize_assets_name(balance_df, "asset")
        balance_df["balance"] = balance_df.apply(lambda row: kraken.decimal_from_value(row["balance"]), axis=1)
        balance_df = balance_df[["balance","assetnorm"]]
        balance_df = balance_df.groupby(['assetnorm']).sum()
        
        balance_json = balance_df.reset_index().to_dict('records')
        
        # Convert Decimal to float
        for record in balance_json:
            for key, value in record.items():
                if isinstance(value, Decimal):
                    record[key] = float(value)
        
        return jsonify({'success': True, 'balance': balance_json})
    except Exception as e:
        logger.error(f"Error in get_balance: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """
    Serve React app for all non-API routes
    """
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    logger.info("Starting Crypto Tax Calculator application...")
    app.run(debug=False, host='0.0.0.0', port=5000) 