#!/usr/bin/env python3
"""Sinh file OpenAPI (YAML) từ FastAPI app, không cần chạy server hay kết nối DB.

Cách dùng:
    python scripts/generate_openapi.py                  # -> ./openapi.yaml
    python scripts/generate_openapi.py -o spec/api.yaml # đường dẫn khác
    python scripts/generate_openapi.py --app main:app   # chỉ định app khác
"""  # noqa: EXE001
import argparse
import importlib
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_app(target: str):
    module_name, _, attr = target.partition(":")
    sys.path.insert(0, str(ROOT))
    module = importlib.import_module(module_name)
    return getattr(module, attr or "app")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate openapi.yaml from FastAPI app")
    parser.add_argument("--app", default="main:app", help="module:attribute của FastAPI app")
    parser.add_argument("-o", "--output", default="openapi.yaml", help="file YAML đầu ra")
    args = parser.parse_args()

    app = load_app(args.app)
    spec = app.openapi()

    out = Path(args.output)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as f:
        yaml.safe_dump(spec, f, sort_keys=False, allow_unicode=True)

    paths = spec.get("paths", {})
    print(f"Đã ghi {out}")
    print(f"OpenAPI {spec.get('openapi')} | {len(paths)} paths:")
    for path, methods in paths.items():
        print(f"  {path}: {', '.join(m.upper() for m in methods)}")


if __name__ == "__main__":
    main()
