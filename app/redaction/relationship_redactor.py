"""Relationship (.rels) target URI redaction module."""

from typing import List
import docx
from app.detection.models import PIIType
from app.mapping.models import EntityMappingRecord


class RelationshipRedactor:
    """Updates target URIs in DOCX relationship parts without hardcoding relationship IDs."""

    @classmethod
    def apply_relationship_redactions(
        cls, doc: docx.Document, mapping_records: List[EntityMappingRecord]
    ) -> int:
        """Update any relationship target URIs (e.g. mailto: emails) containing original PII.

        Args:
            doc: python-docx Document object.
            mapping_records: List of EntityMappingRecord objects from Phase 5.

        Returns:
            Count of updated relationship targets.
        """
        updated_count = 0
        if not mapping_records:
            return 0

        # Filter mappings for emails or web/URI identifiers
        email_mappings = [
            m for m in mapping_records
            if m.entity_type in (PIIType.EMAIL_ADDRESS, PIIType.PERSON)
        ]

        if not email_mappings:
            return 0

        # Iterate over all document relationships (document part rels)
        try:
            rels = doc.part.rels
        except AttributeError:
            return 0

        for r_id, rel in rels.items():
            target_uri = rel.target_ref
            if not target_uri or not isinstance(target_uri, str):
                continue

            for record in email_mappings:
                orig_val = record.original_value.strip()
                fake_val = record.replacement_value.strip()

                if not orig_val:
                    continue

                if orig_val.lower() in target_uri.lower():
                    # Preserve mailto: or prefix if present
                    if target_uri.lower().startswith("mailto:"):
                        new_target = f"mailto:{fake_val}"
                    else:
                        # Case insensitive replacement
                        import re
                        new_target = re.sub(re.escape(orig_val), fake_val, target_uri, flags=re.IGNORECASE)

                    rel._target = new_target
                    updated_count += 1
                    break

        return updated_count
