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
import uuid
from datetime import timezone

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
                        created_datetime: Optional[datetime] = None,
                        updated_datetime: Optional[datetime] = None) -> Optional[Portfolio]:
        """
        Create a new Portfolio instance with the specified parameters.
        
        Args:
            user_id: Unique identifier for the user owning the portfolio.
            reference_asset: Reference asset for the portfolio (e.g., "EUR", "USD")
            portfolio_id: Unique identifier for the portfolio (optional, will be generated if not provided)
            created_datetime: Creation datetime (optional, will use current UTC time if not provided)
            updated_datetime: Last updated datetime (optional)
            
        Returns:
            Portfolio instance if creation successful, None otherwise
            
        Raises:
            ValueError: If required parameters are invalid
        """
        try:
            # For new portfolios (when portfolio_id is None), generate ID and set creation time
            if not portfolio_id:
                portfolio_id = self._generate_portfolio_id()
                created_datetime = datetime.now(timezone.utc)
                logger.info(f"Generated portfolio ID: {portfolio_id} for new portfolio")

            portfolio_instance = Portfolio(
                user_id=user_id,
                portfolio_id=portfolio_id,
                reference_asset=reference_asset,
                created_datetime=created_datetime,
                updated_datetime=updated_datetime
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
            if not portfolio_id:
                logger.error("Missing portfolio_id in portfolio data")
                return None
            
            reference_asset = portfolio_data.get('reference_asset')
            if not reference_asset:
                logger.error("Missing reference_asset in portfolio data")
                return None

            # Handle created_datetime
            created_datetime_str = portfolio_data.get('created_datetime')
            created_datetime = None
            if created_datetime_str:
                try:
                    created_datetime = datetime.fromisoformat(created_datetime_str.replace('Z', '+00:00'))
                except ValueError:
                    logger.error(f"Invalid created_datetime format: {created_datetime_str}")
                    return None
            else:
                logger.error("Missing created_datetime in portfolio data")
                return None
            
            # Handle updated_datetime
            updated_datetime_str = portfolio_data.get('updated_datetime')
            updated_datetime = None
            if updated_datetime_str:
                try:
                    updated_datetime = datetime.fromisoformat(updated_datetime_str.replace('Z', '+00:00'))
                except ValueError:
                    logger.error(f"Invalid updated_datetime format: {updated_datetime_str}")
                    return None
            else:
                logger.error("Missing updated_datetime in portfolio data")
                return None
            
            # Create portfolio instance
            portfolio = self.create_portfolio(
                user_id=user_id,
                portfolio_id=portfolio_id,
                reference_asset=reference_asset,
                created_datetime=created_datetime,
                updated_datetime=updated_datetime
            )
            
            return portfolio
            
        except Exception as e:
            logger.error(f"Failed to create portfolio from data: {str(e)}")
            return None
        
    @staticmethod  
    def _generate_portfolio_id() -> str:
        """
        Generate a unique portfolio ID.
        """
        return f"PF-{str(uuid.uuid4())}"
