"""
R5: Deterministic template library — last-resort tier for common tasks.
At least 5 tasks: palindrome, factorial, fibonacci, fizzbuzz, list_sum.
"""

from __future__ import annotations
import difflib
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

    "calculator": TemplatePair(
        time_complexity="O(1)", space_complexity="O(1)",
        keywords=["calculator", "simple calculator", "basic calculator", "arithmetic calculator"],
        code='''\
def calculator(a: float, b: float, operator: str) -> float:
    """Apply a basic arithmetic operator (+, -, *, /, //, %, **) to two numbers. No eval()."""
    for value in (a, b):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Operands must be numbers")
    if operator in ("/", "//", "%") and b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    operations = {
        "+": lambda x, y: x + y,
        "-": lambda x, y: x - y,
        "*": lambda x, y: x * y,
        "/": lambda x, y: x / y,
        "//": lambda x, y: x // y,
        "%": lambda x, y: x % y,
        "**": lambda x, y: x ** y,
    }
    if operator not in operations:
        raise ValueError(f"Unsupported operator: {operator!r}. Use one of {', '.join(operations)}")
    return operations[operator](a, b)
''',
        tests='''\
import pytest
from solution import calculator

def test_calculator_add_subtract():
    assert calculator(7, 3, "+") == 10
    assert calculator(7, 3, "-") == 4

def test_calculator_multiply_divide():
    assert calculator(6, 4, "*") == 24
    assert calculator(7, 2, "/") == 3.5

def test_calculator_floor_div_mod_power():
    assert calculator(7, 2, "//") == 3
    assert calculator(7, 2, "%") == 1
    assert calculator(2, 10, "**") == 1024

def test_calculator_negatives_and_floats():
    assert calculator(-5, 2.5, "+") == -2.5

def test_calculator_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        calculator(1, 0, "/")

def test_calculator_unknown_operator():
    with pytest.raises(ValueError):
        calculator(1, 2, "^")

def test_calculator_type_error():
    with pytest.raises(TypeError):
        calculator("1", 2, "+")
''',
    ),

    # ── Searching ────────────────────────────────────────────────────────────
    "linear_search": TemplatePair(
        time_complexity="O(n)", space_complexity="O(1)",
        keywords=["linear search", "linear_search", "linearsearch", "sequential search"],
        code='''\
def linear_search(items: list, target) -> int:
    """Return the index of the first occurrence of target in items, or -1 if not found."""
    if not isinstance(items, (list, tuple)):
        raise TypeError("items must be a list or tuple")
    for index, value in enumerate(items):
        if value == target:
            return index
    return -1
''',
        tests='''\
import pytest
from solution import linear_search

def test_linear_search_found():
    assert linear_search([4, 2, 7, 1], 7) == 2

def test_linear_search_first_occurrence():
    assert linear_search([5, 3, 5, 3], 3) == 1

def test_linear_search_not_found():
    assert linear_search([1, 2, 3], 9) == -1

def test_linear_search_empty():
    assert linear_search([], 1) == -1

def test_linear_search_strings():
    assert linear_search(["a", "b", "c"], "c") == 2

def test_linear_search_type_error():
    with pytest.raises(TypeError):
        linear_search("abc", "a")
''',
    ),

    "binary_search": TemplatePair(
        time_complexity="O(log n)", space_complexity="O(1)",
        keywords=["binary search", "binary_search", "binarysearch", "bisect"],
        code='''\
def binary_search(items: list, target) -> int:
    """Return the index of target in the sorted list items, or -1 if not found (iterative)."""
    if not isinstance(items, (list, tuple)):
        raise TypeError("items must be a list or tuple")
    low, high = 0, len(items) - 1
    while low <= high:
        mid = (low + high) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
''',
        tests='''\
import pytest
from solution import binary_search

def test_binary_search_middle():
    assert binary_search([1, 3, 5, 7, 9], 5) == 2

def test_binary_search_first_and_last():
    assert binary_search([1, 3, 5, 7, 9], 1) == 0
    assert binary_search([1, 3, 5, 7, 9], 9) == 4

def test_binary_search_not_found():
    assert binary_search([1, 3, 5, 7, 9], 4) == -1

def test_binary_search_empty():
    assert binary_search([], 1) == -1

def test_binary_search_single():
    assert binary_search([42], 42) == 0

def test_binary_search_negatives():
    assert binary_search([-10, -3, 0, 8], -3) == 1

def test_binary_search_type_error():
    with pytest.raises(TypeError):
        binary_search(None, 1)
''',
    ),

    # ── Sorting ──────────────────────────────────────────────────────────────
    "bubble_sort": TemplatePair(
        time_complexity="O(n^2)", space_complexity="O(n)",
        keywords=["bubble sort", "bubble_sort", "bubblesort"],
        code='''\
def bubble_sort(items: list) -> list:
    """Return a new list sorted in ascending order using bubble sort (stops early if already sorted)."""
    if not isinstance(items, (list, tuple)):
        raise TypeError("items must be a list or tuple")
    result = list(items)
    n = len(result)
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            if result[j] > result[j + 1]:
                result[j], result[j + 1] = result[j + 1], result[j]
                swapped = True
        if not swapped:
            break
    return result
''',
        tests="",  # filled by _sort_tests below
    ),

    "selection_sort": TemplatePair(
        time_complexity="O(n^2)", space_complexity="O(n)",
        keywords=["selection sort", "selection_sort", "selectionsort"],
        code='''\
def selection_sort(items: list) -> list:
    """Return a new list sorted in ascending order using selection sort."""
    if not isinstance(items, (list, tuple)):
        raise TypeError("items must be a list or tuple")
    result = list(items)
    n = len(result)
    for i in range(n - 1):
        min_index = i
        for j in range(i + 1, n):
            if result[j] < result[min_index]:
                min_index = j
        result[i], result[min_index] = result[min_index], result[i]
    return result
''',
        tests="",  # filled by _sort_tests below
    ),

    "insertion_sort": TemplatePair(
        time_complexity="O(n^2)", space_complexity="O(n)",
        keywords=["insertion sort", "insertion_sort", "insertionsort"],
        code='''\
def insertion_sort(items: list) -> list:
    """Return a new list sorted in ascending order using insertion sort (stable)."""
    if not isinstance(items, (list, tuple)):
        raise TypeError("items must be a list or tuple")
    result = list(items)
    for i in range(1, len(result)):
        key = result[i]
        j = i - 1
        while j >= 0 and result[j] > key:
            result[j + 1] = result[j]
            j -= 1
        result[j + 1] = key
    return result
''',
        tests="",  # filled by _sort_tests below
    ),

    "merge_sort": TemplatePair(
        time_complexity="O(n log n)", space_complexity="O(n)",
        keywords=["merge sort", "merge_sort", "mergesort",
                  "sort a list", "sort the list", "sort list", "sort an array", "sort the array",
                  "sort array", "sorting algorithm", "sort numbers"],
        code='''\
def merge_sort(items: list) -> list:
    """Return a new list sorted in ascending order using merge sort (stable)."""
    if not isinstance(items, (list, tuple)):
        raise TypeError("items must be a list or tuple")
    if len(items) <= 1:
        return list(items)
    mid = len(items) // 2
    left = merge_sort(items[:mid])
    right = merge_sort(items[mid:])
    merged = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged
''',
        tests="",  # filled by _sort_tests below
    ),

    "quick_sort": TemplatePair(
        time_complexity="O(n log n) average, O(n^2) worst", space_complexity="O(n)",
        keywords=["quick sort", "quick_sort", "quicksort"],
        code='''\
def quick_sort(items: list) -> list:
    """Return a new list sorted in ascending order using quick sort (middle pivot, 3-way partition)."""
    if not isinstance(items, (list, tuple)):
        raise TypeError("items must be a list or tuple")
    if len(items) <= 1:
        return list(items)
    pivot = items[len(items) // 2]
    smaller = [x for x in items if x < pivot]
    equal = [x for x in items if x == pivot]
    larger = [x for x in items if x > pivot]
    return quick_sort(smaller) + equal + quick_sort(larger)
''',
        tests="",  # filled by _sort_tests below
    ),
}


