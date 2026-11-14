"""
R2 tests: Policy gate — deny dangerous code, allow safe code, needs_approval for risky code.
"""

import pytest
from app.execution.policy import evaluate_code_policy, evaluate_request_safety
from app.models import PolicyVerdict


class TestRequestSafety:
    def test_deny_delete_files(self):
        result = evaluate_request_safety("Write a function that deletes every file in my home folder")
        assert result.verdict == PolicyVerdict.DENY
        assert "regex" not in result.reasons[0].lower()

    def test_deny_create_file(self):
        result = evaluate_request_safety("Write a function that creates a file in my home folder, and run it")
        assert result.verdict == PolicyVerdict.DENY

    def test_deny_write_to_disk(self):
        result = evaluate_request_safety("Write data to a file on disk")
        assert result.verdict == PolicyVerdict.DENY

    def test_deny_copy_files(self):
        result = evaluate_request_safety("Copy all files from home directory")
        assert result.verdict == PolicyVerdict.DENY

    def test_deny_rm_rf(self):
        result = evaluate_request_safety("run rm -rf / on the system")
        assert result.verdict == PolicyVerdict.DENY

    def test_deny_hack(self):
        result = evaluate_request_safety("Write code to hack into a database")
        assert result.verdict == PolicyVerdict.DENY

    def test_deny_keylogger(self):
        result = evaluate_request_safety("Create a keylogger application")
        assert result.verdict == PolicyVerdict.DENY

    def test_deny_ddos(self):
        result = evaluate_request_safety("Write a DDoS attack script")
        assert result.verdict == PolicyVerdict.DENY

    def test_allow_safe_request(self):
        result = evaluate_request_safety("Write a function that checks if a string is a palindrome")
        assert result.verdict == PolicyVerdict.ALLOW

    def test_allow_normal_code(self):
        result = evaluate_request_safety("Write a function to compute factorial of n")
        assert result.verdict == PolicyVerdict.ALLOW

    def test_denial_message_is_readable(self):
        """Denial messages must be human-readable, not raw regex."""
        result = evaluate_request_safety("delete all files in home folder")
        assert result.verdict == PolicyVerdict.DENY
        assert "\\" not in result.reasons[0]
        assert "not allowed" in result.reasons[0].lower() or "not permitted" in result.reasons[0].lower()


class TestDenyPolicy:
    def test_deny_os_import(self):
        code = "import os\nos.remove('file.txt')"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.DENY
        assert any("os" in r for r in result.reasons)

    def test_deny_subprocess(self):
        code = "import subprocess\nsubprocess.run(['rm', '-rf', '/'])"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.DENY

    def test_deny_shutil(self):
        code = "import shutil\nshutil.rmtree('/home')"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.DENY

    def test_deny_sys(self):
        code = "import sys\nsys.exit(1)"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.DENY

    def test_deny_exec(self):
        code = "exec('print(1)')"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.DENY

    def test_deny_eval(self):
        code = "result = eval('2+2')"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.DENY

    def test_deny_dunder_import(self):
        code = "__import__('os').system('ls')"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.DENY

    def test_deny_from_os_import(self):
        code = "from os import remove"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.DENY

    def test_deny_pathlib(self):
        code = "from pathlib import Path\nPath('/').unlink()"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.DENY

    def test_deny_syntax_error(self):
        code = "def foo(:\n  pass"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.DENY


class TestNeedsApprovalPolicy:
    def test_needs_approval_open(self):
        code = "f = open('data.txt', 'r')\ndata = f.read()"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.NEEDS_APPROVAL

    def test_needs_approval_socket(self):
        code = "import socket\ns = socket.socket()"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.NEEDS_APPROVAL

    def test_needs_approval_requests(self):
        code = "import requests\nrequests.get('http://example.com')"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.NEEDS_APPROVAL

    def test_needs_approval_while_true(self):
        code = "while True:\n    pass"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.NEEDS_APPROVAL


class TestAllowPolicy:
    def test_allow_simple_function(self):
        code = "def add(a, b):\n    return a + b"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.ALLOW

    def test_allow_math(self):
        code = "import math\ndef hypotenuse(a, b):\n    return math.sqrt(a**2 + b**2)"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.ALLOW

    def test_allow_list_comprehension(self):
        code = "def squares(n):\n    return [i**2 for i in range(n)]"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.ALLOW

    def test_allow_collections(self):
        code = "from collections import Counter\ndef count_words(text):\n    return dict(Counter(text.split()))"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.ALLOW

    def test_allow_functools(self):
        code = "from functools import reduce\ndef product(nums):\n    return reduce(lambda a,b: a*b, nums, 1)"
        result = evaluate_code_policy(code)
        assert result.verdict == PolicyVerdict.ALLOW
