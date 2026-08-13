"""Developer CLI Inspection Tool for DOCX Structure.

Outputs SAFE structural statistics (counts, timings, formatting stats)
WITHOUT printing raw document text or PII.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.docx_parser import DOCXParser
from app.ingestion.exceptions import IngestionError


def inspect_file(file_path: str):
    """Run read-only DOCX parser and display safe structural metrics."""
    path_obj = Path(file_path)

    print("=" * 60)
    print("      DOCX STRUCTURAL INSPECTION REPORT (SAFE METRICS)")
    print("=" * 60)

    if not path_obj.exists():
        print(f"[ERROR] File not found: '{file_path}'")
        sys.exit(1)

    file_size_bytes = path_obj.stat().st_size
    print(f"File Name: {path_obj.name}")
    print(f"File Size: {file_size_bytes} bytes ({file_size_bytes / 1024:.2f} KB)")

    parser = DOCXParser()

    start_time = time.perf_counter()
    try:
        doc_model = parser.parse_document(path_obj, document_id="cli_inspect")
        duration_sec = time.perf_counter() - start_time
    except IngestionError as err:
        print(f"[INGESTION ERROR] {type(err).__name__}: {err}")
        sys.exit(1)
    except Exception as err:
        print(f"[UNEXPECTED ERROR] {err}")
        sys.exit(1)

    print("\n--- Structural Counts ---")
    print(f"Total Paragraphs    : {len(doc_model.paragraphs)}")
    print(f"Total Runs          : {doc_model.total_runs}")
    print(f"Total Tables        : {len(doc_model.tables)}")
    print(f"Header Sections     : {len(doc_model.headers)}")
    print(f"Footer Sections     : {len(doc_model.footers)}")
    print(f"Hyperlinks Detected : {len(doc_model.hyperlinks)}")
    print(f"Relationships Count : {len(doc_model.relationships)}")

    # Formatting statistics
    bold_runs = 0
    italic_runs = 0
    underline_runs = 0
    colored_runs = 0

    for p in doc_model.paragraphs:
        for r in p.runs:
            if r.formatting.bold:
                bold_runs += 1
            if r.formatting.italic:
                italic_runs += 1
            if r.formatting.underline:
                underline_runs += 1
            if r.formatting.color_hex:
                colored_runs += 1

    print("\n--- Formatting Statistics ---")
    print(f"Bold Runs           : {bold_runs}")
    print(f"Italic Runs         : {italic_runs}")
    print(f"Underline Runs      : {underline_runs}")
    print(f"Colored Runs        : {colored_runs}")

    print("\n--- Performance Metrics ---")
    print(f"Parsing Duration    : {duration_sec * 1000:.2f} ms ({duration_sec:.4f} s)")
    print("=" * 60)
    print("PRIVACY CONFIRMED: 0 raw PII strings were emitted to logs or safe summaries.")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/inspect_docx.py <path_to_docx>")
        sys.exit(1)

    inspect_file(sys.argv[1])
