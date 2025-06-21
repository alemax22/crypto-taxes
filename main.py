#!/usr/bin/env python3
"""
Italian Crypto Tax Calculator for 2025
This script connects to Kraken API, downloads user transactions,
and computes Italian crypto taxes according to 2025 regulations.
"""

from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

import kraken
from decimal import Decimal


def main():

    load_dotenv()

    reference_asset = "ZEUR"
    exception_assets = ["KFEE","NFT"]
    api_key = kraken.get_kraken_api_key()
    api_sec = kraken.get_kraken_api_sec()
    start_date = "2021-01-01"
    response = kraken.get_ledger(start_date, 0, api_key, api_sec)
    print("Total number of transactions: " + str(response["result"]["count"]))
    # Get all ledger data
    # Retrive the local copy of the data
    start_timestamp = datetime.strptime(start_date, "%Y-%m-%d")
    filename = "kraken_ledger.parquet"
    ledger_df = pd.DataFrame([])
    # Read data from file
    try:
        ledger_df = pd.read_parquet(filename, engine="fastparquet")
        # Update startdate based on the data retrieved from the file
        if ledger_df.shape[0] > 0:
            ledger_df = ledger_df[ledger_df["date"] > start_date]
            # Update start date to retrieve data from the
            start_timestamp = ledger_df.iloc[0].loc["date"]
            start_date = str(start_timestamp)[:10]
    except FileNotFoundError:
        print("No file found")

    ledger_df_delta = kraken.retrieve_all_ledger_data(start_date, api_key, api_sec)
    # Remove duplicated data
    ledger_df_delta = ledger_df_delta.loc[ledger_df_delta["date"] > start_timestamp]
    
    # Ensure both DataFrames have the same structure before concatenation
    if ledger_df.empty:
        # If ledger_df is empty, just use ledger_df_delta
        ledger_df = ledger_df_delta
    elif ledger_df_delta.empty:
        # If ledger_df_delta is empty, keep ledger_df as is
        pass
    else:
        # Both have data, ensure they have the same columns and dtypes
        # Get the union of all columns
        all_columns = list(set(ledger_df.columns) | set(ledger_df_delta.columns))
        
        # Ensure both DataFrames have all columns with consistent dtypes
        for col in all_columns:
            if col not in ledger_df.columns:
                ledger_df[col] = None
            if col not in ledger_df_delta.columns:
                ledger_df_delta[col] = None
        
        # Reorder columns to match
        ledger_df = ledger_df[all_columns]
        ledger_df_delta = ledger_df_delta[all_columns]
        
        # Concat data
        ledger_df = pd.concat([ledger_df_delta, ledger_df], ignore_index=False)
    # Write back to file
    ledger_df.to_parquet(filename, engine="fastparquet", compression="GZIP")
    # Create columns with decimal value
    ledger_df["decimalamount"] = ledger_df.apply(lambda row: kraken.decimal_from_value(row["amount"]), axis=1)
    ledger_df["decimalbalance"] = ledger_df.apply(lambda row: kraken.decimal_from_value(row["balance"]), axis=1)
    ledger_df["decimalfee"] = ledger_df.apply(lambda row: kraken.decimal_from_value(row["fee"]), axis=1)
    ledger_df["justdate"] = ledger_df['date'].dt.normalize()
    ledger_df.dtypes
    ledger_df = kraken.normalize_assets_name(ledger_df, "asset", True)
    assets_in_portofolio = ledger_df["assetnorm"].unique()
    operation_types = ledger_df["type"].unique()
    print(operation_types)
    # Trades - approximate all plus and minus (Staking and Credit Card buys are left behind)
    ledger_df_trade = ledger_df[ledger_df["assetnorm"]!="KFEE"]
    ledger_df_trade = ledger_df_trade[(ledger_df_trade["type"]=="spend")|(ledger_df_trade["type"]=="receive")|(ledger_df_trade["type"]=="trade")].set_index("refid")
    ledger_df_from = ledger_df_trade[ledger_df_trade["decimalamount"] < 0]
    ledger_df_to = ledger_df_trade[ledger_df_trade["decimalamount"] >= 0]
    ledger_df_trade = ledger_df_from.join(ledger_df_to, how="left", lsuffix="_from", rsuffix="_to")
    ledger_df_trade = ledger_df_trade.sort_values(by=['date_from'], ascending=False)

    # Check consistency
    if ledger_df_trade.index.duplicated().any():
        print("There are duplicate indexes:")
        print(ledger_df_trade[ledger_df_trade.index.duplicated()])
    else:
        print("No duplicate indexes.")

    # Reformat the dataframe by keeping only the relevant columns
    ledger_df_trade = ledger_df_trade[["date_to","decimalamount_from","decimalamount_to","assetnorm_from","assetnorm_to", "justdate_to"]]
    # Rearrage the DF in such a way to have a column with all the crypto and one with only their value in ZEUR
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
    print(ledger_df_trade_final.shape)

    ## UPDATE CURRENT PRICE OF CRYPTOS
    # Compute for each crypto the quantity to be sold
    tradable_asset_pair = kraken.create_tradable_asset_matrix()
    # MATIC was replaced with POL - Create the new row data
    new_row_data = {
        'altname': 'POLEUR',
        'index': 'POLEUR',
        'wsname': 'POL/EUR'
    }
    new_index = pd.MultiIndex.from_tuples([('MATIC', 'ZEUR')], names=['base', 'quote'])
    new_row_df = pd.DataFrame([new_row_data], index=new_index)
    tradable_asset_pair = pd.concat([tradable_asset_pair, new_row_df])
    OHLC_df = pd.DataFrame([])
    metric = "close"
    interval = 1
    for asset in assets_in_portofolio:
        if (asset not in exception_assets) and (asset != reference_asset):
            # print("Downloading data for asset pair: "+asset + " / " + reference_asset)
            pair_name = tradable_asset_pair.loc[asset,reference_asset].loc["altname"]
            pair_altname = tradable_asset_pair.loc[asset,reference_asset].loc["index"]
            # Retrieve OHLC data
            print("pair_name",pair_name,"pair_altname",pair_altname)
            OHLC_df_current = kraken.get_ohlc_data(pair_name, pair_altname, interval)
            # Reformat data
            OHLC_df_current = OHLC_df_current.reset_index()
            OHLC_df_current["date"] = pd.to_datetime(OHLC_df_current["timestamp"], unit='s')
            # Convert to Decimal
            OHLC_df_current[metric] = OHLC_df_current.apply(lambda row: kraken.decimal_from_value(row[metric]), axis=1)
            OHLC_df_current = pd.DataFrame(OHLC_df_current[metric])
            OHLC_df_current = OHLC_df_current.rename(columns={metric: asset})
            OHLC_df_current = OHLC_df_current.transpose()
            OHLC_df = pd.concat([OHLC_df, OHLC_df_current])

    OHLC_df = OHLC_df.iloc[:,-1:]
    # Rename column without knowing its name
    OHLC_df.rename(columns = {list(OHLC_df)[0]: 'price'}, inplace = True)

    ## SELLING STRATEGY AUTOMATIC
    balance_df = kraken.get_balance_dataframe(api_key, api_sec)
    balance_df = balance_df.reset_index(names=['asset'])
    balance_df = kraken.normalize_assets_name(balance_df, "asset")
    balance_df["balance"] = balance_df.apply(lambda row: kraken.decimal_from_value(row["balance"]), axis=1)
    balance_df = balance_df[["balance","assetnorm"]]
    balance_df = balance_df.groupby(['assetnorm']).sum()

    ledger_out_df3, gains_final_df = kraken.simulate_taxes(ledger_df_trade_final, None)
    gains_final_df = gains_final_df.groupby(['year','asset']).sum()

    gains_final_df = gains_final_df.groupby(['year']).sum()

    #Taxes
    gains_final_df["taxes"] = (gains_final_df["gain"])*Decimal(0.26)
    print(gains_final_df.head(20))

if __name__ == "__main__":
    main() 