"""
R2: Report builder — template filled from real pytest results, not model prose.
"""

from __future__ import annotations
from app.models import ExecutionReport, PolicyVerdict

REPORT_TEMPLATE = """\
╔══════════════════════════════════════════════════════════╗
║                   CodeForge Report                       ║
╠══════════════════════════════════════════════════════════╣
║ Request:   {request_summary:<45} ║
║ Verdict:   {verdict:<45} ║
║ Tier:      {tier:<45} ║
╠══════════════════════════════════════════════════════════╣
║ Tests:     {test_status:<45} ║
║ Exit Code: {exit_code:<45} ║
╠══════════════════════════════════════════════════════════╣
║ Idempotency Key: {idempotency_key:<38} ║
╚══════════════════════════════════════════════════════════╝

── Generated Code ──
{code}

── Test Output ──
{test_output}
"""

DENIED_TEMPLATE = """\
╔══════════════════════════════════════════════════════════╗
║                   CodeForge Report                       ║
╠══════════════════════════════════════════════════════════╣
║ Request:   {request_summary:<45} ║
║ Verdict:   DENIED                                        ║
║ Reasons:   {reasons:<45} ║
╚══════════════════════════════════════════════════════════╝

Your request was denied because the generated code violated safety policies.
No code was executed.
"""


def build_report(report: ExecutionReport) -> str:
    if report.policy_verdict == PolicyVerdict.DENY:
        return DENIED_TEMPLATE.format(
            request_summary=report.request_summary[:45],
            reasons=report.error[:45] if report.error else "Policy violation",
        )

    test_status = "PASSED" if report.tests_passed else "FAILED"
    return REPORT_TEMPLATE.format(
        request_summary=report.request_summary[:45],
        verdict=report.policy_verdict.value.upper(),
        tier=report.tier,
        test_status=test_status,
        exit_code=str(report.exit_code),
        idempotency_key=report.idempotency_key[:38],
        code=report.code,
        test_output=report.test_output,
    )
