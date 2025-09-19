#!/usr/bin/env python3
"""
FastAPI server for Crypto Taxes Portfolio Management
Provides REST API endpoints for wallet management operations
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
import logging
import os
import sys

# Add the current directory to Python path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wallets.portfolio import Portfolio
from wallets.portfolio_factory import PortfolioFactory
from wallets.portfolio_repository import PostgresPortfolioRepository
from wallets.wallet_enums import WalletType, WalletSyncStatus
from db import init_db, engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s:%(process)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Global constants
DEFAULT_USER_ID = "test"  # Default user ID for portfolio operations

# Global portfolio instance
portfolio_factory = PortfolioFactory()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    try:
        # Ensure database tables exist (safe if DB not used yet)
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    yield
    
    # Shutdown (if needed)
    logger.info("Application shutting down")

# Create FastAPI app
app = FastAPI(
    title="Crypto Taxes Portfolio API",
    description="API for managing cryptocurrency wallets and portfolios",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation
class WalletCreateRequest(BaseModel):
    wallet_type: str = Field(..., description="Type of wallet (e.g., 'Kraken')")
    name: str = Field(..., description="Name of the wallet")
    api_key: Optional[str] = Field(None, description="API key for the wallet")
    api_secret: Optional[str] = Field(None, description="API secret for the wallet")
    description: Optional[str] = Field("", description="Optional description of the wallet")


class WalletResponse(BaseModel):
    wallet_id: str
    wallet_type: str
    name: str
    description: str
    is_active: bool
    created_datetime: str
    updated_datetime: Optional[str]
    reference_fiat: str
    sync_status: str


class PortfolioCreateRequest(BaseModel):
    reference_asset: str = Field(default="EUR", description="Reference asset for the portfolio (e.g., 'EUR', 'USD')")


class PortfolioResponse(BaseModel):
    portfolio_id: str
    user_id: str
    reference_asset: str
    created_datetime: str
    updated_datetime: str

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

@app.get("/", response_model=ApiResponse)
async def root():
    """Root endpoint with API information."""
    return ApiResponse(
        success=True,
        message="Crypto Taxes Portfolio API is running",
        data={
            "version": "1.0.0",
            "endpoints": {
                "list_portfolios": "/portfolios",
                "create_portfolio": "/portfolios",
                "delete_portfolio": "/portfolios/{portfolio_id}",
                "list_wallets": "/portfolios/{portfolio_id}/wallets",
                "add_wallet": "/portfolios/{portfolio_id}/wallets",
                "get_wallet": "/portfolios/{portfolio_id}/wallets/{wallet_id}",
                "remove_wallet": "/portfolios/{portfolio_id}/wallets/{wallet_id}",
                "synchronize_wallets": "/portfolios/{portfolio_id}/wallets/synchronize"
            }
        }
    )

def ensure_user_has_portfolio(user_id: str = DEFAULT_USER_ID) -> Portfolio:
    """
    Ensure the user has a portfolio, creating one if necessary.
    Returns the Portfolio instance.
    """
    portfolio_repo = PostgresPortfolioRepository()
    portfolio_instance = portfolio_repo.get_user_portfolio(user_id)
    
    if not portfolio_instance:
        logger.info(f"Creating default portfolio for user '{user_id}'")
        portfolio_instance = portfolio_factory.create_portfolio(
            user_id=user_id,
            reference_asset="EUR"  # Default reference asset
        )
        
        if portfolio_instance:
            is_saved = portfolio_repo.save_portfolio(portfolio_instance)
            if not is_saved:
                raise Exception("Failed to save default portfolio")
        else:
            raise Exception("Failed to create default portfolio")
    
    return portfolio_instance


@app.get("/portfolios", response_model=ApiResponse)
async def list_portfolios():
    """List portfolios for the default user (always returns exactly one portfolio)."""
    try:
        # Ensure user has a portfolio
        portfolio_instance = ensure_user_has_portfolio()
        
        # Convert portfolio to response format
        portfolio_dict = {
            'portfolio_id': portfolio_instance.portfolio_id,
            'user_id': portfolio_instance.user_id,
            'reference_asset': portfolio_instance.reference_asset,
            'created_datetime': portfolio_instance.created_datetime.isoformat() if portfolio_instance.created_datetime else '',
            'updated_datetime': portfolio_instance.updated_datetime.isoformat() if portfolio_instance.updated_datetime else ''
        }
        
        return ApiResponse(
            success=True,
            message=f"Found 1 portfolio for user '{DEFAULT_USER_ID}'",
            data=[portfolio_dict]  # Always return array with single portfolio
        )
    except Exception as e:
        logger.error(f"Error listing portfolios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list portfolios: {str(e)}"
        )


@app.post("/portfolios", response_model=ApiResponse)
async def create_portfolio(portfolio_request: PortfolioCreateRequest):
    """Create or update the user's portfolio (enforces one portfolio per user)."""
    try:
        portfolio_repo = PostgresPortfolioRepository()
        
        # Check if user already has a portfolio
        existing_portfolio = portfolio_repo.get_user_portfolio(DEFAULT_USER_ID)
        
        if existing_portfolio:
            # Update existing portfolio instead of creating new one
            logger.info(f"User '{DEFAULT_USER_ID}' already has portfolio, updating reference asset")
            existing_portfolio.reference_asset = portfolio_request.reference_asset
            
            is_saved = portfolio_repo.save_portfolio(existing_portfolio)
            if not is_saved:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update existing portfolio"
                )
            
            portfolio_dict = {
                'portfolio_id': existing_portfolio.portfolio_id,
                'user_id': existing_portfolio.user_id,
                'reference_asset': existing_portfolio.reference_asset,
                'created_datetime': existing_portfolio.created_datetime.isoformat() if existing_portfolio.created_datetime else '',
                'updated_datetime': existing_portfolio.updated_datetime.isoformat() if existing_portfolio.updated_datetime else ''
            }
            
            return ApiResponse(
                success=True,
                message=f"Portfolio updated successfully with reference asset '{portfolio_request.reference_asset}'",
                data=portfolio_dict
            )
        else:
            # Create new portfolio
            portfolio_instance = portfolio_factory.create_portfolio(
                user_id=DEFAULT_USER_ID,
                reference_asset=portfolio_request.reference_asset
            )
            
            if not portfolio_instance:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create portfolio instance"
                )
            
            is_saved = portfolio_repo.save_portfolio(portfolio_instance)
            if not is_saved:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save portfolio to database"
                )
            
            portfolio_dict = {
                'portfolio_id': portfolio_instance.portfolio_id,
                'user_id': portfolio_instance.user_id,
                'reference_asset': portfolio_instance.reference_asset,
                'created_datetime': portfolio_instance.created_datetime.isoformat() if portfolio_instance.created_datetime else '',
                'updated_datetime': portfolio_instance.updated_datetime.isoformat() if portfolio_instance.updated_datetime else ''
            }
            
            return ApiResponse(
                success=True,
                message=f"Portfolio created successfully with reference asset '{portfolio_request.reference_asset}'",
                data=portfolio_dict
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating/updating portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create/update portfolio: {str(e)}"
        )


