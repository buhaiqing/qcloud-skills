"""CLI entry point stub. Full daemon loop ships in later tasks."""
import argparse


def main() -> int:
    parser = argparse.ArgumentParser(prog="qcloud_agent_daemon")
    parser.add_argument("--config", help="patrols YAML path")
    parser.add_argument("--sources", help="comma-separated source list")
    args = parser.parse_args()
    print(f"qcloud-agent-daemon {__version__ if (__version__ := __import__('qcloud_agent_daemon').__version__) else '0.0.0'} — stub")
    print(f"  config: {args.config}")
    print(f"  sources: {args.sources}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
