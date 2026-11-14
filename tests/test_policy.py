"""
R2 tests: Policy gate — deny dangerous code, allow safe code, needs_approval for risky code.
"""

import pytest
from app.execution.policy import evaluate_code_policy
from app.models import PolicyVerdict


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