@app.delete("/portfolios/{portfolio_id}", response_model=ApiResponse)
async def delete_portfolio(portfolio_id: str):
    """Delete a portfolio by ID (enforces user ownership)."""
    try:
        # Get portfolio from repository to verify it exists and belongs to the user
        portfolio_repo = PostgresPortfolioRepository()
        portfolio_instance = portfolio_repo.get_portfolio_by_id(portfolio_id)
        
        if not portfolio_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio with ID '{portfolio_id}' not found"
            )
        
        # Verify portfolio belongs to the default user
        if portfolio_instance.user_id != DEFAULT_USER_ID:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Portfolio '{portfolio_id}' does not belong to the current user"
            )
        
        # Delete portfolio
        is_deleted = portfolio_repo.delete_portfolio_by_id(portfolio_id)
        
        if not is_deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete portfolio '{portfolio_id}'"
            )
        
        return ApiResponse(
            success=True,
            message=f"Portfolio '{portfolio_id}' deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete portfolio: {str(e)}"
        )


@app.get("/portfolios/{portfolio_id}/wallets", response_model=ApiResponse)
async def list_wallets(portfolio_id: str):
    """List all wallets in the specified portfolio."""
    try:
        # Get portfolio from repository
        portfolio_repo = PostgresPortfolioRepository()
        portfolio_instance = portfolio_repo.get_portfolio_by_id(portfolio_id)
        
        if not portfolio_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio with ID '{portfolio_id}' not found"
            )
        
        # Verify portfolio belongs to the current user
        if portfolio_instance.user_id != DEFAULT_USER_ID:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Portfolio '{portfolio_id}' does not belong to the current user"
            )
        
        wallets = portfolio_instance.list_wallets()
        # Convert wallet objects to dictionaries
        wallet_dicts = []
        for wallet in wallets:
            wallet_dict = {
                'wallet_id': wallet.id,
                'wallet_type': wallet.get_wallet_type().value,
                'name': wallet.name,
                'description': wallet.description or '',
                'is_active': bool(wallet.is_active),
                'created_datetime': wallet.created_datetime.isoformat() if wallet.created_datetime else '',
                'updated_datetime': wallet.updated_datetime.isoformat() if wallet.updated_datetime else '',
                'reference_fiat': wallet.reference_fiat,
                'sync_status': (wallet.sync_status.value if wallet.sync_status else WalletSyncStatus.NOT_SYNCHRONIZED.value),
                'portfolio_id': wallet.portfolio_id,
            }
            wallet_dicts.append(wallet_dict)
        
        return ApiResponse(
            success=True,
            message=f"Found {len(wallet_dicts)} wallets in portfolio {portfolio_id}",
            data=wallet_dicts
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing wallets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list wallets: {str(e)}"
        )

