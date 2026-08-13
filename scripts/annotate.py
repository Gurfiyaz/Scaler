"""Independent Manual Annotation Helper CLI for PII Ground Truth.

CRITICAL PRINCIPLE: Detector outputs are NEVER loaded or displayed by this tool.
Ground truth is created purely via independent human inspection of reconstructed document text.
"""

import sys
from pathlib import Path
from typing import List, Optional

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.detection.models import PIIType
from app.evaluation.ground_truth import GroundTruthManager
from app.evaluation.models import GroundTruthAnnotation, GroundTruthDocument
from app.ingestion.docx_parser import DOCXParser


def get_prospectus_path() -> Path:
    """Find local prospectus document path."""
    candidates = [
        Path(r"C:\Users\gurfiyaz basha\Downloads\Enterprise Data - Assignment.docx"),
        Path("sample_data/Red Herring Prospectus.docx"),
        Path("Red Herring Prospectus.docx"),
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("Target assessment prospectus document not found.")


def print_menu():
    print("\n" + "=" * 60)
    print("      INDEPENDENT MANUAL PII ANNOTATION CLI TOOL")
    print("=" * 60)
    print("1. View all document paragraphs & offsets")
    print("2. View a specific paragraph text with character indices")
    print("3. Add a ground-truth PII annotation [start, end)")
    print("4. List currently saved annotations")
    print("5. Delete an annotation")
    print("6. Save ground truth to private_data/ground_truth.json & Exit")
    print("7. Exit without saving")
    print("=" * 60)


def display_paragraph_with_indices(text: str):
    """Print text with character index markers every 10 chars."""
    print("\n--- RECONSTRUCTED TEXT ---")
    print(text)
    print("--- CHARACTER INDEX MARKERS ---")
    lines = []
    idx_line = ""
    for i, ch in enumerate(text):
        if i % 10 == 0:
            idx_line += str(i % 100).zfill(2)
        else:
            idx_line += " "
    print(idx_line)
    print("-" * 60)


def main():
    try:
        doc_path = get_prospectus_path()
    except FileNotFoundError as err:
        print(f"Error: {err}")
        return

    print(f"Loading document for independent manual inspection: {doc_path.name}")
    parser = DOCXParser()
    doc_model = parser.parse_document(doc_path)
    print(f"Parsed {len(doc_model.paragraphs)} reconstructed paragraphs.")

    out_file = Path("private_data/ground_truth.json")
    if out_file.exists():
        gt_doc = GroundTruthManager.load_from_file(out_file)
        print(f"Loaded existing ground truth with {len(gt_doc.annotations)} annotations.")
    else:
        gt_doc = GroundTruthDocument(document_id=doc_path.name, annotations=[])

    while True:
        print_menu()
        choice = input("Enter option (1-7): ").strip()

        if choice == "1":
            print("\n--- ALL PARAGRAPHS ---")
            for p in doc_model.paragraphs:
                preview = p.reconstructed_text[:80].replace("\n", " ")
                print(f"P{p.paragraph_index:02d} [{p.location.location_type.value}]: {preview} (Len: {len(p.reconstructed_text)})")

        elif choice == "2":
            p_str = input("Enter paragraph index: ").strip()
            if not p_str.isdigit():
                print("Invalid paragraph index.")
                continue
            p_idx = int(p_str)
            target_p = next((p for p in doc_model.paragraphs if p.paragraph_index == p_idx), None)
            if not target_p:
                print("Paragraph index not found.")
                continue
            display_paragraph_with_indices(target_p.reconstructed_text)

        elif choice == "3":
            p_str = input("Enter paragraph index: ").strip()
            if not p_str.isdigit():
                print("Invalid paragraph index.")
                continue
            p_idx = int(p_str)
            target_p = next((p for p in doc_model.paragraphs if p.paragraph_index == p_idx), None)
            if not target_p:
                print("Paragraph index not found.")
                continue

            display_paragraph_with_indices(target_p.reconstructed_text)

            print("\nSelect PIIType category:")
            cats = list(PIIType)
            for i, cat in enumerate(cats, 1):
                print(f"  {i}. {cat.value}")
            cat_choice = input(f"Select category (1-{len(cats)}): ").strip()
            if not cat_choice.isdigit() or not (1 <= int(cat_choice) <= len(cats)):
                print("Invalid category choice.")
                continue
            selected_cat = cats[int(cat_choice) - 1]

            start_str = input("Enter start character offset: ").strip()
            end_str = input("Enter end character offset (exclusive): ").strip()

            if not (start_str.isdigit() and end_str.isdigit()):
                print("Offsets must be integers.")
                continue

            start = int(start_str)
            end = int(end_str)

            if not (0 <= start < end <= len(target_p.reconstructed_text)):
                print(f"Invalid offsets [0, {len(target_p.reconstructed_text)}].")
                continue

            highlighted = target_p.reconstructed_text[start:end]
            confirm = input(f"Confirm annotating '{highlighted}' as {selected_cat.value}? (y/n): ").strip().lower()
            if confirm == "y":
                ann_id = f"gt_p{p_idx:02d}_{len(gt_doc.annotations)+1}"
                ann = GroundTruthAnnotation(
                    entity_type=selected_cat,
                    start=start,
                    end=end,
                    paragraph_index=p_idx,
                    annotation_id=ann_id,
                    location=target_p.location,
                )
                gt_doc.annotations.append(ann)
                print(f"Added annotation {ann_id}.")

        elif choice == "4":
            print("\n--- CURRENT SAVED ANNOTATIONS ---")
            if not gt_doc.annotations:
                print("No annotations recorded yet.")
            for i, ann in enumerate(gt_doc.annotations, 1):
                print(f"{i:02d}. ID: {ann.annotation_id} | P{ann.paragraph_index:02d} [{ann.start}:{ann.end}] | Category: {ann.entity_type.value}")

        elif choice == "5":
            if not gt_doc.annotations:
                print("No annotations to delete.")
                continue
            del_str = input("Enter annotation number to delete: ").strip()
            if del_str.isdigit() and 1 <= int(del_str) <= len(gt_doc.annotations):
                removed = gt_doc.annotations.pop(int(del_str) - 1)
                print(f"Removed annotation {removed.annotation_id}.")

        elif choice == "6":
            GroundTruthManager.save_to_file(gt_doc, out_file)
            print(f"Saved {len(gt_doc.annotations)} annotations to private file '{out_file}'. Privacy preserved.")
            break

        elif choice == "7":
            print("Exited without saving.")
            break


if __name__ == "__main__":
    main()
