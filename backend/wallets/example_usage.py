#!/usr/bin/env python3
"""
Example usage of the Portfolio and Wallet classes
"""

import logging
from .portfolio import Portfolio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Example usage of the Portfolio class."""
    
    # Initialize portfolio
    print("=== Initializing Portfolio ===")
    portfolio = Portfolio()
    
    # Show initial state
    print(f"Initial wallet count: {len(portfolio.list_wallets())}")
    
    # Add a Kraken wallet
    print("\n=== Adding Kraken Wallet ===")
    wallet_id = portfolio.add_wallet(
        wallet_type="Kraken",
        name="My Kraken Account",
        api_key="your_kraken_api_key_here",
        api_secret="your_kraken_api_secret_here",
        description="Main trading account",
        notes="Used for daily trading"
    )
    
    if wallet_id:
        print(f"Successfully added wallet with ID: {wallet_id}")
    else:
        print("Failed to add wallet")
        return
    
    # List all wallets (API keys will be hidden)
    print("\n=== Listing All Wallets ===")
    wallets = portfolio.list_wallets()
    for wallet in wallets:
        print(f"ID: {wallet['wallet_id']}")
        print(f"Name: {wallet['name']}")
        print(f"Type: {wallet['wallet_type']}")
        print(f"Active: {wallet['is_active']}")
        print(f"Created: {wallet['created_date']}")
        print("---")
    
    # Load and use a specific wallet
    print("\n=== Loading Wallet Instance ===")
    wallet_instance = portfolio.load_wallet(wallet_id)
    if wallet_instance:
        print(f"Loaded wallet: {wallet_instance.name}")
        print(f"Wallet type: {type(wallet_instance).__name__}")
        
        # Test authentication (this will use the decrypted credentials)
        print("\n=== Testing Authentication ===")
        auth_result = wallet_instance.authenticate()
        print(f"Authentication successful: {auth_result}")
        
        # Get balance (this will use the decrypted credentials)
        print("\n=== Getting Balance ===")
        try:
            balance = wallet_instance.get_balance()
            print(f"Balance: {balance}")
        except Exception as e:
            print(f"Error getting balance: {e}")
    else:
        print("Failed to load wallet instance")
    
    # Update wallet
    print("\n=== Updating Wallet ===")
    success = portfolio.update_wallet(
        wallet_id,
        description="Updated description",
        notes="Updated notes"
    )
    print(f"Update successful: {success}")
    
    # Get active wallets
    print("\n=== Active Wallets ===")
    active_wallets = portfolio.get_active_wallets()
    print(f"Active wallets: {len(active_wallets)}")
    
    # Get portfolio summary
    print("\n=== Portfolio Summary ===")
    summary = portfolio.get_wallet_summary()
    print(f"Total wallets: {summary['total_wallets']}")
    print(f"Active wallets: {summary['active_wallets']}")
    print(f"Inactive wallets: {summary['inactive_wallets']}")
    print(f"Wallet types: {summary['wallet_types']}")
    
    # Export wallets (without sensitive data)
    print("\n=== Exporting Wallets ===")
    export_success = portfolio.export_wallets("wallets_export.json")
    print(f"Export successful: {export_success}")
    
    # Backup encryption key
    print("\n=== Backing Up Encryption Key ===")
    backup_success = portfolio.backup_encryption_key("portfolio_key_backup.key")
    print(f"Backup successful: {backup_success}")
    
    # Demonstrate encryption/decryption cycle
    print("\n=== Encryption/Decryption Demo ===")
    print("Note: API keys are automatically encrypted when saved to CSV")
    print("and decrypted when loaded into memory for use.")
    print("The encryption key is stored separately for security.")
    
    # Show that credentials are decrypted in memory
    wallet_config = portfolio.get_wallet_by_id(wallet_id)
    if wallet_config:
        print(f"API key in memory (first 10 chars): {wallet_config['api_key'][:10]}...")
        print(f"API secret in memory (first 10 chars): {wallet_config['api_secret'][:10]}...")
    
    # Remove wallet (optional - uncomment to test)
    # print("\n=== Removing Wallet ===")
    # remove_success = portfolio.remove_wallet(wallet_id)
    # print(f"Remove successful: {remove_success}")

if __name__ == "__main__":
    main() 