@app.get("/api/health", response_model=ApiResponse)
async def api_health():
    """Health endpoint that also validates DB connectivity."""
    try:
        # Quick DB check
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        return ApiResponse(success=True, message="ok", data={"db": "ok"})
    except Exception as e:
        logger.error(f"Healthcheck DB error: {e}")
        return ApiResponse(success=False, message="db error", data={"error": str(e)})

@app.post("/portfolios/{portfolio_id}/wallets", response_model=ApiResponse)
async def add_wallet(portfolio_id: str, wallet_request: WalletCreateRequest):
    """Add a new wallet to the specified portfolio."""
    try:
        # Get portfolio from repository
        portfolio_repo = PostgresPortfolioRepository()
        portfolio_instance = portfolio_repo.get_portfolio_by_id(portfolio_id)
        
        if not portfolio_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio with ID '{portfolio_id}' not found"
            )
        
        # Verify portfolio belongs to the current user
        if portfolio_instance.user_id != DEFAULT_USER_ID:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Portfolio '{portfolio_id}' does not belong to the current user"
            )
        
        logger.info(f"Wallet request: {wallet_request}")

        # Normalize wallet_type (accepts 'Kraken', 'KRAKEN', or enum value)
        wt_str = wallet_request.wallet_type
        wallet_type_enum = None
        try:
            wallet_type_enum = WalletType[wt_str.upper()]
        except Exception:
            for enum_item in WalletType:
                if enum_item.value.replace('Wallet', '').lower() == wt_str.lower():
                    wallet_type_enum = enum_item
                    break
        if wallet_type_enum is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported wallet_type: {wt_str}")

        wallet = portfolio_instance.add_wallet(
            wallet_type=wallet_type_enum,
            name=wallet_request.name,
            api_key=wallet_request.api_key,
            api_secret=wallet_request.api_secret,
            description=wallet_request.description
        )

        logger.info(f"Wallet ID: {wallet.id if wallet else None}")
        
        if wallet:
            return ApiResponse(
                success=True,
                message=f"Wallet '{wallet_request.name}' added successfully to portfolio {portfolio_id}",
                data={"wallet_id": wallet.id}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add wallet. Check your credentials and wallet type."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add wallet: {str(e)}"
        )

