"""FastAPI REST server for OpenPrompt."""

from __future__ import annotations

from openprompt import __version__
from openprompt.config.models import ServerConfig
from openprompt.core.dataset.models import load_dataset
from openprompt.providers.errors import ProviderError
from openprompt.server.client_factory import openprompt_client
from openprompt.server.dataset_handlers import run_dataset_eval, run_dataset_optimize
from openprompt.server.dataset_upload import (
    parse_labels_json,
    parse_schema_json,
    temp_dataset_from_upload,
)
from openprompt.server.middleware import configure_middleware
from openprompt.server.schemas import (
    BenchmarkRequest,
    BenchmarkResponse,
    CompressRequest,
    CostRecommendRequest,
    CostRecommendResponse,
    DatasetEvalResponse,
    DatasetOptimizeResponse,
    EvaluateRequest,
    EvaluateResponse,
    HealthResponse,
    LintRequest,
    LintResponse,
    MultiModelOptimizeRequest,
    MultiModelOptimizeResponse,
    OptimizeRequest,
    OptimizeResponse,
)
from openprompt.server.tempfiles import temp_prompt_files, temp_tests_file

try:
    from starlette.requests import Request
except ImportError:  # pragma: no cover - optional server extra
    Request = object  # type: ignore[misc,assignment]


async def _read_upload_files(files) -> list[tuple[str, bytes]]:
    from fastapi import UploadFile
    from starlette.datastructures import UploadFile as StarletteUploadFile

    if isinstance(files, (UploadFile, StarletteUploadFile)):
        file_items = [files]
    elif isinstance(files, list):
        file_items = files
    else:
        file_items = [files]

    uploads: list[tuple[str, bytes]] = []
    for upload in file_items:
        if not isinstance(upload, (UploadFile, StarletteUploadFile)):
            continue
        name = upload.filename or "sample"
        uploads.append((name, await upload.read()))
    if not uploads:
        raise ValueError("At least one sample file is required.")
    return uploads


