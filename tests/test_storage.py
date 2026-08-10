from openprompt.core.storage.sqlite import RunStore


def test_sqlite_logs_cost_and_latency(tmp_path) -> None:
    db = tmp_path / "runs.db"
    store = RunStore(db)
    run_id = store.log_run(
        prompt_name="demo",
        strategy="eval",
        model="mock",
        score=0.9,
        tokens=120,
        cost_usd=0.002,
        latency_ms=45.0,
    )
    assert run_id == 1
    runs = store.recent_runs()
    assert runs[0].cost_usd == 0.002
    assert runs[0].latency_ms == 45.0
