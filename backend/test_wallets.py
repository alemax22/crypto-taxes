#!/usr/bin/env python3
"""
Test script for the wallets module
This can be run directly to test the wallet functionality
"""

import sys
import os
import logging

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wallets.portfolio import Portfolio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test the Portfolio class."""
    
    print("=== Testing Portfolio Module ===")
    
    try:
        # Initialize portfolio
        print("Initializing portfolio...")
        portfolio = Portfolio()
        print(f"✓ Portfolio initialized successfully")
        
        # Show initial state
        wallets = portfolio.list_wallets()
        print(f"✓ Found {len(wallets)} existing wallets")
        
        # Test adding a wallet (with dummy credentials)
        print("\nTesting wallet addition...")
        wallet_id = portfolio.add_wallet(
            wallet_type="Kraken",
            name="Test Kraken Account",
            api_key="test_api_key_12345",
            api_secret="test_api_secret_67890",
            description="Test account for demonstration",
            notes="This is a test wallet"
        )
        
        if wallet_id:
            print(f"✓ Successfully added test wallet with ID: {wallet_id}")
            
            # List wallets again
            wallets = portfolio.list_wallets()
            print(f"✓ Now have {len(wallets)} wallets")
            
            # Test loading the wallet
            print("\nTesting wallet loading...")
            wallet_instance = portfolio.load_wallet(wallet_id)
            if wallet_instance:
                print(f"✓ Successfully loaded wallet: {wallet_instance.name}")
                print(f"✓ Wallet type: {type(wallet_instance).__name__}")
            else:
                print("✗ Failed to load wallet instance")
            
            # Test portfolio summary
            print("\nTesting portfolio summary...")
            summary = portfolio.get_wallet_summary()
            print(f"✓ Portfolio summary: {summary}")
            
            # Clean up - remove test wallet
            print("\nCleaning up test wallet...")
            if portfolio.remove_wallet(wallet_id):
                print(f"✓ Successfully removed test wallet")
            else:
                print("✗ Failed to remove test wallet")
                
        else:
            print("✗ Failed to add test wallet")
            
    except Exception as e:
        print(f"✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 