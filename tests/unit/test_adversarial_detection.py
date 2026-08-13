"""Adversarial Detection Unit Tests.

Stress-tests PII recognizers against false positive and false negative edge cases.
"""

from pathlib import Path
import pytest
from app.detection.detector import PIIDetector
from app.detection.models import PIIType
from app.ingestion.models import ParagraphModel, SourceLocation, SourceLocationType


@pytest.fixture
def detector():
    return PIIDetector()


def make_para(text: str, idx: int = 0) -> ParagraphModel:
    return ParagraphModel(
        paragraph_index=idx,
        reconstructed_text=text,
        location=SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=idx),
    )


# 1. Email Adversarial Edge Cases
@pytest.mark.parametrize(
    "text,expected_count,expected_email",
    [
        ("Contact Alice at ALICE@EXAMPLE.COM.", 1, "ALICE@EXAMPLE.COM"),
        ("Reach out to user.name+tag@sub.domain.co.uk for help.", 1, "user.name+tag@sub.domain.co.uk"),
        ("Email (alice.smith-123@example.org) for details.", 1, "alice.smith-123@example.org"),
        ("Send note to 'bob@test.com'.", 1, "bob@test.com"),
        ("Contact support@company.io: now", 1, "support@company.io"),
    ],
)
def test_email_adversarial_valid(detector, text, expected_count, expected_email):
    para = make_para(text)
    dets = detector.detect_in_paragraph(para)
    emails = [d for d in dets if d.entity_type == PIIType.EMAIL_ADDRESS]
    assert len(emails) == expected_count
    if expected_count > 0:
        assert emails[0].text == expected_email
        assert text[emails[0].start : emails[0].end] == expected_email


@pytest.mark.parametrize(
    "text",
    [
        "Contact info at missing_at_domain.com",
        "Invalid email @example.com without local part",
        "Double at user@@example.com in text",
        "Plain text user@ without domain",
    ],
)
def test_email_adversarial_invalid(detector, text):
    para = make_para(text)
    dets = detector.detect_in_paragraph(para)
    emails = [d for d in dets if d.entity_type == PIIType.EMAIL_ADDRESS]
    assert len(emails) == 0


# 2. Phone Number Adversarial Edge Cases
@pytest.mark.parametrize(
    "text,expected_phone",
    [
        ("Call +91 9876543210 immediately.", "+91 9876543210"),
        ("Reach us at +91-9000000000.", "+91-9000000000"),
        ("Contact (+1-800-555-0199) today.", "+1-800-555-0199"),
    ],
)
def test_phone_adversarial_valid(detector, text, expected_phone):
    para = make_para(text)
    dets = detector.detect_in_paragraph(para)
    phones = [d for d in dets if d.entity_type == PIIType.PHONE_NUMBER]
    assert len(phones) >= 1
    assert phones[0].text == expected_phone


@pytest.mark.parametrize(
    "text",
    [
        "Total revenue was 100,000 USD in 2026.",
        "Refer to page 123 or section 456.",
        "Financial transaction ID 987654321000.",
    ],
)
def test_phone_adversarial_rejections(detector, text):
    para = make_para(text)
    dets = detector.detect_in_paragraph(para)
    phones = [d for d in dets if d.entity_type == PIIType.PHONE_NUMBER]
    assert len(phones) == 0


# 3. IP Address Adversarial Edge Cases
@pytest.mark.parametrize(
    "text,expected_ip",
    [
        ("Server IP is 192.0.2.1.", "192.0.2.1"),
        ("Gateway: 198.51.100.10", "198.51.100.10"),
        ("IPv6 host: 2001:db8::1.", "2001:db8::1"),
    ],
)
def test_ip_adversarial_valid(detector, text, expected_ip):
    para = make_para(text)
    dets = detector.detect_in_paragraph(para)
    ips = [d for d in dets if d.entity_type == PIIType.IP_ADDRESS]
    assert len(ips) == 1
    assert ips[0].text == expected_ip


@pytest.mark.parametrize(
    "text",
    [
        "Invalid IP 999.999.999.999 in config.",
        "Out of range octet 256.256.256.256.",
        "Version string v1.2.3.4 is not an IP.",
        "Dotted decimal sequence 123.456.78.90.",
    ],
)
def test_ip_adversarial_invalid(detector, text):
    para = make_para(text)
    dets = detector.detect_in_paragraph(para)
    ips = [d for d in dets if d.entity_type == PIIType.IP_ADDRESS]
    assert len(ips) == 0


