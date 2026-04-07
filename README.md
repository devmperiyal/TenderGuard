# TenderGuard — AI-Powered Tender Compliance Validator

> Automatically extract mandatory requirements from RFP documents and validate vendor proposals using semantic AI matching.

---

## What It Does

When companies respond to government or corporate tenders, legal and procurement teams must manually verify that every mandatory requirement in a 100+ page RFP document is addressed in the vendor's proposal. Missing even one requirement can disqualify the entire bid.

**TenderGuard automates this process end-to-end:**

1. Upload an RFP PDF → AI extracts all mandatory requirements
2. Review and edit the extracted requirements in a dashboard
3. Upload the vendor proposal → AI semantically matches it against every requirement
4. Get a full compliance report with scores, matched text, and actionable recommendations

---

## Features

- **AI Requirement Extraction** — Detects mandatory language (`shall`, `must`, `required`, `mandatory`) using spaCy NLP and classifies requirements into categories (Technical, Legal, Financial, Security, Service Level, Qualifications)
- **Semantic Matching** — Uses `sentence-transformers` (`all-MiniLM-L6-v2`) and cosine similarity to match proposal text against requirements even when wording differs
- **Compliance Scoring** — Weighted formula: `(Fully Addressed + 0.5 × Partially Addressed + Missing or Insufficiently Addressed × 0) ÷ Total Requirements × 100`
- **4-Level Classification** — Fully Addressed / Partially Addressed / Insufficiently Addressed / Missing
- **Editable Dashboard** — Add, edit, or delete requirements before validation
- **User Authentication** — Multi-user support with hashed passwords and session management
- **Export** — Download full compliance report as JSON
- **PostgreSQL Backend** — All projects, requirements, and results persisted per user

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| NLP Extraction | spaCy (`en_core_web_sm`) |
| Semantic Matching | Sentence-Transformers, scikit-learn |
| PDF Processing | PyPDF2 |
| Database | PostgreSQL, psycopg2 |
| Auth | Werkzeug password hashing |
| Frontend | Bootstrap 5, Font Awesome |

---

## Project Structure

```
TenderGuard/
├── app.py                  # Main Flask application & all routes
├── requirements.txt        # Python dependencies
├── app_db_schema.sql       # PostgreSQL schema
├── .gitignore
├── README.md
├── templates/
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   ├── index.html          # RFP upload page
│   ├── dashboard.html      # Requirements review & edit
│   └── results.html        # Compliance validation report
├── utils/
│   ├── __init__.py
│   ├── extractor.py        # Requirement extraction engine
│   └── validator.py        # Semantic bid validator
└── uploads/                # Temporary PDF storage (gitignored)
```

---

## Setup & Installation

### Prerequisites
- Python 3.9+
- PostgreSQL 13+

### 1. Clone the repository
```bash
git clone https://github.com/devmperiyal/TenderGuard.git
cd TenderGuard
```

### 2. Create and activate virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 4. Set up PostgreSQL database
```bash
# Create the database
psql -U postgres -c "CREATE DATABASE tenderguard_db;"

# Run the schema
psql -U postgres -d tenderguard_db -f app_db_schema.sql
```

### 5. Configure database credentials
Open `app.py` and update the `DB_CONFIG` block:
```python
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'tenderguard_db',
    'user': 'postgres',
    'password': 'your_password_here'
}
```

### 6. Run the application
```bash
python app.py
```

Open your browser at: **http://127.0.0.1:5000**

---

## How to Use

1. **Register / Login** at the home screen
2. **Upload RFP PDF** — the AI extracts all mandatory requirements automatically
3. **Review the Dashboard** — edit, delete, or add requirements as needed
4. **Upload Vendor Proposal PDF** — the AI runs semantic matching
5. **View Results** — see the compliance score, matched text, and per-requirement status
6. **Export** — download the full report as JSON

---

## Compliance Scoring

| Status | Points | Meaning |
|---|---|---|
| ✅ Fully Addressed | 1.00 | Strong semantic match with high confidence |
| ⚠️ Partially Addressed | 0.50 | Topic covered but lacks full detail |
| ❌ Insufficiently Addressed | 0.00 | Mentioned but response too weak to confirm compliance |
| ❌ Missing | 0.00 | No matching content found in proposal |

**Compliance Score = (Fully Addressed + 0.5 × Partially Addressed + Missing or Insufficiently Addressed × 0) ÷ Total Requirements × 100**

---

## Similarity Thresholds

| Confidence | Status |
|---|---|
| > 0.80 similarity + confidence | Fully Addressed |
| ≥ 0.65 confidence | Partially Addressed |
| > 0.40 similarity | Insufficiently Addressed |
| ≤ 0.40 similarity | Missing |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Home / RFP upload page |
| POST | `/upload-rfp` | Upload RFP, extract requirements |
| GET | `/dashboard` | View and edit requirements |
| POST | `/update-requirement` | Add / edit / delete a requirement |
| POST | `/upload-proposal` | Upload proposal, run validation |
| GET | `/results` | View compliance report |
| GET | `/export-results` | Download results as JSON |
| GET | `/clear` | Start a new analysis |

---

## Author

**Devavrath M Periyal**  