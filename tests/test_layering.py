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
