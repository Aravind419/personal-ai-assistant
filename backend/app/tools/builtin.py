import os
import re
import json
import math
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.tools.base import BaseTool, ToolRegistry
from app.tools.schemas import PermissionLevel, ToolCategory, ExecutionEnvironment

WORKSPACE_STORAGE_DIR = Path(os.getcwd()) / "workspace_storage"
WORKSPACE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_READ_BYTES = 5 * 1024 * 1024   # 5 MB read cap
MAX_FILE_WRITE_BYTES = 5 * 1024 * 1024  # 5 MB write cap


def _validate_safe_path(rel_or_abs_path: str) -> Path:
    """
    Strictly validates that the target file path resides within the sandboxed
    workspace storage directory and prevents directory traversal attacks,
    symlink escapes, null-byte injection, and access to sensitive files.
    """
    if not rel_or_abs_path or not str(rel_or_abs_path).strip():
        raise PermissionError("Access denied: Target file path cannot be empty.")

    # 1. Null-byte injection defense
    if "\0" in str(rel_or_abs_path):
        raise PermissionError("Access denied: Null byte in file path.")

    workspace_root = WORKSPACE_STORAGE_DIR.resolve()
    clean_path = Path(rel_or_abs_path).expanduser()

    # 2. Check for symlinks in raw path before resolution
    raw_path = (workspace_root / clean_path) if not clean_path.is_absolute() else clean_path
    if os.path.islink(raw_path):
        raise PermissionError("Access denied: Symlinks are prohibited in the sandboxed workspace.")

    # 3. Resolve target
    target = raw_path.resolve()

    # 4. Check for symlinks on resolved target and in hierarchy
    if os.path.islink(target):
        raise PermissionError("Access denied: Symlinks are prohibited in the sandboxed workspace.")

    curr = raw_path
    while curr != workspace_root and curr.parent != curr:
        if os.path.islink(curr):
            raise PermissionError("Access denied: Symlinks in path hierarchy are prohibited.")
        curr = curr.parent

    # 5. Must reside strictly within workspace storage directory
    try:
        rel = target.relative_to(workspace_root)
    except ValueError:
        raise PermissionError(
            f"Access denied: Path '{rel_or_abs_path}' traverses outside the sandboxed workspace directory."
        )

    # 6. Cannot target the root workspace directory itself
    if target == workspace_root:
        raise PermissionError("Access denied: Cannot perform file operations directly on the workspace root directory.")

    # 7. Block sensitive directories and file patterns anywhere in the path hierarchy
    forbidden_parts = {
        ".git", ".env", ".ssh", ".aws", ".azure", ".kube",
        ".gnupg", ".config", "node_modules", ".venv", "__pycache__"
    }
    for part in target.parts:
        part_lower = part.lower()
        if part_lower in forbidden_parts or part_lower.startswith(".env"):
            raise PermissionError(f"Access denied: Access to sensitive path component '{part}' is strictly blocked.")

    # 8. Block sensitive filenames
    blocked_filenames = {
        ".env", "id_rsa", "id_ed25519", "id_dsa", "id_ecdsa",
        "credentials", "config.json", "id_rsa.pub", ".bash_history",
        "known_hosts", "authorized_keys"
    }
    if target.name.lower() in blocked_filenames or target.name.lower().startswith(".env"):
        raise PermissionError(f"Access denied: Access to sensitive file '{target.name}' is strictly blocked.")

    return target


class SystemClockTool(BaseTool):
    """Safe tool providing accurate server time, date, and timezone offset."""
    @property
    def name(self) -> str:
        return "get_system_time"

    @property
    def description(self) -> str:
        return "Returns current server date, time, and UTC offset."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SYSTEM

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }

    async def run(self, **kwargs) -> Dict[str, Any]:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        return {
            "iso": now_utc.isoformat(),
            "date": now_utc.strftime("%Y-%m-%d"),
            "time": now_utc.strftime("%H:%M:%S UTC"),
            "timestamp": now_utc.timestamp(),
        }


