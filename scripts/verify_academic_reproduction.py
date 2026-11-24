"""Run six public synthetic cases offline; no database, provider or account is used."""

import argparse
from pathlib import Path

from tong_quant.application.academic_verification import verify_academic_reproduction
from tong_quant.data.financial_inputs import financial_input_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify_academic_reproduction()
    content = financial_input_json(result) + "\n"
    if args.output:
        try:
            with args.output.expanduser().open("x", encoding="utf-8") as handle:
                handle.write(content)
        except OSError:
            parser.exit(2, "Verification output could not be created; existing files unchanged.\n")
    else:
        print(content, end="")
    if result["status"] != "CHECKS_PASSED":
        parser.exit(1)


if __name__ == "__main__":
    main()