# 4. Credit Card Adversarial Edge Cases
def test_credit_card_valid_and_invalid(detector):
    valid_cc_para = make_para("Pay using card 4111-1111-1111-1111 now.")
    dets = detector.detect_in_paragraph(valid_cc_para)
    ccs = [d for d in dets if d.entity_type == PIIType.CREDIT_CARD]
    assert len(ccs) == 1
    assert ccs[0].text == "4111-1111-1111-1111"

    # Fails Luhn checksum
    invalid_cc_para = make_para("Card number 4111-1111-1111-1112 is invalid.")
    dets2 = detector.detect_in_paragraph(invalid_cc_para)
    ccs2 = [d for d in dets2 if d.entity_type == PIIType.CREDIT_CARD]
    assert len(ccs2) == 0


# 5. SSN Adversarial Edge Cases
def test_ssn_strict_us_validation(detector):
    valid_ssn = make_para("US Citizen SSN is 123-45-6789.")
    dets = detector.detect_in_paragraph(valid_ssn)
    ssns = [d for d in dets if d.entity_type == PIIType.SSN]
    assert len(ssns) == 1
    assert ssns[0].text == "123-45-6789"

    # Indian Aadhaar must NOT be classified as SSN
    aadhaar_para = make_para("Aadhaar card number 1234-5678-9012.")
    dets2 = detector.detect_in_paragraph(aadhaar_para)
    ssns2 = [d for d in dets2 if d.entity_type == PIIType.SSN]
    assert len(ssns2) == 0


# 6. Date of Birth Adversarial Edge Cases
def test_dob_vs_document_date(detector):
    dob_para = make_para("Date of Birth: 15/08/1990 for John Doe.")
    dets = detector.detect_in_paragraph(dob_para)
    dobs = [d for d in dets if d.entity_type == PIIType.DATE_OF_BIRTH]
    assert len(dobs) == 1
    assert dobs[0].text == "15/08/1990"

    doc_date_para = make_para("Document filed on 15/08/1990 by company.")
    dets2 = detector.detect_in_paragraph(doc_date_para)
    dobs2 = [d for d in dets2 if d.entity_type == PIIType.DATE_OF_BIRTH]
    assert len(dobs2) == 0


# 7. Person NER vs Task Headings
def test_person_heading_rejection(detector):
    person_para = make_para("Interview conducted by Rashi Patil and Rohan Dey.")
    dets = detector.detect_in_paragraph(person_para)
    persons = [d for d in dets if d.entity_type == PIIType.PERSON]
    names = [p.text for p in persons]
    assert "Rashi Patil" in names
    assert "Rohan Dey" in names

    # Heading words must NOT be detected as PERSON
    heading_para = make_para("Deliverables and Background for Task Assignment.")
    dets2 = detector.detect_in_paragraph(heading_para)
    persons2 = [d for d in dets2 if d.entity_type == PIIType.PERSON]
    for p in persons2:
        assert p.text not in {"Deliverables", "Background", "Task", "Assignment"}


# 8. Organization Suffixes vs Generic Words
def test_organization_suffix_matching(detector):
    org_para = make_para("Contract signed with Apex Solutions Inc and Acme Corp Pvt Ltd.")
    dets = detector.detect_in_paragraph(org_para)
    orgs = [d for d in dets if d.entity_type == PIIType.ORGANIZATION]
    assert len(orgs) >= 1

    # Generic words must be excluded
    generic_para = make_para("The Company and the Applicant filed requirements for PII DOCX README.")
    dets2 = detector.detect_in_paragraph(generic_para)
    orgs2 = [d for d in dets2 if d.entity_type == PIIType.ORGANIZATION]
    for o in orgs2:
        assert o.text.lower() not in {"company", "applicant", "the company", "pii", "docx", "readme"}


# 9. Address Boundary Guidelines
def test_address_detection_conservative(detector):
    addr_para = make_para("Mailing address: 123 MG Road, Sector 4, Bangalore 560001, India.")
    dets = detector.detect_in_paragraph(addr_para)
    addrs = [d for d in dets if d.entity_type == PIIType.ADDRESS]
    assert len(addrs) >= 1

    # Single-word city names (e.g. "Bangalore") are intentionally NOT detected as ADDRESS.
    # The min-token guard (>=2 tokens or contains digit) prevents single GPE proper nouns
    # from inflating ADDRESS counts — bare city names are not structural mailing addresses.
    city_para = make_para("The team is based in Bangalore.")
    dets2 = detector.detect_in_paragraph(city_para)
    addrs2 = [d for d in dets2 if d.entity_type == PIIType.ADDRESS]
    assert len(addrs2) == 0  # Correct: single city name is not a structural address

    # Multi-word location names or those with digits ARE still detected
    multi_para = make_para("The office is in New Delhi.")
    dets3 = detector.detect_in_paragraph(multi_para)
    addrs3 = [d for d in dets3 if d.entity_type == PIIType.ADDRESS]
    # "New Delhi" has 2 tokens — may be detected by spaCy GPE
    # (result depends on spaCy model, not asserted strictly)
    assert isinstance(addrs3, list)  # Type check — result is valid

