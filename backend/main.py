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
    filename = "../kraken_ledger.parquet"
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
    # Get OHLC data with persistence - this will load existing data and fetch new data as needed
    print("\nFetching OHLC data with persistence...")
    OHLC_df = kraken.get_ohlc_data_with_persistence(
        assets_in_portfolio=assets_in_portofolio,
        reference_asset=reference_asset,
        exception_assets=exception_assets,
        start_date=start_date
    )
    
    print(f"OHLC data shape: {OHLC_df.shape}")
    if not OHLC_df.empty:
        print(f"Date range: {OHLC_df.index.get_level_values('date').min()} to {OHLC_df.index.get_level_values('date').max()}")
        print(f"Assets: {OHLC_df.index.get_level_values('crypto').unique()}")

    ## SELLING STRATEGY AUTOMATIC
    balance_df = kraken.get_balance_dataframe(api_key, api_sec)
    balance_df = balance_df.reset_index(names=['asset'])
    balance_df = kraken.normalize_assets_name(balance_df, "asset")
    balance_df["balance"] = balance_df.apply(lambda row: kraken.decimal_from_value(row["balance"]), axis=1)
    balance_df = balance_df[["balance","assetnorm"]]
    balance_df = balance_df.groupby(['assetnorm']).sum()

    print("Balance assets:")
    print(balance_df.index.unique())

    # Calculate year-end balances before simulating taxes
    kraken.calculate_year_end_balances(ledger_df, OHLC_df, reference_asset, exception_assets)

    ledger_out_df3, gains_final_df = kraken.compute_taxes(ledger_df_trade_final)
    
    # Display detailed gains information with initial and final values
    print("\n" + "="*100)
    print("DETAILED GAINS ANALYSIS")
    print("="*100)
    
    if not gains_final_df.empty:
        print(f"{'Year':<6} {'Asset':<10} {'Initial Value (EUR)':<20} {'Final Value (EUR)':<20} {'Gain/Loss (EUR)':<20} {'Verification':<15}")
        print("-" * 100)
        
        for _, row in gains_final_df.iterrows():
            year = row['year']
            asset = row['asset']
            initial_value = row['initial_purchase_value']
            final_value = row['final_sale_value']
            gain = row['gain']
            
            # Verify the calculation
            calculated_gain = final_value - initial_value
            verification = "✓ OK" if abs(gain - calculated_gain) < Decimal('0.01') else "✗ ERROR"
            
            print(f"{year:<6} {asset:<10} {float(initial_value):<20.2f} {float(final_value):<20.2f} {float(gain):<20.2f} {verification:<15}")
    
    # Group by year and asset for tax calculation
    gains_by_year_asset = gains_final_df.groupby(['year','asset']).sum()
    
    # Group by year only for final tax summary
    gains_by_year = gains_final_df.groupby(['year']).sum()

    #Taxes with 2024 franchigia (deductible threshold)
    # Apply franchigia for 2024, normal tax calculation for other years
    gains_by_year["taxes"] = gains_by_year.apply(
        lambda row: kraken.calculate_taxes_with_franchigia(row["gain"], row.name) if row.name == 2024 
        else row["gain"] * Decimal(0.26), 
        axis=1
    )
    
    print("\n" + "="*80)
    print("TAX SUMMARY BY YEAR")
    print("="*80)
    print("Tax calculation with 2024 franchigia (2000 EUR deductible threshold):")
    
    # Reset index to make year a column and remove the aggregated asset column
    gains_by_year_display = gains_by_year.reset_index()
    gains_by_year_display = gains_by_year_display.drop(columns=['asset'], errors='ignore')
    
    # Format all numeric columns to 2 decimal places
    for col in gains_by_year_display.columns:
        if col != 'year' and gains_by_year_display[col].dtype in ['float64', 'object']:
            gains_by_year_display[col] = gains_by_year_display[col].apply(
                lambda x: f"{float(x):.2f}" if pd.notna(x) else "0.00"
            )
    
    # Set pandas display options to show all columns
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    
    print(gains_by_year_display.to_string(index=False))

if __name__ == "__main__":
    main() 