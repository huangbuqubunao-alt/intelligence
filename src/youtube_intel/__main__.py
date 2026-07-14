"""Command-line entry point for YouTube Intelligence Agent."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="youtube-intel",
        description="Local-first YouTube intelligence agent",
    )
    parser.parse_args()


if __name__ == "__main__":
    main()
