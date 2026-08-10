"""Agent and tool-description optimization strategy."""

from __future__ import annotations

from openprompt.core.ast.models import AgentSpec, PromptAST, ToolSpec
from openprompt.core.optimizer.models import OptimizeResult
from openprompt.core.optimizer.strategies import (
    StrategyContext,
    _evaluate_ast,
    _heuristic_warnings,
    _strategy_hybrid,
)


def strategy_agent(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    """Optimize system, planning, and tool-description layers."""
    working = ast.clone()
    if not working.agent:
        working.agent = AgentSpec(
            system_prompt="You are a capable agent that uses tools precisely.",
            planning_prompt="Before acting, outline steps and select the minimum tools needed.",
            tool_use_prompt="Call tools with valid JSON arguments matching each tool schema.",
        )

    agent = working.agent
    if agent.tools:
        tool_lines = ["Available tools:"]
        for tool in agent.tools:
            tool_lines.append(f"- {tool.name}: {tool.description}")
            if tool.parameters_schema:
                tool_lines.append(f"  Parameters schema: {tool.parameters_schema}")
        working.context.append("\n".join(tool_lines))

    constraints = list(working.constraints)
    constraints.extend(
        [
            "Never invent tool names not listed in the tool catalog.",
            "Return tool calls as JSON objects with 'name' and 'arguments' fields.",
            f"Limit to at most {agent.max_tool_calls} tool calls per turn.",
        ]
    )
    working.constraints = constraints

    if agent.system_prompt and (not working.role or not working.role.description):
        from openprompt.core.ast.models import RoleSpec

        working.role = RoleSpec(description=agent.system_prompt, enabled=True)

    result = _strategy_hybrid(working, ctx)
    result.strategy = "agent"
    result.report_lines = [
        "Agent layer optimization: system + planning + tool descriptions + hybrid search.",
        *result.report_lines,
    ]
    result.warnings = _heuristic_warnings(ctx)
    return result


def optimize_tool_descriptions(tools: list[ToolSpec], ctx: StrategyContext) -> list[ToolSpec]:
    """Refine tool descriptions for clarity and schema completeness."""
    improved: list[ToolSpec] = []
    for tool in tools:
        desc = tool.description.strip()
        if len(desc) < 40:
            desc = f"{desc}. Use when the user request matches this tool's purpose."
        schema = tool.parameters_schema or {"type": "object", "properties": {}}
        if "type" not in schema:
            schema = {"type": "object", "properties": schema.get("properties", {})}
        improved.append(
            ToolSpec(
                name=tool.name,
                description=desc,
                parameters_schema=schema,
                examples=tool.examples,
            )
        )
    return improved
