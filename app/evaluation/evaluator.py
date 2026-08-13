"""Independent PII Evaluation Engine with Exact Span & 1-to-1 Matching."""

from typing import Dict, List, Set, Tuple
from app.detection.models import PIIDetection, PIIType
from app.evaluation.models import CategoryMetrics, EvaluationReport, GroundTruthAnnotation, GroundTruthDocument


class Evaluator:
    """Evaluates PII detector predictions against independent ground truth annotations."""

    def evaluate(
        self,
        ground_truth: GroundTruthDocument,
        predictions: List[PIIDetection],
    ) -> EvaluationReport:
        """Perform deterministic 1-to-1 exact span matching evaluation."""
        all_categories = list(PIIType)

        # Organize GT and Predictions by category
        gt_by_cat: Dict[PIIType, List[GroundTruthAnnotation]] = {c: [] for c in all_categories}
        for gt in ground_truth.annotations:
            gt_by_cat[gt.entity_type].append(gt)

        pred_by_cat: Dict[PIIType, List[PIIDetection]] = {c: [] for c in all_categories}
        for pred in predictions:
            pred_by_cat[pred.entity_type].append(pred)

        per_cat_metrics: Dict[PIIType, CategoryMetrics] = {}
        error_analysis: Dict[str, List[Dict[str, str]]] = {
            "false_positives": [],
            "false_negatives": [],
            "entity_type_mismatches": [],
            "boundary_mismatches": [],
        }

        total_tp = 0
        total_fp = 0
        total_fn = 0

        # Evaluate each PII category independently
        for cat in all_categories:
            gts = gt_by_cat[cat]
            preds = pred_by_cat[cat]

            tp, fp, fn, matched_gt_ids, matched_pred_indices = self._evaluate_category_exact(gts, preds)

            p = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
            r = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
            f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0
            em_ratio = (tp / (tp + fp + fn)) if (tp + fp + fn) > 0 else 0.0

            notes = ""
            if len(gts) == 0 and len(preds) == 0:
                notes = "Not present in evaluation document."

            per_cat_metrics[cat] = CategoryMetrics(
                category=cat,
                ground_truth_count=len(gts),
                predicted_count=len(preds),
                tp=tp,
                fp=fp,
                fn=fn,
                precision=round(p, 4),
                recall=round(r, 4),
                f1=round(f1, 4),
                exact_match_ratio=round(em_ratio, 4),
                notes=notes,
            )

            total_tp += tp
            total_fp += fp
            total_fn += fn

        # Error Analysis Classification across entire document
        self._analyze_errors(ground_truth.annotations, predictions, error_analysis)

        # Micro-Averaged Metrics across all categories
        micro_p = (total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else 0.0
        micro_r = (total_tp / (total_tp + total_fn)) if (total_tp + total_fn) > 0 else 0.0
        micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)) if (micro_p + micro_r) > 0 else 0.0
        overall_em_ratio = (
            (total_tp / (total_tp + total_fp + total_fn))
            if (total_tp + total_fp + total_fn) > 0
            else 0.0
        )

        # Macro-Averaged Metrics across categories present in GT or Predictions
        active_cats = [
            m for m in per_cat_metrics.values() if m.ground_truth_count > 0 or m.predicted_count > 0
        ]
        if active_cats:
            macro_p = sum(m.precision for m in active_cats) / len(active_cats)
            macro_r = sum(m.recall for m in active_cats) / len(active_cats)
            macro_f1 = sum(m.f1 for m in active_cats) / len(active_cats)
        else:
            macro_p, macro_r, macro_f1 = 0.0, 0.0, 0.0

        return EvaluationReport(
            document_id=ground_truth.document_id,
            per_category=per_cat_metrics,
            total_ground_truth=len(ground_truth.annotations),
            total_predictions=len(predictions),
            total_tp=total_tp,
            total_fp=total_fp,
            total_fn=total_fn,
            micro_precision=round(micro_p, 4),
            micro_recall=round(micro_r, 4),
            micro_f1=round(micro_f1, 4),
            macro_precision=round(macro_p, 4),
            macro_recall=round(macro_r, 4),
            macro_f1=round(macro_f1, 4),
            overall_exact_match_ratio=round(overall_em_ratio, 4),
            error_analysis=error_analysis,
        )

    def _evaluate_category_exact(
        self,
        gts: List[GroundTruthAnnotation],
        preds: List[PIIDetection],
    ) -> Tuple[int, int, int, Set[int], Set[int]]:
        """Exact span + 1-to-1 deterministic matching for a single category."""
        matched_gt_indices: Set[int] = set()
        matched_pred_indices: Set[int] = set()

        tp = 0
        # Deterministic 1-to-1 matching
        for p_idx, pred in enumerate(preds):
            for g_idx, gt in enumerate(gts):
                if g_idx in matched_gt_indices:
                    continue
                if (
                    pred.paragraph_index == gt.paragraph_index
                    and pred.start == gt.start
                    and pred.end == gt.end
                    and pred.entity_type == gt.entity_type
                ):
                    tp += 1
                    matched_gt_indices.add(g_idx)
                    matched_pred_indices.add(p_idx)
                    break

        fp = len(preds) - len(matched_pred_indices)
        fn = len(gts) - len(matched_gt_indices)

        return tp, fp, fn, matched_gt_indices, matched_pred_indices

    def _analyze_errors(
        self,
        all_gts: List[GroundTruthAnnotation],
        all_preds: List[PIIDetection],
        error_analysis: Dict[str, List[Dict[str, str]]],
    ) -> None:
        """Categorize false positive and false negative failure modes without exposing raw PII."""
        # Find unmatched GTs and Preds
        unmatched_gts = []
        unmatched_preds = list(all_preds)

        for gt in all_gts:
            match_found = False
            for p_idx, pred in enumerate(unmatched_preds):
                if (
                    pred.paragraph_index == gt.paragraph_index
                    and pred.start == gt.start
                    and pred.end == gt.end
                    and pred.entity_type == gt.entity_type
                ):
                    match_found = True
                    unmatched_preds.pop(p_idx)
                    break
            if not match_found:
                unmatched_gts.append(gt)

        # Check for boundary or entity_type mismatches among unmatched items
        for gt in unmatched_gts:
            mismatched = False
            for pred in list(unmatched_preds):
                if pred.paragraph_index == gt.paragraph_index:
                    # Check character overlap
                    overlap = max(0, min(pred.end, gt.end) - max(pred.start, gt.start))
                    if overlap > 0:
                        if pred.entity_type != gt.entity_type:
                            error_analysis["entity_type_mismatches"].append({
                                "paragraph": f"P{gt.paragraph_index}",
                                "gt_category": gt.entity_type.value,
                                "pred_category": pred.entity_type.value,
                                "reason": "Predicted entity type does not match ground truth.",
                            })
                        else:
                            error_analysis["boundary_mismatches"].append({
                                "paragraph": f"P{gt.paragraph_index}",
                                "category": gt.entity_type.value,
                                "gt_span": f"[{gt.start}:{gt.end}]",
                                "pred_span": f"[{pred.start}:{pred.end}]",
                                "reason": "Predicted character boundaries partially overlap ground truth.",
                            })
                        mismatched = True
                        break
            if not mismatched:
                error_analysis["false_negatives"].append({
                    "paragraph": f"P{gt.paragraph_index}",
                    "category": gt.entity_type.value,
                    "reason": "Ground-truth entity missed by detector.",
                })

        for pred in unmatched_preds:
            # Check if already recorded in type/boundary mismatch
            already_recorded = False
            for m in error_analysis["entity_type_mismatches"] + error_analysis["boundary_mismatches"]:
                if m["paragraph"] == f"P{pred.paragraph_index}":
                    already_recorded = True
                    break
            if not already_recorded:
                error_analysis["false_positives"].append({
                    "paragraph": f"P{pred.paragraph_index}",
                    "category": pred.entity_type.value,
                    "reason": "Detector predicted entity not present in ground truth.",
                })
