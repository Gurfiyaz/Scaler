"""Unit test suite for Independent PII Evaluation Engine."""

from pathlib import Path
import pytest
from app.detection.models import PIIDetection, PIIType
from app.evaluation.evaluator import Evaluator
from app.evaluation.ground_truth import GroundTruthManager
from app.evaluation.models import GroundTruthAnnotation, GroundTruthDocument

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def evaluator():
    return Evaluator()


# 1. Exact Match TP, FP, FN Test
def test_exact_match_tp_fp_fn(evaluator):
    gt = GroundTruthDocument(
        document_id="test_doc",
        annotations=[
            GroundTruthAnnotation(entity_type=PIIType.PERSON, start=0, end=10, paragraph_index=0),
            GroundTruthAnnotation(entity_type=PIIType.EMAIL_ADDRESS, start=15, end=30, paragraph_index=0),
        ],
    )

    # 1 matching PERSON (TP), 1 extra PERSON (FP), 1 missing EMAIL (FN)
    preds = [
        PIIDetection(entity_type=PIIType.PERSON, start=0, end=10, text="Alice Smith", recognizer="test", confidence=1.0, paragraph_index=0),
        PIIDetection(entity_type=PIIType.PERSON, start=40, end=50, text="Extra Person", recognizer="test", confidence=1.0, paragraph_index=0),
    ]

    report = evaluator.evaluate(gt, preds)

    assert report.total_ground_truth == 2
    assert report.total_predictions == 2
    assert report.total_tp == 1
    assert report.total_fp == 1
    assert report.total_fn == 1

    person_m = report.per_category[PIIType.PERSON]
    assert person_m.tp == 1
    assert person_m.fp == 1
    assert person_m.fn == 0
    assert person_m.precision == 0.5
    assert person_m.recall == 1.0
    assert person_m.f1 == pytest.approx(0.6667, abs=1e-3)

    email_m = report.per_category[PIIType.EMAIL_ADDRESS]
    assert email_m.tp == 0
    assert email_m.fp == 0
    assert email_m.fn == 1
    assert email_m.precision == 0.0
    assert email_m.recall == 0.0


# 2. Wrong Entity Type Handling Test (Counts as 1 FP + 1 FN)
def test_wrong_entity_type(evaluator):
    gt = GroundTruthDocument(
        document_id="test_doc",
        annotations=[
            GroundTruthAnnotation(entity_type=PIIType.PERSON, start=0, end=10, paragraph_index=0),
        ],
    )

    # Predicted same span as ORGANIZATION instead of PERSON
    preds = [
        PIIDetection(entity_type=PIIType.ORGANIZATION, start=0, end=10, text="Acme Corp", recognizer="test", confidence=1.0, paragraph_index=0),
    ]

    report = evaluator.evaluate(gt, preds)

    assert report.total_tp == 0
    assert report.total_fp == 1
    assert report.total_fn == 1
    assert report.micro_precision == 0.0
    assert report.micro_recall == 0.0
    assert len(report.error_analysis["entity_type_mismatches"]) == 1


# 3. Partial Span / Boundary Mismatch Test
def test_partial_span_boundary_mismatch(evaluator):
    gt = GroundTruthDocument(
        document_id="test_doc",
        annotations=[
            GroundTruthAnnotation(entity_type=PIIType.PERSON, start=0, end=15, paragraph_index=0),
        ],
    )

    # Predicted partial span [0, 10) instead of [0, 15)
    preds = [
        PIIDetection(entity_type=PIIType.PERSON, start=0, end=10, text="Alice", recognizer="test", confidence=1.0, paragraph_index=0),
    ]

    report = evaluator.evaluate(gt, preds)

    assert report.total_tp == 0
    assert report.total_fp == 1
    assert report.total_fn == 1
    assert len(report.error_analysis["boundary_mismatches"]) == 1


