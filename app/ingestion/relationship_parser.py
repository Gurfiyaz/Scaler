"""Dynamic relationship XML parser for DOCX containers."""

import zipfile
import xml.etree.ElementTree as ET
from typing import Dict
from app.core.logging_config import logger
from app.ingestion.models import RelationshipModel


class RelationshipParser:
    """Parses OOXML relationship (.rels) files dynamically without hardcoded IDs."""

    REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"

    @classmethod
    def parse_relationships_from_zip(
        cls, z: zipfile.ZipFile, rels_file_path: str = "word/_rels/document.xml.rels"
    ) -> Dict[str, RelationshipModel]:
        """Extract relationship mapping dictionary (rId -> RelationshipModel) from ZIP archive.

        Args:
            z: Open ZipFile object of the DOCX container.
            rels_file_path: Path to the .rels XML file inside the archive.

        Returns:
            Dictionary mapping relationship ID (e.g. 'rId1', 'rId6') to RelationshipModel.
        """
        relationships: Dict[str, RelationshipModel] = {}

        if rels_file_path not in z.namelist():
            logger.debug(f"Relationship file '{rels_file_path}' not found in archive.")
            return relationships

        try:
            raw_xml = z.read(rels_file_path)
            tree = ET.fromstring(raw_xml)

            for elem in tree.iter(f"{cls.REL_NS}Relationship"):
                r_id = elem.attrib.get("Id")
                r_type = elem.attrib.get("Type", "")
                r_target = elem.attrib.get("Target", "")
                r_target_mode = elem.attrib.get("TargetMode", "Internal")

                if r_id:
                    relationships[r_id] = RelationshipModel(
                        relationship_id=r_id,
                        type=r_type,
                        target=r_target,
                        target_mode=r_target_mode,
                    )

        except Exception as err:
            logger.warning(f"Failed to parse relationship file '{rels_file_path}': {err}")

        return relationships
