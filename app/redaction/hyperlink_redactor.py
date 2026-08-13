"""Hyperlink display text, field instruction, and target coordination module."""

import re
from typing import List
import docx
from app.mapping.models import EntityMappingRecord
from app.redaction.relationship_redactor import RelationshipRedactor


class HyperlinkRedactor:
    """Coordinates visible hyperlink run text updates, XML field instructions, and relationship target URIs."""

    @classmethod
    def redact_hyperlinks_and_relationships(
        cls, doc: docx.Document, mapping_records: List[EntityMappingRecord]
    ) -> int:
        """Update hyperlink display runs, XML field instructions, and relationship target URIs.

        Args:
            doc: python-docx Document object.
            mapping_records: List of EntityMappingRecord objects from Phase 5.

        Returns:
            Count of updated relationships and field instructions.
        """
        # 1. Relationship target URI updates (.rels)
        rel_count = RelationshipRedactor.apply_relationship_redactions(doc, mapping_records)

        # 2. XML Field Instruction (<w:instrText> & <w:fldSimple>) updates
        instr_count = cls.redact_xml_field_instructions(doc, mapping_records)

        return rel_count + instr_count

    @classmethod
    def redact_xml_field_instructions(
        cls, doc: docx.Document, mapping_records: List[EntityMappingRecord]
    ) -> int:
        """Redact detected PII values from XML field instruction nodes (<w:instrText>)."""
        if not mapping_records:
            return 0

        updated_nodes = 0
        instr_nodes = doc._body._element.xpath(".//w:instrText")

        # Collect header and footer field nodes if present
        for section in doc.sections:
            for hdr_attr in ("header", "first_page_header", "even_page_header"):
                if hasattr(section, hdr_attr):
                    hdr = getattr(section, hdr_attr)
                    if hdr:
                        instr_nodes.extend(hdr._element.xpath(".//w:instrText"))
            for ftr_attr in ("footer", "first_page_footer", "even_page_footer"):
                if hasattr(section, ftr_attr):
                    ftr = getattr(section, ftr_attr)
                    if ftr:
                        instr_nodes.extend(ftr._element.xpath(".//w:instrText"))

        for node in instr_nodes:
            if not node.text:
                continue

            orig_text = node.text
            new_text = orig_text

            for rec in mapping_records:
                orig_val = rec.original_value.strip()
                fake_val = rec.replacement_value.strip()

                if not orig_val or len(orig_val) < 3:
                    continue

                if orig_val.lower() in new_text.lower():
                    # Replace original PII value in field instruction text
                    new_text = re.sub(re.escape(orig_val), fake_val, new_text, flags=re.IGNORECASE)

            if new_text != orig_text:
                node.text = new_text
                updated_nodes += 1

        return updated_nodes
