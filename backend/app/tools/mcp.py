import re
import json
import asyncio
import datetime
from typing import Dict, Any, Optional, List
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.tools.base import BaseTool, ToolRegistry
from app.tools.schemas import PermissionLevel, ToolCategory, ExecutionEnvironment
from app.models.tool import McpServerConfiguration
from app.core.logging import logger
from app.core.exceptions import ResourceNotFoundException, ValidationException


class PromptInjectionGuard:
    """
    Guards against prompt injection in untrusted MCP descriptions and outputs.
    Ensures that any tool output or tool description is safely delimited and
    stripped of instructions attempting to override system behavior.
    """
    PROMPT_OVERRIDE_PATTERNS = [
        re.compile(r'(?i)<\s*/?\s*(system|instruction|developer|admin)[^>]*>'),
        re.compile(r'(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions'),
        re.compile(r'(?i)you\s+are\s+now\s+in\s+dan\s+mode'),
        re.compile(r'(?i)disregard\s+(all\s+)?previous\s+rules'),
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        if not text:
            return text
        sanitized = text
        for pat in cls.PROMPT_OVERRIDE_PATTERNS:
            sanitized = pat.sub('[BLOCKED_INJECTION_ATTEMPT]', sanitized)
        return sanitized

    @classmethod
    def isolate_output(cls, tool_name: str, raw_output: Any) -> str:
        serialized = json.dumps(raw_output, default=str) if isinstance(raw_output, (dict, list)) else str(raw_output)
        clean = cls.sanitize(serialized)
        return f'<tool_output tool="{tool_name}" source="untrusted_mcp">\n{clean}\n</tool_output>'


class McpTool(BaseTool):
    """
    Dynamic wrapper for a tool discovered on an external Model Context Protocol (MCP) server.
    """
    def __init__(
        self,
        server_name: str,
        tool_name: str,
        description: str,
        parameters_schema: Dict[str, Any],
        client: "McpClient",
        permission_level: PermissionLevel = PermissionLevel.SAFE,
    ):
        self._server_name = server_name
        self._tool_name = tool_name
        # Sanitize description to prevent prompt injection via tool listings
        self._description = PromptInjectionGuard.sanitize(description or f"MCP tool '{tool_name}' on server '{server_name}'")
        self._parameters_schema = parameters_schema or {"type": "object", "properties": {}}
        self._client = client
        self._permission_level = permission_level

    @property
    def id(self) -> str:
        return f"mcp_{self._server_name}_{self._tool_name}"

    @property
    def name(self) -> str:
        return self.id

    @property
    def description(self) -> str:
        return f"[{self._server_name}] {self._description}"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.MCP

    @property
    def execution_environment(self) -> ExecutionEnvironment:
        return ExecutionEnvironment.MCP

    @property
    def permission_level(self) -> PermissionLevel:
        return self._permission_level

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return self._parameters_schema

    async def run(self, **kwargs) -> Any:
        raw_result = await self._client.call_tool(self._tool_name, kwargs)
        # Isolate and sanitize untrusted output
        return PromptInjectionGuard.isolate_output(self.name, raw_result)


class McpClient:
    """
    Communicates with an MCP server via JSON-RPC over stdio or HTTP/SSE.
    """
    def __init__(
        self,
        server_type: str,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: float = 15.0,
    ):
        self.server_type = server_type
        self.command = command
        self.args = args or []
        self.url = url
        self.headers = headers or {}
        self.env = env or {}
        self.timeout = timeout

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Queries MCP server for tools/list."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }
        response = await self._send_request(payload)
        if "error" in response:
            raise RuntimeError(f"MCP tools/list error: {response['error']}")
        
        result = response.get("result", {})
        if not isinstance(result, dict) or "tools" not in result:
            raise ValueError(f"Malformed MCP response: Missing 'tools' array in result: {result}")
        
        return result.get("tools", [])

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Invokes a tool via MCP tools/call."""
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments,
            },
        }
        response = await self._send_request(payload)
        if "error" in response:
            raise RuntimeError(f"MCP tools/call error: {response['error']}")
        
        result = response.get("result", {})
        # Normalize MCP content structure: [{"type": "text", "text": "..."}]
        if isinstance(result, dict) and "content" in result:
            contents = result["content"]
            if isinstance(contents, list) and len(contents) > 0:
                first = contents[0]
                if isinstance(first, dict) and "text" in first:
                    try:
                        return json.loads(first["text"])
                    except Exception:
                        return first["text"]
            return contents
        return result

    async def _send_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if self.server_type in ("http", "sse"):
            if not self.url:
                raise ValueError("Missing URL for HTTP/SSE MCP server.")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    self.url,
                    json=payload,
                    headers={"Content-Type": "application/json", **self.headers},
                )
                res.raise_for_status()
                return res.json()

        elif self.server_type == "stdio":
            if not self.command:
                raise ValueError("Missing command for stdio MCP server.")
            
            proc = None
            try:
                proc = await asyncio.create_subprocess_exec(
                    self.command,
                    *self.args,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdin_data = json.dumps(payload).encode("utf-8") + b"\n"
                stdout_data, stderr_data = await asyncio.wait_for(
                    proc.communicate(stdin_data),
                    timeout=self.timeout,
                )
                if proc.returncode != 0:
                    err_text = stderr_data.decode("utf-8", errors="replace")
                    raise RuntimeError(f"MCP server process exited with code {proc.returncode}: {err_text}")
                
                output_str = stdout_data.decode("utf-8", errors="replace").strip()
                # Parse JSON-RPC line from stdout
                lines = [l.strip() for l in output_str.splitlines() if l.strip()]
                for line in reversed(lines):
                    if line.startswith("{") and line.endswith("}"):
                        return json.loads(line)
                raise ValueError(f"No valid JSON-RPC response in stdout: {output_str[:300]}")
            except asyncio.TimeoutError:
                if proc:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                raise TimeoutError(f"MCP server communication timed out after {self.timeout}s.")
        else:
            raise ValueError(f"Unsupported MCP server type: {self.server_type}")


class McpServerManager:
    """
    Manages configured MCP servers, coordinates discovery, and registers tools.
    """
    @classmethod
    async def discover_and_register_server(
        cls,
        server: McpServerConfiguration,
        db: AsyncSession,
    ) -> int:
        now = datetime.datetime.now(datetime.timezone.utc)
        if not server.is_enabled:
            server.status = "disabled"
            await db.commit()
            return 0

        args = []
        if server.args_json:
            try:
                args = json.loads(server.args_json)
            except Exception:
                pass

        headers = {}
        if server.headers_json:
            try:
                headers = json.loads(server.headers_json)
            except Exception:
                pass

        client = McpClient(
            server_type=server.server_type,
            command=server.command,
            args=args,
            url=server.url,
            headers=headers,
        )

        try:
            tools_list = await client.list_tools()
            registered_count = 0
            for t in tools_list:
                t_name = t.get("name")
                if not t_name:
                    continue
                t_desc = t.get("description", "")
                t_schema = t.get("inputSchema", {}) or {"type": "object", "properties": {}}
                
                mcp_tool = McpTool(
                    server_name=server.name,
                    tool_name=t_name,
                    description=t_desc,
                    parameters_schema=t_schema,
                    client=client,
                    permission_level=PermissionLevel.SAFE,
                )
                ToolRegistry.register(mcp_tool)
                registered_count += 1

            server.status = "connected"
            server.last_health_check = now
            server.last_error = None
            server.discovered_tools_count = registered_count
            await db.commit()
            return registered_count

        except Exception as exc:
            logger.error(f"Failed to discover tools for MCP server '{server.name}': {exc}")
            server.status = "error"
            server.last_health_check = now
            server.last_error = str(exc)
            await db.commit()
            raise
