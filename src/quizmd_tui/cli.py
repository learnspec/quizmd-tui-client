"""CLI entry point for quizmd-tui."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="quizmd",
        description="QuizMD TUI — play quizzes in your terminal",
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=None,
        help=(
            "GitHub source: owner/repo, GitHub URL to a .quiz.md file, "
            "or owner/repo/blob/branch/path.quiz.md"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    args = parser.parse_args(argv)

    from .app import QuizMDApp

    app = QuizMDApp(source=args.source)
    app.run()


if __name__ == "__main__":
    main()
