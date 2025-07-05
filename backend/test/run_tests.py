#!/usr/bin/env python3
"""
Test runner script for the crypto-taxes backend
Provides easy ways to run different types of tests
"""

import sys
import os
import subprocess
import argparse

def run_tests(test_type='all', coverage=True, verbose=True):
    """
    Run tests with specified options.
    
    Args:
        test_type: Type of tests to run ('all', 'unit', 'integration')
        coverage: Whether to run with coverage
        verbose: Whether to run in verbose mode
    """
    
    # Base command
    cmd = ['python', '-m', 'pytest', 'test']  # Run tests from the test/ folder
    
    # Add coverage if requested
    if coverage:
        cmd.extend(['--cov=wallets', '--cov-report=term-missing'])
    
    # Add verbose flag
    if verbose:
        cmd.append('-v')
    
    # Add test type filters
    if test_type == 'unit':
        cmd.extend(['-m', 'unit'])
    elif test_type == 'integration':
        cmd.extend(['-m', 'integration'])
    elif test_type == 'api':
        cmd.extend(['-m', 'api'])
    
    print(f"Running tests with command: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, check=True)
        print("=" * 60)
        print("✅ All tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print("=" * 60)
        print(f"❌ Tests failed with exit code: {e.returncode}")
        return False

def main():
    """Main function to parse arguments and run tests."""
    parser = argparse.ArgumentParser(description='Run crypto-taxes backend tests')
    parser.add_argument(
        '--type', 
        choices=['all', 'unit', 'integration', 'api'],
        default='all',
        help='Type of tests to run'
    )
    parser.add_argument(
        '--no-coverage',
        action='store_true',
        help='Run tests without coverage'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Run tests in quiet mode'
    )
    
    args = parser.parse_args()
    
    # Run tests
    success = run_tests(
        test_type=args.type,
        coverage=not args.no_coverage,
        verbose=not args.quiet
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main() 