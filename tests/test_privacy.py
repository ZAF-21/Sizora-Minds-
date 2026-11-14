"""
R1 tests: PII masking — one test per mask type + negative cases.
"""

import pytest
from app.security.privacy import mask_pii, has_pii, get_masked_fields


# ── API Keys ─────────────────────────────────────────────────────────────────

class TestAPIKeyMasking:
    def test_openai_key(self):
        text = "My key is sk-1234567890abcdefghijklmnop"
        assert "[SECRET]" in mask_pii(text)
        assert "sk-1234567890" not in mask_pii(text)

    def test_groq_key(self):
        text = "Use gsk_abcdefghij1234567890abcd"
        assert "[SECRET]" in mask_pii(text)

    def test_google_key(self):
        text = "Key: AIzaSyA1234567890123456789012345678901"
        assert "[SECRET]" in mask_pii(text)

    def test_aws_key(self):
        text = "AWS key: AKIAIOSFODNN7EXAMPLE"
        assert "[SECRET]" in mask_pii(text)


# ── Email ────────────────────────────────────────────────────────────────────

class TestEmailMasking:
    def test_basic_email(self):
        text = "Send to john@example.com please"
        assert "[EMAIL]" in mask_pii(text)
        assert "john@example.com" not in mask_pii(text)

    def test_complex_email(self):
        text = "Contact first.last+tag@company.co.in"
        assert "[EMAIL]" in mask_pii(text)


# ── Phone Numbers ────────────────────────────────────────────────────────────

class TestPhoneMasking:
    def test_indian_phone_with_country_code(self):
        text = "Call me at +91 98765 43210"
        assert "[PHONE]" in mask_pii(text)

    def test_indian_mobile(self):
        text = "My number is 9876543210"
        assert "[PHONE]" in mask_pii(text)


# ── Aadhaar ──────────────────────────────────────────────────────────────────

class TestAadhaarMasking:
    def test_aadhaar_with_spaces(self):
        text = "Aadhaar: 1234 5678 9012"
        assert "[AADHAAR]" in mask_pii(text)

    def test_aadhaar_with_dashes(self):
        text = "Aadhaar: 1234-5678-9012"
        assert "[AADHAAR]" in mask_pii(text)

    def test_aadhaar_no_separator(self):
        text = "Aadhaar: 123456789012"
        assert "[AADHAAR]" in mask_pii(text)


# ── Card Numbers ─────────────────────────────────────────────────────────────

class TestCardMasking:
    def test_card_with_spaces_luhn_valid(self):
        """4111 1111 1111 1111 passes Luhn — must be masked."""
        text = "Card: 4111 1111 1111 1111"
        assert "[CARD]" in mask_pii(text)

    def test_card_with_dashes_luhn_valid(self):
        text = "Card: 4111-1111-1111-1111"
        assert "[CARD]" in mask_pii(text)

    def test_card_luhn_invalid_not_masked_as_card(self):
        """4111 1111 1111 1112 fails Luhn — must NOT be masked as [CARD]."""
        text = "Reference: 4111 1111 1111 1112"
        assert "[CARD]" not in mask_pii(text)


# ── Negative cases: these must NOT be masked ─────────────────────────────────

class TestNegativeCases:
    def test_short_number_not_masked(self):
        """Regular numbers like 42, 100, 2024 must NOT be masked."""
        text = "Write a function that returns 42"
        assert mask_pii(text) == text

    def test_normal_text_not_masked(self):
        text = "Write a palindrome checker function"
        assert mask_pii(text) == text

    def test_code_not_masked(self):
        text = "def add(a, b): return a + b"
        assert mask_pii(text) == text

    def test_year_not_masked(self):
        text = "Filter records from 2024"
        assert mask_pii(text) == text


# ── Combined ─────────────────────────────────────────────────────────────────

class TestCombined:
    def test_multiple_pii_types(self):
        text = "sk-abc123456789012345678901 email: a@b.com aadhaar: 1234 5678 9012"
        masked = mask_pii(text)
        assert "[SECRET]" in masked
        assert "[EMAIL]" in masked
        assert "[AADHAAR]" in masked
        assert "sk-abc" not in masked
        assert "a@b.com" not in masked

    def test_has_pii_positive(self):
        assert has_pii("key: sk-1234567890abcdefghijklmnop") is True

    def test_has_pii_negative(self):
        assert has_pii("Write a function") is False
