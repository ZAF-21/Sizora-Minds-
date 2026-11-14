"""
R2: Policy gate — a PURE function that parses code with ast (never runs it)
and returns allow, needs_approval, or deny with reasons.
"""

from __future__ import annotations
import ast
from app.models import PolicyResult, PolicyVerdict

# Modules that are always denied
DENIED_MODULES = {
    "os", "sys", "subprocess", "shutil", "pathlib",
    "ctypes", "signal", "importlib", "runpy",
}

# Modules that need human approval
APPROVAL_MODULES = {
    "socket", "http", "urllib", "requests", "httpx",
    "ftplib", "smtplib", "paramiko", "fabric",
}

# Built-in functions that are denied
DENIED_BUILTINS = {
    "exec", "eval", "compile", "__import__", "globals", "locals",
    "breakpoint", "exit", "quit",
}

# AST node types that indicate file/network access
DENIED_PATTERNS = {
    "open",
}


def evaluate_code_policy(code: str) -> PolicyResult:
    """
    Parse code with ast and evaluate its safety. Never executes the code.
    Returns allow, needs_approval, or deny with reasons.
    """
    reasons: list[str] = []
    verdict = PolicyVerdict.ALLOW

    # Step 1: Try to parse the code
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return PolicyResult(
            verdict=PolicyVerdict.DENY,
            reasons=[f"Syntax error: {e}"],
        )

    # Step 2: Walk the AST and check for violations
    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_root = alias.name.split(".")[0]
                if module_root in DENIED_MODULES:
                    reasons.append(f"Denied import: {alias.name}")
                    verdict = PolicyVerdict.DENY
                elif module_root in APPROVAL_MODULES:
                    reasons.append(f"Network/file module needs approval: {alias.name}")
                    if verdict != PolicyVerdict.DENY:
                        verdict = PolicyVerdict.NEEDS_APPROVAL

        if isinstance(node, ast.ImportFrom):
            if node.module:
                module_root = node.module.split(".")[0]
                if module_root in DENIED_MODULES:
                    reasons.append(f"Denied import: from {node.module}")
                    verdict = PolicyVerdict.DENY
                elif module_root in APPROVAL_MODULES:
                    reasons.append(f"Network/file module needs approval: from {node.module}")
                    if verdict != PolicyVerdict.DENY:
                        verdict = PolicyVerdict.NEEDS_APPROVAL

        # Check function calls
        if isinstance(node, ast.Call):
            func_name = _get_call_name(node)
            if func_name in DENIED_BUILTINS:
                reasons.append(f"Denied built-in: {func_name}()")
                verdict = PolicyVerdict.DENY
            elif func_name in DENIED_PATTERNS:
                reasons.append(f"File access needs approval: {func_name}()")
                if verdict != PolicyVerdict.DENY:
                    verdict = PolicyVerdict.NEEDS_APPROVAL

        # Check for while True (potential infinite loop)
        if isinstance(node, ast.While):
            if isinstance(node.test, ast.Constant) and node.test.value is True:
                reasons.append("Potential infinite loop: while True")
                if verdict != PolicyVerdict.DENY:
                    verdict = PolicyVerdict.NEEDS_APPROVAL

    if not reasons:
        reasons.append("Code passed all safety checks")

    return PolicyResult(verdict=verdict, reasons=reasons)


def _get_call_name(node: ast.Call) -> str:
    """Extract function name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""