def create_app(server_config: ServerConfig | None = None):
    try:
        from fastapi import FastAPI, HTTPException, UploadFile
    except ImportError as exc:
        raise ImportError("Install server extras: pip install 'openprompt[server]'") from exc

    cfg = server_config or ServerConfig.from_env()

    app = FastAPI(
        title="OpenPrompt API",
        description="REST API for prompt optimization, evaluation, and benchmarking.",
        version=__version__,
    )
    configure_middleware(app, cfg)

    def _handle_provider_error(exc: Exception) -> None:
        if isinstance(exc, ProviderError):
            code = exc.status_code if exc.status_code is not None else 502
            raise HTTPException(status_code=code, detail=str(exc)) from exc
        raise exc

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(version=__version__)

    @app.post("/lint", response_model=LintResponse)
    def lint_endpoint(body: LintRequest) -> LintResponse:
        client = openprompt_client("mock", "mock-model", warn_mock=False)
        report = client.lint(body.prompt)
        return LintResponse(
            score=report.score,
            categories=report.categories,
            issues=[
                {
                    "code": i.code,
                    "message": i.message,
                    "severity": i.severity.value,
                    "recommendation": i.recommendation,
                }
                for i in report.issues
            ],
        )

    @app.post("/optimize", response_model=OptimizeResponse)
    def optimize_endpoint(body: OptimizeRequest) -> OptimizeResponse:
        try:
            client = openprompt_client(body.provider, body.model, api_key=body.api_key)
            with temp_tests_file(body.tests) as tests_path:
                result = client.optimize(
                    body.prompt,
                    strategy=body.strategy,
                    tests_path=tests_path,
                    objective=body.objective,
                    constraints=body.constraints,
                    eval_budget=body.eval_budget,
                )
            return _optimize_response(result)
        except Exception as exc:
            _handle_provider_error(exc)
            raise

    @app.post("/evaluate", response_model=EvaluateResponse)
    def evaluate_endpoint(body: EvaluateRequest) -> EvaluateResponse:
        try:
            client = openprompt_client(body.provider, body.model, api_key=body.api_key)
            with temp_tests_file(body.tests) as tests_path:
                if tests_path is None:
                    raise HTTPException(status_code=400, detail="tests are required for /evaluate")
                report = client.evaluate(body.prompt, tests=tests_path)
            return EvaluateResponse(
                accuracy=report.accuracy,
                pass_rate=report.pass_rate,
                prompt_tokens=report.prompt_tokens,
                total_cost_usd=report.total_cost_usd,
                total_latency_ms=report.total_latency_ms,
                judge_score=report.judge_score,
                warnings=report.warnings,
                results=[
                    {
                        "name": r.test.name,
                        "passed": r.passed,
                        "score": r.score,
                        "message": r.message,
                    }
                    for r in report.results
                ],
            )
        except HTTPException:
            raise
        except Exception as exc:
            _handle_provider_error(exc)
            raise

    @app.post("/benchmark", response_model=BenchmarkResponse)
    def benchmark_endpoint(body: BenchmarkRequest) -> BenchmarkResponse:
        try:
            client = openprompt_client(body.provider, body.model, api_key=body.api_key)
            with temp_prompt_files(body.prompts) as paths:
                report = client.benchmark(paths)
            return BenchmarkResponse(
                generated_at=report.generated_at,
                entries=[e.__dict__ for e in report.entries],
                markdown=report.to_markdown(),
            )
        except Exception as exc:
            _handle_provider_error(exc)
            raise

    @app.post("/compress", response_model=OptimizeResponse)
    def compress_endpoint(body: CompressRequest) -> OptimizeResponse:
        try:
            client = openprompt_client(body.provider, body.model, api_key=body.api_key)
            result = client.compress(body.prompt)
            return _optimize_response(result)
        except Exception as exc:
            _handle_provider_error(exc)
            raise

    @app.post("/multi-model/optimize", response_model=MultiModelOptimizeResponse)
    def multi_model_endpoint(body: MultiModelOptimizeRequest) -> MultiModelOptimizeResponse:
        try:
            client = openprompt_client("mock", "mock-model", warn_mock=False)
            with temp_tests_file(body.tests) as tests_path:
                models = [m if isinstance(m, str) else f"{m.provider}:{m.model}" for m in body.models]
                result = client.multi_model_optimize(
                    body.prompt,
                    models,
                    strategy=body.strategy,
                    tests_path=tests_path,
                    provider_keys=body.provider_keys,
                    eval_budget=body.eval_budget,
                )
            best_q = result.best_quality
            best_c = result.lowest_cost
            return MultiModelOptimizeResponse(
                markdown_table=result.to_markdown_table(),
                rows=result.to_table_rows(),
                best_quality_model=best_q.spec.label if best_q else None,
                lowest_cost_model=best_c.spec.label if best_c else None,
            )
        except Exception as exc:
            _handle_provider_error(exc)
            raise

    @app.post("/cost/recommend", response_model=CostRecommendResponse)
    def cost_recommend_endpoint(body: CostRecommendRequest) -> CostRecommendResponse:
        try:
            client = openprompt_client(body.provider, body.model, api_key=body.api_key)
            result = client.optimize(body.prompt, strategy=body.strategy)
            rec = client.recommend_cost_quality(result, min_quality=body.min_quality)
            return CostRecommendResponse(
                recommended=rec.recommended.__dict__,
                pareto_frontier=[p.__dict__ for p in rec.pareto_frontier],
                reason=rec.reason,
                quality_per_dollar=rec.quality_per_dollar,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            _handle_provider_error(exc)
            raise

    @app.post("/dataset/eval", response_model=DatasetEvalResponse)
    async def dataset_eval_endpoint(request: Request) -> DatasetEvalResponse:
        try:
            form = await request.form()
            prompt = str(form.get("prompt", ""))
            if not prompt.strip():
                raise HTTPException(status_code=400, detail="prompt is required")

            provider = str(form.get("provider", "mock"))
            model = str(form.get("model", "mock-model"))
            api_key_raw = form.get("api_key")
            api_key = str(api_key_raw).strip() if api_key_raw else None
            dataset_name = str(form.get("dataset_name", "upload"))
            labels = form.get("labels")
            schema = form.get("schema")
            raw_files = form.getlist("files")
            uploads = await _read_upload_files(raw_files)

            field_schema = parse_schema_json(str(schema) if schema is not None else None)
            label_map = parse_labels_json(str(labels) if labels is not None else None)

            with temp_dataset_from_upload(
                uploads,
                name=dataset_name,
                labels=label_map,
                field_schema=field_schema,
            ) as dataset_dir:
                report, meta = run_dataset_eval(
                    prompt,
                    dataset_dir,
                    provider=provider,
                    model=model,
                    api_key=api_key,
                )
            return DatasetEvalResponse(
                accuracy=report.accuracy,
                pass_rate=report.pass_rate,
                prompt_tokens=report.prompt_tokens,
                total_cost_usd=report.total_cost_usd,
                total_latency_ms=report.total_latency_ms,
                judge_score=report.judge_score,
                warnings=report.warnings,
                results=[
                    {
                        "name": r.test.name,
                        "passed": r.passed,
                        "score": r.score,
                        "message": r.message,
                    }
                    for r in report.results
                ],
                dataset_name=meta["dataset_name"],
                sample_count=meta["sample_count"],
                samples=meta["samples"],
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            _handle_provider_error(exc)
            raise

    @app.post("/dataset/optimize", response_model=DatasetOptimizeResponse)
    async def dataset_optimize_endpoint(request: Request) -> DatasetOptimizeResponse:
        try:
            form = await request.form()
            prompt = str(form.get("prompt", ""))
            if not prompt.strip():
                raise HTTPException(status_code=400, detail="prompt is required")

            provider = str(form.get("provider", "mock"))
            model = str(form.get("model", "mock-model"))
            api_key_raw = form.get("api_key")
            api_key = str(api_key_raw).strip() if api_key_raw else None
            strategy = str(form.get("strategy", "extraction"))
            vision_raw = str(form.get("vision", "false")).lower()
            vision = vision_raw in {"1", "true", "yes", "on"}
            dataset_name = str(form.get("dataset_name", "upload"))
            labels = form.get("labels")
            schema = form.get("schema")
            raw_files = form.getlist("files")
            uploads = await _read_upload_files(raw_files)

            field_schema = parse_schema_json(str(schema) if schema is not None else None)
            label_map = parse_labels_json(str(labels) if labels is not None else None)

            with temp_dataset_from_upload(
                uploads,
                name=dataset_name,
                labels=label_map,
                field_schema=field_schema,
            ) as dataset_dir:
                ds = load_dataset(dataset_dir)
                result = run_dataset_optimize(
                    prompt,
                    dataset_dir,
                    provider=provider,
                    model=model,
                    strategy=strategy,
                    vision=vision,
                    api_key=api_key,
                )
            return DatasetOptimizeResponse(
                prompt=result.prompt,
                original_score=result.original_score,
                optimized_score=result.optimized_score,
                score_delta=result.score_delta,
                original_tokens=result.original_tokens,
                optimized_tokens=result.optimized_tokens,
                token_delta_pct=result.token_delta_pct,
                original_cost_usd=result.original_cost_usd,
                optimized_cost_usd=result.optimized_cost_usd,
                cost_delta_pct=result.cost_delta_pct,
                strategy=result.strategy,
                report_lines=result.report_lines,
                warnings=getattr(result, "warnings", []),
                dataset_name=ds.name,
                sample_count=len(ds.samples),
                vision_enabled=vision,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            _handle_provider_error(exc)
            raise

    return app


def _optimize_response(result) -> OptimizeResponse:
    return OptimizeResponse(
        prompt=result.prompt,
        original_score=result.original_score,
        optimized_score=result.optimized_score,
        score_delta=result.score_delta,
        original_tokens=result.original_tokens,
        optimized_tokens=result.optimized_tokens,
        token_delta_pct=result.token_delta_pct,
        original_cost_usd=result.original_cost_usd,
        optimized_cost_usd=result.optimized_cost_usd,
        cost_delta_pct=result.cost_delta_pct,
        strategy=result.strategy,
        report_lines=result.report_lines,
        warnings=getattr(result, "warnings", []),
    )
