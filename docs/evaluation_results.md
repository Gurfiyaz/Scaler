# PII Redaction & Evaluation Methodology Report

## 1. Executive Overview

This document defines the scientific evaluation methodology and metrics computation for the Enterprise PII Redaction Tool. Processing is 100% local, ephemeral, and privacy-preserving.

Evaluation is performed using deterministic **1-to-1 exact span matching** against independently annotated ground-truth datasets. No detector predictions are ever used to generate ground truth, ensuring unbiased evaluation.

---

## 2. Evaluation Datasets

| Dataset | Scope | Ground Truth Status | Purpose |
|---|---|---|---|
| `pii_redaction_test.docx` | Controlled Evaluation Dataset | `tests/fixtures/pii_redaction_test_ground_truth.json` | Independent benchmark evaluation across all 9 PII categories. |
| `Enterprise Data - Assignment.docx` | Assignment Benchmark | `private_data/ground_truth.json` | Verification suite dataset. |
| `Red Herring Prospectus.docx` | Real-world Document | N/A — Not independently annotated | Operational redaction mode. Ground truth unavailable; evaluation metrics reported as N/A. |
| User-Uploaded Documents | Arbitrary DOCX files | N/A — Ground truth unavailable | Ephemeral operational sanitization. Precision/Recall/F1 reported as N/A. |

---

## 3. Ground-Truth Creation Methodology

Ground truth is created entirely independently from the PII Detection Engine:

1. **Independent Manual Annotation**: Human annotators read raw document text and identify ground-truth spans.
2. **Annotation Attributes**:
   - `entity_type`: Canonical category (`PERSON`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `ORGANIZATION`, `ADDRESS`, `SSN`, `CREDIT_CARD`, `DATE_OF_BIRTH`, `IP_ADDRESS`).
   - `paragraph_index`: 0-indexed reconstructed body paragraph position.
   - `start`: Inclusive character offset in paragraph reconstructed text.
   - `end`: Exclusive character offset in paragraph reconstructed text.
3. **No Raw PII Storage**: SHA-256 hashes of original text spans are retained for verification without raw text exposure.

---

## 4. Exact Span Matching & Metric Definitions

Evaluation uses bipartite 1-to-1 exact span matching per category.

### Matching Rules
A predicted span $\hat{s} = (p, \text{start}, \text{end}, c)$ matches a ground-truth span $g = (p', \text{start}', \text{end}', c')$ if and only if:
1. Paragraph index matches: $p = p'$
2. Character start boundary matches: $\text{start} = \text{start}'$
3. Character end boundary matches: $\text{end} = \text{end}'$
4. PII entity category matches: $c = c'$
5. **1-to-1 Constraint**: Each ground-truth span $g$ can be matched to at most one prediction $\hat{s}$. Duplicate or overlapping extra predictions are classified as False Positives (FP).

### Metric Formulas

$$\text{Precision} = \frac{TP}{TP + FP}$$

$$\text{Recall} = \frac{TP}{TP + FN}$$

$$F_1 = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

$$\text{Exact Span Match Ratio} = \frac{TP}{TP + FP + FN}$$

- **Division-by-zero handling**: When $TP + FP = 0$ or $TP + FN = 0$, precision or recall is defined as $0.0$ (or displayed as $N/A$ if no instances exist in ground truth nor predictions).

---

## 5. Micro vs Macro Averaging

- **Micro Metrics**: Aggregated across all categories simultaneously:
  $$\text{Micro Precision} = \frac{\sum TP_c}{\sum (TP_c + FP_c)}, \quad \text{Micro Recall} = \frac{\sum TP_c}{\sum (TP_c + FN_c)}$$
- **Macro Metrics**: Unweighted arithmetic mean across categories present in Ground Truth or Predictions:
  $$\text{Macro Precision} = \frac{1}{|C_{\text{active}}|} \sum_{c \in C_{\text{active}}} \text{Precision}_c$$

---

## 6. Why Accuracy is Reported as N/A

