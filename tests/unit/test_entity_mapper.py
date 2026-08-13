"""Unit tests for EntityMapper, DeterministicGenerator, and ReplacementValidator."""

import pytest
from app.detection.models import PIIDetection, PIIType
from app.ingestion.models import SourceLocation, SourceLocationType
from app.mapping.associations import EntityAssociationManager
from app.mapping.entity_mapper import EntityMapper
from app.mapping.exceptions import InvalidReplacementError
from app.mapping.generators import DeterministicGenerator
from app.mapping.validators import ReplacementValidator


def make_det(text: str, e_type: PIIType, p_idx: int = 0) -> PIIDetection:
    """Helper to create a PIIDetection object."""
    return PIIDetection(
        entity_type=e_type,
        start=0,
        end=len(text),
        text=text,
        recognizer="test",
        confidence=1.0,
        paragraph_index=p_idx,
        location=SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=p_idx),
    )


# 1. Determinism across separate processes / mapper instances
def test_determinism_across_separate_instances():
    det1 = make_det("Rohan Dey", PIIType.PERSON)
    det2 = make_det("Rohan Dey", PIIType.PERSON)

    mapper1 = EntityMapper()
    mapper2 = EntityMapper()

    rec1 = mapper1.map_detection(det1)
    rec2 = mapper2.map_detection(det2)

    assert rec1.replacement_value == rec2.replacement_value
    assert rec1.seed_hash == rec2.seed_hash


# 2. Case and Whitespace Normalization
def test_normalization_consistency():
    mapper = EntityMapper()

    rec1 = mapper.map_detection(make_det("Rohan Dey", PIIType.PERSON))
    rec2 = mapper.map_detection(make_det("rohan dey", PIIType.PERSON))
    rec3 = mapper.map_detection(make_det("  Rohan   Dey  ", PIIType.PERSON))

    assert rec1.replacement_value == rec2.replacement_value
    assert rec2.replacement_value == rec3.replacement_value


# 3. Different Entities map to Different Replacements (Collision Prevention)
def test_collision_prevention_different_entities():
    mapper = EntityMapper()

    rec1 = mapper.map_detection(make_det("Rohan Dey", PIIType.PERSON))
    rec2 = mapper.map_detection(make_det("Rashi Patil", PIIType.PERSON))

    assert rec1.replacement_value != rec2.replacement_value


# 4. Person-Email Association Test
def test_person_email_association():
    mapper = EntityMapper()

    det_person = make_det("Rohan Dey", PIIType.PERSON)
    det_email = make_det("rohan.dey@gmail.com", PIIType.EMAIL_ADDRESS)

    all_dets = [det_person, det_email]

    rec_person = mapper.map_detection(det_person, all_dets)
    rec_email = mapper.map_detection(det_email, all_dets)

    person_fake_parts = rec_person.replacement_value.lower().split()
    email_local = rec_email.replacement_value.split("@")[0].lower()

    # Verify that fake email local part matches fake person name tokens
    assert any(part in email_local for part in person_fake_parts)
    assert rec_email.replacement_value.endswith("@example.com")


# 5. Over-Linking Prevention Test (Unrelated email)
def test_unrelated_email_not_associated():
    mapper = EntityMapper()

    det_person = make_det("Alice Smith", PIIType.PERSON)
    det_support = make_det("support@example.test", PIIType.EMAIL_ADDRESS)

    all_dets = [det_person, det_support]

    rec_person = mapper.map_detection(det_person, all_dets)
    rec_support = mapper.map_detection(det_support, all_dets)

    person_fake_parts = rec_person.replacement_value.lower().split()
    support_local = rec_support.replacement_value.split("@")[0].lower()

    # Generic email local part 'support' must NOT be linked to person name
    assert not any(part in support_local for part in person_fake_parts)


# 6. Type-Specific Generators Tests
def test_generator_phone_format_preservation():
    mapper = EntityMapper()
    det = make_det("+91 9876543210", PIIType.PHONE_NUMBER)
    rec = mapper.map_detection(det)

    assert rec.replacement_value.startswith("+91")
    assert rec.replacement_value != "+91 9876543210"


def test_generator_credit_card_luhn_valid():
    mapper = EntityMapper()
    det = make_det("4111 1111 1111 1111", PIIType.CREDIT_CARD)
    rec = mapper.map_detection(det)

    assert ReplacementValidator.validate_replacement(PIIType.CREDIT_CARD, rec.replacement_value, det.text) is True


def test_generator_ssn_valid():
    mapper = EntityMapper()
    det = make_det("123-45-6789", PIIType.SSN)
    rec = mapper.map_detection(det)

    assert ReplacementValidator.validate_replacement(PIIType.SSN, rec.replacement_value, det.text) is True


def test_generator_ip_address_valid():
    mapper = EntityMapper()
    det = make_det("192.0.2.10", PIIType.IP_ADDRESS)
    rec = mapper.map_detection(det)

    # Must be documentation RFC 5737 IP range
    assert any(rec.replacement_value.startswith(prefix) for prefix in ("192.0.2", "198.51.100", "203.0.113"))


def test_generator_organization_legal_suffix():
    mapper = EntityMapper()
    det = make_det("Acme Pvt Ltd", PIIType.ORGANIZATION)
    rec = mapper.map_detection(det)

    assert "Pvt Ltd" in rec.replacement_value
    assert rec.replacement_value != "Acme Pvt Ltd"


def test_generator_address():
    mapper = EntityMapper()
    det = make_det("Plot 42, MG Road, Bangalore 560001", PIIType.ADDRESS)
    rec = mapper.map_detection(det)

    assert "Synthetic Avenue" in rec.replacement_value or "Plot" in rec.replacement_value
    assert rec.replacement_value != det.text


# 7. Safety Validation: Cannot contain original PII fragment
def test_replacement_safety_rejection():
    with pytest.raises(InvalidReplacementError):
        ReplacementValidator.validate_replacement(PIIType.PERSON, "Rohan Parker", "Rohan Dey")
