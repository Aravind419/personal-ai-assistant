#!/usr/bin/env python3
"""
Controlled real MCP test server communicating over JSON-RPC stdio.
Used for real MCP integration validation in Phase 3.1.
"""
import sys
import json
import time


def main():
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "real-test-stdio-server", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                },
            }
        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "echo_tool",
                            "description": "Echoes text safely",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"msg": {"type": "string"}},
                                "required": ["msg"],
                            },
                        },
                        {
                            "name": "slow_tool",
                            "description": "Simulates slow execution",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"delay": {"type": "number"}},
                            },
                        },
                        {
                            "name": "malformed_output_tool",
                            "description": "Returns raw text without standard wrapper",
                            "inputSchema": {"type": "object", "properties": {}},
                        },
                    ]
                },
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            if tool_name == "echo_tool":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": f"Echoed: {args.get('msg', '')}"}
                        ]
                    },
                }
            elif tool_name == "slow_tool":
                delay = float(args.get("delay", 1.0))
                time.sleep(delay)
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": f"Finished after {delay}s"}
                        ]
                    },
                }
            elif tool_name == "malformed_output_tool":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"raw_custom_field": "non_standard_data"},
                }
            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                }
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32600, "message": f"Unsupported method: {method}"},
            }

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
