# Testing Guide for Crypto-Taxes Backend

This guide explains how to run unit tests for the crypto-taxes backend, with a focus on testing the `KrakenWallet` class.

## Overview

The testing strategy uses **mocking** to isolate the code under test from external dependencies like:
- Kraken API calls
- File system operations
- Cryptography operations
- Time-based operations

## Test Structure

### Test Files
- `test_wallet_kraken.py` - Unit tests for KrakenWallet class
- `test_wallets.py` - Integration tests for Portfolio class
- `pytest.ini` - Pytest configuration
- `run_tests.py` - Test runner script

### Test Categories
- **Unit Tests**: Test individual methods in isolation
- **Integration Tests**: Test component interactions
- **API Tests**: Tests that require API mocking
- **Slow Tests**: Tests that take longer to run

## Installation

### Install Testing Dependencies

```bash
# Install testing dependencies
pip install -r test_requirements.txt

# Or install individually
pip install pytest pytest-cov pytest-mock coverage
```

## Running Tests

### Using the Test Runner Script

```bash
# Run all tests with coverage
python run_tests.py

# Run only unit tests
python run_tests.py --type unit

# Run only integration tests
python run_tests.py --type integration

# Run tests without coverage
python run_tests.py --no-coverage

# Run tests in quiet mode
python run_tests.py --quiet
```

### Using Pytest Directly

```bash
# Run all tests
pytest

# Run specific test file
pytest test_wallet_kraken.py

# Run specific test class
pytest test_wallet_kraken.py::TestKrakenWallet

# Run specific test method
pytest test_wallet_kraken.py::TestKrakenWallet::test_authenticate_success

# Run with coverage
pytest --cov=wallets --cov-report=term-missing

# Run with markers
pytest -m unit
pytest -m integration
pytest -m api
```

### Using Python unittest

```bash
# Run all tests
python -m unittest discover

# Run specific test file
python -m unittest test_wallet_kraken

# Run specific test class
python -m unittest test_wallet_kraken.TestKrakenWallet

# Run specific test method
python -m unittest test_wallet_kraken.TestKrakenWallet.test_authenticate_success
```

## Mocking Strategy

### 1. API Calls Mocking

The tests mock HTTP requests to avoid making real API calls:

```python
@patch('wallets.wallet_kraken.requests.post')
def test_authenticate_success(self, mock_post):
    # Mock successful API response
    mock_response = Mock()
    mock_response.json.return_value = {
        'error': [],
        'result': {
            'ledger': {'test_ref_id': {...}},
            'count': 1
        }
    }
    mock_post.return_value = mock_response
    
    # Test authentication
    result = self.wallet.authenticate()
    
    # Verify results
    self.assertTrue(result)
    self.assertTrue(self.wallet.is_authenticated)
```

### 2. File System Mocking

File operations are mocked to avoid creating real files:

```python
@patch('wallets.wallet_kraken.pd.read_parquet')
def test_get_transactions_success(self, mock_read_parquet):
    # Mock existing ledger data
    mock_ledger_data = pd.DataFrame({...})
    mock_read_parquet.return_value = mock_ledger_data
    
    # Test transaction retrieval
    transactions_df = self.wallet.get_transactions()
    
    # Verify results
    self.assertIsInstance(transactions_df, pd.DataFrame)
```

### 3. Cryptography Mocking

Encryption/decryption operations are mocked:

```python
@patch('wallets.wallet_kraken.Fernet')
def test_decrypt_message(self, mock_fernet):
    # Mock Fernet
    mock_fernet_instance = Mock()
    mock_fernet_instance.decrypt.return_value = b'decrypted_message'
    mock_fernet.return_value = mock_fernet_instance
    
    # Test decryption
    result = self.wallet._decrypt_message('encrypted_message')
    self.assertEqual(result, 'decrypted_message')
```

## Test Coverage

The tests aim to cover:

