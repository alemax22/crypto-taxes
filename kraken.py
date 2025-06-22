import time
import requests
from cryptography.fernet import Fernet
import urllib.parse
import hashlib
import hmac
import base64
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
import os
from config import KRAKEN_API_SETTINGS

# Convert value to Decimal
def decimal_from_value(value):
    return Decimal(value)

def decimal_sum(value1, value2):
    return Decimal(value1) + Decimal(value2)

def generate_key():
    """
    Generates a key and save it into a file
    """
    key = Fernet.generate_key()
    with open("secret.key", "wb") as key_file:
        key_file.write(key)
        
def load_key():
    """
    Loads the key named `secret.key` from the current directory.
    """
    return open("secret.key", "rb").read()

def encrypt_message(message):
    """
    Encrypts a message
    """
    key = load_key()
    encoded_message = message.encode()
    f = Fernet(key)
    encrypted_message = f.encrypt(encoded_message)

    return encrypted_message
    
def decrypt_message(encrypted_message):
    """
    Decrypts an encrypted message
    """
    key = load_key()
    f = Fernet(key)
    decrypted_message = f.decrypt(encrypted_message)

    return decrypted_message.decode()

def get_kraken_api_key():
    
    encrypted_key = os.environ.get("KRAKEN_API_KEY")
    decrypted_key = decrypt_message(encrypted_key)
    
    return decrypted_key

def get_kraken_api_sec():
    
    encrypted_key = os.environ.get("KRAKEN_API_SECRET")
    decrypted_key = decrypt_message(encrypted_key)
    
    return decrypted_key

def write_key_to_file(key, file_name):
    
    with open(file_name, "wb") as key_file:
        key_file.write(key)
        
# Kraken Method
def get_kraken_signature(urlpath, data, secret):

    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()

    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()   

# Attaches auth headers and returns results of a POST request
def kraken_request(uri_path, data, api_key, api_sec):
    headers = {}
    headers['API-Key'] = api_key
    # get_kraken_signature() as defined in the 'Authentication' section
    headers['API-Sign'] = get_kraken_signature(uri_path, data, api_sec)             
    res = requests.post((KRAKEN_API_SETTINGS['base_url'] + uri_path), headers=headers, data=data)
    return res

# Returns results of a GET request
def kraken_public_request(uri_path):       
    req = requests.get((KRAKEN_API_SETTINGS['base_url'] + uri_path))
    return req

# Auxiliary function, from datetime to timestamp
def totimestamp(date):
    unix = datetime.strptime(date, "%Y-%m-%d").timetuple()
    unix_int = np.int32(time.mktime(unix))
    return unix_int

# Get stakable assets
def get_stakeable_assets():
    resp_stak_assets = kraken_request('/0/private/Earn/Strategies', {
            "nonce": str(int(1000*time.time()))
        }, get_kraken_api_key(), get_kraken_api_sec())
    return resp_stak_assets.json() 

# Create asset conversion matrix
def create_asset_conversion_matrix():
    stak_response_json = get_stakeable_assets()
    stakeable_asset_df = pd.DataFrame(stak_response_json["result"]["items"])
    stakeable_asset_df = stakeable_asset_df[["asset","id"]].set_index("id")
    return stakeable_asset_df

# Get stakable assets
def get_tradable_assets():
    resp_trad_assets = kraken_public_request('/0/public/AssetPairs')
    return resp_trad_assets.json() 

