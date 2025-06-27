#!/usr/bin/env python3
"""
Setup script for encrypting Kraken API credentials
This script helps users generate encryption keys and encrypt their API credentials.
"""

import os
from kraken import generate_key, encrypt_message

def main():
    print("🔐 Kraken API Credential Encryption Setup")
    print("=" * 50)
    
    # Check if secret key already exists
    if os.path.exists("secret.key"):
        print("⚠️  Secret key already exists!")
        response = input("Do you want to generate a new key? This will invalidate existing encrypted credentials. (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            return
    
    # Generate encryption key
    print("\n1. Generating encryption key...")
    try:
        generate_key()
        print("✅ Encryption key generated successfully!")
    except Exception as e:
        print(f"❌ Error generating key: {e}")
        return
    
    # Get API credentials from user
    print("\n2. Enter your Kraken API credentials:")
    print("   (Get these from: https://www.kraken.com/u/settings/api)")
    
    api_key = input("Enter your Kraken API Key: ").strip()
    api_secret = input("Enter your Kraken API Secret: ").strip()
    
    if not api_key or not api_secret:
        print("❌ API credentials cannot be empty!")
        return
    
    # Encrypt credentials
    print("\n3. Encrypting credentials...")
    try:
        encrypted_key = encrypt_message(api_key)
        encrypted_secret = encrypt_message(api_secret)
        print("✅ Credentials encrypted successfully!")
    except Exception as e:
        print(f"❌ Error encrypting credentials: {e}")
        return
    
    # Display results
    print("\n4. Add these encrypted values to your .env file:")
    print("-" * 50)
    print(f"KRAKEN_API_KEY={encrypted_key}")
    print(f"KRAKEN_API_SECRET={encrypted_secret}")
    print("-" * 50)
    
    # Create .env file if it doesn't exist
    if not os.path.exists(".env"):
        print("\n5. Creating .env file...")
        try:
            with open(".env", "w") as f:
                f.write(f"KRAKEN_API_KEY={encrypted_key}\n")
                f.write(f"KRAKEN_API_SECRET={encrypted_secret}\n")
            print("✅ .env file created with encrypted credentials!")
        except Exception as e:
            print(f"❌ Error creating .env file: {e}")
            print("Please manually create the .env file with the encrypted values above.")
    else:
        print("\n5. .env file already exists.")
        print("Please manually update it with the encrypted values above.")
    
    print("\n🎉 Setup complete!")
    print("\nImportant security notes:")
    print("- Keep your secret.key file secure and never share it")
    print("- Add secret.key to your .gitignore file")
    print("- The encrypted credentials in .env are safe to commit")
    print("- You can now run the application with: python app.py")

if __name__ == "__main__":
    main() 