#!/usr/bin/env python3
"""
Test script to verify automatic secret key generation
"""

import requests
import json
import os

BASE_URL = "http://localhost:5000"

def test_secret_key_generation():
    """Test that secret.key is automatically generated when storing credentials"""
    print("Testing automatic secret key generation...")
    
    # Check if secret.key exists before test
    if os.path.exists('secret.key'):
        print("✓ secret.key already exists")
    else:
        print("✗ secret.key does not exist (this is expected for first run)")
    
    # Test with invalid credentials to trigger the secret key generation
    data = {
        "api_key": "test_key_for_generation",
        "api_secret": "test_secret_for_generation"
    }
    
    print("\nSending API credentials to trigger secret key generation...")
    response = requests.post(f"{BASE_URL}/api/setup-credentials", json=data)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Check if secret.key was created
    if os.path.exists('secret.key'):
        print("\n✓ secret.key was successfully generated!")
        print(f"File size: {os.path.getsize('secret.key')} bytes")
    else:
        print("\n✗ secret.key was not generated")
    
    print()

def test_credentials_status():
    """Test the credentials status endpoint"""
    print("Testing credentials status...")
    response = requests.get(f"{BASE_URL}/api/check-credentials")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_health():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("Automatic Secret Key Generation Test")
    print("=" * 60)
    
    test_health()
    test_credentials_status()
    test_secret_key_generation()
    
    print("=" * 60)
    print("Test completed!")
    print("=" * 60) 