# Get OHLC data single pair
# since is the timestamp of the last data point we have (so it want be retrieved again)
# the service return the last field, which indicates the latest historical valid timestamp, that MUST be used to retrive the new samples
# it might happen that the service return also timestamp more recent than the last field, but they are not valid as the interval is not complete
# for this reason the function discards all the samples after the last field
def get_ohlc_data(pair, altname, interval=1440, since=None):
    if since is not None:
        resp_ohlc_data = kraken_public_request('/0/public/OHLC?pair=' + pair + '&interval=' + str(interval) + '&since=' + str(since))
    else:
        resp_ohlc_data = kraken_public_request('/0/public/OHLC?pair=' + pair + '&interval=' + str(interval))
    resp_ohlc_data_json = resp_ohlc_data.json()
    resp_ohlc_data_df = pd.DataFrame([])
    if len(resp_ohlc_data_json["error"]) == 0:
        resp_ohlc_data_df = pd.DataFrame(resp_ohlc_data_json["result"][altname], columns=["timestamp","open","high","low","close","vwap","volume","count"])
        resp_ohlc_data_df = resp_ohlc_data_df.set_index("timestamp")
        
        # Get the 'last' field from the API response
        last_valid_timestamp = resp_ohlc_data_json["result"]["last"]
        
        # Discard all samples after the last valid timestamp
        if not resp_ohlc_data_df.empty:
            resp_ohlc_data_df = resp_ohlc_data_df[resp_ohlc_data_df.index <= last_valid_timestamp]
            print(f"Discarded samples after timestamp {last_valid_timestamp} (kept {len(resp_ohlc_data_df)} valid samples)")
    else:
        print(resp_ohlc_data_json["error"])
    return resp_ohlc_data_df

# Create tradable asset matrix
def create_tradable_asset_matrix():
    trad_response_json = get_tradable_assets()
    tradable_asset_df = pd.DataFrame(trad_response_json["result"]).transpose()
    tradable_asset_df = tradable_asset_df[["base","quote","altname","wsname"]]
    tradable_asset_df = tradable_asset_df.reset_index()
    tradable_asset_df = tradable_asset_df.set_index(["base","quote"])
    return tradable_asset_df

# Get the transaction performed in Kraken in a specific time interval
def get_ledger(start_date, ofs, api_key, api_sec, without_count = "false"):
    start_timestamp = totimestamp(start_date)
    resp_ledger = kraken_request('/0/private/Ledgers', {
            "nonce": str(int(1000*time.time())),
            "start": start_timestamp,
            "ofs": ofs,
            "without_count": without_count
        }, api_key, api_sec)
    return resp_ledger.json() 

# Get all transaction performed in Kraken
def retrieve_all_ledger_data(start_date, api_key, api_sec):
    tx_batch_size = 50
    sleeping_time = 4 # After every call we should sleep 4s to refill entirely the call limit counter
    has_new_transactions = True
    ledger_df = pd.DataFrame([])
    consecutive_error_counter = 0
    iter_num = 0
    total_count = 0
    without_count = "false"     
    while has_new_transactions:
        response_json = get_ledger(start_date, iter_num*tx_batch_size, api_key, api_sec, without_count)
        # Get the total counter
        if without_count == "false":
            total_count = response_json["result"]["count"]
            without_count = "true"
        # Check if there were some errors
        if len(response_json["error"]) == 0:
            consecutive_error_counter = 0
            resp_ledger_json = response_json["result"]["ledger"]
            partial_ledger_df =  pd.DataFrame(resp_ledger_json).transpose()
            ledger_df = pd.concat([ledger_df, partial_ledger_df])
            has_new_transactions = (ledger_df.shape[0]) < total_count
            print("Call C-" + str(iter_num) + " performed")
            if has_new_transactions:
                print("\tNow Sleeping...")
                time.sleep(sleeping_time) 
            iter_num = iter_num + 1
        else:
            print("ERROR " + str(consecutive_error_counter))
            print(response_json["error"])
            has_new_transactions = consecutive_error_counter < 2
            consecutive_error_counter = consecutive_error_counter + 1
    # Add date column
    ledger_df["date"] = pd.to_datetime(ledger_df["time"], unit='s')
    return ledger_df  

# Get the current balance
def get_balance(api_key, api_sec, without_count = "false"):
    resp_ledger = kraken_request('/0/private/Balance', {
            "nonce": str(int(1000*time.time()))
        }, api_key, api_sec)
    return resp_ledger.json() 

# Get the current balance
def get_balance_dataframe(api_key, api_sec):
    response_json = get_balance(api_key, api_sec)
    if len(response_json["error"]) == 0:
        resp_balance_json = response_json["result"]
        balance_df =  pd.DataFrame.from_dict(resp_balance_json, orient='index', columns=["balance"])
    else:
        print(response_json["error"])
    return balance_df

