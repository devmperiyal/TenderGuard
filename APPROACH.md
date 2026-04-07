# TenderGuard

AI-Powered Tender Compliance Validator

*Approach Document*

**Devavrath M Periyal**

---

## 1. Problem Statement

Legal and procurement teams must manually verify every mandatory requirement in 100+ page RFP documents against vendor proposals. Missing one requirement can disqualify the entire bid. TenderGuard automates this end-to-end using AI.

---

## 2. Solution Design

### Feature 1 — Requirement Extraction

- Extracts text from RFP PDFs using PyPDF2, segments sentences with spaCy
- Detects mandatory language: "shall" (1.0), "must" (1.0), "required" (0.9), "should" (0.7)
- Classifies into categories: Technical, Legal, Financial, Security, Service Level, Qualifications
- Editable dashboard — users can add, edit, or delete requirements before validation

### Feature 2 — Bid-to-Requirement Validator

- Encodes requirements and proposal segments using Sentence-Transformers (all-MiniLM-L6-v2)
- Computes cosine similarity between each requirement and every proposal segment
- Confidence scoring: boosts for commitment language (will, shall), penalties for vague language (may, might)

---

## 3. Classification & Scoring

| Status | Threshold | Weight | Meaning |
|--------|-----------|--------|---------|
| Fully Addressed | Confidence &gt; 0.80 & Similarity &gt; 0.75 | 1.00 | Strong semantic match |
| Partially Addressed | Confidence &gt;= 0.65 | 0.50 | Covered, lacks detail |
| Insufficiently Addressed | Similarity &gt; 0.40 | 0.00 | Mentioned, too weak |
| Missing | Similarity &lt;= 0.40 | 0.00 | Not found in proposal |

**Score = (Fully Addressed + 0.5 × Partially Addressed + Missing or Insufficiently Addressed × 0) ÷ Total × 100**

---

## 4. Technology Stack

| Component | Technology | Reason |
|-----------|------------|--------|
| Web Framework | Flask | Lightweight, easy ML integration |
| NLP Extraction | spaCy en_core_web_sm | Fast sentence segmentation |
| Semantic Matching | Sentence-Transformers + sklearn | State-of-the-art similarity, offline |
| PDF Processing | PyPDF2 | Reliable multi-page text extraction |
| Database | PostgreSQL + psycopg2 | Persistent multi-user storage |
| Frontend | Bootstrap 5 + Font Awesome | Responsive UI, minimal overhead |

---

## 5. What I Would Improve With More Time

- Fine-tune the semantic model specifically on RFP/procurement domain text for higher accuracy
- Add PDF page number references so reviewers can jump to matched proposal sections
- Add PDF export of the compliance report for formal client submission
- Support re-validation — upload a revised proposal without restarting the project
- Deploy on cloud (Render/AWS) with environment-based config for public access