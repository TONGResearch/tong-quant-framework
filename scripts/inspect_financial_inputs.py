"""Read-only financial provenance/applicability diagnostics; never research approval."""

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path

from tong_quant.core.security import reject_sensitive_structure
from tong_quant.data.artifacts import FileSystemArtifactStore
from tong_quant.data.filing_inputs import ReviewedFinancialInputReader
from tong_quant.data.financial_inputs import financial_input_json
from tong_quant.data.storage.sqlite import SQLiteStore
from tong_quant.domain.enums import Market
from tong_quant.research.financial.comparisons import financial_comparisons
from tong_quant.research.financial.inputs import BankInputPolicy, assess_bank_inputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--market", choices=[item.value for item in Market], default="china_a")
    parser.add_argument("--metrics", nargs="+", required=True)
    parser.add_argument(
        "--sector-profile", choices=("bank", "nonfinancial", "unknown"), required=True,
    )
    parser.add_argument("--as-of")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--bank-inputs", action="store_true")
    parser.add_argument("--bank-max-report-age-days", type=int)
    parser.add_argument("--bank-target-period")
    parser.add_argument(
        "--comparisons", action="store_true", help="Include descriptive changes only",
    )
    args = parser.parse_args()
    if not args.bank_inputs and (
        args.bank_max_report_age_days is not None or args.bank_target_period is not None
    ):
        parser.error("bank age/period options require --bank-inputs")
    if args.bank_inputs and (args.market != "china_a" or args.sector_profile != "bank"):
        parser.error("bank input diagnostics support China-A group banks only")
    bank_policy = BankInputPolicy(
        maximum_report_age_days=(args.bank_max_report_age_days
                                 if args.bank_max_report_age_days is not None else 0),
    )
    if args.output is not None and (args.output.exists() or args.output.is_symlink()):
        parser.error("output exists; overwrite disabled")
    snapshot = ReviewedFinancialInputReader(
        SQLiteStore(args.database, read_only=True), FileSystemArtifactStore(args.artifact_root),
    ).read(
        args.symbol, Market(args.market), tuple(args.metrics),
        as_of=datetime.fromisoformat(args.as_of) if args.as_of else datetime.now(UTC),
        sector_profile=args.sector_profile,
    )
    raw_document = snapshot.document()
    if args.bank_inputs:
        raw_document["bank_input_assessment"] = assess_bank_inputs(
            snapshot, bank_policy, target_period_end=(
                date.fromisoformat(args.bank_target_period) if args.bank_target_period else None),
        ).document()
    if args.comparisons:
        raw_document["comparisons"] = [item.document() for item in financial_comparisons(snapshot)]
    document = json.loads(financial_input_json(raw_document))
    reject_sensitive_structure(document)
    if args.output is None:
        print(json.dumps(document, indent=2, sort_keys=True))
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            args.output.chmod(0o600)
            json.dump(document, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print(args.output)
    raise SystemExit(2)  # Even source-bound LOW observations remain partial diagnostics.


if __name__ == "__main__":
    main()