def normalize_assets_name(df, asset_column_name, log_message=False):
    # Get all assets keys in the portfolio
    assets_in_portofolio = df[asset_column_name].unique()
    if log_message:
        print("All assets:")
        print(assets_in_portofolio)

    # Create a conversion matrix for the staked cryptos
    conv_matrix_df = create_asset_conversion_matrix()

    # Normalize the asset keys
    df["assetnorm"] = df[asset_column_name]
    for index, row in conv_matrix_df.iterrows():
        df.loc[(df[asset_column_name] == index), "assetnorm"] = row[asset_column_name]

    # Fix remaining asset name manually 
    df["assetnorm"] = df["assetnorm"].str.split('.').str[0]
    df["assetnorm"] = df["assetnorm"].str.split('21').str[0]
    df.loc[(df["assetnorm"]=="EUR"),["assetnorm"]] = "ZEUR"
    df.loc[(df["assetnorm"]=="XBT"),["assetnorm"]] = "XXBT"
    df.loc[(df["assetnorm"]=="ETH"),["assetnorm"]] = "XETH"

    # Normalized asset list
    assets_in_portofolio = df["assetnorm"].unique()
    if log_message:
        print("Normalized assets:")
        print(assets_in_portofolio)
    return df

# INPUT: Ledger with trades (without sells), and simulation_df
# OUTPUT: Ledger with remaining trades, dict with gains, initial purchase values, and final sale values
def get_ledger_after_tax_computation(input_ledger_df, input_quantity_to_sell_df):
    
    ledger_out_df = input_ledger_df.copy()
    ledger_out_df = ledger_out_df.reset_index()
    ledger_out_df["isvalid"] = True
    output_gains = {}
    output_initial_values = {}
    output_final_values = {}
    
    for asset, input_row in input_quantity_to_sell_df.iterrows():
        remaining_quantity_to_be_sold = input_row["quantity"]
        gain = Decimal(0)
        initial_purchase_value = Decimal(0)
        final_sale_value = Decimal(0)
        tax_year = input_row["datetime"].year
        
        # Initialize dictionaries
        if output_gains.get((tax_year,asset)) is None:
            output_gains[(tax_year,asset)] = Decimal(0)
            output_initial_values[(tax_year,asset)] = Decimal(0)
            output_final_values[(tax_year,asset)] = Decimal(0)
        
        # Compute gains with LIFO strategy
        if remaining_quantity_to_be_sold > 0:
            # Filter ledger to only include transactions before the sell datetime
            valid_ledger_df = ledger_out_df[
                (ledger_out_df["cryptocur"] == asset) & 
                (ledger_out_df["datetime"] < input_row["datetime"]) &
                (ledger_out_df["isvalid"])
            ].copy()
            
            # Sort by datetime descending to implement LIFO (most recent first)
            valid_ledger_df = valid_ledger_df.sort_values(by=['datetime'], ascending=False)
            
            for index, ledger_row in valid_ledger_df.iterrows():
                if remaining_quantity_to_be_sold > 0:
                    # Use the entire quantity of the row
                    if remaining_quantity_to_be_sold > ledger_row["quantity"]:
                        output_total = ledger_row["quantity"] * input_row["price"]
                        original_cost = ledger_row["total"]
                        gain = gain + output_total - original_cost
                        initial_purchase_value = initial_purchase_value + original_cost
                        final_sale_value = final_sale_value + output_total
                        remaining_quantity_to_be_sold = remaining_quantity_to_be_sold - ledger_row["quantity"]
                        ledger_out_df.at[index,"isvalid"] = False
                     # Update the quantity in the row
                    else:
                        remaining_quantity = ledger_row["quantity"] - remaining_quantity_to_be_sold
                        output_total = remaining_quantity_to_be_sold * input_row["price"]
                        original_cost = remaining_quantity_to_be_sold * ledger_row["price"]
                        gain = gain + output_total - original_cost
                        initial_purchase_value = initial_purchase_value + original_cost
                        final_sale_value = final_sale_value + output_total
                        # Update ledger quantity
                        ledger_out_df.at[index,"quantity"] = remaining_quantity
                        # Update ledger total
                        ledger_out_df.at[index,"total"] = ledger_row["total"] - original_cost
                        remaining_quantity_to_be_sold = 0
            # Remove rows already used
            ledger_out_df = ledger_out_df[ledger_out_df["isvalid"]].copy()
        
        # Save results
        output_gains[(tax_year,asset)] = output_gains[(tax_year,asset)] + gain
        output_initial_values[(tax_year,asset)] = output_initial_values[(tax_year,asset)] + initial_purchase_value
        output_final_values[(tax_year,asset)] = output_final_values[(tax_year,asset)] + final_sale_value
    
    # Output results
    ledger_out_df = ledger_out_df.copy()
    
    # Create DataFrame with all the information
    results_data = []
    for key in output_gains.keys():
        year, asset = key
        gain = output_gains[key]
        initial_value = output_initial_values[key]
        final_value = output_final_values[key]
        
        # Verify that the calculation is correct
        calculated_gain = final_value - initial_value
        if abs(gain - calculated_gain) > Decimal('0.01'):  # Allow for small rounding differences
            print(f"WARNING: Gain calculation mismatch for {asset} in {year}:")
            print(f"  Calculated gain: {calculated_gain}")
            print(f"  Accumulated gain: {gain}")
            print(f"  Final value: {final_value}")
            print(f"  Initial value: {initial_value}")
        
        results_data.append({
            'year': year,
            'asset': asset,
            'gain': gain,
            'initial_purchase_value': initial_value,
            'final_sale_value': final_value
        })
    
    gains_df = pd.DataFrame(results_data)
    
    return ledger_out_df, gains_df