class CalculatorTool(BaseTool):
    """Deterministic, safe arithmetic calculator without arbitrary code eval."""
    @property
    def name(self) -> str:
        return "calculate"

    @property
    def description(self) -> str:
        return "Evaluates basic mathematical operations (addition, subtraction, multiplication, division, exponents, square root)."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.MATH

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide", "power", "sqrt"],
                    "description": "Mathematical operation to perform",
                },
                "a": {"type": "number", "description": "First operand"},
                "b": {"type": "number", "description": "Second operand (optional for sqrt)"},
            },
            "required": ["operation", "a"],
            "additionalProperties": False,
        }

    async def run(self, operation: str, a: float, b: float = 0.0, **kwargs) -> Dict[str, Any]:
        if operation == "add":
            res = a + b
        elif operation == "subtract":
            res = a - b
        elif operation == "multiply":
            res = a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("Division by zero is undefined.")
            res = a / b
        elif operation == "power":
            res = math.pow(a, b)
        elif operation == "sqrt":
            if a < 0:
                raise ValueError("Square root of negative number is not a real number.")
            res = math.sqrt(a)
        else:
            raise ValueError(f"Unsupported operation: {operation}")

        return {"operation": operation, "result": res}


class TextProcessorTool(BaseTool):
    """Safe deterministic text analysis and transformation tool."""
    @property
    def name(self) -> str:
        return "text_processor"

    @property
    def description(self) -> str:
        return "Performs text processing: word count, line count, character count, casing transforms, substring replacement, or regex search."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.TEXT

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Input text to process"},
                "action": {
                    "type": "string",
                    "enum": ["stats", "uppercase", "lowercase", "replace", "regex_search"],
                    "description": "Text operation",
                },
                "search_pattern": {"type": "string", "description": "Pattern to search or replace"},
                "replacement": {"type": "string", "description": "Replacement string for 'replace' action"},
            },
            "required": ["text", "action"],
            "additionalProperties": False,
        }

    async def run(
        self,
        text: str,
        action: str,
        search_pattern: Optional[str] = None,
        replacement: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        if action == "stats":
            lines = text.splitlines()
            words = text.split()
            return {
                "action": action,
                "character_count": len(text),
                "word_count": len(words),
                "line_count": len(lines),
            }
        elif action == "uppercase":
            return {"action": action, "result": text.upper()}
        elif action == "lowercase":
            return {"action": action, "result": text.lower()}
        elif action == "replace":
            if not search_pattern:
                raise ValueError("Missing 'search_pattern' for replace action.")
            rep = replacement or ""
            return {"action": action, "result": text.replace(search_pattern, rep)}
        elif action == "regex_search":
            if not search_pattern:
                raise ValueError("Missing 'search_pattern' for regex_search action.")
            matches = re.findall(search_pattern, text[:10000])  # bound regex check
            return {"action": action, "matches": matches[:50], "total_matches": len(matches)}
        else:
            raise ValueError(f"Unsupported action: {action}")


class JsonValidatorTool(BaseTool):
    """Validates and formats JSON strings."""
    @property
    def name(self) -> str:
        return "json_validator"

    @property
    def description(self) -> str:
        return "Parses, validates, and formats structured JSON strings."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DEVELOPER

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "json_string": {"type": "string", "description": "Raw JSON string to validate"},
                "indent": {"type": "integer", "description": "Number of indentation spaces (default 2)"},
            },
            "required": ["json_string"],
            "additionalProperties": False,
        }

    async def run(self, json_string: str, indent: int = 2, **kwargs) -> Dict[str, Any]:
        try:
            parsed = json.loads(json_string)
            formatted = json.dumps(parsed, indent=indent)
            return {
                "is_valid": True,
                "type": type(parsed).__name__,
                "formatted": formatted,
            }
        except json.JSONDecodeError as err:
            return {
                "is_valid": False,
                "error": str(err),
                "line": err.lineno,
                "column": err.colno,
            }


