import os
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

APP_NAME = "mcp-fastapi-websearch"
APP_VERSION = "0.1.0"

app = FastAPI(title=APP_NAME, version=APP_VERSION)
load_dotenv()


class ChatRequest(BaseModel):
    message: str = Field(..., description="User input text")
    count: int = Field(5, description="Number of search results to return")


def _jsonrpc_response(_id: Any, result: Optional[Any] = None, error: Optional[Dict[str, Any]] = None) -> JSONResponse:
    payload: Dict[str, Any] = {"jsonrpc": "2.0", "id": _id}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result
    return JSONResponse(payload)


@app.post("/mcp")
async def mcp_endpoint(req: Request) -> JSONResponse:
    body = await req.json()
    method = body.get("method")
    params = body.get("params") or {}
    _id = body.get("id")

    if method == "initialize":
        return _jsonrpc_response(
            _id,
            result={
                "serverInfo": {"name": APP_NAME, "version": APP_VERSION},
                "capabilities": {"tools": True},
            },
        )

    if method == "tools/list":
        return _jsonrpc_response(
            _id,
            result={
                "tools": [
                    {
                        "name": "web_search",
                        "description": "Search the web using Brave Search API.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query string."},
                                "count": {"type": "integer", "description": "Number of results to return.", "default": 5},
                            },
                            "required": ["query"],
                        },
                    }
                ]
            },
        )

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        if tool_name != "web_search":
            return _jsonrpc_response(
                _id,
                error={"code": -32601, "message": f"Unknown tool: {tool_name}"},
            )

        query = arguments.get("query")
        if not query:
            return _jsonrpc_response(
                _id,
                error={"code": -32602, "message": "Missing required argument: query"},
            )
        count = int(arguments.get("count") or 5)

        result = await brave_search(query=query, count=count)
        return _jsonrpc_response(
            _id,
            result={
                "content": [
                    {
                        "type": "text",
                        "text": result,
                    }
                ]
            },
        )

    return _jsonrpc_response(_id, error={"code": -32601, "message": f"Unknown method: {method}"})


async def brave_search(query: str, count: int = 5) -> str:
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        lines = [f"Search results for: {query}", "Retrieved at: (stubbed)"]
        for i in range(1, min(count, 3) + 1):
            lines.append(f"{i}. Stub result {i}\n   https://example.com/{i}\n   This is a stubbed search result.")
        return "\n".join(lines)

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
    params = {"q": query, "count": count}

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Brave API error: {resp.status_code} {resp.text}")
        data = resp.json()

    web = data.get("web", {})
    results: List[Dict[str, Any]] = web.get("results", []) or []

    lines = [f"Search results for: {query}", f"Retrieved at: {time.strftime('%Y-%m-%d %H:%M:%S')}"]
    for i, item in enumerate(results[:count], start=1):
        title = item.get("title") or "Untitled"
        url = item.get("url") or ""
        description = (item.get("description") or "").strip()
        lines.append(f"{i}. {title}\n   {url}\n   {description}")
    return "\n".join(lines)


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: ChatRequest) -> Dict[str, Any]:
    mcp_url = os.getenv("MCP_URL", "http://127.0.0.1:8000/mcp")
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "web_search",
            "arguments": {"query": req.message, "count": req.count},
        },
    }

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(mcp_url, json=payload)
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"MCP error: {resp.status_code} {resp.text}")
        data = resp.json()

    if "error" in data:
        raise HTTPException(status_code=500, detail=f"MCP error: {data['error']}")

    return {"result": data.get("result")}
