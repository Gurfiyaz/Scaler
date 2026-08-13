"""Unit tests for individual PII recognizers and validators across all 9 categories."""

import pytest
from app.detection.context_rules import ContextRulesRecognizer
from app.detection.models import PIIType
from app.detection.ner_recognizer import NERRecognizer
from app.detection.regex_recognizer import RegexRecognizer
from app.detection.span_resolver import SpanResolver
from app.detection.validators import validate_ip, validate_luhn, validate_phone, validate_ssn
from app.ingestion.models import ParagraphModel, RunModel, SourceLocation, SourceLocationType


def make_paragraph(text: str) -> ParagraphModel:
    """Helper to construct a simple single-run ParagraphModel."""
    run = RunModel(
        run_index=0,
        paragraph_index=0,
        text=text,
        start_offset=0,
        end_offset=len(text),
    )
    return ParagraphModel(
        paragraph_index=0,
        reconstructed_text=text,
        runs=[run],
        location=SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=0),
    )


# 1. EMAIL Tests
def test_email_detection_valid():
    rec = RegexRecognizer()
    p = make_paragraph("Contact alice@example.test or test+tag@example.org for info.")
    dets = rec.detect_in_paragraph(p)
    emails = [d for d in dets if d.entity_type == PIIType.EMAIL_ADDRESS]
    assert len(emails) == 2
    assert emails[0].text == "alice@example.test"
    assert emails[1].text == "test+tag@example.org"


def test_email_strips_trailing_colon():
    rec = RegexRecognizer()
    p = make_paragraph("Email: alice@example.test:")
    dets = rec.detect_in_paragraph(p)
    emails = [d for d in dets if d.entity_type == PIIType.EMAIL_ADDRESS]
    assert len(emails) == 1
    normalized = SpanResolver.normalize_detection(emails[0], p.reconstructed_text)
    assert normalized.text == "alice@example.test"


# 2. PHONE Tests
def test_phone_detection_indian():
    rec = RegexRecognizer()
    p = make_paragraph("Call us at +91 9000000000 or 9876543210.")
    dets = rec.detect_in_paragraph(p)
    phones = [d for d in dets if d.entity_type == PIIType.PHONE_NUMBER]
    assert len(phones) >= 1
    assert "+91 9000000000" in [ph.text for ph in phones]


def test_phone_rejects_arbitrary_numbers():
    assert validate_phone("2024") is False
    assert validate_phone("12345") is False


# 3. IP Tests
def test_ip_valid_and_invalid():
    assert validate_ip("192.0.2.10") is True
    assert validate_ip("2001:db8::1") is True
    assert validate_ip("256.300.1.1") is False
    assert validate_ip("v1.2.3.4") is False


def test_ip_detection_paragraph():
    rec = RegexRecognizer()
    p = make_paragraph("Server IP is 192.0.2.10 and version 1.2.3.4 is software.")
    dets = rec.detect_in_paragraph(p)
    ips = [d for d in dets if d.entity_type == PIIType.IP_ADDRESS]
    assert len(ips) == 1
    assert ips[0].text == "192.0.2.10"


# 4. CREDIT CARD Tests
def test_luhn_algorithm_validation():
    # Valid Visa test card
    assert validate_luhn("4111 1111 1111 1111") is True
    assert validate_luhn("4111-1111-1111-1111") is True
    # Invalid card number
    assert validate_luhn("4111 1111 1111 1112") is False
    # Arbitrary 16-digit random number failing Luhn
    assert validate_luhn("1234 5678 9012 3456") is False


def test_credit_card_detection():
    rec = RegexRecognizer()
    p = make_paragraph("Card details: 4111 1111 1111 1111 and order 1234 5678 9012 3456.")
    dets = rec.detect_in_paragraph(p)
    ccs = [d for d in dets if d.entity_type == PIIType.CREDIT_CARD]
    assert len(ccs) == 1
    assert ccs[0].text == "4111 1111 1111 1111"


# 5. SSN Tests
def test_ssn_validation():
    assert validate_ssn("123-45-6789") is True
    # Invalid area codes 000, 666, 900
    assert validate_ssn("000-12-3456") is False
    assert validate_ssn("666-12-3456") is False
    assert validate_ssn("950-12-3456") is False
    # Exclude Aadhaar space format
    assert validate_ssn("1234 5678 9012") is False


def test_ssn_detection():
    rec = RegexRecognizer()
    p = make_paragraph("Employee SSN: 123-45-6789.")
    dets = rec.detect_in_paragraph(p)
    ssns = [d for d in dets if d.entity_type == PIIType.SSN]
    assert len(ssns) == 1
    assert ssns[0].text == "123-45-6789"


# 6. DATE OF BIRTH Tests
def test_dob_with_context():
    context_rec = ContextRulesRecognizer()
    p_dob = make_paragraph("DOB: 15-Jan-1985 for record.")
    dets = context_rec.detect_dob(p_dob)
    assert len(dets) == 1
    assert dets[0].text == "15-Jan-1985"

    p_plain = make_paragraph("Prospectus date: 15-Jan-1985 published.")
    dets_plain = context_rec.detect_dob(p_plain)
    assert len(dets_plain) == 0


# 7. PERSON Tests
def test_person_ner_detection():
    ner = NERRecognizer()
    p = make_paragraph("Contact Alice Example for details.")
    dets = ner.detect_in_paragraph(p)
    persons = [d for d in dets if d.entity_type == PIIType.PERSON]
    assert len(persons) >= 1
    assert "Alice Example" in [d.text for d in persons]


def test_person_rejects_task_headings():
    ctx = ContextRulesRecognizer()
    assert ctx.is_excluded_heading("Assignment:") is True
    assert ctx.is_excluded_heading("Deliverables") is True
    assert ctx.is_excluded_heading("Time to complete:") is True


# 8. ORGANIZATION Tests
def test_organization_corp_suffix():
    ner = NERRecognizer()
    p = make_paragraph("Approved by ABC Technologies Pvt Ltd today.")
    dets = ner.detect_in_paragraph(p)
    orgs = [d for d in dets if d.entity_type == PIIType.ORGANIZATION]
    assert len(orgs) >= 1
    assert "ABC Technologies Pvt Ltd" in [o.text for o in orgs]


# 9. ADDRESS Tests
def test_address_detection():
    ctx = ContextRulesRecognizer()
    p = make_paragraph("Mailing Address: Plot 42, MG Road, Prakasam, Andhra Pradesh 523305.")
    dets = ctx.detect_address(p)
    assert len(dets) >= 1
    assert "Prakasam" in dets[0].text or "Andhra Pradesh" in dets[0].text or "MG Road" in dets[0].text
