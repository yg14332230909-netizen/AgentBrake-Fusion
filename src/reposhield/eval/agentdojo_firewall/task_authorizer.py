"""Non-oracle task authorization helper for AgentDojo.

This helper intentionally avoids InjectionTask.ground_truth.  Optional allowed
hints may be supplied by an evaluation harness, but the default path only uses
user task text, tool category, and tool arguments.
"""
from __future__ import annotations

from typing import Any

from .types import ToolCallContext, ToolSpec

KEYWORDS_BY_GROUP = {
    "financial_commit": ("pay", "bill", "transfer", "send money", "payment", "schedule transaction"),
    "external_send": ("send", "email", "message", "share", "notify", "reply"),
    "booking_commit": ("book", "reserve", "hotel", "restaurant", "car rental", "flight"),
    "calendar_mutation": ("calendar", "event", "meeting", "schedule", "reschedule", "cancel"),
    "workspace_mutation": ("file", "create", "append", "write", "update"),
    "destructive_update": ("delete", "remove", "cancel"),
    "membership_mutation": ("invite", "add", "remove", "channel", "slack"),
    "credential_change": ("password", "credential"),
}

def task_authorizes_tool(context: ToolCallContext, spec: ToolSpec) -> bool:
    if context.tool_name in context.allowed_tools:
        return True
    if spec.group in context.allowed_groups:
        return True
    if not spec.side_effect:
        return True
    task = str(context.user_task).lower()
    if not task:
        return False
    if any(keyword in task for keyword in KEYWORDS_BY_GROUP.get(spec.group, ())) :
        return True
    for value in context.tool_args.values():
        if isinstance(value, str) and len(value) >= 3 and value.lower() in task:
            return True
    return False

def sensitive_args_not_in_user_task(args: dict[str, Any], spec: ToolSpec, user_task: str) -> bool:
    task = str(user_task).lower()
    for key in spec.sensitive_args:
        value = args.get(key)
        if isinstance(value, str) and len(value) >= 3 and value.lower() not in task:
            return True
    return False
