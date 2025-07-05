#!/usr/bin/env python3
"""
Test script for the wallets module
This can be run directly to test the wallet functionality
"""

import sys
import os
import logging

# Add the parent directory to Python path to import backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from wallets.portfolio import Portfolio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) 