def _sort_tests(fn: str) -> str:
    """Shared pytest suite for every sorting template."""
    return f'''\
import pytest
from solution import {fn}

def test_{fn}_basic():
    assert {fn}([5, 2, 9, 1, 7]) == [1, 2, 5, 7, 9]

def test_{fn}_duplicates_and_negatives():
    assert {fn}([3, -1, 3, 0, -1]) == [-1, -1, 0, 3, 3]

def test_{fn}_already_sorted_and_reversed():
    assert {fn}([1, 2, 3, 4]) == [1, 2, 3, 4]
    assert {fn}([4, 3, 2, 1]) == [1, 2, 3, 4]

def test_{fn}_empty_and_single():
    assert {fn}([]) == []
    assert {fn}([42]) == [42]

def test_{fn}_does_not_mutate_input():
    data = [3, 1, 2]
    {fn}(data)
    assert data == [3, 1, 2]

def test_{fn}_strings_and_tuple():
    assert {fn}(["pear", "apple", "fig"]) == ["apple", "fig", "pear"]
    assert {fn}((2, 1)) == [1, 2]

def test_{fn}_type_error():
    with pytest.raises(TypeError):
        {fn}(None)
'''


for _name in ("bubble_sort", "selection_sort", "insertion_sort", "merge_sort", "quick_sort"):
    TEMPLATES[_name].tests = _sort_tests(_name)


FUZZY_MIN_KEYWORD_LEN = 7
FUZZY_MIN_RATIO = 0.8


def _fuzzy_match(request_lower: str) -> TemplatePair | None:
    """Typo-tolerant fallback ("pallindrome", "factoral", "bubbel sort"): compare single words and
    adjacent word pairs against single-token keywords (e.g. "bubblesort", "binary_search").
    Generic phrases ("sort array", "list sum") and short keywords ("sum", "fib") are exact-match only."""
    words = re.findall(r"[a-z]+", request_lower)
    candidates = set(words) | {a + b for a, b in zip(words, words[1:])}
    best_match, best_ratio = None, 0.0
    for template in TEMPLATES.values():
        for kw in template.keywords:
            if " " in kw:
                continue
            kw = kw.replace("_", "")
            if len(kw) < FUZZY_MIN_KEYWORD_LEN:
                continue
            for word in candidates:
                ratio = difflib.SequenceMatcher(None, word, kw).ratio()
                if ratio >= FUZZY_MIN_RATIO and ratio > best_ratio:
                    best_match, best_ratio = template, ratio
    return best_match


def match_template(request: str) -> TemplatePair | None:
    """Try to match a request to a known template using keyword matching, then typo-tolerant matching."""
    request_lower = re.sub(r"[-_]+", " ", request.lower())
    request_lower = f"{request_lower} {request.lower()}"
    best_match = None
    best_score = 0

    for name, template in TEMPLATES.items():
        score = sum(1 for kw in template.keywords if kw in request_lower)
        if score > best_score:
            best_score = score
            best_match = template

    return best_match if best_score > 0 else _fuzzy_match(request_lower)