# INPUT: Ledger with all trades
# OUTPUT: Ledger with remaining trades, dict with gains
def compute_taxes(input_ledger_df):
    
    input_ledger_sim_df = input_ledger_df.copy()
    
    # Get all the sell transactions
    input_quantity_already_sold_df = input_ledger_sim_df[input_ledger_sim_df["quantity"]<0].copy()
    input_quantity_already_sold_df["quantity"] = input_quantity_already_sold_df["quantity"] *-1
    input_quantity_already_sold_df = input_quantity_already_sold_df.set_index("cryptocur")
    input_quantity_already_sold_df.sort_values(by=['datetime'], ascending=True, inplace=True)
    input_quantity_already_sold_df = input_quantity_already_sold_df[["price","total","quantity","datetime"]]

    # Remove all the sell transactions from the ledger
    input_ledger_without_sells_df = input_ledger_sim_df[input_ledger_sim_df["quantity"]>=0].copy()
    input_ledger_without_sells_df["total"] = input_ledger_without_sells_df["total"]*-1
    
    # Get ledger and gains
    output_ledger_df, gains_by_year_df = get_ledger_after_tax_computation(input_ledger_without_sells_df, input_quantity_already_sold_df)
    
    return output_ledger_df, gains_by_year_df

def calculate_year_end_balances(ledger_df, OHLC_df, reference_asset="ZEUR", exception_assets=["KFEE","NFT"]):
    """
    Calculate the balance of each crypto at the end of each taxation year
    and their EUR countervalue using the market prices.
    """
    # Get unique years from the ledger data
    years = ledger_df['date'].dt.year.unique()
    years = sorted(years)
    
    print("\n" + "="*80)
    print("YEAR-END BALANCE SUMMARY")
    print("="*80)
    
    for year in years:
        print(f"\n--- {year} YEAR-END BALANCE (December 31, {year}) ---")
        
        # Filter ledger data up to the end of the year
        year_end_date = f"{year}-12-31"
        ledger_until_year_end = ledger_df[ledger_df['date'] <= year_end_date].copy()
        
        # Calculate running balance for each asset
        balance_by_asset = {}
        
        for _, row in ledger_until_year_end.iterrows():
            asset = row['assetnorm']
            amount = row['decimalamount']
            
            if asset not in balance_by_asset:
                balance_by_asset[asset] = Decimal(0)
            
            balance_by_asset[asset] += amount
        
        # Create summary table for this year
        year_summary = []
        year_total_value = Decimal(0)
        
        for asset, balance in balance_by_asset.items():
            if balance != 0 and asset not in exception_assets:
                # Get EUR price for this asset
                if asset == reference_asset:
                    eur_value = balance
                    price = Decimal(1)
                else:
                    # Try to get price for the year-end date
                    try:
                        year_end_datetime = pd.to_datetime(year_end_date)
                        # Look for price data for this asset and date
                        if not OHLC_df.empty and (year_end_datetime, asset) in OHLC_df.index:
                            price = decimal_from_value(OHLC_df.loc[(year_end_datetime, asset), 'price'])
                        else:
                            # Try to get the latest available price for this asset
                            asset_data = OHLC_df.xs(asset, level='crypto', drop_level=False) if not OHLC_df.empty else pd.DataFrame()
                            if not asset_data.empty:
                                # Get the latest price before or on the year-end date
                                available_dates = asset_data.index.get_level_values('date')
                                valid_dates = available_dates[available_dates <= year_end_datetime]
                                if len(valid_dates) > 0:
                                    latest_date = valid_dates.max()
                                    # If you do not have the price for the last day of the year, use the latest available price
                                    price_value = asset_data.loc[latest_date, 'price']
                                    if isinstance(price_value, pd.Series):
                                        price_value = price_value.iloc[0]  # Get the latest date available 
                                    price = decimal_from_value(price_value)
                                else:
                                    price = Decimal(0)
                                    print(f"  Warning: No price data found for {asset} before {year_end_date}")
                            else:
                                price = Decimal(0)
                                print(f"  Warning: No price data found for {asset}")
                        
                        eur_value = balance * price
                    except Exception as e:
                        price = Decimal(0)
                        eur_value = Decimal(0)
                        print(f"  Warning: Error getting price for {asset}: {e}")
                
                year_summary.append({
                    'Asset': asset,
                    'Balance': float(balance),
                    'Price (EUR)': float(price),
                    'Value (EUR)': float(eur_value)
                })
                
                year_total_value += eur_value
        
        # Sort by asset name (alphabetically)
        year_summary.sort(key=lambda x: x['Asset'], reverse=False)  # Sort alphabetically by asset name
        
        # Print year summary
        if year_summary:
            print(f"{'Asset':<15} {'Balance':<15} {'Price (EUR)':<12} {'Value (EUR)':<12}")
            print("-" * 60)
            
            for item in year_summary:
                print(f"{item['Asset']:<15} {item['Balance']:<15.8f} {item['Price (EUR)']:<12.4f} {item['Value (EUR)']:<12.2f}")
            
            print("-" * 60)
            print(f"{'TOTAL':<15} {'':<15} {'':<12} {float(year_total_value):<12.2f}")
        else:
            print("No assets with non-zero balance")
    
    return year_summary