@app.get("/portfolios/{portfolio_id}/wallets/{wallet_id}", response_model=ApiResponse)
async def get_wallet(portfolio_id: str, wallet_id: str):
    """
    Get a specific wallet by ID from the specified portfolio.
    It MUST not return sensitive data like api_key and api_secret.
    """
    try:
        # Get portfolio from repository
        portfolio_repo = PostgresPortfolioRepository()
        portfolio_instance = portfolio_repo.get_portfolio_by_id(portfolio_id)
        
        if not portfolio_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio with ID '{portfolio_id}' not found"
            )
        
        # Verify portfolio belongs to the current user
        if portfolio_instance.user_id != DEFAULT_USER_ID:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Portfolio '{portfolio_id}' does not belong to the current user"
            )
        
        wallet = portfolio_instance.get_wallet_by_id(wallet_id)

        if wallet:
            # Verify wallet belongs to the specified portfolio
            if wallet.portfolio_id != portfolio_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Wallet with ID '{wallet_id}' not found in portfolio '{portfolio_id}'"
                )
            
            # Convert wallet object to dictionary and remove sensitive data
            wallet_dict = {
                'wallet_id': wallet.id,
                'wallet_type': wallet.get_wallet_type().value,
                'name': wallet.name,
                'description': wallet.description or '',
                'is_active': bool(wallet.is_active),
                'created_datetime': wallet.created_datetime.isoformat() if wallet.created_datetime else '',
                'updated_datetime': wallet.updated_datetime.isoformat() if wallet.updated_datetime else '',
                'reference_fiat': wallet.reference_fiat,
                'sync_status': (wallet.sync_status.value if wallet.sync_status else WalletSyncStatus.NOT_SYNCHRONIZED.value),
                'portfolio_id': wallet.portfolio_id,
            }
        else:
            wallet_dict = None

        if wallet_dict:
            return ApiResponse(
                success=True,
                message="Wallet found",
                data=wallet_dict
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet with ID '{wallet_id}' not found in portfolio '{portfolio_id}'"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get wallet: {str(e)}"
        )

@app.delete("/portfolios/{portfolio_id}/wallets/{wallet_id}", response_model=ApiResponse)
async def remove_wallet(portfolio_id: str, wallet_id: str):
    """Remove a wallet from the specified portfolio."""
    try:
        # Get portfolio from repository
        portfolio_repo = PostgresPortfolioRepository()
        portfolio_instance = portfolio_repo.get_portfolio_by_id(portfolio_id)
        
        if not portfolio_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio with ID '{portfolio_id}' not found"
            )
        
        # Verify portfolio belongs to the current user
        if portfolio_instance.user_id != DEFAULT_USER_ID:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Portfolio '{portfolio_id}' does not belong to the current user"
            )
        
        # First verify the wallet exists and belongs to the portfolio
        wallet = portfolio_instance.get_wallet_by_id(wallet_id)
        if not wallet or wallet.portfolio_id != portfolio_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet with ID '{wallet_id}' not found in portfolio '{portfolio_id}'"
            )
        
        success = portfolio_instance.remove_wallet(wallet_id)
        if success:
            return ApiResponse(
                success=True,
                message=f"Wallet '{wallet_id}' removed successfully from portfolio '{portfolio_id}'"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to remove wallet '{wallet_id}' from portfolio '{portfolio_id}'"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove wallet: {str(e)}"
        )

@app.post("/portfolios/{portfolio_id}/wallets/synchronize", response_model=ApiResponse)
async def synchronize_wallets(portfolio_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Synchronize all wallets in the specified portfolio."""
    try:
        # Get portfolio from repository
        portfolio_repo = PostgresPortfolioRepository()
        portfolio_instance = portfolio_repo.get_portfolio_by_id(portfolio_id)
        
        if not portfolio_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio with ID '{portfolio_id}' not found"
            )
        
        # Verify portfolio belongs to the current user
        if portfolio_instance.user_id != DEFAULT_USER_ID:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Portfolio '{portfolio_id}' does not belong to the current user"
            )
        
        results = portfolio_instance.synchronize_all_wallets(start_date)
        return ApiResponse(
            success=True,
            message=f"Synchronization completed for portfolio '{portfolio_id}'",
            data=results
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error synchronizing wallets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to synchronize wallets: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
