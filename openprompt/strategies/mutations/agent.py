"""Agent / tool-description mutation operator."""

from __future__ import annotations

from openprompt.core.ast.models import AgentSpec, PromptAST
from openprompt.core.optimizer.agent_strategy import optimize_tool_descriptions
from openprompt.core.optimizer.strategies import StrategyContext
from openprompt.strategies.mutations.base import OptimizeContext


class AgentMutation:
    name = "agent"

    def mutate(self, ast: PromptAST, context: OptimizeContext) -> PromptAST:
        updated = ast.clone()
        agent = updated.agent or AgentSpec(
            system_prompt="You are a precise tool-using agent.",
            planning_prompt="Plan before calling tools.",
            tool_use_prompt="Emit valid JSON tool calls only.",
        )
        if agent.tools:
            dummy_ctx = StrategyContext(provider=_DummyProvider(), config=None)
            agent.tools = optimize_tool_descriptions(agent.tools, dummy_ctx)
        updated.agent = agent
        constraints = list(updated.constraints)
        constraints.append("Validate tool arguments against each tool JSON schema before calling.")
        updated.constraints = constraints
        return updated


class _DummyProvider:
    name = "mock"
    model = "mock-model"

    def generate(self, *args, **kwargs):
        raise NotImplementedError
