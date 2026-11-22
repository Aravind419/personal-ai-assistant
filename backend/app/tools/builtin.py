import datetime
import math
from typing import Dict, Any
from app.tools.base import BaseTool, ToolRegistry


class SystemClockTool(BaseTool):
    """Safe tool providing accurate server time and date."""
    @property
    def name(self) -> str:
        return "get_system_time"

    @property
    def description(self) -> str:
        return "Returns current server date, time, and UTC offset."

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": [],
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
    """Deterministic, safe arithmetic calculator without arbitrary Python code eval."""
    @property
    def name(self) -> str:
        return "calculate"

    @property
    def description(self) -> str:
        return "Evaluates basic mathematical operations (addition, subtraction, multiplication, division, exponents)."

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


# Register built-in baseline safe tools
ToolRegistry.register(SystemClockTool())
ToolRegistry.register(CalculatorTool())
