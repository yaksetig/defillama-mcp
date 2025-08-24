import os
from typing import Any, Dict, List
import httpx
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Get port from Railway's environment variable
port = int(os.environ.get("PORT", 8080))

# Create FastAPI app
app = FastAPI(
    title="DeFi Llama API Server",
    description="DeFi Llama data API server for Railway deployment",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
DEFI_API_BASE = "https://api.llama.fi"
COIN_API_BASE = "https://coins.llama.fi"
YIELDS_API_BASE = "https://yields.llama.fi"
USER_AGENT = "DEFI-MCP/1.0"

# Request models
class TokenPriceRequest(BaseModel):
    token: str

class ProtocolRequest(BaseModel):
    protocol: str

class ChainRequest(BaseModel):
    chain: str

class PoolRequest(BaseModel):
    pool: str

async def make_request(url: str) -> Dict[str, Any] | List | None:
    """Make a request to the API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error {e.response.status_code} for {url}: {e.response.text}")
            return None
        except httpx.RequestError as e:
            print(f"Request error for {url}: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error for {url}: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error for {url}: {str(e)}")
            return None

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "DeFi Llama API Server",
        "version": "1.0.0",
        "endpoints": {
            "protocols": "/protocols",
            "protocol_tvl": "/protocol/{protocol}",
            "chain_tvl": "/chain/{chain}",
            "token_prices": "/token/{token}",
            "pools": "/pools",
            "pool_tvl": "/pool/{pool}"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "defillama-api"}

@app.get("/protocols")
async def get_protocols():
    """Retrieve a list of all DeFi protocols from DeFi Llama, limited to the first 20 results."""
    url = f"{DEFI_API_BASE}/protocols"
    data = await make_request(url)
    
    if data is None:
        raise HTTPException(status_code=500, detail="Failed to fetch protocols")
    
    return {"protocols": data[:20]}

@app.get("/protocol/{protocol}")
async def get_protocol_tvl(protocol: str):
    """Get Total Value Locked (TVL) information for a specific DeFi protocol.
    
    Example:
    - protocol="aave" - Returns TVL data for Aave protocol across different chains
    - protocol="uniswap" - Returns TVL data for Uniswap protocol across different chains
    """
    url = f"{DEFI_API_BASE}/protocol/{protocol}"
    data = await make_request(url)
    
    if data is None:
        raise HTTPException(status_code=500, detail=f"Failed to fetch TVL for protocol: {protocol}")
    
    return {
        "protocol": protocol,
        "current_chain_tvls": data.get("currentChainTvls", {}),
        "metadata": {
            "name": data.get("name"),
            "symbol": data.get("symbol"),
            "url": data.get("url"),
            "description": data.get("description"),
            "chain": data.get("chain"),
            "logo": data.get("logo"),
            "category": data.get("category")
        }
    }

@app.get("/chain/{chain}")
async def get_chain_tvl(chain: str):
    """Retrieve historical Total Value Locked (TVL) data for a specific blockchain.
    
    Example:
    - chain="ethereum" - Returns historical TVL data for Ethereum blockchain
    - chain="bsc" - Returns historical TVL data for Binance Smart Chain
    """
    url = f"{DEFI_API_BASE}/v2/historicalChainTvl/{chain}"
    data = await make_request(url)
    
    if data is None:
        raise HTTPException(status_code=500, detail=f"Failed to fetch TVL for chain: {chain}")
    
    return {
        "chain": chain,
        "tvl_data": data[:30]
    }

@app.get("/token/{token}")
async def get_token_prices(token: str):
    """Get current price information for a specific token.
    
    Example:
    - token="ethereum:0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2" - WETH token
    - token="bsc:0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c" - WBNB token
    - token="coingecko:ethereum" - Ethereum via CoinGecko ID
    """
    url = f"{COIN_API_BASE}/prices/current/{token}"
    data = await make_request(url)
    
    if data is None:
        raise HTTPException(status_code=500, detail=f"Failed to fetch price for token: {token}")
    
    return {
        "token": token,
        "price_data": data
    }

@app.get("/pools")
async def get_pools():
    """Retrieve a list of all liquidity pools from DeFi Llama, limited to the first 30 results."""
    url = f"{YIELDS_API_BASE}/pools"
    data = await make_request(url)
    
    if data is None:
        raise HTTPException(status_code=500, detail="Failed to fetch pools")
    
    if isinstance(data, dict) and 'data' in data:
        return {"pools": data['data'][:30]}
    
    return {"pools": data[:30] if isinstance(data, list) else data}

@app.get("/pool/{pool}")
async def get_pool_tvl(pool: str):
    """Get detailed information about a specific liquidity pool by its ID.
    
    Example:
    - pool="747c1d2a-c668-4682-b9f9-296708a3dd90" - Returns detailed data for the specified pool
    """
    url = f"{YIELDS_API_BASE}/chart/{pool}"
    data = await make_request(url)
    
    if data is None:
        raise HTTPException(status_code=500, detail=f"Failed to fetch pool data for: {pool}")
    
    if isinstance(data, dict) and 'data' in data:
        return {
            "pool_id": pool,
            "chart_data": data['data'][:30],
            "status": data.get('status')
        }
    
    return {
        "pool_id": pool,
        "data": data[:30] if isinstance(data, list) else data
    }

# Alternative POST endpoints for more complex requests
@app.post("/protocols")
async def get_protocols_post():
    """POST version of get_protocols for consistency."""
    return await get_protocols()

@app.post("/protocol")
async def get_protocol_tvl_post(request: ProtocolRequest):
    """POST version of get_protocol_tvl."""
    return await get_protocol_tvl(request.protocol)

@app.post("/chain")
async def get_chain_tvl_post(request: ChainRequest):
    """POST version of get_chain_tvl."""
    return await get_chain_tvl(request.chain)

@app.post("/token")
async def get_token_prices_post(request: TokenPriceRequest):
    """POST version of get_token_prices."""
    return await get_token_prices(request.token)

@app.post("/pools")
async def get_pools_post():
    """POST version of get_pools."""
    return await get_pools()

@app.post("/pool")
async def get_pool_tvl_post(request: PoolRequest):
    """POST version of get_pool_tvl."""
    return await get_pool_tvl(request.pool)

if __name__ == "__main__":
    print(f"Starting DeFi Llama API server on port {port}")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )
