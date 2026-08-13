# PII Redaction Tool

A privacy-preserving DOCX PII detection and redaction system.

---

## Features

- DOCX ingestion
- multi-layer PII detection
- deterministic replacement mapping
- cross-run DOCX handling
- XML-level redaction
- residual PII validation
- document integrity validation
- independent evaluation framework
- FastAPI API
- privacy-preserving frontend
- ephemeral file handling
- automated tests
- Render deployment support

---

## Supported PII Categories

1. **PERSON**
2. **EMAIL_ADDRESS**
3. **PHONE_NUMBER**
4. **ORGANIZATION**
5. **ADDRESS**
6. **SSN**
7. **CREDIT_CARD**
8. **DATE_OF_BIRTH**
9. **IP_ADDRESS**

---

## Architecture

```
Browser
↓
FastAPI
↓
Processing Service
↓
DOCX Parser
↓
PII Detector
↓
Entity Mapper
↓
DOCX Redactor
↓
Validator
↓
Evaluation
```

---

## Local Setup Instructions

```bash
# Clone repository
git clone https://github.com/Gurfiyaz/Scaler-AI.git
cd Scaler-AI

# Create virtual environment and install dependencies
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Download required spaCy language model
python -m spacy download en_core_web_sm

# Start the application
python run.py
```

---

## API Endpoints

- `GET /health`
- `GET /api/info`
- `POST /api/process`
- `GET /api/download/{download_id}`

---

## Evaluation Methodology

The evaluation framework relies on **independent ground truth** ensuring unbiased metric calculation:

- **TP (True Positives)**: Detected PII correctly matched to ground truth.
- **FP (False Positives)**: Detected PII not in ground truth.
- **FN (False Negatives)**: Ground truth PII missed by the detector.
- **Precision**: TP / (TP + FP)
- **Recall**: TP / (TP + FN)
- **F1**: 2 * (Precision * Recall) / (Precision + Recall)
- **micro/macro averaging**: Micro computes metrics globally across all categories, macro computes average of category metrics.
- **exact span matching**: Strictly 1-to-1 matching based on exact character span overlap.
- **why conventional accuracy may be N/A for sparse span extraction**: In sparse PII span extraction over free text, the universe of negative (non-PII) character spans is infinite/un-enumerated. True Negatives (TN) cannot be legitimately counted, rendering conventional accuracy undefined.

---

## Privacy

- no raw PII in API responses
- no persistent database required
- ephemeral processing
- original document remains unchanged
- private ground truth is excluded

---

## Testing

136/136 tests passed.

```bash
pytest
```

---

## Deployment

Render deployment is fully supported:
1. Connect your GitHub repository to Render as a "Web Service".
2. Set the build command to: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`
3. Set the start command to: `python run.py`
4. Ensure environment variables correspond to `.env.example`.
