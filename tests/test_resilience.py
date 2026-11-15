"""
R5 tests: Resilience — chaos mode, circuit breaker, template fallback.
"""

import pytest
from app.resilience.chaos import enable_chaos, disable_chaos, chaos_maybe_fail, ChaosError
from app.resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, CircuitState
from app.resilience.templates import match_template, TEMPLATES
from app.resilience.retry import full_jitter_delay, is_transient_error
from app.resilience.fallback import AllTiersExhaustedError


class TestChaos:
    def test_chaos_disabled_by_default(self):
        """No failures when chaos is off."""
        disable_chaos()
        for _ in range(100):
            chaos_maybe_fail()  # Should never raise

    def test_chaos_enabled_fails(self):
        """With 100% failure rate, should always raise."""
        enable_chaos(failure_rate=1.0)
        with pytest.raises(ChaosError):
            chaos_maybe_fail()
        disable_chaos()

    def test_chaos_zero_rate(self):
        """With 0% failure rate, should never raise."""
        enable_chaos(failure_rate=0.0)
        for _ in range(100):
            chaos_maybe_fail()
        disable_chaos()


class TestCircuitBreaker:
    def test_closed_by_default(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            try:
                cb.call(self._failing_func)
            except ValueError:
                pass
        assert cb.state == CircuitState.OPEN

    def test_open_circuit_fails_fast(self):
        cb = CircuitBreaker(failure_threshold=1)
        try:
            cb.call(self._failing_func)
        except ValueError:
            pass
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(self._succeeding_func)

    def test_reset(self):
        cb = CircuitBreaker(failure_threshold=1)
        try:
            cb.call(self._failing_func)
        except ValueError:
            pass
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        result = cb.call(self._succeeding_func)
        assert result == "ok"

    @staticmethod
    def _failing_func():
        raise ValueError("simulated failure")

    @staticmethod
    def _succeeding_func():
        return "ok"


class TestTemplates:
    def test_palindrome_template_match(self):
        template = match_template("Write a palindrome checker")
        assert template is not None
        assert "is_palindrome" in template.code

    def test_factorial_template_match(self):
        template = match_template("compute the factorial of a number")
        assert template is not None
        assert "factorial" in template.code

    def test_fibonacci_template_match(self):
        template = match_template("generate fibonacci numbers")
        assert template is not None
        assert "fibonacci" in template.code

    def test_fizzbuzz_template_match(self):
        template = match_template("implement fizzbuzz")
        assert template is not None
        assert "fizzbuzz" in template.code.lower()

    def test_list_sum_template_match(self):
        template = match_template("return the sum of a list")
        assert template is not None
        assert "list_sum" in template.code

    def test_no_match_for_unknown(self):
        template = match_template("implement a B-tree with deletion")
        assert template is None

    @pytest.mark.parametrize("request_text,expected", [
        ("give me pallindrome code bro", "palindrome"),
        ("palindrom checker", "palindrome"),
        ("write factoral function", "factorial"),
        ("fizz-buzz program", "fizzbuzz"),
        ("bubbel sort", "bubble_sort"),
        ("quik sort code", "quick_sort"),
        ("binery search", "binary_search"),
    ])
    def test_typos_match_template(self, request_text, expected):
        assert match_template(request_text) is TEMPLATES[expected]

    @pytest.mark.parametrize("request_text,expected", [
        ("Implement binary search", "binary_search"),
        ("Write a linear search function", "linear_search"),
        ("Write bubble sort", "bubble_sort"),
        ("Implement selection sort", "selection_sort"),
        ("Write an insertion sort function", "insertion_sort"),
        ("Write merge sort in python", "merge_sort"),
        ("Implement quicksort", "quick_sort"),
        ("Write a function to sort a list please", "merge_sort"),
    ])
    def test_search_and_sort_templates(self, request_text, expected):
        assert match_template(request_text) is TEMPLATES[expected]

    @pytest.mark.parametrize("request_text", [
        "Count vowels in a string",
        "merge two sorted arrays",
        "write a parser for dates",
    ])
    def test_fuzzy_no_false_positive(self, request_text):
        assert match_template(request_text) is None

    @pytest.mark.parametrize("name", list(TEMPLATES))
    def test_template_passes_own_tests_in_sandbox(self, name):
        from app.execution.sandbox import run_in_sandbox
        from app.execution.policy import evaluate_code_policy
        from app.models import PolicyVerdict
        t = TEMPLATES[name]
        assert evaluate_code_policy(t.code).verdict == PolicyVerdict.ALLOW
        result = run_in_sandbox(t.code, t.tests)
        assert result["passed"], result["output"][-500:]

    def test_all_templates_have_code_and_tests(self):
        for name, t in TEMPLATES.items():
            assert len(t.code.strip()) > 0, f"Template {name} has no code"
            assert len(t.tests.strip()) > 0, f"Template {name} has no tests"
            assert len(t.keywords) > 0, f"Template {name} has no keywords"


class TestRetry:
    def test_full_jitter_delay_within_bounds(self):
        for attempt in range(5):
            delay = full_jitter_delay(attempt, base=1.0, cap=30.0)
            assert 0 <= delay <= 30.0

    def test_is_transient_429(self):
        assert is_transient_error(Exception("429 Too Many Requests")) is True

    def test_is_transient_timeout(self):
        assert is_transient_error(Exception("connection timeout")) is True

    def test_not_transient_400(self):
        assert is_transient_error(Exception("400 Bad Request")) is False

    def test_not_transient_auth(self):
        assert is_transient_error(Exception("401 Unauthorized")) is False
