import time
import requests
from cryptography.fernet import Fernet
import urllib.parse
import hashlib
import hmac
import base64
import pandas as pd
import numpy as np
from datetime import datetime
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
def get_ohlc_data(pair, altname, interval=21600):
    resp_ohlc_data = kraken_public_request('/0/public/OHLC?pair=' + pair + '&interval=' + str(interval))
    resp_ohlc_data_json = resp_ohlc_data.json()
    resp_ohlc_data_df = pd.DataFrame([])
    if len(resp_ohlc_data_json["error"]) == 0:
        resp_ohlc_data_df = pd.DataFrame(resp_ohlc_data_json["result"][altname], columns=["timestamp","open","high","low","close","vwap","volume","count"])
        resp_ohlc_data_df = resp_ohlc_data_df.set_index("timestamp")
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
# OUTPUT: Ledger with remaining trades, dict with gains
def get_ledger_after_tax_computation(input_ledger_df, input_quantity_to_sell_df):
    
    ledger_out_df = input_ledger_df.copy()
    ledger_out_df = ledger_out_df.reset_index()
    ledger_out_df["isvalid"] = True
    output_gains = {}
    for asset, input_row in input_quantity_to_sell_df.iterrows():
        remaining_quantity_to_be_sold = input_row["quantity"]
        gain = Decimal(0)
        tax_year = input_row["datetime"].year
        # Initialize dictionary
        if output_gains.get((tax_year,asset)) is None:
            output_gains[(tax_year,asset)] = Decimal(0)
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
                        remaining_quantity_to_be_sold = remaining_quantity_to_be_sold - ledger_row["quantity"]
                        ledger_out_df.at[index,"isvalid"] = False
                     # Update the quantity in the row
                    else:
                        remaining_quantity = ledger_row["quantity"] - remaining_quantity_to_be_sold
                        output_total = remaining_quantity_to_be_sold * input_row["price"]
                        original_cost = remaining_quantity_to_be_sold * ledger_row["price"]
                        gain = gain + output_total - original_cost
                        # Update ledger quantity
                        ledger_out_df.at[index,"quantity"] = remaining_quantity
                        # Update ledger total
                        ledger_out_df.at[index,"total"] = ledger_row["total"] - original_cost
                        remaining_quantity_to_be_sold = 0
            # Remove rows already used
            ledger_out_df = ledger_out_df[ledger_out_df["isvalid"]].copy()
        # Save results
        output_gains[(tax_year,asset)] = output_gains[(tax_year,asset)] + gain
    
    # Output results
    ledger_out_df = ledger_out_df.copy()
    gains_df=pd.DataFrame.from_dict(output_gains, orient='index', columns=["gain"])
    gains_df.index = pd.MultiIndex.from_tuples(gains_df.index, names=['year', 'asset'])
    gains_df.reset_index(inplace=True)
    
    return ledger_out_df, gains_df

# INPUT: Ledger with all trades, and df with assets to be sold (if not passed we return the taxes for the trades already done)
# OUTPUT: Ledger with remaining trades, dict with gains
def simulate_taxes(input_ledger_df, input_quantity_to_sell_df=None):
    
    input_ledger_sim_df = input_ledger_df.copy()
    
    # Insert simulated buys into the ledger
    if input_quantity_to_sell_df is not None:
        # Prepare it to be added into the ledger 
        simulated_ledger_df = input_quantity_to_sell_df[input_quantity_to_sell_df["quantity"]>0].copy()
        simulated_ledger_df = simulated_ledger_df.reset_index(names=['cryptocur'])
        simulated_ledger_df["quantity"] = simulated_ledger_df["quantity"]*-1
        simulated_ledger_df["date"] = simulated_ledger_df['datetime'].dt.normalize()
        simulated_ledger_df["refid"] = "SIM-" + simulated_ledger_df.index.to_series().apply(lambda x: f"{x:010}")
        simulated_ledger_df = simulated_ledger_df.set_index("refid")
        
        # Pre-append them to the ledger
        input_ledger_sim_df = pd.concat([simulated_ledger_df, input_ledger_sim_df], ignore_index=False)
        input_ledger_sim_df.sort_values(by=['datetime'], ascending=False, inplace=True)
    
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