#!/usr/bin/env python3
"""
FastAPI server for Crypto Taxes Portfolio Management
Provides REST API endpoints for wallet management operations
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import os
import sys

# Add the current directory to Python path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wallets.portfolio import Portfolio
from wallets.wallet_enums import WalletType
from db import init_db, engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Crypto Taxes Portfolio API",
    description="API for managing cryptocurrency wallets and portfolios",
    version="1.0.0"
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
    skip_auth: Optional[bool] = Field(False, description="Skip external authentication (testing only)")

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

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

# Global portfolio instance
portfolio = None

@app.on_event("startup")
async def startup_event():
    """Initialize the portfolio on startup."""
    global portfolio
    try:
        # Ensure database tables exist (safe if DB not used yet)
        init_db()
        portfolio = Portfolio(reference_asset="EUR")
        logger.info("Portfolio initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize portfolio: {e}")
        raise

@app.get("/", response_model=ApiResponse)
async def root():
    """Root endpoint with API information."""
    return ApiResponse(
        success=True,
        message="Crypto Taxes Portfolio API is running",
        data={
            "version": "1.0.0",
            "endpoints": {
                "list_wallets": "/wallets",
                "add_wallet": "/wallets",
                "get_wallet": "/wallets/{wallet_id}",
                "remove_wallet": "/wallets/{wallet_id}",
                "synchronize_wallets": "/wallets/synchronize"
            }
        }
    )

@app.get("/wallets", response_model=ApiResponse)
async def list_wallets():
    """List all wallets in the portfolio."""
    try:
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Portfolio not initialized"
            )
        
        wallets = portfolio.list_wallets()
        return ApiResponse(
            success=True,
            message=f"Found {len(wallets)} wallets",
            data=wallets
        )
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

@app.post("/wallets", response_model=ApiResponse)
async def add_wallet(wallet_request: WalletCreateRequest):
    """Add a new wallet to the portfolio."""
    try:
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Portfolio not initialized"
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

        wallet_id = portfolio.add_wallet(
            wallet_type=wallet_type_enum,
            name=wallet_request.name,
            api_key=wallet_request.api_key,
            api_secret=wallet_request.api_secret,
            description=wallet_request.description,
            skip_auth=bool(wallet_request.skip_auth)
        )

        logger.info(f"Wallet ID: {wallet_id}")
        
        if wallet_id:
            return ApiResponse(
                success=True,
                message=f"Wallet '{wallet_request.name}' added successfully",
                data={"wallet_id": wallet_id}
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

@app.get("/wallets/{wallet_id}", response_model=ApiResponse)
async def get_wallet(wallet_id: str):
    """
    Get a specific wallet by ID.
    It MUST not return sensitive data like api_key and api_secret.
    """
    try:
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Portfolio not initialized"
            )
        
        wallet = portfolio.get_wallet_by_id(wallet_id)

        # Remove api_key and api_secret from the wallet
        wallet.pop("api_key", None)
        wallet.pop("api_secret", None)

        if wallet:
            return ApiResponse(
                success=True,
                message="Wallet found",
                data=wallet
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet with ID '{wallet_id}' not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get wallet: {str(e)}"
        )

@app.delete("/wallets/{wallet_id}", response_model=ApiResponse)
async def remove_wallet(wallet_id: str):
    """Remove a wallet from the portfolio."""
    try:
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Portfolio not initialized"
            )
        
        success = portfolio.remove_wallet(wallet_id)
        if success:
            return ApiResponse(
                success=True,
                message=f"Wallet '{wallet_id}' removed successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet with ID '{wallet_id}' not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove wallet: {str(e)}"
        )

@app.post("/wallets/synchronize", response_model=ApiResponse)
async def synchronize_wallets(start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Synchronize all wallets in the portfolio."""
    try:
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Portfolio not initialized"
            )
        
        results = portfolio.synchronize_all_wallets(start_date, end_date)
        return ApiResponse(
            success=True,
            message="Synchronization completed",
            data=results
        )
    except Exception as e:
        logger.error(f"Error synchronizing wallets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to synchronize wallets: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
