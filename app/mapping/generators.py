"""Deterministic synthetic replacement generators seeded via SHA-256 digests."""

import hashlib
import re
from typing import Optional
from faker import Faker
from app.detection.models import PIIType
from app.detection.validators import validate_luhn


class DeterministicGenerator:
    """Generates synthetic replacements using SHA-256 seeded Faker instances.

    DOES NOT use Python's built-in hash() to ensure process-independent determinism.
    """

    _faker: Optional[Faker] = None

    @classmethod
    def get_seed_hash(cls, normalized_text: str, entity_type: PIIType) -> str:
        """Compute stable SHA-256 fingerprint string."""
        raw_key = f"{normalized_text.strip().lower()}:{entity_type.value}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def get_seeded_faker(cls, seed_hash: str) -> Faker:
        """Create or reuse a Faker instance seeded deterministically from SHA-256 hash."""
        if cls._faker is None:
            cls._faker = Faker()
        seed_int = int(seed_hash[:8], 16)
        cls._faker.seed_instance(seed_int)
        return cls._faker

    @classmethod
    def generate_replacement(
        cls,
        normalized_text: str,
        entity_type: PIIType,
        associated_person_replacement: Optional[str] = None,
    ) -> tuple[str, str]:
        """Generate a deterministic, type-aware synthetic replacement value.

        Args:
            normalized_text: Normalized original entity text.
            entity_type: PIIType category.
            associated_person_replacement: Optional fake person replacement if associated.

        Returns:
            Tuple of (replacement_value_str, seed_hash_str).
        """
        seed_hash = cls.get_seed_hash(normalized_text, entity_type)
        fk = cls.get_seeded_faker(seed_hash)

        if entity_type == PIIType.PERSON:
            replacement = f"{fk.first_name()} {fk.last_name()}"

        elif entity_type == PIIType.EMAIL_ADDRESS:
            if associated_person_replacement:
                # Link email local part to associated fake person name (e.g. Peter Parker -> peter.parker@example.com)
                clean_name = re.sub(r"\W+", ".", associated_person_replacement.lower()).strip(".")
                replacement = f"{clean_name}@example.com"
            else:
                fname = fk.first_name().lower()
                lname = fk.last_name().lower()
                domain_choice = fk.random_element(["example.com", "example.org", "example.test"])
                replacement = f"{fname}.{lname}@{domain_choice}"

        elif entity_type == PIIType.PHONE_NUMBER:
            # Preserve +91 prefix or 10-digit Indian numbers vs international
            clean_digits = re.sub(r"\D", "", normalized_text)
            if normalized_text.startswith("+91") or (len(clean_digits) == 10 and clean_digits and clean_digits[0] in "6789"):
                first_digit = fk.random_element(["6", "7", "8", "9"])
                rem_digits = f"{fk.random_int(min=100000000, max=999999999):09d}"
                replacement = f"+91 {first_digit}{rem_digits[:4]} {rem_digits[4:]}"
            else:
                us_area_codes = ["212", "312", "415", "650", "206", "305", "408", "512"]
                area = fk.random_element(us_area_codes)
                suffix = fk.random_int(min=1000, max=9999)
                replacement = f"+1-{area}-555-{suffix:04d}"

        elif entity_type == PIIType.ORGANIZATION:
            comp_name = fk.company()
            # Clean any trailing legal suffixes from comp_name to prevent double suffixes
            clean_comp = re.sub(
                r"\b(Pvt|Ltd|Inc|LLP|Corp|Corporation|Limited|Company|Co)\b\.?",
                "",
                comp_name,
                flags=re.IGNORECASE,
            ).strip(" ,.")
            if not clean_comp or len(clean_comp) < 3:
                clean_comp = f"{fk.last_name()} Enterprise"

            if "pvt" in normalized_text.lower() or "ltd" in normalized_text.lower():
                replacement = f"{clean_comp} Pvt Ltd"
            elif "inc" in normalized_text.lower():
                replacement = f"{clean_comp} Inc."
            elif "llp" in normalized_text.lower():
                replacement = f"{clean_comp} LLP"
            else:
                replacement = f"{clean_comp} Corp"

        elif entity_type == PIIType.ADDRESS:
            street_num = fk.random_int(min=10, max=999)
            pin = fk.random_int(min=100000, max=999999)
            replacement = f"Plot {street_num}, Synthetic Avenue, Test City, {pin}"

        elif entity_type == PIIType.SSN:
            # Valid US SSN format: XXX-XX-XXXX (area 100-899 excluding 666, group 10-99, serial 1000-9999)
            area = fk.random_int(min=100, max=899)
            if area == 666:
                area = 665
            group = fk.random_int(min=10, max=99)
            serial = fk.random_int(min=1000, max=9999)
            replacement = f"{area:03d}-{group:02d}-{serial:04d}"

        elif entity_type == PIIType.CREDIT_CARD:
            # Generate valid Luhn card number using seeded Faker
            raw_card = fk.credit_card_number(card_type="visa")
            replacement = f"{raw_card[:4]} {raw_card[4:8]} {raw_card[8:12]} {raw_card[12:]}"

        elif entity_type == PIIType.DATE_OF_BIRTH:
            day = fk.random_int(min=1, max=28)
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            month_str = fk.random_element(month_names)
            year = fk.random_int(min=1975, max=2000)
            replacement = f"{day:02d}-{month_str}-{year}"

        elif entity_type == PIIType.IP_ADDRESS:
            # RFC 5737 Documentation test range (192.0.2.x or 198.51.100.x or 203.0.113.x)
            subnet = fk.random_element(["192.0.2", "198.51.100", "203.0.113"])
            host = fk.random_int(min=1, max=254)
            replacement = f"{subnet}.{host}"

        else:
            replacement = f"SYNTHETIC_{entity_type.value}"

        return replacement, seed_hash
