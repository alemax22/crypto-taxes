#!/usr/bin/env python3
"""
Portfolio Factory
Factory class for creating Portfolio instances in a Domain-Driven Design architecture
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging
import sys
import os

# Add parent directory to path to import config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wallets.portfolio import Portfolio

logger = logging.getLogger(__name__)


class PortfolioFactory:
    """
    Factory class for creating Portfolio instances.
    
    This factory is responsible for creating Portfolio objects whether they are
    new instances or retrieved from the PortfolioRepository. It centralizes
    the portfolio creation logic and ensures consistent instantiation.
    """
    
    def __init__(self):
        """Initialize the portfolio factory."""
        logger.info("PortfolioFactory initialized")
    
    def create_portfolio(self, 
                        user_id: str,
                        reference_asset: str = "EUR",
                        portfolio_id: Optional[str] = None,
                        created_datetime: Optional[datetime] = None) -> Optional[Portfolio]:
        """
        Create a new Portfolio instance with the specified parameters.
        
        Args:
            name: Name of the portfolio
            reference_asset: Reference asset for the portfolio (e.g., "EUR", "USD")
            portfolio_id: Unique identifier for the portfolio (optional, will be generated if not provided)
            description: Description of the portfolio (optional)
            created_datetime: Creation datetime (optional, will use current UTC time if not provided)
            
        Returns:
            Portfolio instance if creation successful, None otherwise
            
        Raises:
            ValueError: If required parameters are invalid
        """
        try:
            portfolio_instance = Portfolio(
                user_id=user_id,
                portfolio_id=portfolio_id,
                reference_asset=reference_asset,
                created_datetime=created_datetime
            )
            
            logger.info(f"Created portfolio (ID: {portfolio_instance.portfolio_id}, reference asset: {portfolio_instance.reference_asset})")
            return portfolio_instance
            
        except Exception as e:
            logger.error(f"Failed to create portfolio: {str(e)}")
            return None
    
    def create_portfolio_from_raw_data(self, portfolio_data: Dict[str, Any]) -> Optional[Portfolio]:
        """
        Create a Portfolio instance from a dictionary of portfolio data.
        
        This method is typically used by the PortfolioRepository to reconstruct
        portfolio instances from persisted data.
        
        Having this method and not including this logic in the PortfolioRepository
        allows to keep the PortfolioRepository agnostic of the Portfolio implementation.
        
        It expects all the datetime in ISO 8601 format, with UTC timezone.

        Args:
            portfolio_data: Dictionary containing portfolio configuration data
            
        Returns:
            Portfolio instance if creation successful, None otherwise
        """
        try:
            user_id = portfolio_data.get('user_id')
            if not user_id:
                logger.error("Missing user_id in portfolio data")
                return None

            portfolio_id = portfolio_data.get('portfolio_id')
            reference_asset = portfolio_data.get('reference_asset', 'EUR')

            # Handle created_datetime
            created_datetime_str = portfolio_data.get('created_datetime')
            created_datetime = None
            if created_datetime_str:
                try:
                    created_datetime = datetime.fromisoformat(created_datetime_str.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid created_datetime format: {created_datetime_str}")
            
            # Create portfolio instance
            portfolio = self.create_portfolio(
                reference_asset=reference_asset,
                portfolio_id=portfolio_id,
                created_datetime=created_datetime
            )
            
            return portfolio
            
        except Exception as e:
            logger.error(f"Failed to create portfolio from data: {str(e)}")
            return None
