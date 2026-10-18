import ast
from pathlib import Path

PACKAGE_ROOT = Path("src/tong_quant")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def _tong_quant_dependencies(root: Path) -> set[str]:
    return {
        module
        for path in root.rglob("*.py")
        for module in _imported_modules(path)
        if module == "tong_quant" or module.startswith("tong_quant.")
    }


def test_order_models_exist_only_in_execution_package() -> None:
    offenders = []
    for path in PACKAGE_ROOT.rglob("*.py"):
        if "execution" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if any(
            isinstance(node, ast.ClassDef) and node.name == "Order"
            for node in ast.walk(tree)
        ):
            offenders.append(str(path))

    assert offenders == []


def test_sse_input_inventory_is_transport_free_and_notice_adapter_is_data_only() -> None:
    for path in ("application/sse_runtime_inputs.py", "application/sse_calendar_plan.py",
                 "application/sse_pilot_coverage.py",
                 "application/deployment_preflight.py",
                 "application/dependency_lock.py",
                 "data/storage/artifact_audit.py",
                 "research/bar_inputs.py",
                 "data/calendar_evidence.py"):
        reader_imports = _imported_modules(PACKAGE_ROOT / path)
        assert "requests" not in reader_imports
        assert not any(
            module.startswith("tong_quant.data.providers.")
            and module != "tong_quant.data.providers.contracts"
            for module in reader_imports
        )
    forbidden = {"execution", "paper", "brokers", "portfolio", "notifications"}
    for path in ("data/providers/sse_calendar.py", "data/providers/akshare_prices.py",
                 "data/providers/akshare_suspensions.py", "data/price_evidence.py",
                 "data/providers/akshare_financials.py",
                 "data/storage/artifact_audit.py",
                 "research/bar_inputs.py",
                 "application/sse_pilot_coverage.py",
                 "data/lifecycle_review.py"):
        assert not any(
            module.startswith("tong_quant.") and module.split(".")[1] in forbidden
            for module in _imported_modules(PACKAGE_ROOT / path)
        )


def test_validation_has_no_execution_or_order_dependency() -> None:
    validation_root = Path("src/tong_quant/validation")
    offenders = sorted(
        module
        for module in _tong_quant_dependencies(validation_root)
        if module == "tong_quant.execution" or module.startswith("tong_quant.execution.")
    )

    assert offenders == []


def test_risk_stays_independent_of_portfolio_and_execution() -> None:
    dependencies = _tong_quant_dependencies(PACKAGE_ROOT / "risk")
    assert not any(
        module.split(".")[1] in {"portfolio", "execution", "notifications"}
        for module in dependencies
    )


def test_upstream_engines_do_not_import_execution() -> None:
    for package in ("screening", "research", "market_regime", "portfolio", "markets"):
        assert not any(
            module == "tong_quant.execution" or module.startswith("tong_quant.execution.")
            for module in _tong_quant_dependencies(PACKAGE_ROOT / package)
        ), package


def test_screening_does_not_own_research_outcome_or_investment_models() -> None:
    screening_root = Path("src/tong_quant/screening")
    offenders = []
    forbidden = ("class ResearchOutcome", "class InvestmentAssessment", "assess_investment")
    for path in screening_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(item in text for item in forbidden):
            offenders.append(str(path))

    assert offenders == []


def test_notifications_do_not_depend_on_execution_or_order_models() -> None:
    notification_root = Path("src/tong_quant/notifications")
    forbidden_roots = {
        "execution",
        "brokers",
        "orders",
        "trades",
        "fills",
        "paper",
        "strategies",
    }
    offenders = sorted(
        module
        for module in _tong_quant_dependencies(notification_root)
        if len(module.split(".")) > 1 and module.split(".")[1] in forbidden_roots
    )

    assert offenders == []


def test_provider_health_does_not_depend_on_notifications_or_trading() -> None:
    forbidden_roots = {
        "notifications",
        "execution",
        "brokers",
        "orders",
        "trades",
        "fills",
        "paper",
        "portfolio",
    }
    offenders = sorted(
        module
        for module in _imported_modules(
            Path("src/tong_quant/data/provider_health.py")
        )
        if len(module.split(".")) > 1 and module.split(".")[1] in forbidden_roots
    )

    assert offenders == []


def test_evidence_readiness_does_not_depend_on_downstream_or_trading_layers() -> None:
    forbidden_roots = {
        "notifications",
        "execution",
        "brokers",
        "orders",
        "trades",
        "fills",
        "paper",
        "portfolio",
        "research",
        "screening",
        "validation",
    }
    offenders = sorted(
        module
        for path in (
            Path("src/tong_quant/data/evidence_readiness.py"),
            Path("src/tong_quant/data/evidence_sources.py"),
        )
        for module in _imported_modules(path)
        if len(module.split(".")) > 1 and module.split(".")[1] in forbidden_roots
    )

    assert offenders == []


def test_evidence_archives_do_not_depend_on_downstream_or_trading_layers() -> None:
    forbidden_roots = {
        "notifications",
        "execution",
        "brokers",
        "orders",
        "trades",
        "fills",
        "paper",
        "portfolio",
        "research",
        "screening",
        "validation",
    }
    offenders = sorted(
        module
        for path in (
            Path("src/tong_quant/data/evidence_archive.py"),
            Path("src/tong_quant/data/evidence_bundle.py"),
        )
        for module in _imported_modules(path)
        if len(module.split(".")) > 1 and module.split(".")[1] in forbidden_roots
    )

    assert offenders == []


def test_notification_service_is_research_artifact_oriented() -> None:
    text = Path("src/tong_quant/notifications/service.py").read_text(encoding="utf-8")

    assert "generate_research_report" in text
    assert "generate_validation_report" in text
    assert "generate_portfolio_proposal" in text
    assert "generate_risk_assessment" in text
    assert "send_signal" not in text


def test_notification_channels_only_consume_rendered_messages() -> None:
    text = Path("src/tong_quant/notifications/base.py").read_text(encoding="utf-8")

    assert "def send(self, message: NotificationMessage)" in text
    assert "ResearchReport" not in text
    assert "ValidationReport" not in text
    assert "PortfolioProposal" not in text
    assert "RiskAssessment" not in text


def test_top_level_packages_have_no_static_import_cycles() -> None:
    graph: dict[str, set[str]] = {}
    for path in PACKAGE_ROOT.rglob("*.py"):
        relative = path.relative_to(PACKAGE_ROOT)
        if len(relative.parts) < 2:
            continue
        source = relative.parts[0]
        graph.setdefault(source, set())
        for module in _imported_modules(path):
            parts = module.split(".")
            if len(parts) >= 2 and parts[0] == "tong_quant" and parts[1] != source:
                graph[source].add(parts[1])

    visiting: list[str] = []
    visited: set[str] = set()

    def visit(package: str) -> None:
        if package in visiting:
            cycle_start = visiting.index(package)
            cycle = (*visiting[cycle_start:], package)
            raise AssertionError(f"static package dependency cycle: {' -> '.join(cycle)}")
        if package in visited:
            return
        visiting.append(package)
        for dependency in sorted(graph.get(package, ())):
            visit(dependency)
        visiting.pop()
        visited.add(package)

    for package in sorted(graph):
        visit(package)
