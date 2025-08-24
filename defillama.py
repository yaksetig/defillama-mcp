import os
from typing import Any
import httpx
import json
from mcp.server.fastmcp import FastMCP

# Get port from Railway's environment variable
port = int(os.environ.get("PORT", 8080))

# Initialize Defillama mcp server with correct host and port
# Use stdio transport instead of sse for better compatibility
mcp = FastMCP("defillama-mcp")

# Constants
DEFI_API_BASE = "https://api.llama.fi"
COIN_API_BASE = "https://coins.llama.fi"
YIELDS_API_BASE = "https://yields.llama.fi"
USER_AGENT = "DEFI-MCP/1.0"

@mcp.tool(
   description="Retrieve a list of all DeFi protocols from DeFi Llama, limited to the first 20 results"
)
async def get_protocols() -> dict[Any, Any]:
   """Get all protocols from defillama.
   """
   url = f"{DEFI_API_BASE}/protocols"
   data = await make_request(url)
   if data is None:
       return {"error": "Failed to fetch protocols"}
   return {"protocols": data[:20]}

@mcp.tool(
   description="Get Total Value Locked (TVL) information for a specific DeFi protocol"
)
async def get_protocol_tvl(protocol: str) -> dict[Any, Any]:
   """Get a defi protocol tvl from defillama
   
   Args:
       protocol: protocol name
       
   Example:
       - protocol="aave" - Returns TVL data for Aave protocol across different chains
       - protocol="uniswap" - Returns TVL data for Uniswap protocol across different chains
   """
   url = f"{DEFI_API_BASE}/protocol/{protocol}"
   data = await make_request(url)
   if data is None:
       return {"error": f"Failed to fetch TVL for protocol: {protocol}"}
   return data.get("currentChainTvls", data)

@mcp.tool(
   description="Retrieve historical Total Value Locked (TVL) data for a specific blockchain"
)
async def get_chain_tvl(chain: str) -> dict[Any, Any]:
   """Get a chain's tvl

   Args:
       chain: chain name
       
   Example:
       - chain="ethereum" - Returns historical TVL data for Ethereum blockchain
       - chain="bsc" - Returns historical TVL data for Binance Smart Chain
   """
   url = f"{DEFI_API_BASE}/v2/historicalChainTvl/{chain}"
   data = await make_request(url)
   if data is None:
       return {"error": f"Failed to fetch TVL for chain: {chain}"}
   return {"chain": chain, "tvl_data": data[:30]}

@mcp.tool(
   description="Get current price information for a specific token, for example token=ethereum:0xdF574c24545E5FfEcb9a659c229253D4111d87e1 token=coingecko:ethereum"
)
async def get_token_prices(token: str) -> dict[Any, Any]:
   """Get a token's price
   
   Args:
       token: token name
   Example:
       - token="ethereum:0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2" - Returns price information for WETH token
       - token="bsc:0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c" - Returns price information for WBNB token
   """
   url = f"{COIN_API_BASE}/prices/current/{token}"
   data = await make_request(url)
   if data is None:
       return {"error": f"Failed to fetch price for token: {token}"}
   return data

@mcp.tool(
   description="Retrieve a list of all liquidity pools from DeFi Llama, limited to the first 30 results"
)
async def get_pools() -> dict[str, Any]:
   """Get all pools from defillama.
   """
   url = f"{YIELDS_API_BASE}/pools"
   data = await make_request(url)
   if data is None:
       return {"error": "Failed to fetch pools"}
   
   if isinstance(data, dict) and 'data' in data:
       return {"pools": data['data'][:30]}
   return {"pools": data[:30] if isinstance(data, list) else data}

@mcp.tool(
   description="Get detailed information about a specific liquidity pool by its ID")
async def get_pool_tvl(pool: str) -> dict[str, Any]:
   """Get a pool's tvl from defillama.
   
   Args:
       pool: pool id
       
   Example:
       - pool="747c1d2a-c668-4682-b9f9-296708a3dd90" - Returns detailed data for the specified pool
       - pool="2cbc5e8f-b7ef-4568-8e8e-1a7543af4e5f" - Returns detailed data for the specified pool
   """
   url = f"{YIELDS_API_BASE}/chart/{pool}"
   data = await make_request(url)
   if data is None:
       return {"error": f"Failed to fetch pool data for: {pool}"}
   
   if isinstance(data, dict) and 'data' in data:
       return {"pool_id": pool, "data": data['data'][:30]}
   return {"pool_id": pool, "data": data[:30] if isinstance(data, list) else data}

async def make_request(url: str) -> dict[str, Any] | list | None:
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

if __name__ == "__main__":
    # For Railway deployment, we need to use stdio transport
    # Railway expects the MCP server to communicate via stdin/stdout
    mcp.run()  # This defaults to stdio transport
