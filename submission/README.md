# PII Redaction Tool

A production-quality system for detecting and redacting Personally Identifiable Information (PII) from Microsoft Word (.docx) documents. Built for the Scaler AI Labs assessment.

---

## Problem Statement

Financial and legal documents such as Red Herring Prospectuses contain PII — full names, addresses, phone numbers, email addresses, and organization names — that must be removed or replaced before sharing. This tool reads a DOCX, detects PII across all content regions (body, tables, headers, footers, hyperlinks), and replaces each detected entity with a realistic but completely synthetic alternative, preserving the document's structure and readability.

---

## Supported PII Categories

| Category | Examples |
|---|---|
| PERSON | Full names of directors, promoters, individuals |
| EMAIL_ADDRESS | Any valid email address |
| PHONE_NUMBER | Indian (+91) and international formats |
| ORGANIZATION | Company and institution names |
| ADDRESS | Physical / mailing addresses |
| SSN | US Social Security Numbers |
| CREDIT_CARD | Luhn-valid credit card numbers |
| DATE_OF_BIRTH | Dates identified contextually as DOB |
| IP_ADDRESS | IPv4 and IPv6 addresses |

---

## Architecture

```
DOCX Upload (multipart/form-data)
        ↓
DOCXParser — extracts paragraphs, tables, headers, footers, hyperlinks
        ↓
PIIDetector — multilayer detection:
  Layer 1: RegexRecognizer (Email, Phone, SSN, CC, IP)
  Layer 2: ContextRulesRecognizer (DOB, Address)
  Layer 3: spaCy NER (Person, Organization, Location)
  SpanResolver — deduplicates and resolves overlapping spans
        ↓
EntityMapper — deterministic seeded mapping:
  SHA-256(original_text + category) → seed → Faker → synthetic replacement
  Collision-safe: guaranteed-unique via registry-index fallback
        ↓
DOCXRedactor — in-place XML run rewriting:
  Body paragraphs, table cells, headers, footers, hyperlink targets
        ↓
DocumentValidator — post-redaction security:
  Structural DOCX validity check
  Residual PII scan (extracted text vs. original PII dict)
  SHA-256 integrity check on original input file
        ↓
Download Token → Redacted DOCX
```

---

## Detection Approach

- **Regex**: High-precision patterns for structured PII (email, phone, SSN, credit card, IP). Luhn validation for credit cards. Phone validated via `phonenumbers` library.
- **Contextual NLP**: Heuristic keyword context rules for detecting Date of Birth (distinguishes from document/publication dates) and Address blocks.
- **spaCy NER** (`en_core_web_sm`): Detects PERSON, ORGANIZATION, and LOCATION entities with contextual sentence understanding.
- **Span Resolver**: Bipartite overlap resolution — higher-confidence detections win over lower-confidence ones when spans conflict.

---

## Replacement (Anonymization) Strategy

Each unique original PII string is mapped to a synthetic replacement using:

1. **SHA-256 seed**: `SHA256(normalized_text + ":" + category)` → deterministic integer seed
2. **Seeded Faker**: `Faker.seed_instance(seed)` → generates category-appropriate synthetic value
3. **Consistency**: The same original entity always maps to the same replacement within a document run
4. **Collision safety**: If two different originals generate the same replacement, a guaranteed-unique registry-index suffix is appended

### Safe replacement domains
- Emails: `@example.com`, `@example.org`, `@example.test`
- IP addresses: RFC 5737 documentation ranges (`192.0.2.x`, `198.51.100.x`, `203.0.113.x`)
- SSNs: Valid format with safe test values (area 100-899, excluding 666)

---

## DOCX Coverage

The redaction engine processes:
- ✅ Body paragraphs
- ✅ Table cells (all rows, all columns, nested tables)
- ✅ Document headers (default, first-page, even-page)
- ✅ Document footers (default, first-page, even-page)
- ✅ Hyperlink relationship targets (mailto: URLs)
- ✅ Text split across multiple XML runs (reconstructed before detection)

---

## Validation Approach

After generating the redacted DOCX:
1. Reopen the output file with python-docx to confirm structural validity
2. Extract all text from the output
3. Compare against every detected original PII string (normalized: strip whitespace, lowercase)
4. Raise an error if any original PII is found in the output
5. Recompute SHA-256 of the original input to confirm it was never modified

---

## Privacy & Security

- No original PII is ever returned in API responses (aggregate counts only)
- No raw PII is logged (logger outputs category counts only)
- Download tokens expire after 10 minutes (configurable via `DOWNLOAD_TTL_SECONDS`)
- Input files are stored in temporary files and immediately deleted after processing
- Source-to-replacement mapping is never exposed through the public API

---

## Evaluation Methodology

### Controlled Test Dataset
**Source**: `tests/fixtures/pii_redaction_test.docx` — 35 independently annotated entities across all 9 categories.

Evaluation uses exact span matching with Jaccard boundary threshold ≥ 0.5:
- **TP**: Detected entity overlaps with a ground-truth entity of the same category
- **FP**: Detected entity has no matching ground-truth entity
- **FN**: Ground-truth entity has no matching detection

### Metrics (Controlled Dataset)

| Metric | Value |
|---|---|
| Precision | **94.3%** |
| Recall | **94.3%** |
| F1 Score | **94.3%** |
| Macro F1 | 92.1% |

### Why Accuracy is Not Reported

Accuracy requires True Negatives (TN), but TN for span extraction = all character spans in the document that are not PII — an unbounded, unenumerable set. Accuracy is mathematically undefined for NER tasks. Precision, Recall, and F1 are the correct metrics.

### User-Uploaded Documents (No Ground Truth)

For documents without independently annotated ground truth (including the Red Herring Prospectus), the system correctly reports:
- Detection counts per category ✅
- Replacement counts ✅
- Residual PII validation ✅
- Precision/Recall/F1: **N/A** (no fabricated numbers)

---

## Red Herring Prospectus Results

| Metric | Value |
|---|---|
| Total PII Detected | **3,545** |
| Unique Entities | **901** |
| Replacements Applied | 3,514 text + 79 hyperlinks |
| DOCX Valid | ✅ |
| Residual PII | ✅ 0 original strings leaked |
| Original File Unchanged | ✅ SHA-256 verified |

**Detections by category**: PERSON 760, EMAIL 70, PHONE 49, ORGANIZATION 2562, ADDRESS 104

---

## Known Tradeoffs & Limitations

**False Positives** (precision risk):
- ORGANIZATION is broad — some capitalised legal/generic terms may be flagged
- SEBI, BSE, NSE, and standard regulatory terms are explicitly excluded
- PERSON may occasionally flag capitalised heading words without name context

**False Negatives** (recall risk):
- Person names split across unusual XML run boundaries may be missed
- Single-occurrence names without honorific or surrounding context
- Non-standard phone formats (e.g., missing country code, unusual separator)

---

## How to Run Locally

```bash
git clone https://github.com/Gurfiyaz/Scaler-AI.git
cd Scaler-AI
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python run.py
# Open: http://localhost:8000
```

## How to Run Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -q
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/info` | Service information |
| POST | `/api/process` | Upload and process DOCX |
| GET | `/api/download/{id}` | Download redacted DOCX |

## Deployment

Deployed on Render as a Web Service:
- **Build**: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`
- **Start**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health**: `GET /health`

See `render.yaml` and `Procfile` for full configuration.
