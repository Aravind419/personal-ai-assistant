from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import time
from app.core.logging import logger


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


class BaseTool(ABC):
    """
    Abstract interface for backend-executed agent tools.
    Execution is strictly sandboxed on the backend without arbitrary shell/filesystem privileges.
    """
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
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON Schema definition for tool arguments."""
        pass

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """Internal tool execution logic."""
        pass

    async def execute(self, tool_call_id: str, arguments: Dict[str, Any]) -> ToolCallResult:
        """
        Validates arguments and executes the tool with latency measurement and error handling.
        """
        start = time.perf_counter()
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


class ToolRegistry:
    """
    Central registry for inspecting and dispatching backend agent tools.
    """
    _tools: Dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool: BaseTool):
        cls._tools[tool.name] = tool

    @classmethod
    def get(cls, name: str) -> Optional[BaseTool]:
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters_schema,
                },
            }
            for t in cls._tools.values()
        ]

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
        return await tool.execute(request.id, request.arguments)
