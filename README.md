# TenderGuard – Tender Compliance Validator

## 📌 Overview

TenderGuard is a web-based application that helps automate the process of verifying whether vendor proposals satisfy all requirements in a Request for Proposal (RFP).

The system reads RFP documents (PDF), extracts mandatory requirements, and prepares them for validation.

---

## 🚀 Features

* Upload RFP PDF document
* Extract text from PDF
* Identify mandatory requirements using keywords:

  * must
  * shall
  * required
* Display extracted requirements

---

## 🛠️ Tech Stack

* Python
* Flask
* PyPDF2
* HTML (basic frontend)
* Git & GitHub

---

## ⚙️ How to Run

1. Clone the repository
   git clone https://github.com/devmperiyal/TenderGuard.git

2. Go to project folder
   cd TenderGuard

3. Create virtual environment
   python -m venv venv

4. Activate virtual environment
   venv\Scripts\activate

5. Install dependencies
   pip install flask PyPDF2

6. Run the app
   python app.py

7. Open in browser
   http://127.0.0.1:5000/

---

## 📂 Structure

* app.py → main backend code
* README.md → project documentation

---

## 🎯 Future Work

* Compare RFP with vendor proposals
* Add AI-based semantic matching
* Add confidence scoring
* Improve UI

---

## 👨‍💻 Author

Devavrath M Periyal