In sparse PII span extraction over free text:
1. The universe of negative (non-PII) character spans is infinite / un-enumerated.
2. True Negatives ($TN$) cannot be legitimately counted without defining an arbitrary candidate generator.
3. Inventing an arbitrary $TN$ count would artificially inflate Accuracy to $>99\%$, creating a false sense of security.

Therefore:
> **Accuracy is explicitly reported as N/A** with the explanation:
> *"Conventional accuracy is not defined because the evaluator does not enumerate a finite true-negative population for sparse span extraction."*

Primary reliance is placed on **Micro/Macro F1** and **Exact Span Match Ratio**.

---

## 7. Results on Controlled Dataset (`pii_redaction_test.docx`)

### Summary Metrics
- **Total Ground Truth Entities**: 29
- **Total Predicted Entities**: 36
- **True Positives (TP)**: 25
- **False Positives (FP)**: 11
- **False Negatives (FN)**: 4
- **Micro Precision**: 69.44%
- **Micro Recall**: 86.21%
- **Micro F1**: 76.92%
- **Macro Precision**: 81.39%
- **Macro Recall**: 85.18%
- **Macro F1**: 81.77%
- **Exact Span Match Ratio**: 62.50%
- **Accuracy**: N/A

### Per-Category Breakdown

| Category | Ground Truth | Predicted | TP | FP | FN | Precision | Recall | F1 | Exact Span Match |
|---|---|---|---|---|---|---|---|---|---|
| **PERSON** | 3 | 5 | 1 | 4 | 2 | 20.00% | 33.33% | 25.00% | 14.29% |
| **EMAIL_ADDRESS** | 3 | 3 | 3 | 0 | 0 | 100.00% | 100.00% | 100.00% | 100.00% |
| **PHONE_NUMBER** | 3 | 3 | 3 | 0 | 0 | 100.00% | 100.00% | 100.00% | 100.00% |
| **ORGANIZATION** | 2 | 8 | 1 | 7 | 1 | 12.50% | 50.00% | 20.00% | 10.00% |
| **ADDRESS** | 6 | 5 | 5 | 0 | 1 | 100.00% | 83.33% | 90.91% | 83.33% |
| **SSN** | 3 | 3 | 3 | 0 | 0 | 100.00% | 100.00% | 100.00% | 100.00% |
| **CREDIT_CARD** | 3 | 3 | 3 | 0 | 0 | 100.00% | 100.00% | 100.00% | 100.00% |
| **DATE_OF_BIRTH** | 3 | 3 | 3 | 0 | 0 | 100.00% | 100.00% | 100.00% | 100.00% |
| **IP_ADDRESS** | 3 | 3 | 3 | 0 | 0 | 100.00% | 100.00% | 100.00% | 100.00% |

---

## 8. Error & False Positive Analysis

### Organization False Positives (7 FPs)
spaCy NER tagged generic document labels as `ORG`:
- `"DATASET"` (P00, P111)
- `"Login IP Address"` (P64)
- `"IP Address"` (P86)
- `"Credit Card"` (P90)
- `"NON-PII TEST DATA"` (P94)
- `"Project Name"` (P106)

### Person False Positives & False Negatives (4 FPs, 2 FNs)
- FPs: `"PII REDACTION"` (P00 header), `"Email"` (P08, P12, P74 labels tagged as PERSON by spaCy).
- FNs: `"Priya Sharma"` (P11), `"Arjun Kapoor"` (P73) missed due to paragraph format variations in spaCy NER.

### Non-PII Isolation Verification
The following non-PII test patterns were **NOT** falsely flagged as PII:
- Order Number (`ORD-2026-10482`)
- Ticket Number (`TKT-483920`)
- Invoice Number (`INV-2026-7712`)
- Product Code (`PROD-AX-204`)
- Company Revenue (`₹12,500,000`)
- Document Date (`14 August 2026`)
- Page Number (`42`)
- Department (`Engineering`)
