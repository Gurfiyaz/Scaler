"""Master Entity Mapping and Consistency Registry Engine."""

import re
from typing import Dict, List, Optional, Set
from app.core.logging_config import logger
from app.detection.models import PIIDetection, PIIType
from app.mapping.associations import EntityAssociationManager
from app.mapping.exceptions import CollisionError, InvalidReplacementError
from app.mapping.generators import DeterministicGenerator
from app.mapping.models import EntityMappingKey, EntityMappingRecord
from app.mapping.validators import ReplacementValidator


class EntityMapper:
    """Read-only entity mapping registry for maintaining consistent fake replacements during a processing run."""

    def __init__(self):
        # Current run in-memory mapping registry
        self._registry: Dict[EntityMappingKey, EntityMappingRecord] = {}
        # Category-scoped collision prevention set: (PIIType, replacement_str)
        self._used_replacements: Set[tuple[PIIType, str]] = set()

    @classmethod
    def normalize_key_text(cls, text: str, entity_type: PIIType) -> str:
        """Normalize raw entity text into a canonical dictionary key per PII type."""
        clean = text.strip()

        if entity_type == PIIType.PERSON:
            # Collapse multiple spaces and lowercase for key matching
            return re.sub(r"\s+", " ", clean).lower()
        elif entity_type == PIIType.EMAIL_ADDRESS:
            return clean.lower()
        elif entity_type == PIIType.PHONE_NUMBER:
            # Strip non-digits except leading plus (+)
            has_plus = clean.startswith("+")
            digits = re.sub(r"\D", "", clean)
            return f"+{digits}" if has_plus else digits
        else:
            return clean.lower()

    def map_detection(
        self,
        detection: PIIDetection,
        all_detections_in_doc: Optional[List[PIIDetection]] = None,
    ) -> EntityMappingRecord:
        """Map a detected PII entity to a deterministic, consistent synthetic replacement record.

        Args:
            detection: PIIDetection object from Phase 4.
            all_detections_in_doc: Optional full list of document detections for cross-entity linking.

        Returns:
            EntityMappingRecord containing replacement value and SHA-256 fingerprint.
        """
        orig_text = detection.text
        e_type = detection.entity_type
        norm_key_text = self.normalize_key_text(orig_text, e_type)
        key = EntityMappingKey(entity_type=e_type, normalized_original=norm_key_text)

        # 1. Return existing mapping if already mapped in this processing run
        if key in self._registry:
            return self._registry[key]

        # 2. Check Person-Email Cross-Entity Association
        associated_person_fake: Optional[str] = None
        if e_type == PIIType.EMAIL_ADDRESS and all_detections_in_doc:
            matched_person_orig = EntityAssociationManager.match_email_to_person(
                orig_text, all_detections_in_doc
            )
            if matched_person_orig:
                person_key_text = self.normalize_key_text(matched_person_orig, PIIType.PERSON)
                person_key = EntityMappingKey(
                    entity_type=PIIType.PERSON, normalized_original=person_key_text
                )
                if person_key in self._registry:
                    associated_person_fake = self._registry[person_key].replacement_value
                else:
                    # Map the person first to derive their fake name
                    matching_person_dets = [
                        d for d in all_detections_in_doc
                        if d.entity_type == PIIType.PERSON and self.normalize_key_text(d.text, PIIType.PERSON) == person_key_text
                    ]
                    if matching_person_dets:
                        person_rec = self.map_detection(matching_person_dets[0], all_detections_in_doc)
                        associated_person_fake = person_rec.replacement_value

        # 3. Generate Deterministic Replacement
        replacement_val, seed_hash = DeterministicGenerator.generate_replacement(
            norm_key_text, e_type, associated_person_fake
        )

        # 4. Category-Scoped Collision Prevention Check
        attempts = 0
        final_replacement = replacement_val
        while (e_type, final_replacement) in self._used_replacements:
            attempts += 1
            if attempts > 100:
                raise CollisionError(f"Failed to resolve collision after 100 attempts for category '{e_type.value}'")
            # Re-seed deterministically with attempt counter
            alt_key = f"{norm_key_text}_attempt_{attempts}"
            final_replacement, _ = DeterministicGenerator.generate_replacement(
                alt_key, e_type, associated_person_fake
            )
            if attempts > 50:
                if e_type == PIIType.EMAIL_ADDRESS and "@" in final_replacement:
                    user_part, domain_part = final_replacement.rsplit("@", 1)
                    final_replacement = f"{user_part}.{attempts - 49}@{domain_part}"
                elif e_type in (PIIType.PERSON, PIIType.ORGANIZATION, PIIType.ADDRESS):
                    final_replacement = f"{final_replacement} {attempts - 49}"

        # 5. Replacement Safety & Format Validation
        ReplacementValidator.validate_replacement(e_type, final_replacement, orig_text)

        # 6. Register Record
        creation_idx = len(self._registry)
        record = EntityMappingRecord(
            original_value=orig_text,
            normalized_original=norm_key_text,
            entity_type=e_type,
            replacement_value=final_replacement,
            seed_hash=seed_hash,
            associated_person_name=associated_person_fake,
            creation_index=creation_idx,
        )

        self._registry[key] = record
        self._used_replacements.add((e_type, final_replacement))

        return record

    def map_all_detections(
        self, detections: List[PIIDetection]
    ) -> Dict[EntityMappingKey, EntityMappingRecord]:
        """Batch map a list of detections for a document processing run."""
        records: Dict[EntityMappingKey, EntityMappingRecord] = {}
        for det in detections:
            rec = self.map_detection(det, detections)
            key = EntityMappingKey(
                entity_type=det.entity_type,
                normalized_original=self.normalize_key_text(det.text, det.entity_type),
            )
            records[key] = rec

        # Safe privacy logging: Log aggregated counts ONLY, NEVER raw pairs
        cat_counts: Dict[str, int] = {}
        for rec in self._registry.values():
            cat = rec.entity_type.value
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        logger.info(
            f"Entity Mapping Complete. Mapped {len(self._registry)} unique entities across categories: {cat_counts}"
        )

        return records

    def clear(self):
        """Clear current run mapping state."""
        self._registry.clear()
        self._used_replacements.clear()