# 4. Duplicate Prediction Handling Test (1-to-1 Bipartite Matching)
def test_duplicate_predictions_one_to_one(evaluator):
    gt = GroundTruthDocument(
        document_id="test_doc",
        annotations=[
            GroundTruthAnnotation(entity_type=PIIType.PERSON, start=0, end=10, paragraph_index=0),
        ],
    )

    # 2 duplicate predictions for the exact same span
    preds = [
        PIIDetection(entity_type=PIIType.PERSON, start=0, end=10, text="Alice Smith", recognizer="rec1", confidence=0.9, paragraph_index=0),
        PIIDetection(entity_type=PIIType.PERSON, start=0, end=10, text="Alice Smith", recognizer="rec2", confidence=0.8, paragraph_index=0),
    ]

    report = evaluator.evaluate(gt, preds)

    assert report.total_tp == 1
    assert report.total_fp == 1  # 2nd duplicate counted as FP
    assert report.total_fn == 0
    assert report.micro_precision == 0.5
    assert report.micro_recall == 1.0


# 5. Empty Ground Truth / Empty Predictions Test
def test_empty_ground_truth_and_predictions(evaluator):
    gt = GroundTruthDocument(document_id="empty_doc", annotations=[])
    preds = []

    report = evaluator.evaluate(gt, preds)

    assert report.total_ground_truth == 0
    assert report.total_predictions == 0
    assert report.total_tp == 0
    assert report.total_fp == 0
    assert report.total_fn == 0
    assert report.micro_precision == 0.0
    assert report.micro_recall == 0.0
    assert report.overall_exact_match_ratio == 0.0


# 6. Zero Denominator Notes Test
def test_zero_denominator_absent_category_notes(evaluator):
    gt = GroundTruthDocument(
        document_id="test_doc",
        annotations=[
            GroundTruthAnnotation(entity_type=PIIType.PERSON, start=0, end=10, paragraph_index=0),
        ],
    )
    preds = [
        PIIDetection(entity_type=PIIType.PERSON, start=0, end=10, text="Alice Smith", recognizer="test", confidence=1.0, paragraph_index=0),
    ]

    report = evaluator.evaluate(gt, preds)

    ssn_m = report.per_category[PIIType.SSN]
    assert ssn_m.ground_truth_count == 0
    assert ssn_m.predicted_count == 0
    assert ssn_m.notes == "Not present in evaluation document."


# 7. Exact Span Match Ratio (Jaccard-Style) Test
def test_exact_span_match_ratio_jaccard(evaluator):
    gt = GroundTruthDocument(
        document_id="test_doc",
        annotations=[
            GroundTruthAnnotation(entity_type=PIIType.PERSON, start=0, end=10, paragraph_index=0),
            GroundTruthAnnotation(entity_type=PIIType.PERSON, start=20, end=30, paragraph_index=0),
        ],
    )

    # 1 TP, 1 FP (extra pred), 1 FN (missing GT) -> Jaccard = TP / (TP + FP + FN) = 1 / (1 + 1 + 1) = 0.3333
    preds = [
        PIIDetection(entity_type=PIIType.PERSON, start=0, end=10, text="Alice Smith", recognizer="test", confidence=1.0, paragraph_index=0),
        PIIDetection(entity_type=PIIType.PERSON, start=40, end=50, text="Extra Person", recognizer="test", confidence=1.0, paragraph_index=0),
    ]

    report = evaluator.evaluate(gt, preds)

    person_m = report.per_category[PIIType.PERSON]
    assert person_m.exact_match_ratio == pytest.approx(0.3333, abs=1e-3)
    assert report.overall_exact_match_ratio == pytest.approx(0.3333, abs=1e-3)


# 8. Synthetic Known Metric Results Test
def test_synthetic_fixture_evaluation(evaluator):
    synth_gt_path = FIXTURES_DIR / "synthetic_ground_truth.json"
    gt = GroundTruthManager.load_from_file(synth_gt_path)

    # Create predictions matching all 9 synthetic ground truth annotations exactly
    preds = []
    for ann in gt.annotations:
        preds.append(
            PIIDetection(
                entity_type=ann.entity_type,
                start=ann.start,
                end=ann.end,
                text="synthetic_text",
                recognizer="synth_test",
                confidence=1.0,
                paragraph_index=ann.paragraph_index,
            )
        )

    report = evaluator.evaluate(gt, preds)

    assert report.total_ground_truth == 9
    assert report.total_predictions == 9
    assert report.total_tp == 9
    assert report.total_fp == 0
    assert report.total_fn == 0
    assert report.micro_precision == 1.0
    assert report.micro_recall == 1.0
    assert report.micro_f1 == 1.0
    assert report.overall_exact_match_ratio == 1.0
