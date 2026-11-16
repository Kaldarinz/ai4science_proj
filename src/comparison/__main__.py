"""Run with .venv/bin/python -m src.comparison from the project root."""

import argparse
import sys

from . import DEFAULT_ROOT, aggregate, build, prepare
from .inputs import WORKSPACE, PipelineError, artifact_path


def main(argv=None, *, root=DEFAULT_ROOT):
    parser = argparse.ArgumentParser(
        description="Prepare candidates or build comparison results."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    preparer = commands.add_parser(
        "prepare", help="write candidate context without scientific decisions"
    )
    preparer.add_argument("--article", type=int, help="one completed article only")
    builder = commands.add_parser("build", help="consume the completed matching audit")
    builder.add_argument("--stage", choices=("draft", "final"), required=True)
    builder.add_argument(
        "--article", type=int, help="one draft article checkpoint only"
    )
    commands.add_parser(
        "aggregate", help="validate article checkpoints and assemble a corpus draft"
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            document = prepare(root, article=args.article)
            path = artifact_path(WORKSPACE, args.article)
            print(f"Prepared {len(document['candidates'])} candidate entries in {path}")
            print(
                f"Review candidates and write {artifact_path('results/matching_audit.csv', args.article)}; "
                "no scientific decisions were generated."
            )
        elif args.command == "aggregate":
            summary = aggregate(root)
            print(
                f"Aggregated draft: {summary['articles']['n_complete']} complete articles"
            )
            print(
                "Next: .venv/bin/python checks/check.py --analysis draft; then request curator review."
            )
        else:
            summary = build(root, stage=args.stage, article=args.article)
            print(
                f"Built {args.stage}: {summary['comparison']['n_included_pairs']} included pairs"
            )
            scope = f" --article {args.article}" if args.article is not None else ""
            print(
                f"Next: .venv/bin/python checks/check.py --analysis {args.stage}{scope}"
            )
        return 0
    except (PipelineError, OSError, ValueError) as error:
        print(f"FAILED: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
