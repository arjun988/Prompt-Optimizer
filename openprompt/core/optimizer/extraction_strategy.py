"""Few-shot auto-selection strategy."""

from __future__ import annotations

from openprompt.core.ast.models import PromptAST
from openprompt.core.dataset.models import load_dataset
from openprompt.core.optimizer.few_shot import apply_few_shot_to_ast, select_few_shot_examples
from openprompt.core.optimizer.models import OptimizeResult
from openprompt.core.optimizer.strategies import StrategyContext, _heuristic_warnings, _strategy_hybrid


def strategy_few_shot(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    """Select diverse few-shot examples then run hybrid optimization."""
    working = ast.clone()
    pool = list(working.examples)

    if working.dataset and working.dataset.example_pool_path:
        from pathlib import Path

        ds = load_dataset(Path(working.dataset.example_pool_path).parent)
        pool.extend(ds.example_pool)

    if not pool and ctx.config and ctx.config.evaluation.example_pool_path:
        from pathlib import Path

        ds = load_dataset(ctx.config.evaluation.example_pool_path)
        pool.extend(ds.example_pool)

    k = 3
    if ctx.config and ctx.config.optimizer.few_shot_count:
        k = ctx.config.optimizer.few_shot_count

    task_desc = working.objective.raw if working.objective and working.objective.raw else ""
    selection = select_few_shot_examples(pool, k=k, task_description=task_desc, difficulty_tests=ctx.tests)
    working = apply_few_shot_to_ast(working, selection.selected)

    result = _strategy_hybrid(working, ctx)
    result.strategy = "few_shot"
    result.report_lines = [selection.reason, *result.report_lines]
    result.warnings = _heuristic_warnings(ctx)
    return result


def strategy_extraction(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    """Dataset-aware extraction optimization: few-shot + GRPO + hybrid."""
    from openprompt.core.optimizer.grpo import strategy_grpo

    working = ast.clone()
    if working.dataset and working.dataset.path:
        from pathlib import Path

        from openprompt.core.dataset.models import dataset_to_test_cases, load_dataset

        ds = load_dataset(working.dataset.path)
        if not ctx.tests:
            ctx.tests = dataset_to_test_cases(ds)
        if ds.field_schema and (not working.output or not working.output.schema_):
            from openprompt.core.ast.models import OutputFormat, OutputSpec

            working.output = OutputSpec(format=OutputFormat.JSON, schema=ds.field_schema)

    few_result = strategy_few_shot(working, ctx)
    grpo_result = strategy_grpo(few_result.optimized, ctx)
    grpo_result.strategy = "extraction"
    grpo_result.report_lines = [
        "Extraction optimization: dataset-linked few-shot + GRPO + eval validation.",
        *few_result.report_lines,
        *grpo_result.report_lines,
    ]
    return grpo_result
