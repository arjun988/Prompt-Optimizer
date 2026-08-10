"""Example strategy plugin — wraps rewrite with a custom report line."""

from __future__ import annotations

from openprompt.core.ast.models import PromptAST
from openprompt.core.optimizer.models import OptimizeResult
from openprompt.core.optimizer.strategies import StrategyContext, _strategy_rewrite


class PassthroughRewriteStrategy:
    """Demo plugin strategy registered via entry point."""

    name = "passthrough_rewrite"

    def run(self, ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
        result = _strategy_rewrite(ast, ctx)
        result.strategy = self.name
        result.report_lines.append("Executed via passthrough_rewrite plugin strategy.")
        return result
