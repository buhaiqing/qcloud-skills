from __future__ import annotations

import typer
from copilot.engine import CopilotEngine
from copilot.env_loader import ensure_runtime_env
from copilot.models import Report
from copilot.report_gen import render_markdown
from copilot.session import SessionManager
from copilot.strategy import apply_strategy, load_strategy_file

app = typer.Typer(help="AIOps Copilot — Natural-language orchestration for Tencent Cloud operations")
strategy_app = typer.Typer(help="Inspection strategy (Agent inband)")
app.add_typer(strategy_app, name="strategy")


@app.callback()
def _bootstrap_env() -> None:
    """Load .env (COPILOT_* / TENCENTCLOUD_*) before any subcommand — CI mode reads LLM config here."""
    ensure_runtime_env()


def _emit_report(report: Report) -> None:
    typer.echo(render_markdown(report).rstrip())
    if report.report_path:
        label = "Summary saved" if report.audience == "summary" else "Report saved"
        typer.echo(f"\n{label}: {report.report_path}")
    if report.summary_report_path and report.audience != "summary":
        typer.echo(f"Summary saved: {report.summary_report_path}")
    elif report.summary_report_path and report.audience == "summary":
        typer.echo(f"Detailed report: {report.summary_report_path}")


@app.command()
def plan(
    plan_file: str = typer.Option(..., "--plan", help="Path to execution plan JSON"),
    session: str = typer.Option(..., "--session", "-s", help="Session ID for blackboard"),
    format: str = typer.Option("detailed", "--format", help="Output format: detailed|summary"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print step order without executing"),
    reviewed: bool = typer.Option(
        False, "--reviewed", help="Confirm critical findings reviewed (L3 gate bypass)"
    ),
):
    """Execute a structured multi-step plan from JSON."""
    audience = "summary" if format == "summary" else "detailed"
    engine = CopilotEngine()
    result = engine.run_plan(
        plan_file,
        session_id=session,
        audience=audience,
        dry_run=dry_run,
        l3_reviewed=reviewed,
    )
    if dry_run:
        typer.echo(f"Plan: {result['plan_id']}")
        typer.echo(f"Session: {result['session_id']}")
        typer.echo("Step order:")
        for step_id in result["step_order"]:
            reads = result["reads_from_blackboard"].get(step_id, [])
            writes = result["writes_to_blackboard"].get(step_id, False)
            typer.echo(f"  {step_id}  reads={reads}  writes={writes}")
        return

    _emit_report(result)


@app.command()
def ask(
    query: str = typer.Argument(..., help="Natural-language AIOps query"),
    session: str | None = typer.Option(None, "--session", "-s", help="Session ID to continue"),
    format: str = typer.Option("auto", "--format", help="Output format: detailed|summary|auto"),
    confirm: bool = typer.Option(
        False, "--confirm", help="Confirm destructive operations (L2 gate bypass)"
    ),
    reviewed: bool = typer.Option(
        False, "--reviewed", help="Confirm critical findings reviewed (L3 gate bypass)"
    ),
    inspection_mode: str | None = typer.Option(
        None,
        "--inspection-mode",
        help="Force delivery|ci (overrides env/keywords when set)",
    ),
):
    """Ask a natural-language AIOps question."""
    audience = "summary" if format == "summary" else "detailed"
    engine = CopilotEngine()
    report = engine.ask(
        query,
        session_id=session,
        audience=audience,
        l2_confirmed=confirm,
        l3_reviewed=reviewed,
        inspection_mode=inspection_mode,
    )
    _emit_report(report)


@app.command()
def run(
    query: str = typer.Argument(..., help="One-shot query (no session)"),
    output: str = typer.Option("markdown", "--output", help="Output format: markdown|json"),
):
    """Execute a one-shot AIOps query."""
    engine = CopilotEngine()
    report = engine.ask(query, session_id=None, audience="detailed")
    _emit_report(report)


@strategy_app.command("apply")
def strategy_apply(
    session: str = typer.Option(..., "--session", "-s", help="Blackboard session ID"),
    file: str = typer.Option(..., "--file", help="Inspection strategy JSON file"),
    decision_maker: str = typer.Option(
        "agent_session_v1",
        "--decision-maker",
        help="decision_maker enum: agent_session_v1 | topology_reasoner_v1 | llm_reasoner_v1",
    ),
):
    """Apply Agent-produced inspection strategy to Blackboard evidence_chain."""
    try:
        strategy = load_strategy_file(file)
        result = apply_strategy(session, strategy, decision_maker=decision_maker)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc
    except Exception as exc:
        typer.echo(f"Strategy validation failed: {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(f"Strategy applied: session={result['session_id']}")
    typer.echo(f"  path: {result['strategy_path']}")
    typer.echo(f"  decision_maker: {result['decision_maker']}")
    if result["selected_analyzers"]:
        typer.echo(f"  selected_analyzers: {', '.join(result['selected_analyzers'])}")


@app.command()
def sessions(
    action: str = typer.Argument("list", help="Action: list|show|delete"),
    session_id: str | None = typer.Argument(None, help="Session ID (required for show/delete)"),
):
    """Manage Copilot sessions."""
    sm = SessionManager()
    if action == "list":
        sessions = sm.list_sessions()
        if not sessions:
            typer.echo("No sessions found.")
        else:
            for sid in sessions:
                typer.echo(f"  {sid}")
    elif action == "show":
        if not session_id:
            typer.echo("Error: session_id required for show action", err=True)
            raise typer.Exit(1)
        state = sm.load_session(session_id)
        if state is None:
            typer.echo(f"Session {session_id} not found.", err=True)
            raise typer.Exit(1)
        typer.echo(f"Session: {state.session_id}")
        typer.echo(f"Created: {state.created_at}")
        typer.echo(f"History entries: {len(state.history)}")
        if state.current_plan:
            typer.echo(f"Current plan: {state.current_plan.intent.primary.value}")
    elif action == "delete":
        if not session_id:
            typer.echo("Error: session_id required for delete action", err=True)
            raise typer.Exit(1)
        typer.echo(f"Deleted session {session_id}.")
    else:
        typer.echo(f"Unknown action: {action}", err=True)
        raise typer.Exit(1)


@app.command()
def health(
    action: str = typer.Argument("report", help="Action: report|top-errors|sweep"),
    days: int = typer.Option(7, "--days", help="Days to report on"),
    limit: int = typer.Option(5, "--limit", help="Top-N limit"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Dry-run for sweep"),
):
    """View Copilot and skill health metrics."""
    health_file = _health_file()
    if not health_file.exists():
        typer.echo("No health data found.")
        return
    events = _read_health_events(health_file, days)
    if action == "report":
        _health_report(events, limit)
    elif action == "top-errors":
        _top_errors(events, limit)
    elif action == "sweep":
        _sweep(health_file, days, dry_run)


def _health_file():
    from pathlib import Path

    return Path.home() / ".runtime" / "health" / "skill-metrics.jsonl"


def _read_health_events(path, days):
    import json
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events = []
    if not path.exists():
        return events
    for line in path.open():
        try:
            ev = json.loads(line)
            if datetime.fromisoformat(ev["ts"].replace("Z", "+00:00")) >= cutoff:
                events.append(ev)
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return events


def _health_report(events, limit):
    from collections import Counter

    typer.echo(f"Health report — {len(events)} events")
    skill_counts = Counter(e["skill"] for e in events)
    ok = sum(1 for e in events if e["status"] == "ok")
    err = sum(1 for e in events if e["status"] == "error")
    typer.echo(f"  OK: {ok}, Error: {err}")
    typer.echo("\nTop skills:")
    for skill, count in skill_counts.most_common(limit):
        typer.echo(f"  {skill}: {count}")


def _top_errors(events, limit):
    from collections import Counter

    err_events = [e for e in events if e["status"] == "error"]
    err_codes = Counter(e.get("error_code") for e in err_events)
    typer.echo(f"Top {limit} error codes:")
    for code, count in err_codes.most_common(limit):
        typer.echo(f"  {code}: {count}")


def _sweep(health_file, days, dry_run):
    import json
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    remaining = []
    for line in health_file.open():
        try:
            ev = json.loads(line)
            if datetime.fromisoformat(ev["ts"].replace("Z", "+00:00")) >= cutoff:
                remaining.append(ev)
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    if dry_run:
        typer.echo(f"Dry-run: would keep {len(remaining)} events")
    else:
        with health_file.open("w") as f:
            for ev in remaining:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        typer.echo(f"Swept {len(remaining)} events")


@app.callback()
def main():
    pass


if __name__ == "__main__":
    app()
