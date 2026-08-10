from openprompt.core.ast.models import PromptAST, RoleSpec


def test_ast_clone(sample_ast: PromptAST) -> None:
    cloned = sample_ast.clone()
    cloned.role = RoleSpec(description="different", enabled=True)
    assert sample_ast.role
    assert sample_ast.role.description == "an expert assistant"


def test_ast_token_estimate(sample_ast: PromptAST) -> None:
    assert sample_ast.estimate_tokens() > 0