class FileReaderTool(BaseTool):
    """Safe tool for reading text files in the authorized workspace storage."""
    @property
    def name(self) -> str:
        return "file_reader"

    @property
    def description(self) -> str:
        return "Reads content from an authorized file in the sandboxed workspace."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative filename or path within workspace_storage"},
                "max_lines": {"type": "integer", "description": "Maximum lines to read (default 500)"},
            },
            "required": ["file_path"],
            "additionalProperties": False,
        }

    def extract_target_resource(self, arguments: Dict[str, Any]) -> Optional[str]:
        return arguments.get("file_path")

    async def run(self, file_path: str, max_lines: int = 500, **kwargs) -> Dict[str, Any]:
        safe_path = _validate_safe_path(file_path)
        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not safe_path.is_file():
            raise ValueError(f"Path is not a regular file: {file_path}")

        file_size = safe_path.stat().st_size
        if file_size > MAX_FILE_READ_BYTES:
            raise ValueError(
                f"File size ({file_size} bytes) exceeds maximum allowable read limit of {MAX_FILE_READ_BYTES} bytes."
            )

        with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
            lines = []
            for _ in range(max_lines):
                line = f.readline(65536)  # Bound line read length
                if not line:
                    break
                lines.append(line)
            content = "".join(lines)

        return {
            "file_path": str(safe_path.name),
            "size_bytes": file_size,
            "lines_read": len(lines),
            "content": content,
        }


class FileSearcherTool(BaseTool):
    """Searches files in the authorized workspace storage."""
    @property
    def name(self) -> str:
        return "file_searcher"

    @property
    def description(self) -> str:
        return "Searches for files matching a pattern or containing query text in the workspace."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern (e.g. *.txt, *.json)"},
                "query": {"type": "string", "description": "Optional text to search inside matching files"},
            },
            "required": ["pattern"],
            "additionalProperties": False,
        }

    async def run(self, pattern: str, query: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        matches = []
        for file in WORKSPACE_STORAGE_DIR.glob(pattern):
            if file.is_file():
                match_info: Dict[str, Any] = {
                    "filename": file.name,
                    "size_bytes": file.stat().st_size,
                }
                if query:
                    try:
                        with open(file, "r", encoding="utf-8", errors="replace") as f:
                            text = f.read()
                            if query.lower() in text.lower():
                                match_info["matched_query"] = True
                                matches.append(match_info)
                    except Exception:
                        pass
                else:
                    matches.append(match_info)

        return {"pattern": pattern, "results_count": len(matches), "matches": matches[:50]}


class FileWriterTool(BaseTool):
    """
    Level 2 Sensitive tool: Writes or updates a file in workspace storage.
    Requires explicit user approval before execution.
    """
    @property
    def name(self) -> str:
        return "file_writer"

    @property
    def description(self) -> str:
        return "Writes or updates text content in an authorized file in the workspace storage."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SENSITIVE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Filename or path within workspace_storage"},
                "content": {"type": "string", "description": "Text content to write"},
                "mode": {"type": "string", "enum": ["overwrite", "append"], "description": "Write mode (default: overwrite)"},
            },
            "required": ["file_path", "content"],
            "additionalProperties": False,
        }

    def extract_target_resource(self, arguments: Dict[str, Any]) -> Optional[str]:
        return arguments.get("file_path")

    def build_consequence_summary(self, arguments: Dict[str, Any]) -> str:
        fp = arguments.get("file_path", "unknown")
        mode = arguments.get("mode", "overwrite")
        content_len = len(arguments.get("content", ""))
        return f"Will {mode} file '{fp}' with {content_len} characters of text."

    async def run(self, file_path: str, content: str, mode: str = "overwrite", **kwargs) -> Dict[str, Any]:
        safe_path = _validate_safe_path(file_path)
        content_bytes = content.encode("utf-8")
        if len(content_bytes) > MAX_FILE_WRITE_BYTES:
            raise ValueError(
                f"Content size ({len(content_bytes)} bytes) exceeds maximum write limit of {MAX_FILE_WRITE_BYTES} bytes."
            )

        if mode == "append" and safe_path.exists():
            if safe_path.stat().st_size + len(content_bytes) > MAX_FILE_WRITE_BYTES:
                raise ValueError(
                    f"Resulting file size would exceed maximum write limit of {MAX_FILE_WRITE_BYTES} bytes."
                )

        write_mode = "a" if mode == "append" else "w"

        with open(safe_path, write_mode, encoding="utf-8") as f:
            f.write(content)

        return {
            "file_path": str(safe_path.name),
            "bytes_written": len(content_bytes),
            "mode": mode,
            "status": "written_successfully",
        }