def get_ohlc_data_with_persistence(assets_in_portfolio, reference_asset="ZEUR", exception_assets=["KFEE","NFT"], start_date="2021-01-01"):
    """
    Get OHLC data for multiple assets with persistence to parquet file.
    Queries the API day by day and merges with existing data.
    
    Returns:
        DataFrame with MultiIndex (date, crypto) and 'price' column
    """
    
    
    filename = "kraken_ohlc.parquet"
    tradable_asset_pair = create_tradable_asset_matrix()
    
    # Add MATIC/POL mapping
    new_row_data = {
        'altname': 'POLEUR',
        'index': 'POLEUR',
        'wsname': 'POL/EUR'
    }
    new_index = pd.MultiIndex.from_tuples([('MATIC', 'ZEUR')], names=['base', 'quote'])
    new_row_df = pd.DataFrame([new_row_data], index=new_index)
    tradable_asset_pair = pd.concat([tradable_asset_pair, new_row_df])
    
    # Load existing data
    existing_ohlc_df = pd.DataFrame()
    try:
        existing_ohlc_df = pd.read_parquet(filename, engine="fastparquet")
        print(f"\tLoaded existing OHLC data: {existing_ohlc_df.shape[0]} records")
    except FileNotFoundError:
        print("No existing OHLC data found, checking for historical CSV files...")
        
        # Check if kraken_historical_ohlc_data folder exists
        csv_folder = "kraken_historical_ohlc_data"
        if os.path.exists(csv_folder):
            print(f"Found historical data folder: {csv_folder}")
            
            # Collect historical data from CSV files
            historical_data = []
            
            for asset in assets_in_portfolio:
                if (asset not in exception_assets) and (asset != reference_asset):
                    try:
                        pair_name = tradable_asset_pair.loc[asset, reference_asset].loc["altname"]
                        
                        # Look for CSV file with 1440 minutes frequency
                        csv_filename = f"{csv_folder}/{pair_name}_1440.csv"
                        
                        if os.path.exists(csv_filename):
                            print(f"Loading historical data for {asset} from {csv_filename}")
                            
                            # Read CSV file without headers and with specific column names
                            csv_df = pd.read_csv(csv_filename, header=None, 
                                                names=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'trades'])
                            
                            # Convert timestamp to datetime and normalize to date
                            csv_df["date"] = pd.to_datetime(csv_df["timestamp"], unit='s').dt.normalize()
                            
                            # Convert close price to Decimal and create records
                            for _, row in csv_df.iterrows():
                                price = decimal_from_value(row["close"])
                                historical_data.append({
                                    'date': row["date"],
                                    'crypto': asset,
                                    'price': price,
                                    'timestamp': row["timestamp"]
                                })
                            
                            print(f"Loaded {len(csv_df)} historical records for {asset}")
                        else:
                            print(f"No historical CSV file found for {asset} ({csv_filename})")
                            
                    except Exception as e:
                        print(f"Error loading historical data for {asset}: {e}")
                        continue
            
            # Create DataFrame from historical data
            if historical_data:
                existing_ohlc_df = pd.DataFrame(historical_data)
                existing_ohlc_df = existing_ohlc_df.set_index(['date', 'crypto'])
                print(f"Created initial dataset with {len(historical_data)} historical records")
            else:
                print("No historical data found, starting fresh")
        else:
            print(f"Historical data folder {csv_folder} not found, starting fresh")
    
    # Collect new OHLC data
    new_ohlc_data = []
    
    for asset in assets_in_portfolio:
        if (asset not in exception_assets) and (asset != reference_asset):
            try:
                pair_name = tradable_asset_pair.loc[asset, reference_asset].loc["altname"]
                pair_altname = tradable_asset_pair.loc[asset, reference_asset].loc["index"]
                
                # Get the latest timestamp for this asset from existing data
                latest_timestamp = None
                if not existing_ohlc_df.empty:
                    asset_data = existing_ohlc_df.xs(asset, level='crypto', drop_level=False) if asset in existing_ohlc_df.index.get_level_values('crypto') else pd.DataFrame()
                    if not asset_data.empty and 'timestamp' in asset_data.columns:
                        latest_timestamp = asset_data['timestamp'].max()
                        print(f"Latest timestamp for {asset}: {latest_timestamp} ({datetime.fromtimestamp(latest_timestamp)})")
                
                # Check if we need to fetch new data (avoid calls for very recent timestamps)
                current_time = datetime.now().timestamp()
                min_interval_seconds = 1440 * 60 * 2 # 2 * 1440 minutes in seconds
                
                if latest_timestamp is not None and (current_time - latest_timestamp) < min_interval_seconds:
                    print(f"Skipping {asset} - latest data is too recent (less than 1440 minutes ago)")
                    continue
                
                print(f"Fetching data for {asset} ({pair_name})")
                
                # Get OHLC data with daily interval (1440 minutes) and latest timestamp
                ohlc_df = get_ohlc_data(pair_name, pair_altname, interval=1440, since=latest_timestamp)

                print(f"\tfetched {ohlc_df.shape[0]} rows")
                
                if not ohlc_df.empty:
                    # Reset index to get timestamp as column
                    ohlc_df = ohlc_df.reset_index()
                    ohlc_df["date"] = pd.to_datetime(ohlc_df["timestamp"], unit='s').dt.normalize()
                    
                    # Convert close price to Decimal and create records
                    for _, row in ohlc_df.iterrows():
                        price = decimal_from_value(row["close"])
                        new_ohlc_data.append({
                            'date': row["date"],
                            'crypto': asset,
                            'price': price,
                            'timestamp': row["timestamp"]
                        })
                
                # Sleep to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"Error fetching data for {asset}: {e}")
                continue
    
    # Create new DataFrame
    if new_ohlc_data:
        new_ohlc_df = pd.DataFrame(new_ohlc_data)
        new_ohlc_df = new_ohlc_df.set_index(['date', 'crypto'])
        print(f"Fetched {len(new_ohlc_data)} new OHLC records")
    else:
        new_ohlc_df = pd.DataFrame()
        print("No new OHLC data fetched")
    
    # Merge with existing data
    if not existing_ohlc_df.empty and not new_ohlc_df.empty:
        # Combine existing and new data
        combined_df = pd.concat([existing_ohlc_df, new_ohlc_df])
        # Remove duplicates (keep the newest instance)
        combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
        print(f"Combined data: {combined_df.shape[0]} records and deleted {existing_ohlc_df.shape[0] + new_ohlc_df.shape[0] - combined_df.shape[0]} duplicates")
    elif not existing_ohlc_df.empty:
        combined_df = existing_ohlc_df
    elif not new_ohlc_df.empty:
        combined_df = new_ohlc_df
    else:
        # Create empty DataFrame with proper structure
        combined_df = pd.DataFrame(columns=['price', 'timestamp'])
        combined_df.index = pd.MultiIndex.from_tuples([], names=['date', 'crypto'])
    
    # Save to parquet file (with timestamp included)
    if not combined_df.empty:
        combined_df.to_parquet(filename, engine="fastparquet", compression="GZIP")
        print(f"Saved OHLC data to {filename}")
    
    # # Check that the distance between every sample of the same asset is 1440 minutes
    # for asset in combined_df.index.get_level_values('crypto').unique():
    #     asset_data = combined_df.xs(asset, level='crypto')
    #     if not asset_data.empty:
    #         # Sort by timestamp before checking intervals
    #         asset_data = asset_data.sort_values('timestamp')
    #         # Get the difference between consecutive timestamps
    #         time_diffs = asset_data['timestamp'].diff().dropna()
    #         # Check if all differences are 1440 minutes (1440 * 60 seconds)
    #         if not (time_diffs == 1440 * 60).all():
    #             print(f"WARNING: {asset} has non-1440 minute intervals")
    #             # Print all samples with different intervals
    #             non_standard_intervals = time_diffs[time_diffs != 1440 * 60]
    #             for idx, interval in non_standard_intervals.items():
    #                 interval_minutes = interval / 60
    #                 print(f"  {asset}: timestamp {idx} has interval of {interval_minutes:.0f} minutes")

    print(f"Combined data: {combined_df.shape[0]} records")

    # Return only the price column for compatibility with existing code
    if not combined_df.empty:
        return combined_df[['price']]
    else:
        return combined_df

