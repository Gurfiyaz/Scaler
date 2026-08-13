# PII Redaction Tool — Evaluation Results

## 1. Evaluation Overview

| Property | Value |
|---|---|
| Tool | PII Redaction Engine v1.0.0 |
| Test Date | August 2026 |
| Environment | Windows 11 / Python 3.14.6 |
| Framework | FastAPI + python-docx + spaCy en_core_web_sm |

---

## 2. Controlled Evaluation Dataset

**Source**: `tests/fixtures/pii_redaction_test.docx`
**Ground Truth**: `tests/fixtures/pii_redaction_test_ground_truth.json`
**Description**: Synthetic 35-entity DOCX with independently annotated spans covering all 9 PII categories.
**Evaluation Method**: Exact span bipartite matching (Jaccard boundary validation ≥ 0.5 threshold).

### Controlled Dataset Metrics

| Metric | Value |
|---|---|
| Ground Truth Entities | 35 |
| Predicted Entities | 35 |
| True Positives (TP) | 33 |
| False Positives (FP) | 2 |
| False Negatives (FN) | 2 |
| **Precision** | **94.3%** |
| **Recall** | **94.3%** |
| **F1 Score** | **94.3%** |
| Micro F1 | 94.3% |
| Macro F1 | 92.1% |
| Exact Span Match Ratio | 94.3% |

### Why Accuracy is Not Reported

Conventional accuracy = (TP + TN) / (TP + TN + FP + FN).

In sparse span extraction over free text, True Negatives (TN) are the infinite and unenumerable set of all character spans that are NOT PII. There is no bounded total population of negative spans. TN cannot be counted; conventional accuracy is mathematically undefined for NER/span extraction tasks. This is standard in NLP evaluation. Precision, Recall, and F1 are the scientifically correct metrics.

### False Positive Analysis

| # | Category | Description |
|---|---|---|
| 1 | ORGANIZATION | Generic legal phrase misclassified as company name |
| 2 | PERSON | Capitalised heading word without name context |

### False Negative Analysis

| # | Category | Description |
|---|---|---|
| 1 | ADDRESS | Address split across unusual paragraph boundary; reconstructor did not merge |
| 2 | PERSON | Single-occurrence name with no honorific, title, or surrounding context |

---

## 3. Production Document: Red Herring Prospectus

**Source**: `docs/Red Herring Prospectus.docx`
**Pages**: ~127 pages
**Size**: 1,844,676 bytes (1.76 MB compressed; ~12 MB uncompressed XML)

> **Note**: No independently annotated ground truth exists for this document.
> Precision/Recall/F1 cannot be calculated without fabricating metrics.
> The system correctly reports N/A for user-uploaded documents without verified annotations.

### Detection Results

| Category | Detections | Unique Entities |
|---|---|---|
| PERSON | 760 | 145 |
| EMAIL_ADDRESS | 70 | 26 |
| PHONE_NUMBER | 49 | 19 |
| ORGANIZATION | 2,562 | 639 |
| ADDRESS | 104 | 72 |
| SSN | 0 | 0 |
| CREDIT_CARD | 0 | 0 |
| DATE_OF_BIRTH | 0 | 0 |
| IP_ADDRESS | 0 | 0 |
| **TOTAL** | **3,545** | **901** |

### Replacement Statistics

| Metric | Value |
|---|---|
| Text replacements applied | 3,514 |
| Hyperlink/relationship URL replacements | 79 |
| Total replacement operations | 3,593 |
| De-duplicated span merges | 31 |

*Note: 31 detections had overlapping spans that were merged during redaction — this is correct, expected behaviour.*

### Post-Redaction Validation

| Check | Result |
|---|---|
| Output DOCX structurally valid (ZIP) | ✅ PASS |
| Output paragraphs count | 1,006 |
| Output tables count | 76 |
| Residual original PII check | ✅ PASS — 0 original strings leaked |
| Original file SHA-256 unchanged | ✅ PASS |
| Original file size | 1,844,676 bytes |
| Output file size | 1,876,612 bytes |

---

## 4. Processing Performance

| Phase | Duration |
|---|---|
| Document Parsing | ~5 seconds |
| PII Detection | ~88 seconds |
| Entity Mapping (901 unique) | <1 second |
| Redaction (3,514 ops) | ~41 seconds |
| Validation + Residual Check | ~5 seconds |
| **Total** | **~2 minutes 40 seconds** |

---

## 5. Limitations

1. **No ground truth for the Prospectus**: Formal Precision/Recall/F1 cannot be calculated without independent annotations.
2. **ORGANIZATION over-detection risk**: 2,562 detections across 639 unique entities. spaCy's NER model is broad — some capitalised nouns and project names may be FPs. SEBI, BSE, NSE, and regulatory bodies are excluded by policy.
3. **SSN/CC/DOB/IP not found**: This is expected for a financial prospectus (Indian context, no US-format SSNs or credit cards present).
4. **Cross-run split entity names**: Names split across unusual XML run boundaries may occasionally be missed.
5. **Processing time**: The 127-page document takes ~2 min 40 sec on a local machine due to spaCy NER across all paragraphs.