class FileDeleterTool(BaseTool):
    """
    Level 3 Critical tool: Deletes a file in workspace storage.
    Requires explicit action-specific critical confirmation.
    """
    @property
    def name(self) -> str:
        return "file_deleter"

    @property
    def description(self) -> str:
        return "Permanently removes a file from the workspace storage directory."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.CRITICAL

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Filename to delete within workspace_storage"},
            },
            "required": ["file_path"],
            "additionalProperties": False,
        }

    def extract_target_resource(self, arguments: Dict[str, Any]) -> Optional[str]:
        return arguments.get("file_path")

    def build_consequence_summary(self, arguments: Dict[str, Any]) -> str:
        fp = arguments.get("file_path", "unknown")
        return f"DANGER: Permanently deletes file '{fp}'. This operation cannot be undone."

    async def run(self, file_path: str, **kwargs) -> Dict[str, Any]:
        safe_path = _validate_safe_path(file_path)
        if safe_path.name in {".gitkeep", ".gitignore"}:
            raise PermissionError(f"Cannot delete protected infrastructure file: {safe_path.name}")

        if not safe_path.exists():
            raise FileNotFoundError(f"Cannot delete: File '{file_path}' does not exist.")
        if not safe_path.is_file():
            raise ValueError(f"Cannot delete: '{file_path}' is not a regular file.")

        safe_path.unlink()
        return {
            "file_path": str(safe_path.name),
            "status": "deleted_successfully",
        }


# ============================================================================
#                         EXPANDED REAL AGENT TOOLS
# ============================================================================

import csv
import io
import asyncio
import sys
import httpx
from urllib.parse import urlparse


class WebSearchTool(BaseTool):
    """Real web search tool using DuckDuckGo API/HTML search."""
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Searches the live public web for current information, news, and technical documentation."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.WEB

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "description": "Search expression or question"},
                "max_results": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
            },
        }

    async def run(self, query: str, max_results: int = 5, **kwargs) -> Dict[str, Any]:
        if not query or not query.strip():
            return {"query": query, "results": [], "count": 0}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        try:
            # 1. DuckDuckGo Instant Answer API
            api_url = "https://api.duckduckgo.com/"
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(
                    api_url,
                    params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
                    headers=headers,
                )
                results = []
                if resp.status_code == 200:
                    data = resp.json()
                    abstract = data.get("AbstractText")
                    abstract_url = data.get("AbstractURL")
                    source = data.get("AbstractSource")
                    if abstract and abstract_url:
                        results.append({
                            "title": data.get("Heading") or source or "Overview",
                            "url": abstract_url,
                            "snippet": abstract,
                        })

                    for topic in data.get("RelatedTopics", []):
                        if len(results) >= max_results:
                            break
                        if isinstance(topic, dict) and topic.get("Text") and topic.get("FirstURL"):
                            results.append({
                                "title": topic.get("Text")[:60] + "...",
                                "url": topic.get("FirstURL"),
                                "snippet": topic.get("Text"),
                            })

                # If instant answer returned results, return them
                if results:
                    return {
                        "query": query,
                        "count": len(results),
                        "results": results,
                    }

                # 2. Fallback to DuckDuckGo HTML search
                html_resp = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers=headers,
                )
                if html_resp.status_code == 200:
                    # Regex extract results
                    pattern = re.compile(
                        r'<a class="result__url" href="(?P<url>[^"]+)".*?<a class="result__snippet[^>]*>(?P<snippet>.*?)</a>',
                        re.DOTALL | re.IGNORECASE,
                    )
                    matches = list(pattern.finditer(html_resp.text))
                    for m in matches[:max_results]:
                        url = m.group("url").strip()
                        raw_snip = m.group("snippet")
                        clean_snip = re.sub(r'<[^>]+>', '', raw_snip).strip()
                        results.append({
                            "title": query,
                            "url": url,
                            "snippet": clean_snip,
                        })

                return {
                    "query": query,
                    "count": len(results),
                    "results": results if results else [{"message": "No direct search results found for this query."}],
                }
        except Exception as e:
            return {"query": query, "count": 0, "error": f"Web search failed: {str(e)}", "results": []}


