"""Ground-truth dataset loader and serializer."""

import json
from pathlib import Path
from typing import Any, Dict, List, Union
from app.detection.models import PIIType
from app.evaluation.models import GroundTruthAnnotation, GroundTruthDocument
from app.ingestion.models import SourceLocation, SourceLocationType


class GroundTruthManager:
    """Manages serialization and deserialization of ground-truth annotation datasets."""

    @staticmethod
    def load_from_file(file_path: Union[str, Path]) -> GroundTruthDocument:
        """Load ground-truth annotations from a JSON file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Ground truth file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return GroundTruthManager.from_dict(data)

    @staticmethod
    def save_to_file(doc: GroundTruthDocument, file_path: Union[str, Path]) -> None:
        """Save ground-truth document to a JSON file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = GroundTruthManager.to_dict(doc)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> GroundTruthDocument:
        """Construct GroundTruthDocument from dictionary format."""
        doc_id = data.get("document", data.get("document_id", "unknown_doc"))
        created_at = data.get("created_at", "")
        annotator_id = data.get("annotator_id", "human_annotator")
        metadata = data.get("metadata", {})

        annotations: List[GroundTruthAnnotation] = []
        for raw in data.get("annotations", []):
            try:
                entity_type = PIIType(raw["entity_type"])
            except ValueError:
                # Fallback for unknown entity types
                continue

            location = None
            if "location" in raw and isinstance(raw["location"], dict):
                loc_dict = raw["location"]
                loc_type = SourceLocationType(loc_dict.get("location_type", "body"))
                location = SourceLocation(
                    location_type=loc_type,
                    paragraph_index=loc_dict.get("paragraph_index", raw.get("paragraph_index", 0)),
                    table_index=loc_dict.get("table_index"),
                    row_index=loc_dict.get("row_index"),
                    cell_index=loc_dict.get("cell_index"),
                    header_kind=loc_dict.get("header_kind"),
                    footer_kind=loc_dict.get("footer_kind"),
                )

            ann = GroundTruthAnnotation(
                entity_type=entity_type,
                start=int(raw["start"]),
                end=int(raw["end"]),
                paragraph_index=int(raw.get("paragraph_index", 0)),
                annotation_id=raw.get("annotation_id", f"gt_{len(annotations)+1}"),
                location=location,
                text_sha256=raw.get("text_sha256"),
                metadata=raw.get("metadata", {}),
            )
            annotations.append(ann)

        return GroundTruthDocument(
            document_id=doc_id,
            annotations=annotations,
            created_at=created_at,
            annotator_id=annotator_id,
            metadata=metadata,
        )

    @staticmethod
    def to_dict(doc: GroundTruthDocument) -> Dict[str, Any]:
        """Convert GroundTruthDocument to dictionary format."""
        raw_annotations = []
        for ann in doc.annotations:
            raw_ann: Dict[str, Any] = {
                "annotation_id": ann.annotation_id,
                "entity_type": ann.entity_type.value,
                "start": ann.start,
                "end": ann.end,
                "paragraph_index": ann.paragraph_index,
            }
            if ann.location:
                raw_ann["location"] = {
                    "location_type": ann.location.location_type.value,
                    "paragraph_index": ann.location.paragraph_index,
                    "table_index": ann.location.table_index,
                    "row_index": ann.location.row_index,
                    "cell_index": ann.location.cell_index,
                    "header_kind": ann.location.header_kind,
                    "footer_kind": ann.location.footer_kind,
                }
            if ann.text_sha256:
                raw_ann["text_sha256"] = ann.text_sha256
            if ann.metadata:
                raw_ann["metadata"] = ann.metadata

            raw_annotations.append(raw_ann)

        return {
            "document": doc.document_id,
            "created_at": doc.created_at,
            "annotator_id": doc.annotator_id,
            "annotations": raw_annotations,
            "metadata": doc.metadata,
        }