def calculate_taxes_with_franchigia(gain, year):
    """
    Calculate taxes considering the 2024 franchigia of 2000 EUR.
    Only gains/losses exceeding 2000 EUR in absolute value are taxable.
    """
    gain_abs = abs(gain)
    if gain_abs <= 2000:
        # If absolute gain/loss is 2000 EUR or less, no taxes
        return Decimal(0)
    else:
        # If absolute gain/loss exceeds 2000 EUR, tax only the excess
        if gain > 0:
            # Positive gain: tax the amount exceeding 2000 EUR
            taxable_amount = gain - 2000
        else:
            # Negative gain (loss): tax the amount exceeding 2000 EUR (but this would be negative)
            taxable_amount = gain + 2000
        
        return taxable_amount * Decimal(0.26)

if __name__ == "__main__":
    # Call the get_ohlc_data_with_persistence function with the assets in the portfolio
    assets_in_portfolio = ['POL', 'XETH', 'SOL', 'KSM', 'DOT', 'ATOM', 'ADA', 'XXBT', 'MATIC',
       'XXRP', 'AAVE', 'ENA', 'UNI', 'EOS', 'LUNA', 'ALGO', 'ETHW', 'LUNA2',
       '1INCH', 'UST']
    get_ohlc_data_with_persistence(assets_in_portfolio)
