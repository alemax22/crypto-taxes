#!/usr/bin/env python3
"""
Portfolio Repository
Domain-Driven Design repository for portfolio persistence and retrieval
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import os
import logging
import sys
from sqlalchemy import Column, String, DateTime, text
from datetime import datetime

# Add parent directory to path to import config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wallets.portfolio import Portfolio
from wallets.portfolio_factory import PortfolioFactory
from db import SessionLocal, Base, engine, SCHEMA_NAME

logger = logging.getLogger(__name__)


class PortfolioRepository(ABC):
    """
    Abstract portfolio repository interface.
    
    This interface defines the contract for portfolio persistence operations
    in a Domain-Driven Design architecture.
    """
    def __init__(self):
        self.portfolio_factory = PortfolioFactory()

    @abstractmethod
    def save_portfolio(self, portfolio: Portfolio) -> bool:
        """
        Save a portfolio configuration to the repository.
        
        Args:
            portfolio: Portfolio instance
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_portfolio_by_id(self, portfolio_id: str) -> Optional[Portfolio]:
        """
        Find a portfolio configuration by its ID.
        
        Args:
            portfolio_id: Unique identifier of the portfolio
        Returns:
            Portfolio instance or None if not found
        """
        pass
    
    @abstractmethod
    def get_user_portfolio(self, user_id: str) -> Optional[Portfolio]:
        """
        Retrieve the user's portfolio from the repository.
        
        Returns:
            Portfolio instance or None if not found
        """
        pass
    
    @abstractmethod
    def delete_portfolio_by_id(self, portfolio_id: str) -> bool:
        """
        Delete a portfolio from the repository.
        
        Args:
            portfolio_id: Unique identifier of the portfolio to delete
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        pass


class PortfolioORM(Base):
    __tablename__ = "portfolios"
    __table_args__ = {"schema": SCHEMA_NAME}

    portfolio_id = Column(String(128), primary_key=True)
    user_id = Column(String(128), nullable=False) 
    reference_asset = Column(String(8))
    created_datetime = Column(DateTime, default=datetime.utcnow)
    updated_datetime = Column(DateTime, nullable=True)


class PostgresPortfolioRepository(PortfolioRepository):
    """
    Postgres implementation of the portfolio repository using SQLAlchemy.
    """

    def __init__(self):
        super().__init__()
        # Ensure tables exist
        try:
            # Ensure schema exists
            with engine.begin() as conn:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA_NAME}"'))
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def _deserialize_portfolio(self, orm: PortfolioORM) -> Optional[Portfolio]:
        raw = {
            'portfolio_id': orm.portfolio_id,
            'user_id': orm.user_id,
            'reference_asset': orm.reference_asset,
            'created_datetime': orm.created_datetime.isoformat() if orm.created_datetime else '',
            'updated_datetime': orm.updated_datetime.isoformat() if orm.updated_datetime else '',
        }
        return self.portfolio_factory.create_portfolio_from_raw_data(raw)

    def _serialize_portfolio(self, portfolio: Portfolio) -> Dict[str, Any]:
        return {
            'portfolio_id': portfolio.portfolio_id,
            'user_id': portfolio.user_id,
            'reference_asset': portfolio.reference_asset,
            'updated_datetime': datetime.utcnow(),
        }

    def save_portfolio(self, portfolio: Portfolio) -> bool:
        try:
            with SessionLocal() as session:
                data = self._serialize_portfolio(portfolio)
                session.merge(PortfolioORM(**data))
                session.commit()
                return True
        except Exception as e:
            logger.error(f"DB error saving portfolio: {e}")
            return False

    def get_portfolio_by_id(self, portfolio_id: str) -> Optional[Portfolio]:
        try:
            with SessionLocal() as session:
                orm = session.query(PortfolioORM).filter(
                    PortfolioORM.portfolio_id == portfolio_id,
                ).one_or_none()
                if not orm:
                    return None
                return self._deserialize_portfolio(orm)
        except Exception as e:
            logger.error(f"DB error getting portfolio by id: {e}")
            return None

    def get_user_portfolio(self, user_id: str) -> Optional[Portfolio]:
        try:
            with SessionLocal() as session:
                orm = session.query(PortfolioORM).filter(
                    PortfolioORM.user_id == user_id,
                ).one_or_none()
                if not orm:
                    return None
                return self._deserialize_portfolio(orm)
        except Exception as e:
            logger.error(f"DB error getting user portfolio: {e}")
            return None

    def delete_portfolio_by_id(self, portfolio_id: str) -> bool:
        try:
            with SessionLocal() as session:
                orm = session.query(PortfolioORM).filter(
                    PortfolioORM.portfolio_id == portfolio_id,
                ).one_or_none()
                if not orm:
                    return False
                session.delete(orm)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"DB error deleting portfolio: {e}")
            return False
