"""In-place paragraph run rewriting engine preserving XML formatting and cross-run spans."""

from typing import List
import docx
from app.redaction.models import RedactionTask


class RunRewriter:
    """Rewrites text within python-docx Paragraph XML runs without destroying run-level formatting."""

    @classmethod
    def apply_paragraph_redactions(
        cls, doc_p: docx.text.paragraph.Paragraph, tasks: List[RedactionTask]
    ) -> int:
        """Apply non-overlapping redaction tasks to a paragraph in right-to-left order.

        Args:
            doc_p: python-docx Paragraph object.
            tasks: List of RedactionTask objects targeting this paragraph.

        Returns:
            Count of successfully applied replacement tasks.
        """
        if not tasks:
            return 0

        # Sort tasks in descending order of start_offset (right-to-left edit plan)
        sorted_tasks = sorted(tasks, key=lambda t: t.start_offset, reverse=True)
        applied_count = 0

        for task in sorted_tasks:
            # Collect all XML runs in paragraph (including runs inside <w:hyperlink>)
            xml_runs = [docx.text.run.Run(r_elem, doc_p) for r_elem in doc_p._p.xpath(".//w:r")]
            if not xml_runs:
                continue

            # Build character offsets for each run
            run_offsets: List[tuple[int, int]] = []
            curr_off = 0
            for r in xml_runs:
                r_len = len(r.text or "")
                run_offsets.append((curr_off, curr_off + r_len))
                curr_off += r_len

            # Identify affected runs
            start_off = task.start_offset
            end_off = task.end_offset
            replacement = task.replacement_text

            affected_indices = []
            for i, (r_start, r_end) in enumerate(run_offsets):
                # Check overlap between [r_start, r_end) and [start_off, end_off)
                if max(r_start, start_off) < min(r_end, end_off):
                    affected_indices.append(i)

            if not affected_indices:
                continue

            first_idx = affected_indices[0]
            last_idx = affected_indices[-1]

            # 1. Single-run PII Replacement
            if first_idx == last_idx:
                r = xml_runs[first_idx]
                r_start, _ = run_offsets[first_idx]
                local_start = start_off - r_start
                local_end = end_off - r_start
                orig_text = r.text or ""
                new_text = orig_text[:local_start] + replacement + orig_text[local_end:]
                r.text = new_text
                applied_count += 1

            # 2. Cross-run PII Replacement
            else:
                first_run = xml_runs[first_idx]
                first_r_start, _ = run_offsets[first_idx]
                first_local_start = start_off - first_r_start
                first_orig = first_run.text or ""

                last_run = xml_runs[last_idx]
                last_r_start, _ = run_offsets[last_idx]
                last_local_end = end_off - last_r_start
                last_orig = last_run.text or ""
                last_suffix = last_orig[last_local_end:]

                # First affected run gets prefix + replacement + last run suffix
                first_run.text = first_orig[:first_local_start] + replacement + last_suffix

                # Clear text in intermediate and last runs (clears text node while preserving XML attributes/styles)
                for mid_idx in affected_indices[1:]:
                    xml_runs[mid_idx].text = ""

                applied_count += 1

        return applied_count
