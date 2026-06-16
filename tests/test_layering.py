from pathlib import Path


def test_order_models_exist_only_in_execution_package() -> None:
    package_root = Path("src/tong_quant")
    offenders = []
    for path in package_root.rglob("*.py"):
        if "execution" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if "class Order" in text:
            offenders.append(str(path))

    assert offenders == []


def test_validation_has_no_execution_or_order_dependency() -> None:
    validation_root = Path("src/tong_quant/validation")
    offenders = []
    forbidden = (
        "tong_quant.execution",
        "class Order",
        "create_order",
        "submit_order",
        "place_order",
        "ENTER_LONG",
        "EXIT_LONG",
    )
    for path in validation_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(item in text for item in forbidden):
            offenders.append(str(path))

    assert offenders == []


def test_screening_does_not_own_research_outcome_or_investment_models() -> None:
    screening_root = Path("src/tong_quant/screening")
    offenders = []
    forbidden = ("class ResearchOutcome", "class InvestmentAssessment", "assess_investment")
    for path in screening_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(item in text for item in forbidden):
            offenders.append(str(path))

    assert offenders == []