class WebFetchPageTool(BaseTool):
    """Fetches and cleans live text content from a web page."""
    @property
    def name(self) -> str:
        return "web_fetch_page"

    @property
    def description(self) -> str:
        return "Fetches clean readable text from a public web page URL (excluding scripts, styling, and navigation)."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.WEB

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string", "description": "Public HTTP/HTTPS URL to fetch"},
            },
        }

    async def run(self, url: str, **kwargs) -> Dict[str, Any]:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {"error": "Invalid URL scheme. Only http and https are permitted."}

        # SSRF protection: block loopback and private ranges
        host = (parsed.hostname or "").lower()
        if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or host.startswith("192.168.") or host.startswith("10."):
            return {"error": "Access to local/private network addresses is blocked for security."}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    return {"url": url, "status_code": resp.status_code, "error": f"HTTP {resp.status_code}"}

                content_type = resp.headers.get("content-type", "")
                if "html" not in content_type and "text" not in content_type:
                    return {"url": url, "content_type": content_type, "message": "Binary or non-text content."}

                raw_html = resp.text
                # Remove scripts, styles, header, footer, nav
                clean = re.sub(r'<script.*?</script>', ' ', raw_html, flags=re.DOTALL | re.IGNORECASE)
                clean = re.sub(r'<style.*?</style>', ' ', clean, flags=re.DOTALL | re.IGNORECASE)
                clean = re.sub(r'<nav.*?</nav>', ' ', clean, flags=re.DOTALL | re.IGNORECASE)
                clean = re.sub(r'<header.*?</header>', ' ', clean, flags=re.DOTALL | re.IGNORECASE)
                clean = re.sub(r'<footer.*?</footer>', ' ', clean, flags=re.DOTALL | re.IGNORECASE)
                # Strip all HTML tags
                text = re.sub(r'<[^>]+>', ' ', clean)
                # Collapse whitespace
                text = re.sub(r'\s+', ' ', text).strip()

                # Extract title
                title_match = re.search(r'<title>(.*?)</title>', raw_html, re.IGNORECASE | re.DOTALL)
                title = title_match.group(1).strip() if title_match else parsed.netloc

                max_chars = 6000
                truncated = len(text) > max_chars
                return {
                    "url": url,
                    "title": title,
                    "character_count": len(text),
                    "truncated": truncated,
                    "text": text[:max_chars] + ("... [truncated]" if truncated else ""),
                }
        except Exception as e:
            return {"url": url, "error": f"Failed to fetch page: {str(e)}"}


