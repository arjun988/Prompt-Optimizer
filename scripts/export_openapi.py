"""Export committed OpenAPI spec artifact."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    from openprompt.server.app import create_app

    app = create_app()
    spec = app.openapi()
    out = Path(__file__).resolve().parents[1] / "openapi.json"
    out.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
