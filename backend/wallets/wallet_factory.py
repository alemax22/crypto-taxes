#!/usr/bin/env python3
"""
Wallet Factory
Factory class for creating Wallet instances in a Domain-Driven Design architecture
"""

from typing import Dict, Any, Optional, Type
from datetime import datetime
import logging
import sys
import os
import hashlib

# Add parent directory to path to import config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wallets.wallet import Wallet
from wallets.wallet_enums import WalletType, WalletSyncStatus

# Import all the wallet classes
from wallets.wallet_kraken import KrakenWallet

logger = logging.getLogger(__name__)


class WalletFactory:
    """
    Factory class for creating Wallet instances.
    
    This factory is responsible for creating Wallet objects whether they are
    new instances or retrieved from the WalletRepository. It centralizes
    the wallet creation logic and ensures consistent instantiation.
    """
    
    def __init__(self):
        """Initialize the wallet factory."""
        logger.info("WalletFactory initialized")
    
    def _get_wallet_class(self, wallet_type: WalletType) -> Optional[Type[Wallet]]:
        """
        Get wallet class using naming convention from WalletType enum.
        
        Args:
            wallet_type: The wallet type enum
            
        Returns:
            Wallet class or None if not found
        """
        try:
            # Use the enum value directly as the class name
            class_name = wallet_type.value
            wallet_class = eval(class_name)
            return wallet_class
        except (NameError, AttributeError) as e:
            logger.error(f"Wallet class not found for type {wallet_type.value}: {e}")
            return None
    
    @staticmethod  
    def _generate_wallet_id(wallet_type: WalletType, portfolio_id: str, api_key: Optional[str]) -> str:
        """
        Generate a deterministic wallet ID.
        
        Format: "WalletType.value-<ALPHANUMERIC_CODE>"
        The code is derived from a hash of (portfolio_id, api_key, wallet_type).
        This is stable for the same inputs and accepts variable-length values.
        
        Args:
            wallet_type: The wallet type enum
            portfolio_id: The portfolio identifier
            api_key: API key associated with the wallet (can be None)
            
        Returns:
            Deterministic wallet ID
        """
        
        api_key_str = api_key or ""
        hash_input = f"{portfolio_id}::{api_key_str}::{wallet_type.value}".encode("utf-8")
        digest_hex = hashlib.sha256(hash_input).hexdigest()
        # Use a reasonably short, alphanumeric code (hex) while keeping collision risk low
        code = digest_hex[:36] # same length as uuid4
        return f"{wallet_type.value}-{code}"
    
    def create_wallet(self, 
                     wallet_type: WalletType,
                     name: str,
                     reference_fiat: str,
                     portfolio_id: str,
                     id: Optional[str] = None,
                     description: str = "",
                     api_key: Optional[str] = None,
                     api_secret: Optional[str] = None,
                     is_active: bool = False,
                     created_datetime: Optional[datetime] = None,
                     updated_datetime: Optional[datetime] = None,
                     sync_status: WalletSyncStatus = WalletSyncStatus.NOT_SYNCHRONIZED) -> Optional[Wallet]:
        """
        Create a new Wallet instance with the specified parameters.
        
        Args:
            wallet_type: Type of wallet to create (e.g., WalletType.KRAKEN)
            name: Name of the wallet
            reference_fiat: Reference fiat currency
            portfolio_id: ID of the portfolio this wallet belongs to
            id: Unique identifier for the wallet (optional, will be generated if not provided)
            description: Description of the wallet (optional)
            api_key: API key for authentication (optional)
            api_secret: API secret for authentication (optional)
            is_active: Whether the wallet is active (optional)
            created_datetime: When the wallet was created (optional)
            updated_datetime: Last synchronization/update timestamp (optional)
            sync_status: Status of the synchronization process (optional)
            
        Returns:
            Wallet instance if creation successful, None otherwise
            
        Raises:
            ValueError: If wallet_type is not supported
        """
        try:
            wallet_class = self._get_wallet_class(wallet_type)
            if not wallet_class:
                raise ValueError(f"Unsupported wallet type: {wallet_type.value}")
            
            # Generate ID if not provided
            if id is None:
                id = self._generate_wallet_id(wallet_type, portfolio_id, api_key)
                logger.info(f"Generated wallet ID: {id}")
            
            wallet_instance = wallet_class(
                name=name,
                id=id,
                reference_fiat=reference_fiat,
                portfolio_id=portfolio_id,
                description=description,
                api_key=api_key,
                api_secret=api_secret,
                is_active=is_active,
                created_datetime=created_datetime,
                updated_datetime=updated_datetime,
                sync_status=sync_status
            )
            
            logger.info(f"Created {wallet_type.value} wallet: {name} (ID: {id})")
            return wallet_instance
            
        except Exception as e:
            logger.error(f"Failed to create wallet: {str(e)}")
            return None
    
    def create_wallet_from_raw_data(self, wallet_data: Dict[str, Any]) -> Optional[Wallet]:
        """
        Create a Wallet instance from a dictionary of wallet data.
        
        This method is typically used by the WalletRepository to reconstruct
        wallet instances from persisted data.
        
        Having this method and not including this logic in the WalletRepository
        allows to keep the WalletRepository agnostic of the Wallet implementation.
        
        It expects all the datetime in ISO 8601 format, with UTC timezone.

        Args:
            wallet_data: Dictionary containing wallet configuration data
            
        Returns:
            Wallet instance if creation successful, None otherwise
        """
        try:
            # Extract required fields
            wallet_type_str = wallet_data.get('wallet_type')
            if not wallet_type_str:
                logger.error("Missing wallet_type in wallet data")
                return None
            
            # Convert string to WalletType enum
            try:
                # From string value of Enum we get the enum
                wallet_type = WalletType(wallet_type_str)
            except ValueError:
                logger.error(f"Invalid wallet type: {wallet_type_str}")
                return None
            
            # Extract other required fields
            name = wallet_data.get('name')
            wallet_id = wallet_data.get('wallet_id')
            reference_fiat = wallet_data.get('reference_fiat')
            portfolio_id = wallet_data.get('portfolio_id')
            
            if not all([name, reference_fiat, portfolio_id]):
                logger.error("Missing required fields in wallet data")
                return None
            
            # Extract optional fields
            description = wallet_data.get('description', '')
            api_key = wallet_data.get('api_key')
            api_secret = wallet_data.get('api_secret')
            is_active = wallet_data.get('is_active', False)
            
            # Handle created_datetime
            created_datetime_str = wallet_data.get('created_datetime')
            created_datetime = None
            if created_datetime_str:
                try:
                    created_datetime = datetime.fromisoformat(created_datetime_str.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid created_datetime format: {created_datetime_str}")
            
            # Handle updated_datetime  
            updated_datetime_str = wallet_data.get('updated_datetime')
            updated_datetime = None
            if updated_datetime_str:
                try:
                    updated_datetime = datetime.fromisoformat(updated_datetime_str.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid updated_datetime format: {updated_datetime_str}")
            
            # Handle sync_status
            sync_status_str = wallet_data.get('sync_status','')
            try:
                sync_status = WalletSyncStatus(sync_status_str)
            except ValueError:
                logger.warning(f"Invalid sync_status: {sync_status_str}, using default")
                sync_status = WalletSyncStatus.NOT_SYNCHRONIZED
            
            # Create wallet instance
            return self.create_wallet(
                wallet_type=wallet_type,
                name=name,
                reference_fiat=reference_fiat,
                portfolio_id=portfolio_id,
                id=wallet_id,
                description=description,
                api_key=api_key,
                api_secret=api_secret,
                is_active=is_active,
                created_datetime=created_datetime,
                updated_datetime=updated_datetime,
                sync_status=sync_status
            )
            
        except Exception as e:
            logger.error(f"Failed to create wallet from data: {str(e)}")
            return None 
