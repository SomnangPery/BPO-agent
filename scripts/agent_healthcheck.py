"""IC Agent health check.

Run:
    venv\\Scripts\\python.exe scripts\\agent_healthcheck.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from anthropic import Anthropic


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _ok(name: str, detail: str = "") -> tuple[str, bool, str]:
    return (name, True, detail)


def _fail(name: str, detail: str) -> tuple[str, bool, str]:
    return (name, False, detail)


def _check_claude_api() -> tuple[str, bool, str]:
    try:
        from ic_agent.config import AGENT_MODEL, ANTHROPIC_API_KEY, LLM_TIMEOUT_SECONDS

        if not ANTHROPIC_API_KEY:
            return _fail("claude_api", "ANTHROPIC_API_KEY is missing")

        response = Anthropic(api_key=ANTHROPIC_API_KEY, timeout=LLM_TIMEOUT_SECONDS).messages.create(
            model=AGENT_MODEL,
            max_tokens=16,
            temperature=0,
            messages=[{"role": "user", "content": "Reply with: ok"}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()
        if not text:
            return _fail("claude_api", "empty response")
        return _ok("claude_api", f"reachable (model={AGENT_MODEL})")
    except Exception as exc:
        return _fail("claude_api", f"unreachable: {exc}")


def _format_check_output(checks: list[tuple[str, bool, str]]) -> str:
    """Format health check results with organized sections and visual indicators."""
    lines = []
    lines.append("\n🏥 IC AGENT HEALTH CHECK")
    lines.append("=" * 60)
    
    passed_checks = [c for c in checks if c[1]]
    failed_checks = [c for c in checks if not c[1]]
    passed = len(passed_checks)
    total = len(checks)
    
    # Summary section
    status_emoji = "✅" if passed == total else "⚠️ " if passed > 0 else "❌"
    lines.append(f"\n{status_emoji} STATUS: {passed}/{total} checks passed\n")
    
    # Passed checks section
    if passed_checks:
        lines.append("✅ PASSING CHECKS:")
        for name, _, detail in passed_checks:
            lines.append(f"   ✓ {name.replace('_', ' ').title()}: {detail}")
    
    # Failed checks section
    if failed_checks:
        lines.append("\n❌ FAILED CHECKS:")
        for name, _, detail in failed_checks:
            lines.append(f"   ✗ {name.replace('_', ' ').title()}: {detail}")
    
    lines.append("\n" + "=" * 60)
    lines.append(f"Summary: {json.dumps({'passed': passed, 'total': total})}\n")
    
    return "\n".join(lines)


def _main() -> int:
    checks: list[tuple[str, bool, str]] = []

    try:
        from ic_agent.config import CHROMA_PERSIST_DIR, KNOWLEDGE_DIR

        checks.append(_ok("config", "imported successfully"))
        checks.append(_ok("knowledge_dir", str(Path(KNOWLEDGE_DIR).resolve())))
        checks.append(_ok("chroma_dir", str(Path(CHROMA_PERSIST_DIR).resolve())))
    except Exception as exc:
        checks.append(_fail("config", f"import failed: {exc}"))

    try:
        from ic_agent.tools import build_tools

        tool_names = [tool.name for tool in build_tools()]
        checks.append(_ok("tools", f"{len(tool_names)} tools available: {', '.join(tool_names)}"))
    except Exception as exc:
        checks.append(_fail("tools", f"build failed: {exc}"))

    try:
        from ic_agent.agent import create_ic_agent

        _ = create_ic_agent()
        checks.append(_ok("react_agent", "created and ready"))
    except Exception as exc:
        checks.append(_fail("react_agent", f"create failed: {exc}"))

    checks.append(_check_claude_api())

    print(_format_check_output(checks))

    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(_main())
