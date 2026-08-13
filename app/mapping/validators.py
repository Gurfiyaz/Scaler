"""Replacement safety and format validation module."""

import re
from app.detection.models import PIIType
from app.detection.validators import validate_ip, validate_luhn, validate_phone, validate_ssn
from app.mapping.exceptions import InvalidReplacementError


class ReplacementValidator:
    """Validates that synthetic replacements satisfy type constraints and contain no source PII."""

    RESERVED_DOMAINS = ("@example.com", "@example.org", "@example.test")

    @classmethod
    def validate_replacement(
        cls, entity_type: PIIType, replacement_value: str, original_value: str
    ) -> bool:
        """Validate format and safety of a generated replacement string.

        Raises:
            InvalidReplacementError: If replacement is invalid or contains original PII.
        """
        clean_rep = replacement_value.strip()
        clean_orig = original_value.strip()

        if not clean_rep:
            raise InvalidReplacementError("Replacement value cannot be empty.")

        # Safety Check: Replacement must not equal original PII
        if clean_rep.lower() == clean_orig.lower():
            raise InvalidReplacementError("Replacement value is identical to original PII.")

        # Safety Check for names/orgs: Must not contain any distinctive token of original name
        GENERIC_WORDS = {
            "pvt", "ltd", "inc", "corp", "llp", "llc", "limited", "co", "company", "labs",
            "technologies", "services", "solutions", "systems", "and", "the", "for", "group",
            "holdings", "enterprises", "enterprise", "international", "global", "national", "trust", "bank", "fund",
            "associates", "partners", "capital", "management", "financial", "advisors", "india", "private"
        }
        if entity_type in (PIIType.PERSON, PIIType.ORGANIZATION):
            orig_tokens = [t.lower() for t in re.split(r"\W+", clean_orig) if len(t) > 2 and t.lower() not in GENERIC_WORDS]
            for token in orig_tokens:
                if re.search(r"\b" + re.escape(token) + r"\b", clean_rep, re.IGNORECASE):
                    raise InvalidReplacementError(
                        f"Replacement contains original PII token fragment: '{token}'"
                    )

        # Type-specific format checks
        if entity_type == PIIType.CREDIT_CARD:
            if not validate_luhn(clean_rep):
                raise InvalidReplacementError("Generated credit card failed Luhn checksum.")

        elif entity_type == PIIType.IP_ADDRESS:
            if not validate_ip(clean_rep):
                raise InvalidReplacementError("Generated IP address failed IP format validation.")

        elif entity_type == PIIType.SSN:
            if not validate_ssn(clean_rep):
                raise InvalidReplacementError("Generated SSN failed US SSN validation rules.")

        elif entity_type == PIIType.PHONE_NUMBER:
            if not validate_phone(clean_rep):
                raise InvalidReplacementError("Generated phone number failed phone validation.")

        elif entity_type == PIIType.EMAIL_ADDRESS:
            if not any(clean_rep.endswith(dom) for dom in cls.RESERVED_DOMAINS):
                raise InvalidReplacementError(
                    f"Generated email '{clean_rep}' does not use a reserved test domain (@example.com)."
                )

        return True
