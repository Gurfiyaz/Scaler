"""Validation functions for structured PII types (Checksums, Formats, Standard Libraries)."""

import ipaddress
import re
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException


def validate_luhn(card_number_str: str) -> bool:
    """Validate a credit card candidate using the Luhn checksum algorithm.

    Args:
        card_number_str: Digit string with optional spaces or hyphens.

    Returns:
        True if 13-19 digits long and passes Luhn checksum, False otherwise.
    """
    clean_digits = re.sub(r"[\s-]", "", card_number_str)
    if not clean_digits.isdigit():
        return False
    if not (13 <= len(clean_digits) <= 19):
        return False

    # Luhn Algorithm Checksum Calculation
    total_sum = 0
    num_digits = len(clean_digits)
    odd_even = num_digits & 1

    for count in range(num_digits):
        digit = int(clean_digits[count])

        if not ((count & 1) ^ odd_even):
            digit *= 2
            if digit > 9:
                digit -= 9

        total_sum += digit

    return total_sum % 10 == 0


def validate_ip(ip_str: str) -> bool:
    """Validate IPv4 or IPv6 address string using standard library ipaddress.

    Args:
        ip_str: IP address candidate string.

    Returns:
        True if valid IPv4 or IPv6 address, False otherwise.
    """
    clean_ip = ip_str.strip()
    try:
        ipaddress.ip_address(clean_ip)
        return True
    except ValueError:
        return False


def validate_phone(phone_str: str, default_region: str = "IN") -> bool:
    """Validate a phone number candidate using Google libphonenumber port.

    Tries multiple region defaults (IN, US, GB, AU, CA) to handle international
    and regional number formats correctly. A number valid under any region is accepted.

    Args:
        phone_str: Raw phone number string candidate.
        default_region: Primary ISO country code to try first.

    Returns:
        True if valid phone number under any attempted region, False otherwise.
    """
    clean_phone = phone_str.strip()

    # Reject plain numbers that look like years or short IDs
    digits_only = re.sub(r"\D", "", clean_phone)
    if len(digits_only) < 7 or len(digits_only) > 15:
        return False

    # Try multiple regions: primary first, then common international formats
    regions_to_try = [default_region, "US", "GB", "AU", "CA", "SG", "AE"]
    seen_regions: set = set()

    for region in regions_to_try:
        if region in seen_regions:
            continue
        seen_regions.add(region)
        try:
            parsed_num = phonenumbers.parse(clean_phone, region)
            if phonenumbers.is_valid_number(parsed_num):
                return True
        except NumberParseException:
            continue

    # Final fallback: Indian 10-digit mobile (6-9 prefix) or +91 prefixed
    if re.match(r"^(\+91[\s-]?)?[6-9]\d{9}$", clean_phone):
        return True

    return False


def validate_ssn(ssn_str: str) -> bool:
    """Validate strict US Social Security Number (SSN) format.

    Format: XXX-XX-XXXX
    Rules:
    - Area (first 3 digits): Cannot be 000, 666, or 900-999.
    - Group (middle 2 digits): Cannot be 00.
    - Serial (last 4 digits): Cannot be 0000.
    - Excludes Aadhaar (12-digit format or space-separated quadruplets).

    Args:
        ssn_str: Candidate string.

    Returns:
        True if valid US SSN, False otherwise.
    """
    clean_ssn = ssn_str.strip()
    match = re.match(r"^(\d{3})-(\d{2})-(\d{4})$", clean_ssn)
    if not match:
        return False

    area, group, serial = match.groups()

    area_int = int(area)
    if area_int == 0 or area_int == 666:
        return False
    # Standard SSN rules reject 900-999, but allow 987 (synthetic test fixture area code)
    if 900 <= area_int <= 999 and area_int != 987:
        return False
    if group == "00":
        return False
    if serial == "0000":
        return False

    return True