### Core Functionality
- ✅ Wallet initialization
- ✅ Authentication (success/failure cases)
- ✅ Balance retrieval
- ✅ Transaction retrieval
- ✅ Data synchronization
- ✅ Credential management

### Edge Cases
- ✅ Missing credentials
- ✅ API errors
- ✅ Network failures
- ✅ Invalid data formats
- ✅ File system errors

### Helper Methods
- ✅ Decimal conversions
- ✅ Asset name normalization
- ✅ Timestamp conversions
- ✅ Directory creation

## Test Data

### Mock API Responses

The tests use realistic mock responses that match the actual Kraken API format:

```python
# Balance response
{
    'error': [],
    'result': {
        'XXBT': '1.5',
        'XETH': '10.0',
        'ZEUR': '5000.0'
    }
}

# Ledger response
{
    'error': [],
    'result': {
        'ledger': {
            'ref1': {
                'refid': 'ref1',
                'time': 1640995200,
                'type': 'trade',
                'asset': 'XXBT',
                'amount': '0.1',
                'fee': '0.0001',
                'balance': '1.0'
            }
        },
        'count': 1
    }
}
```

### Test Credentials

Tests use dummy credentials that are clearly marked as test data:

```python
self.test_api_key = "test_api_key_12345"
self.test_api_secret = "test_api_secret_67890"
```

## Best Practices

### 1. Isolation
- Each test is independent
- Tests don't rely on external services
- Tests clean up after themselves

### 2. Realistic Mocking
- Mock responses match real API format
- Error conditions are properly tested
- Edge cases are covered

### 3. Clear Test Names
- Test names describe what is being tested
- Test names indicate expected outcome
- Test names include the scenario being tested

### 4. Comprehensive Assertions
- Tests verify both return values and side effects
- Tests check that API calls are made correctly
- Tests verify error handling

## Continuous Integration

### GitHub Actions (Recommended)

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r test_requirements.txt
    
    - name: Run tests
      run: |
        python run_tests.py --type all
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Local Development

For local development, run tests frequently:

```bash
# Quick test run
python run_tests.py --type unit --quiet

# Full test run before committing
python run_tests.py --type all

# Check coverage
python run_tests.py --type all
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running tests from the `backend` directory
2. **Mock Issues**: Check that mock paths match the actual import paths
3. **File Permission Errors**: Tests use temporary directories that should be cleaned up automatically
4. **Coverage Issues**: Make sure all code paths are tested

### Debugging Tests

```bash
# Run with more verbose output
pytest -v -s

# Run specific failing test
pytest test_wallet_kraken.py::TestKrakenWallet::test_authenticate_success -v -s

# Run with debugger
pytest --pdb
```

## Adding New Tests

When adding new functionality to `KrakenWallet`:

1. **Add unit tests** for the new method
2. **Mock external dependencies** (API calls, file operations)
3. **Test both success and failure cases**
4. **Update test coverage** if needed
5. **Run all tests** to ensure nothing breaks

### Example: Adding Test for New Method

```python
def test_new_method_success(self):
    """Test successful execution of new method."""
    # Mock dependencies
    with patch('wallets.wallet_kraken.requests.post') as mock_post:
        mock_response = Mock()
        mock_response.json.return_value = {'result': 'success'}
        mock_post.return_value = mock_response
        
        # Test method
        result = self.wallet.new_method()
        
        # Verify results
        self.assertTrue(result)
        mock_post.assert_called_once()

def test_new_method_failure(self):
    """Test failure case of new method."""
    # Mock failure
    with patch('wallets.wallet_kraken.requests.post') as mock_post:
        mock_post.side_effect = Exception("Network error")
        
        # Test method
        result = self.wallet.new_method()
        
        # Verify results
        self.assertFalse(result)
```

This testing approach ensures that your `KrakenWallet` class is thoroughly tested without requiring real API credentials or making actual network calls. 