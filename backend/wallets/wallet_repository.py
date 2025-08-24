
#!/usr/bin/env python3
"""
Wallet Repository
Domain-Driven Design repository for wallet persistence and retrieval
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import os
import logging
from cryptography.fernet import Fernet
import sys
from sqlalchemy import Column, String, Boolean, DateTime, text
from datetime import datetime, timezone
from typing import Optional

# Add parent directory to path to import config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wallets.wallet_enums import WalletSyncStatus
from config import WALLETS_DIR
from wallets.wallet import Wallet
from wallets.wallet_factory import WalletFactory
from db import SessionLocal, Base, engine, SCHEMA_NAME

logger = logging.getLogger(__name__)

PORTFOLIO_ENCRYPTION_KEY_FILE_NAME = "portfolio_key.key"

class WalletRepository(ABC):
    """
    Abstract wallet repository interface.
    
    This interface defines the contract for wallet persistence operations
    in a Domain-Driven Design architecture.
    """
    def __init__(self):
        self.wallet_factory = WalletFactory()
        self.encryption_key_file = os.path.join(WALLETS_DIR, PORTFOLIO_ENCRYPTION_KEY_FILE_NAME)
        os.makedirs(os.path.dirname(WALLETS_DIR), exist_ok=True)
        os.makedirs(WALLETS_DIR, exist_ok=True)
        self._initialize_encryption()

    @abstractmethod
    def save_wallet(self, wallet: Wallet) -> bool:
        """
        Save a wallet configuration to the repository.
        
        Args:
            wallet: Wallet instance
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_wallet_by_id(self, wallet_id: str) -> Optional[Wallet]:
        """
        Find a wallet configuration by its ID.
        
        Args:
            wallet_id: Unique identifier of the wallet
        Returns:
            Wallet instance or None if not found
        """
        pass
    
    @abstractmethod
    def get_all_wallets_in_portfolio(self, portfolio_id: str) -> List[Wallet]:
        """
        Retrieve all wallet configurations from the repository for a given portfolio.
        
        Args:
            portfolio_id: Unique identifier of the portfolio
            
        Returns:
            List of wallet instances
        """
        pass
    
    @abstractmethod
    def delete_wallet_by_id(self, wallet_id: str) -> bool:
        """
        Delete a wallet from the repository.
        
        Args:
            wallet_id: Unique identifier of the wallet to delete
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        pass

    @abstractmethod
    def save_all_wallets(self, wallet_list: List[Wallet]) -> None:
        """
        Save all wallet data to the repository.
        It does not remove wallets that are not in the list.
        
        Args:
            wallet_list: List of wallet instances
        """
        pass

    def _initialize_encryption(self) -> None:
        if not os.path.exists(self.encryption_key_file):
            self._generate_encryption_key()

    def _generate_encryption_key(self) -> None:
        key = Fernet.generate_key()
        with open(self.encryption_key_file, "wb") as key_file:
            key_file.write(key)

    def _load_encryption_key(self) -> bytes:
        with open(self.encryption_key_file, "rb") as key_file:
            return key_file.read()

    def _encrypt_api_credentials(self, api_key: Optional[str], api_secret: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if not api_key or not api_secret:
            return api_key, api_secret
        f = Fernet(self._load_encryption_key())
        return f.encrypt(api_key.encode()).decode(), f.encrypt(api_secret.encode()).decode()

    def _decrypt_api_credentials(self, encrypted_api_key: Optional[str], encrypted_api_secret: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if not encrypted_api_key or not encrypted_api_secret:
            return encrypted_api_key, encrypted_api_secret
        f = Fernet(self._load_encryption_key())
        return f.decrypt(encrypted_api_key.encode()).decode(), f.decrypt(encrypted_api_secret.encode()).decode()

class WalletORM(Base):
    __tablename__ = "wallets"
    __table_args__ = {"schema": SCHEMA_NAME}

    wallet_id = Column(String(128), primary_key=True)
    portfolio_id = Column(String(128), index=True)
    wallet_type = Column(String(64), index=True)
    name = Column(String(255))
    description = Column(String(1024), nullable=True)
    api_key = Column(String(2048), nullable=True)
    api_secret = Column(String(2048), nullable=True)
    is_active = Column(Boolean, default=False)
    created_datetime = Column(DateTime, default=datetime.now(timezone.utc))
    updated_datetime = Column(DateTime, nullable=True)
    reference_fiat = Column(String(8))
    sync_status = Column(String(64), default=WalletSyncStatus.NOT_SYNCHRONIZED.value)


class PostgresWalletRepository(WalletRepository):
    """
    Postgres implementation of the wallet repository using SQLAlchemy.
    API credentials are encrypted at rest using the same Fernet key file used by CSV repo.
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

    def _deserialize_wallet(self, orm: WalletORM) -> Optional[Wallet]:
        api_key, api_secret = self._decrypt_api_credentials(orm.api_key, orm.api_secret)
        raw = {
            'wallet_id': orm.wallet_id,
            'wallet_type': orm.wallet_type,
            'name': orm.name,
            'description': orm.description or '',
            'api_key': api_key,
            'api_secret': api_secret,
            'is_active': orm.is_active,
            'created_datetime': orm.created_datetime.isoformat() if orm.created_datetime else '',
            'updated_datetime': orm.updated_datetime.isoformat() if orm.updated_datetime else '',
            'reference_fiat': orm.reference_fiat,
            'sync_status': orm.sync_status,
            'portfolio_id': orm.portfolio_id,
        }
        return self.wallet_factory.create_wallet_from_raw_data(raw)

    def _serialize_wallet(self, wallet: Wallet) -> Dict[str, Any]:
        enc_key, enc_secret = self._encrypt_api_credentials(wallet.api_key, wallet.api_secret)
        return {
            'wallet_id': wallet.id,
            'portfolio_id': wallet.portfolio_id,
            'wallet_type': wallet.get_wallet_type().value,
            'name': wallet.name,
            'description': wallet.description or '',
            'api_key': enc_key,
            'api_secret': enc_secret,
            'is_active': bool(wallet.is_active),
            'reference_fiat': wallet.reference_fiat,
            'sync_status': (wallet.sync_status.value if wallet.sync_status else WalletSyncStatus.NOT_SYNCHRONIZED.value),
        }

    def save_wallet(self, wallet: Wallet) -> bool:
        try:
            with SessionLocal() as session:
                data = self._serialize_wallet(wallet)
                session.merge(WalletORM(**data))
                session.commit()
                return True
        except Exception as e:
            logger.error(f"DB error saving wallet: {e}")
            return False

    def get_wallet_by_id(self, wallet_id: str) -> Optional[Wallet]:
        try:
            with SessionLocal() as session:
                orm = session.query(WalletORM).filter(
                    WalletORM.wallet_id == wallet_id,
                ).one_or_none()
                if not orm:
                    return None
                return self._deserialize_wallet(orm)
        except Exception as e:
            logger.error(f"DB error getting wallet by id: {e}")
            return None

    def get_all_wallets_in_portfolio(self, portfolio_id: str) -> List[Wallet]:
        try:
            with SessionLocal() as session:
                orms = session.query(WalletORM).filter(WalletORM.portfolio_id == portfolio_id).all()
                if not orms:
                    return []
                wallets = []
                for orm in orms:
                    wallet = self._deserialize_wallet(orm)
                    wallets.append(wallet)
                return wallets
        except Exception as e:
            logger.error(f"DB error listing wallets: {e}")
            return []

    def delete_wallet_by_id(self, wallet_id: str) -> bool:
        try:
            with SessionLocal() as session:
                orm = session.query(WalletORM).filter(
                    WalletORM.wallet_id == wallet_id,
                ).one_or_none()
                if not orm:
                    return False
                session.delete(orm)
                session.commit()
                return True
        except Exception as e:
            logger.error(f"DB error deleting wallet: {e}")
            return False

    def save_all_wallets(self, wallet_list: List[Wallet]) -> None:
        try:
            with SessionLocal() as session:
                for wallet in wallet_list:
                    data = self._serialize_wallet(wallet)
                    session.merge(WalletORM(**data))
                session.commit()
        except Exception as e:
            logger.error(f"DB error saving all wallets: {e}")