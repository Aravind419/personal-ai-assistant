import pytest
from app.tools.base import ToolRegistry, ToolCallRequest
from app.tools.builtin import SystemClockTool, CalculatorTool


@pytest.mark.asyncio
async def test_tool_registry():
    tools = ToolRegistry.list_tools()
    tool_names = [t["function"]["name"] for t in tools]
    assert "get_system_time" in tool_names
    assert "calculate" in tool_names


@pytest.mark.asyncio
async def test_system_clock_tool():
    req = ToolCallRequest(id="call_1", name="get_system_time", arguments={})
    result = await ToolRegistry.dispatch(req)
    assert result.success is True
    assert "iso" in result.result
    assert "UTC" in result.result["time"]


@pytest.mark.asyncio
async def test_calculator_tool_operations():
    # Multiply
    req = ToolCallRequest(
        id="call_2",
        name="calculate",
        arguments={"operation": "multiply", "a": 7, "b": 6},
    )
    result = await ToolRegistry.dispatch(req)
    assert result.success is True
    assert result.result["result"] == 42.0

    # Division by zero
    req_div_zero = ToolCallRequest(
        id="call_3",
        name="calculate",
        arguments={"operation": "divide", "a": 10, "b": 0},
    )
    res_zero = await ToolRegistry.dispatch(req_div_zero)
    assert res_zero.success is False
    assert "division by zero" in res_zero.error.lower()


@pytest.mark.asyncio
async def test_unregistered_tool():
    req = ToolCallRequest(id="call_4", name="unknown_shell_exec", arguments={})
    res = await ToolRegistry.dispatch(req)
    assert res.success is False
    assert "not registered" in res.error.lower()
