import os
import json
import asyncio
from typing import Any, Dict, List
import httpx
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Get port from Railway's environment variable
port = int(os.environ.get("PORT", 8080))

app = FastAPI()

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
        except Exception as e:
            print(f"Error making request to {url}: {str(e)}")
            return None

# MCP Protocol endpoints
@app.get("/")
async def root():
    return {
        "jsonrpc": "2.0",
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "defillama-mcp",
                "version": "1.0.0"
            }
        }
    }

@app.post("/")
async def handle_mcp_request(request: Request):
    """Handle MCP JSON-RPC requests"""
    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "defillama-mcp",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "get_protocols",
                            "description": "Retrieve a list of all DeFi protocols from DeFi Llama, limited to the first 20 results",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "get_protocol_tvl",
                            "description": "Get Total Value Locked (TVL) information for a specific DeFi protocol",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "protocol": {
                                        "type": "string",
                                        "description": "Protocol name (e.g., 'aave', 'uniswap')"
                                    }
                                },
                                "required": ["protocol"]
                            }
                        },
                        {
                            "name": "get_chain_tvl",
                            "description": "Retrieve historical Total Value Locked (TVL) data for a specific blockchain",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "chain": {
                                        "type": "string",
                                        "description": "Chain name (e.g., 'ethereum', 'bsc')"
                                    }
                                },
                                "required": ["chain"]
                            }
                        },
                        {
                            "name": "get_token_prices",
                            "description": "Get current price information for a specific token",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "token": {
                                        "type": "string",
                                        "description": "Token identifier (e.g., 'ethereum:0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2')"
                                    }
                                },
                                "required": ["token"]
                            }
                        },
                        {
                            "name": "get_pools",
                            "description": "Retrieve a list of all liquidity pools from DeFi Llama, limited to the first 30 results",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        },
                        {
                            "name": "get_pool_tvl",
                            "description": "Get detailed information about a specific liquidity pool by its ID",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "pool": {
                                        "type": "string",
                                        "description": "Pool ID"
                                    }
                                },
                                "required": ["pool"]
                            }
                        }
                    ]
                }
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "get_protocols":
                result = await get_protocols()
            elif tool_name == "get_protocol_tvl":
                result = await get_protocol_tvl(arguments.get("protocol"))
            elif tool_name == "get_chain_tvl":
                result = await get_chain_tvl(arguments.get("chain"))
            elif tool_name == "get_token_prices":
                result = await get_token_prices(arguments.get("token"))
            elif tool_name == "get_pools":
                result = await get_pools()
            elif tool_name == "get_pool_tvl":
                result = await get_pool_tvl(arguments.get("pool"))
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {tool_name}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": body.get("id") if 'body' in locals() else None,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

# Tool implementations
async def get_protocols():
    """Get all protocols from defillama."""
    url = f"{DEFI_API_BASE}/protocols"
    data = await make_request(url)
    if data is None:
        return {"error": "Failed to fetch protocols"}
    return {"protocols": data[:20]}

async def get_protocol_tvl(protocol: str):
    """Get a defi protocol tvl from defillama"""
    if not protocol:
        return {"error": "Protocol name is required"}
    
    url = f"{DEFI_API_BASE}/protocol/{protocol}"
    data = await make_request(url)
    if data is None:
        return {"error": f"Failed to fetch TVL for protocol: {protocol}"}
    
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

async def get_chain_tvl(chain: str):
    """Get a chain's tvl"""
    if not chain:
        return {"error": "Chain name is required"}
        
    url = f"{DEFI_API_BASE}/v2/historicalChainTvl/{chain}"
    data = await make_request(url)
    if data is None:
        return {"error": f"Failed to fetch TVL for chain: {chain}"}
    return {"chain": chain, "tvl_data": data[:30]}

async def get_token_prices(token: str):
    """Get a token's price"""
    if not token:
        return {"error": "Token identifier is required"}
        
    url = f"{COIN_API_BASE}/prices/current/{token}"
    data = await make_request(url)
    if data is None:
        return {"error": f"Failed to fetch price for token: {token}"}
    return {"token": token, "price_data": data}

async def get_pools():
    """Get all pools from defillama."""
    url = f"{YIELDS_API_BASE}/pools"
    data = await make_request(url)
    if data is None:
        return {"error": "Failed to fetch pools"}
    
    if isinstance(data, dict) and 'data' in data:
        return {"pools": data['data'][:30]}
    return {"pools": data[:30] if isinstance(data, list) else data}

async def get_pool_tvl(pool: str):
    """Get a pool's tvl from defillama."""
    if not pool:
        return {"error": "Pool ID is required"}
        
    url = f"{YIELDS_API_BASE}/chart/{pool}"
    data = await make_request(url)
    if data is None:
        return {"error": f"Failed to fetch pool data for: {pool}"}
    
    if isinstance(data, dict) and 'data' in data:
        return {"pool_id": pool, "chart_data": data['data'][:30], "status": data.get('status')}
    return {"pool_id": pool, "data": data[:30] if isinstance(data, list) else data}

if __name__ == "__main__":
    print(f"Starting MCP server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