class DataReadCsvTool(BaseTool):
    """Inspects a CSV file in the sandboxed workspace."""
    @property
    def name(self) -> str:
        return "data_read_csv"

    @property
    def description(self) -> str:
        return "Reads a CSV file from workspace storage and returns column headers, row counts, and preview data."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FILE

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["file_path"],
            "properties": {
                "file_path": {"type": "string", "description": "Filename of CSV file in workspace_storage"},
                "preview_rows": {"type": "integer", "default": 5, "maximum": 20},
            },
        }

    async def run(self, file_path: str, preview_rows: int = 5, **kwargs) -> Dict[str, Any]:
        safe_path = _validate_safe_path(file_path)
        if not safe_path.exists():
            return {"error": f"File '{file_path}' does not exist in workspace storage."}

        with open(safe_path, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            headers = next(reader, [])
            rows = []
            total_rows = 0
            for r in reader:
                total_rows += 1
                if len(rows) < preview_rows:
                    rows.append(r)

        return {
            "file": safe_path.name,
            "headers": headers,
            "total_rows": total_rows,
            "preview_rows": rows,
        }


class DataStatisticsTool(BaseTool):
    """Calculates statistical metrics for numeric columns in a CSV file."""
    @property
    def name(self) -> str:
        return "data_statistics"

    @property
    def description(self) -> str:
        return "Calculates count, sum, mean, median, min, and max for numeric columns in a workspace CSV file."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.MATH

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SAFE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["file_path", "column_name"],
            "properties": {
                "file_path": {"type": "string", "description": "CSV filename in workspace_storage"},
                "column_name": {"type": "string", "description": "Name of numeric column to analyze"},
            },
        }

    async def run(self, file_path: str, column_name: str, **kwargs) -> Dict[str, Any]:
        safe_path = _validate_safe_path(file_path)
        if not safe_path.exists():
            return {"error": f"File '{file_path}' does not exist."}

        values: List[float] = []
        with open(safe_path, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or column_name not in reader.fieldnames:
                return {
                    "error": f"Column '{column_name}' not found. Available columns: {reader.fieldnames or []}"
                }
            for row in reader:
                val_str = (row.get(column_name) or "").strip().replace(",", "")
                if val_str:
                    try:
                        values.append(float(val_str))
                    except ValueError:
                        pass

        if not values:
            return {"error": f"No numeric values found in column '{column_name}'."}

        values.sort()
        count = len(values)
        total = sum(values)
        mean = total / count
        median = values[count // 2] if count % 2 != 0 else (values[count // 2 - 1] + values[count // 2]) / 2.0
        min_val = values[0]
        max_val = values[-1]

        return {
            "file": safe_path.name,
            "column": column_name,
            "count": count,
            "sum": round(total, 4),
            "mean": round(mean, 4),
            "median": round(median, 4),
            "min": min_val,
            "max": max_val,
        }


class CodeExecutionPythonTool(BaseTool):
    """Controlled, isolated Python execution with timeout and output caps."""
    @property
    def name(self) -> str:
        return "code_execution_python"

    @property
    def description(self) -> str:
        return "Executes Python code in an isolated subprocess with a strict 5-second timeout and blocked host environment."

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DEVELOPER

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.SENSITIVE

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["code"],
            "properties": {
                "code": {"type": "string", "description": "Python code snippet to execute"},
            },
        }

    async def run(self, code: str, **kwargs) -> Dict[str, Any]:
        # Clean execution environment: strip database credentials and API secrets
        safe_env = {
            "PYTHONIOENCODING": "utf-8",
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "TEMP": str(WORKSPACE_STORAGE_DIR),
        }

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                code,
                cwd=str(WORKSPACE_STORAGE_DIR),
                env=safe_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            stdout = stdout_bytes.decode("utf-8", errors="replace")[:8000]
            stderr = stderr_bytes.decode("utf-8", errors="replace")[:4000]

            return {
                "exit_code": proc.returncode,
                "success": proc.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
            }
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return {"success": False, "error": "Execution timed out after 5.0 seconds."}
        except Exception as e:
            return {"success": False, "error": f"Subprocess failed: {str(e)}"}


# Register all native built-in tools
ToolRegistry.register(SystemClockTool())
ToolRegistry.register(CalculatorTool())
ToolRegistry.register(TextProcessorTool())
ToolRegistry.register(JsonValidatorTool())
ToolRegistry.register(FileReaderTool())
ToolRegistry.register(FileSearcherTool())
ToolRegistry.register(FileWriterTool())
ToolRegistry.register(FileDeleterTool())

# Register new agent capabilities
ToolRegistry.register(WebSearchTool())
ToolRegistry.register(WebFetchPageTool())
ToolRegistry.register(DataReadCsvTool())
ToolRegistry.register(DataStatisticsTool())
ToolRegistry.register(CodeExecutionPythonTool())

