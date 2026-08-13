"""Conservative Person-Email cross-entity association manager."""

import re
from typing import List, Optional
from app.detection.models import PIIDetection, PIIType


class EntityAssociationManager:
    """Manages associations between detected Person names and Email addresses."""

    GENERIC_LOCAL_PARTS = {"support", "info", "admin", "contact", "sales", "help", "office", "billing"}

    @classmethod
    def match_email_to_person(
        cls, email_text: str, candidate_persons: List[PIIDetection]
    ) -> Optional[str]:
        """Check if an email's local part correlates with a detected Person entity name.

        Args:
            email_text: Raw email text (e.g. 'rohan.dey@gmail.com').
            candidate_persons: List of detected PERSON PIIDetection objects in paragraph/document.

        Returns:
            Matched person original text (e.g. 'Rohan Dey') if strongly associated, else None.
        """
        if "@" not in email_text:
            return None

        local_part = email_text.split("@")[0].lower()

        # Reject generic local parts
        if local_part in cls.GENERIC_LOCAL_PARTS:
            return None

        email_tokens = [t for t in re.split(r"\W+", local_part) if len(t) > 2]
        if not email_tokens:
            return None

        for person_det in candidate_persons:
            if person_det.entity_type != PIIType.PERSON:
                continue

            person_text = person_det.text
            person_tokens = [t.lower() for t in re.split(r"\W+", person_text) if len(t) > 2]

            # Check if any email token matches a person name token
            for e_tok in email_tokens:
                for p_tok in person_tokens:
                    if e_tok == p_tok or (len(e_tok) > 3 and e_tok in p_tok):
                        return person_text

        return None
