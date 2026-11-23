from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import time
import re
from pydantic import BaseModel, Field

from app.core.logging import logger
from app.tools.schemas import (
    PermissionLevel,
    ToolCategory,
    ExecutionEnvironment,
    ToolDefinitionResponse,
)
from app.tools.validator import ToolSchemaValidator


class ToolCallRequest(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolCallResult(BaseModel):
    id: str
    name: str
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None
    approval_id: Optional[str] = None
    awaiting_approval: bool = False


class BaseTool(ABC):
    """
    Abstract interface for backend-executed agent tools.
    Every tool defines its schemas, permission level, risk classification,
    and timeout. Execution is strictly controlled without arbitrary shell/code privileges.
    """
    @property
    def id(self) -> str:
        return self.name

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Natural language description for model function-calling schemas."""
        pass

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SYSTEM

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON Schema definition for tool arguments."""
        pass

    @property
    def output_schema(self) -> Optional[Dict[str, Any]]:
        return None

    @property
    def permission_level(self) -> PermissionLevel:
        """Permission tier: safe (Level 1), sensitive (Level 2), critical (Level 3)."""
        return PermissionLevel.SAFE

    @property
    def risk_classification(self) -> str:
        if self.permission_level == PermissionLevel.CRITICAL:
            return "critical"
        elif self.permission_level == PermissionLevel.SENSITIVE:
            return "medium"
        return "low"

    @property
    def timeout_seconds(self) -> float:
        return 30.0

    @property
    def requires_approval(self) -> bool:
        return self.permission_level in (PermissionLevel.SENSITIVE, PermissionLevel.CRITICAL)

    @property
    def is_enabled(self) -> bool:
        return True

    @property
    def execution_environment(self) -> ExecutionEnvironment:
        return ExecutionEnvironment.BUILTIN

    @property
    def availability_status(self) -> str:
        return "available"

    def extract_target_resource(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Extracts the primary target resource (file path, table, endpoint) from arguments."""
        for key in ["path", "file_path", "filename", "resource", "target", "query", "url"]:
            if key in arguments:
                return str(arguments[key])
        return None

    def build_consequence_summary(self, arguments: Dict[str, Any]) -> str:
        """Generates a human-readable explanation of what will occur if approved."""
        res = self.extract_target_resource(arguments)
        if res:
            return f"Executes action '{self.name}' targeting resource: {res}"
        return f"Executes action '{self.name}' with {len(arguments)} parameter(s)."

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """Internal tool execution logic."""
        pass

    async def execute(self, tool_call_id: str, arguments: Dict[str, Any]) -> ToolCallResult:
        """
        Validates arguments against parameters_schema and executes the tool with latency measurement.
        """
        start = time.perf_counter()
        
        # Schema validation
        valid, err_msg = ToolSchemaValidator.validate(self.parameters_schema, arguments)
        if not valid:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return ToolCallResult(
                id=tool_call_id,
                name=self.name,
                success=False,
                error=err_msg,
                latency_ms=latency,
            )

        try:
            res = await self.run(**arguments)
            latency = round((time.perf_counter() - start) * 1000, 2)
            return ToolCallResult(
                id=tool_call_id,
                name=self.name,
                success=True,
                result=res,
                latency_ms=latency,
            )
        except Exception as exc:
            latency = round((time.perf_counter() - start) * 1000, 2)
            logger.warning(f"Tool {self.name} failed during execution: {exc}")
            return ToolCallResult(
                id=tool_call_id,
                name=self.name,
                success=False,
                error=str(exc),
                latency_ms=latency,
            )

    def to_openai_tool_schema(self) -> Dict[str, Any]:
        """Returns standard OpenAI/OpenRouter function schema for the tool."""
        # Clean function name to strictly match standard ^[a-zA-Z0-9_-]+$
        clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", self.id)
        return {
            "type": "function",
            "function": {
                "name": clean_name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }

    def to_definition_response(self) -> ToolDefinitionResponse:
        return ToolDefinitionResponse(
            id=self.id,
            name=self.name,
            description=self.description,
            category=self.category,
            parameters_schema=self.parameters_schema,
            output_schema=self.output_schema,
            permission_level=self.permission_level,
            risk_classification=self.risk_classification,
            timeout_seconds=self.timeout_seconds,
            requires_approval=self.requires_approval,
            is_enabled=self.is_enabled,
            execution_environment=self.execution_environment,
            availability_status=self.availability_status,
        )


class ToolRegistry:
    """
    Central registry for inspecting and dispatching backend agent tools.
    """
    _tools: Dict[str, BaseTool] = {}
    _disabled_tools: set[str] = set()

    @classmethod
    def register(cls, tool: BaseTool):
        cls._tools[tool.name] = tool
        if hasattr(tool, "id") and tool.id:
            cls._tools[tool.id] = tool

    @classmethod
    def unregister(cls, name: str):
        tool = cls._tools.pop(name, None)
        if tool:
            cls._tools.pop(tool.name, None)
            if hasattr(tool, "id") and tool.id:
                cls._tools.pop(tool.id, None)
        cls._disabled_tools.discard(name)

    @classmethod
    def get(cls, name: str) -> Optional[BaseTool]:
        if not name:
            return None
        # 1. Exact match
        if name in cls._tools:
            return cls._tools[name]
        # 2. Case-insensitive match
        name_lower = name.strip().lower()
        for k, v in cls._tools.items():
            if k.lower() == name_lower:
                return v
        # 3. Normalized snake_case match (e.g. "Get Gmail Profile" -> "gmail_get_profile")
        normalized = re.sub(r"[^a-zA-Z0-9]+", "_", name_lower).strip("_")
        for k, v in cls._tools.items():
            k_norm = re.sub(r"[^a-zA-Z0-9]+", "_", k.lower()).strip("_")
            if k_norm == normalized or (hasattr(v, "id") and v.id == normalized):
                return v
        return None

    @classmethod
    def has(cls, name: str) -> bool:
        return cls.get(name) is not None

    @classmethod
    def is_enabled(cls, name: str) -> bool:
        tool = cls.get(name)
        if not tool:
            return False
        if tool.name in cls._disabled_tools or (hasattr(tool, "id") and tool.id in cls._disabled_tools):
            return False
        return tool.is_enabled

    @classmethod
    def set_enabled(cls, name: str, enabled: bool):
        tool = cls.get(name)
        if tool:
            target_names = {tool.name}
            if hasattr(tool, "id") and tool.id:
                target_names.add(tool.id)
            for t_name in target_names:
                if enabled:
                    cls._disabled_tools.discard(t_name)
                else:
                    cls._disabled_tools.add(t_name)

    @classmethod
    def _unique_tools(cls) -> List[BaseTool]:
        """Returns unique tool instances without ID/name duplicates."""
        seen = set()
        unique = []
        for tool in cls._tools.values():
            tool_key = getattr(tool, "id", None) or tool.name
            if tool_key not in seen:
                seen.add(tool_key)
                unique.append(tool)
        return unique

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        """Returns OpenAI-compatible function definition schemas for enabled tools."""
        return [
            t.to_openai_tool_schema()
            for t in cls._unique_tools()
            if cls.is_enabled(getattr(t, "id", t.name))
        ]

    @classmethod
    def list_all_definitions(cls) -> List[ToolDefinitionResponse]:
        """Returns rich tool definitions including permissions and status."""
        definitions = []
        for t in cls._unique_tools():
            defn = t.to_definition_response()
            tool_key = getattr(t, "id", t.name)
            if tool_key in cls._disabled_tools or t.name in cls._disabled_tools:
                defn.is_enabled = False
            definitions.append(defn)
        return definitions

    @classmethod
    async def dispatch(cls, request: ToolCallRequest) -> ToolCallResult:
        tool = cls.get(request.name)
        if not tool:
            return ToolCallResult(
                id=request.id,
                name=request.name,
                success=False,
                error=f"Tool '{request.name}' is not registered in the system.",
            )
        if not cls.is_enabled(request.name):
            return ToolCallResult(
                id=request.id,
                name=request.name,
                success=False,
                error=f"Tool '{request.name}' is currently disabled by administrative policy.",
            )
        return await tool.execute(request.id, request.arguments)
