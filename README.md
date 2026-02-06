# MCP FastAPI Web Search Server

Minimal MCP-style JSON-RPC server using FastAPI with a `web_search` tool backed by Brave Search API.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set your Brave Search API key:

```bash
export BRAVE_API_KEY="your_key_here"
```

Run the server:

```bash
uvicorn app:app --reload --port 8000
```

## MCP JSON-RPC Usage

Initialize:

```bash
curl -s http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

List tools:

```bash
curl -s http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

Call the web search tool:

```bash
curl -s http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "id":3,
    "method":"tools/call",
    "params":{
      "name":"web_search",
      "arguments":{"query":"fastapi mcp server","count":3}
    }
  }'
```

Health check:

```bash
curl -s http://127.0.0.1:8000/health
```

## Chat Endpoint (calls MCP web_search)

The `/chat` endpoint accepts user input and forwards it to the MCP `tools/call` for `web_search`.

```bash
curl -s http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Michael Jordan","count":3}'
```
