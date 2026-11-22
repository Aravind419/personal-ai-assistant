from typing import Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool, ToolRegistry
from app.tools.schemas import PermissionLevel
from app.tools.approval_manager import ApprovalManager
from app.models.tool import ToolApproval


class ToolPermissionEngine:
    """
    Evaluates whether a tool execution is authorized under configured permissions
    or requires user approval.
    """

    @classmethod
    async def evaluate_execution(
        cls,
        tool: BaseTool,
        arguments: Dict[str, Any],
        approval_id: Optional[str] = None,
        force_skip_approval: bool = False,
        db: Optional[AsyncSession] = None,
    ) -> Tuple[bool, Optional[str], Optional[ToolApproval]]:
        """
        Returns (is_authorized, denial_or_approval_reason, approval_instance).
        """
        # 1. Check if tool is enabled in the registry
        if not ToolRegistry.is_enabled(tool.name):
            return False, f"Tool '{tool.name}' is currently disabled.", None

        # 2. Check permission level
        # Level 1 — Safe actions: auto-execute
        if tool.permission_level == PermissionLevel.SAFE and not tool.requires_approval:
            return True, None, None

        # Override for testing or direct programmatic authorization if specified
        if force_skip_approval:
            return True, None, None

        # Level 2 (Sensitive) and Level 3 (Critical) actions require valid approval
        if not approval_id:
            reason = (
                f"Action '{tool.name}' is classified as {tool.permission_level.value.upper()} "
                f"({tool.risk_classification} risk) and requires explicit human-in-the-loop approval."
            )
            return False, reason, None

        # If approval_id is provided, validate it against the database
        if not db:
            return False, "Database session required to validate approval.", None

        valid, err_msg, approval = await ApprovalManager.validate_approval_for_arguments(
            approval_id=approval_id,
            arguments=arguments,
            db=db,
        )
        if not valid:
            return False, err_msg, approval

        return True, None, approval
