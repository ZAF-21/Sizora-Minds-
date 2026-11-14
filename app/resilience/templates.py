"""
R5: Deterministic template library — last-resort tier for common tasks.
At least 5 tasks: palindrome, factorial, fibonacci, fizzbuzz, list_sum.
"""

from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass
class TemplatePair:
    code: str
    tests: str
    keywords: list[str]
    time_complexity: str = ""
    space_complexity: str = ""


TEMPLATES: dict[str, TemplatePair] = {
    "palindrome": TemplatePair(
        time_complexity="O(n)", space_complexity="O(n)",
        keywords=["palindrome", "is_palindrome", "reverse string", "reads the same"],
        code='''\
def is_palindrome(s: str) -> bool:
    """Check if a string is a palindrome (case-insensitive, ignoring non-alphanumeric)."""
    cleaned = ''.join(c.lower() for c in s if c.isalnum())
    return cleaned == cleaned[::-1]
''',
        tests='''\
from solution import is_palindrome

def test_palindrome_basic():
    assert is_palindrome("racecar") == True

def test_palindrome_mixed_case():
    assert is_palindrome("RaceCar") == True

def test_palindrome_with_spaces():
    assert is_palindrome("A man a plan a canal Panama") == True

def test_not_palindrome():
    assert is_palindrome("hello") == False

def test_empty_string():
    assert is_palindrome("") == True

def test_single_char():
    assert is_palindrome("a") == True
''',
    ),

    "factorial": TemplatePair(
        time_complexity="O(n)", space_complexity="O(1)",
        keywords=["factorial", "n!", "product of all"],
        code='''\
def factorial(n: int) -> int:
    """Return the factorial of n. Raises ValueError for negative input."""
    if not isinstance(n, int):
        raise TypeError("Input must be an integer")
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
''',
        tests='''\
import pytest
from solution import factorial

def test_factorial_zero():
    assert factorial(0) == 1

def test_factorial_one():
    assert factorial(1) == 1

def test_factorial_five():
    assert factorial(5) == 120

def test_factorial_ten():
    assert factorial(10) == 3628800

def test_factorial_negative():
    with pytest.raises(ValueError):
        factorial(-1)

def test_factorial_type_error():
    with pytest.raises(TypeError):
        factorial(3.5)
''',
    ),

    "fibonacci": TemplatePair(
        time_complexity="O(n)", space_complexity="O(n)",
        keywords=["fibonacci", "fib", "fibonacci sequence", "fibonacci number"],
        code='''\
def fibonacci(n: int) -> list[int]:
    """Return the first n Fibonacci numbers."""
    if not isinstance(n, int) or n < 0:
        raise ValueError("Input must be a non-negative integer")
    if n == 0:
        return []
    if n == 1:
        return [0]
    fibs = [0, 1]
    for _ in range(2, n):
        fibs.append(fibs[-1] + fibs[-2])
    return fibs
''',
        tests='''\
import pytest
from solution import fibonacci

def test_fibonacci_zero():
    assert fibonacci(0) == []

def test_fibonacci_one():
    assert fibonacci(1) == [0]

def test_fibonacci_two():
    assert fibonacci(2) == [0, 1]

def test_fibonacci_ten():
    assert fibonacci(10) == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

def test_fibonacci_negative():
    with pytest.raises(ValueError):
        fibonacci(-1)
''',
    ),

    "fizzbuzz": TemplatePair(
        time_complexity="O(n)", space_complexity="O(n)",
        keywords=["fizzbuzz", "fizz buzz", "divisible by 3 and 5"],
        code='''\
def fizzbuzz(n: int) -> list[str]:
    """Return FizzBuzz results for numbers 1 through n."""
    if not isinstance(n, int) or n < 1:
        raise ValueError("Input must be a positive integer")
    result = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            result.append("FizzBuzz")
        elif i % 3 == 0:
            result.append("Fizz")
        elif i % 5 == 0:
            result.append("Buzz")
        else:
            result.append(str(i))
    return result
''',
        tests='''\
import pytest
from solution import fizzbuzz

def test_fizzbuzz_fifteen():
    result = fizzbuzz(15)
    assert result[0] == "1"
    assert result[2] == "Fizz"
    assert result[4] == "Buzz"
    assert result[14] == "FizzBuzz"

def test_fizzbuzz_one():
    assert fizzbuzz(1) == ["1"]

def test_fizzbuzz_three():
    assert fizzbuzz(3) == ["1", "2", "Fizz"]

def test_fizzbuzz_five():
    assert fizzbuzz(5) == ["1", "2", "Fizz", "4", "Buzz"]

def test_fizzbuzz_invalid():
    with pytest.raises(ValueError):
        fizzbuzz(0)
''',
    ),

    "list_sum": TemplatePair(
        time_complexity="O(n)", space_complexity="O(1)",
        keywords=["sum", "list sum", "sum of list", "add all", "total"],
        code='''\
def list_sum(items) -> int | float:
    """
    If items is a list, return its sum using a list comprehension.
    If items is a tuple, use functional programming (reduce).
    """
    from functools import reduce
    if isinstance(items, list):
        return sum([x for x in items])
    elif isinstance(items, tuple):
        if len(items) == 0:
            return 0
        return reduce(lambda a, b: a + b, items)
    else:
        raise TypeError("Input must be a list or tuple")
''',
        tests='''\
import pytest
from solution import list_sum

def test_list_sum_basic():
    assert list_sum([1, 2, 3]) == 6

def test_list_sum_empty():
    assert list_sum([]) == 0

def test_tuple_sum_basic():
    assert list_sum((1, 2, 3)) == 6

def test_tuple_sum_empty():
    assert list_sum(()) == 0

def test_list_sum_floats():
    assert list_sum([1.5, 2.5]) == 4.0

def test_invalid_type():
    with pytest.raises(TypeError):
        list_sum("hello")
''',
    ),

    "reverse_string": TemplatePair(
        time_complexity="O(n)", space_complexity="O(n)",
        keywords=["reverse", "reverse string", "reverse a string"],
        code='''\
def reverse_string(s: str) -> str:
    """Reverse a string."""
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    return s[::-1]
''',
        tests='''\
import pytest
from solution import reverse_string

def test_reverse_basic():
    assert reverse_string("hello") == "olleh"

def test_reverse_empty():
    assert reverse_string("") == ""

def test_reverse_single():
    assert reverse_string("a") == "a"

def test_reverse_palindrome():
    assert reverse_string("racecar") == "racecar"

def test_reverse_type_error():
    with pytest.raises(TypeError):
        reverse_string(123)
''',
    ),
}


def match_template(request: str) -> TemplatePair | None:
    """Try to match a request to a known template using keyword matching."""
    request_lower = request.lower()
    best_match = None
    best_score = 0

    for name, template in TEMPLATES.items():
        score = sum(1 for kw in template.keywords if kw in request_lower)
        if score > best_score:
            best_score = score
            best_match = template

    return best_match if best_score > 0 else None
