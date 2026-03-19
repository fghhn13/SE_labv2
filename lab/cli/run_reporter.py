import argparse
from pathlib import Path
from typing import Optional


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Run offline reporters on events.jsonl.")
    parser.add_argument("--reporter-name", type=str, default="text_summary")
    parser.add_argument("--events-jsonl", type=str, required=True)
    parser.add_argument("--summary-out", type=str, default=None)
    parser.add_argument("--run-id", type=str, default=None)
    args = parser.parse_args(argv)

    # Late imports so reporter auto-registration side-effects happen.
    from lab.reporters.registry import create as create_reporter
    import lab.reporters as _  # noqa: F401

    reporter = create_reporter(
        args.reporter_name,
        source_file=args.events_jsonl,
        output_file=args.summary_out,
        run_id=args.run_id,
    )
    reporter.generate()


if __name__ == "__main__":
    main()

