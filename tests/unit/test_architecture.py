"""Keep the dependency direction explicit as feature modules are added."""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "src" / "keitaro_wrapper"
FRAMEWORKS = {"fastapi", "starlette", "pydantic", "pydantic_settings", "sqlalchemy", "httpx"}


def imported_modules(path):
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module
        elif isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)


@pytest.mark.parametrize(
    "layer,allowed",
    [
        ("common", {"common"}),
        ("domain", {"domain", "common"}),
        ("application", {"application", "domain", "common"}),
    ],
)
def test_inner_layers_do_not_depend_on_transport_or_infrastructure(layer, allowed):
    violations = []
    for path in (ROOT / layer).rglob("*.py"):
        for module in imported_modules(path):
            parts = module.split(".")
            if parts[0] in FRAMEWORKS or (
                parts[0] == "keitaro_wrapper" and parts[1] not in allowed
            ):
                violations.append(f"{path.relative_to(ROOT)} imports {module}")
    assert violations == []


def test_api_handlers_do_not_open_database_transactions():
    violations = []
    for path in (ROOT / "api").rglob("handlers.py"):
        for module in imported_modules(path):
            if module.startswith(
                ("sqlalchemy", "keitaro_wrapper.infrastructure", "keitaro_wrapper.bootstrap")
            ):
                violations.append(f"{path.relative_to(ROOT)} imports {module}")
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Attribute) and node.attr in {
                "transaction",
                "session",
                "database",
            }:
                # Starlette's signed HTTP session is transport state, not an ORM session.
                if (
                    node.attr == "session"
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "request"
                ):
                    continue
                violations.append(f"{path.relative_to(ROOT)} accesses {node.attr}")
    assert violations == []


def test_packages_do_not_reexport_implementation():
    for path in ROOT.rglob("__init__.py"):
        assert not list(imported_modules(path)), path


def test_inner_layers_do_not_decode_adapter_snapshots_or_read_wall_clock():
    violations = []
    for layer in ("domain", "application"):
        for path in (ROOT / layer).rglob("*.py"):
            for module in imported_modules(path):
                if module == "json" or module == "keitaro_wrapper.common.clock":
                    violations.append(f"{path.relative_to(ROOT)} imports {module}")
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Attribute) and node.attr == "token":
                    violations.append(f"{path.relative_to(ROOT)} decodes adapter-owned state")
    assert violations == []
