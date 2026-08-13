"""Cross-run span mapping utility.

Maps character offset spans [start_offset, end_offset) within a reconstructed paragraph
to the exact run(s) containing those character spans.
"""

from typing import List
from app.ingestion.models import ParagraphModel, RunModel


class RunMapper:
    """Utility for resolving paragraph character offsets to underlying DOCX runs."""

    @staticmethod
    def map_span_to_runs(
        paragraph: ParagraphModel, start_offset: int, end_offset: int
    ) -> List[RunModel]:
        """Resolve a half-open character span [start_offset, end_offset) to run(s).

        Args:
            paragraph: The reconstructed paragraph containing runs with offsets.
            start_offset: Inclusive start character index in paragraph.reconstructed_text.
            end_offset: Exclusive end character index in paragraph.reconstructed_text.

        Returns:
            List of RunModel objects that overlap with the specified span.

        Raises:
            ValueError: If offsets are negative, start > end, or end > len(paragraph text).
        """
        text_len = len(paragraph.reconstructed_text)

        if start_offset < 0 or end_offset < 0:
            raise ValueError(f"Offsets must be non-negative: start={start_offset}, end={end_offset}")
        if start_offset > end_offset:
            raise ValueError(f"start_offset ({start_offset}) cannot be greater than end_offset ({end_offset})")
        if end_offset > text_len:
            raise ValueError(
                f"end_offset ({end_offset}) exceeds paragraph text length ({text_len})"
            )

        # Empty span handling: match half-open interval [run.start_offset, run.end_offset)
        if start_offset == end_offset:
            for run in paragraph.runs:
                if run.start_offset <= start_offset < run.end_offset or (
                    start_offset == text_len and start_offset == run.end_offset
                ):
                    return [run]
            return []

        overlapping_runs: List[RunModel] = []
        for run in paragraph.runs:
            # Overlap condition for half-open intervals [start_offset, end_offset) and [run.start_offset, run.end_offset)
            if max(start_offset, run.start_offset) < min(end_offset, run.end_offset):
                overlapping_runs.append(run)

        return overlapping_runs
