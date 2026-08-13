# PII Redaction Tool - Final Submission

## Problem Statement
The assignment required building a comprehensive, privacy-preserving DOCX PII detection and redaction system. The system must process an uploaded DOCX, intelligently identify 9 canonical categories of Personally Identifiable Information (PII), dynamically map them to realistic synthetic alternatives, and replace them in-place directly inside the DOCX XML structure. Critically, the output must remain a valid DOCX file, the exact structural formatting must be preserved, and the system must ensure zero leakage of original PII strings.

## Approach
The architecture is built on a multilayer detection and redaction pipeline:
1. **Ingestion & Parsing**: Extracts paragraphs, tables, headers, footers, and hyperlinks from the DOCX using `python-docx`, reconstructing document runs to handle PII split across XML boundaries.
2. **Multilayer Detection**: Combines highly optimized regex models, checksum validations (e.g., Luhn algorithm for Credit Cards), and Contextual NLP via spaCy to reliably identify entities.
3. **Deterministic Mapping**: Maintains an ephemeral memory of all detected PII during the session. It deterministically assigns a safe, synthetic replacement to each unique PII string using seeded generation (`Faker`). This guarantees that "John Doe" is mapped to the same synthetic name (e.g., "Daniel Mercer") consistently across all 127 pages of a document.
4. **In-Place Redaction**: Modifies the underlying DOCX XML runs (`<w:t>`) to replace the text without corrupting the surrounding formatting, bolding, italics, or table structures.
5. **Post-Redaction Validation**: A strict security layer that extracts the raw text from the final generated DOCX and scans it against the original PII mapping to guarantee that 0 original strings leaked into the final output.

## PII Categories Supported
1. **PERSON**: Full names (via spaCy NER and custom heuristics).
2. **EMAIL_ADDRESS**: All standard email formats.
3. **PHONE_NUMBER**: International and Indian format phone numbers.
4. **ORGANIZATION**: Company names, avoiding generic regulatory terms (SEBI, BSE, etc.).
5. **ADDRESS**: Physical mailing addresses and locations.
6. **SSN**: Strict US Social Security Numbers.
7. **CREDIT_CARD**: Luhn-validated credit card numbers.
8. **DATE_OF_BIRTH**: Differentiated from generic document/publication dates.
9. **IP_ADDRESS**: IPv4 and IPv6 addresses.

## Synthetic Replacement Strategy & Consistency
The `EntityMapper` uses a seeded pseudo-random number generator (PRNG) tied to a hash of the original PII string. When a PERSON like "Sarthak Malvadkar" is encountered, it is hashed to a deterministic seed, which `Faker` uses to generate a consistent synthetic name like "Daniel Mercer". This guarantees that every occurrence of the same original entity receives the exact same replacement, preserving semantic coherence without leaking identity.

## DOCX Coverage
The parser deeply traverses the document structure, ensuring coverage of:
- Body paragraphs
- Nested table cells
- Headers and footers
- Hyperlink relationship targets (e.g., mailto: links)

## Validation Approach
After generating the redacted DOCX, the `DOCXRedactor` automatically extracts the plain text from the new file and performs a rigorous substring and normalized comparison against the known source PII dictionary. If any original PII is found, the system fails the validation.

## Evaluation Methodology
The evaluation subsystem calculates True Positives (TP), False Positives (FP), and False Negatives (FN) using an exact-span matching algorithm (Jaccard boundary validation). Precision, Recall, and F1-scores are derived dynamically.

**Note on the Red Herring Prospectus:**
Because the Red Herring Prospectus is a 127-page real-world document without an independently annotated ground truth dataset, formal Precision, Recall, and F1 scores cannot be mathematically calculated without fabricating metrics (which the system strictly forbids). Our evaluation framework detects the absence of ground truth and correctly marks the evaluation as `N/A`. The metrics provided in the `Evaluation_Report.docx` and `ground_truth.json` files correspond to our controlled evaluation dataset (`pii_redaction_test.docx`) which validates the engine's core capabilities.

## Limitations, False Positives & False Negatives
- **False Positives**: NLP models (spaCy) occasionally flag generic nouns or capitalized legal terms at the beginning of sentences as `ORGANIZATION` or `PERSON`.
- **False Negatives**: Highly unusual address structures or highly ambiguous names lacking contextual clues (e.g., "Mr.") might be missed.
- **Accuracy Metric**: Standard accuracy is defined as `(TP + TN) / (TP + TN + FP + FN)`. For sparse span extraction in a 127-page free-text document, the universe of True Negatives (TN) is functionally infinite and undefined. We calculate Precision, Recall, and F1-score as the scientifically accurate metrics.

## Security Considerations
- The API is stateless; documents and PII are stored ephemerally and deleted securely.
- No raw PII is ever returned in the API responses or logged to the console.
- Download links expire via a strict TTL.

## Local Setup & Deployment
```bash
git clone https://github.com/Gurfiyaz/Scaler-AI.git
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python run.py
```
**API Endpoints:**
- `GET /health` - Healthcheck
- `GET /api/info` - Service Info
- `POST /api/process` - Multipart DOCX processing
- `GET /api/download/{id}` - Secure retrieval of processed output
