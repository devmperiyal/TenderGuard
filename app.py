from flask import Flask, request, render_template, jsonify, session, redirect, url_for
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename
import os
import json
import uuid
from typing import List, Dict
import re

# Import our utility modules
from utils.extractor import RequirementExtractor
from utils.validator import BidValidator

users = {}  # simple storage

app = Flask(__name__)
app.secret_key = 'tender-compliance-validator-secret-key'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# ================= AUTH ROUTES =================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in users:
            return "User already exists!"

        users[username] = password
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in users and users[username] == password:
            session['user'] = username
            return redirect(url_for("home"))
        else:
            return "Invalid credentials"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for("login"))

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize AI components
extractor = RequirementExtractor()
validator = BidValidator()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_stream):
    """Extract text from PDF file"""
    try:
        reader = PdfReader(file_stream)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return None
    
@app.route("/")
def home():
    if 'user' not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/upload-rfp", methods=["POST"])
def upload_rfp():
    """Handle RFP document upload and extract requirements"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400
    
    # Extract text from PDF
    file.seek(0)
    text = extract_text_from_pdf(file)
    
    if not text:
        return jsonify({'error': 'Could not extract text from PDF'}), 400
    
    # Extract requirements using NLP
    requirements = extractor.extract_requirements(text)
    
    # Store in session
    session['requirements'] = requirements
    session['rfp_text'] = text[:5000]  # Store preview
    session['rfp_filename'] = secure_filename(file.filename)
    
    return jsonify({
        'success': True,
        'requirements_count': len(requirements),
        'redirect': url_for('dashboard')
    })

@app.route("/dashboard")
def dashboard():
    """Display extracted requirements in editable table"""
    requirements = session.get('requirements', [])
    if not requirements:
        return redirect(url_for('home'))
    
    # Group by category for display
    categories = {}
    for req in requirements:
        cat = req['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(req)
    
    return render_template('dashboard.html', 
                         requirements=requirements,
                         categories=categories,
                         rfp_filename=session.get('rfp_filename', 'Unknown'))

@app.route("/update-requirement", methods=["POST"])
def update_requirement():
    """Update a requirement (edit, delete, or confirm)"""
    data = request.get_json()
    req_id = data.get('id')
    action = data.get('action')
    
    requirements = session.get('requirements', [])
    
    if action == 'delete':
        requirements = [r for r in requirements if r['id'] != req_id]
    elif action == 'update':
        for req in requirements:
            if req['id'] == req_id:
                req['text'] = data.get('text', req['text'])
                req['category'] = data.get('category', req['category'])
                req['confidence'] = data.get('confidence', req['confidence'])
                break
    elif action == 'add':
        new_req = {
            'id': f"REQ-{len(requirements)+1:03d}-{str(uuid.uuid4())[:4]}",
            'text': data.get('text'),
            'category': data.get('category', 'General Requirements'),
            'confidence': 1.0,
            'keywords_found': ['manual'],
            'status': 'pending',
            'matched_proposal_text': None,
            'match_confidence': 0.0,
            'validation_status': 'Not Checked'
        }
        requirements.append(new_req)
    
    session['requirements'] = requirements
    return jsonify({'success': True, 'requirements': requirements})

@app.route("/upload-proposal", methods=["POST"])
def upload_proposal():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400
    
    # Get current requirements
    requirements = session.get('requirements', [])
    if not requirements:
        return jsonify({'error': 'No requirements loaded. Please upload RFP first.'}), 400

    try:
        # Extract proposal text
        file.seek(0)
        proposal_text = extract_text_from_pdf(file)

        if not proposal_text:
            return jsonify({'error': 'Could not extract text from proposal PDF'}), 400

        # Validate proposal
        validated_requirements = validator.validate_proposal(requirements, proposal_text)

        # Update session
        session['requirements'] = validated_requirements
        session['proposal_text'] = proposal_text[:3000]
        session['proposal_filename'] = secure_filename(file.filename)

        # Calculate summary
        total = len(validated_requirements)
        addressed = sum(1 for r in validated_requirements if 'Fully' in r['validation_status'])
        partial = sum(1 for r in validated_requirements if 'Partially' in r['validation_status'])
        missing = sum(1 for r in validated_requirements if 'Missing' in r['validation_status'] or 'Insufficient' in r['validation_status'])

        return jsonify({
            'success': True,
            'redirect': url_for('results'),
            'summary': {
                'total': total,
                'addressed': addressed,
                'partial': partial,
                'missing': missing,
                'compliance_score': round((addressed + (partial * 0.5)) / total * 100, 1) if total > 0 else 0
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    
    # Update session
    session['requirements'] = validated_requirements
    session['proposal_text'] = proposal_text[:3000]  # Store preview
    session['proposal_filename'] = secure_filename(file.filename)
    
    # Calculate summary statistics
    total = len(validated_requirements)
    addressed = sum(1 for r in validated_requirements if 'Fully' in r['validation_status'])
    partial = sum(1 for r in validated_requirements if 'Partially' in r['validation_status'])
    missing = sum(1 for r in validated_requirements if 'Missing' in r['validation_status'] or 'Insufficient' in r['validation_status'])
    
    return jsonify({
        'success': True,
        'redirect': url_for('results'),
        'summary': {
            'total': total,
            'addressed': addressed,
            'partial': partial,
            'missing': missing,
            'compliance_score': round((addressed + (partial * 0.5)) / total * 100, 1) if total > 0 else 0
        }
    })

@app.route("/results")
def results():
    """Display validation results"""
    requirements = session.get('requirements', [])
    if not requirements:
        return redirect(url_for('home'))
    
    # Calculate statistics
    total = len(requirements)
    addressed = sum(1 for r in requirements if 'Fully' in r['validation_status'])
    partial = sum(1 for r in requirements if 'Partially' in r['validation_status'])
    missing = sum(1 for r in requirements if 'Missing' in r['validation_status'] or 'Insufficient' in r['validation_status'])
    not_checked = sum(1 for r in requirements if r['validation_status'] == 'Not Checked')
    
    # Group by status for display
    by_status = {
        'Fully Addressed': [r for r in requirements if 'Fully' in r['validation_status']],
        'Partially Addressed': [r for r in requirements if 'Partially' in r['validation_status']],
        'Missing/Insufficient': [r for r in requirements if 'Missing' in r['validation_status'] or 'Insufficient' in r['validation_status']],
        'Not Checked': [r for r in requirements if r['validation_status'] == 'Not Checked']
    }
    
    compliance_score = round((addressed + (partial * 0.5)) / total * 100, 1) if total > 0 else 0
    
    return render_template('results.html',
                         requirements=requirements,
                         by_status=by_status,
                         stats={
                             'total': total,
                             'addressed': addressed,
                             'partial': partial,
                             'missing': missing,
                             'not_checked': not_checked,
                             'compliance_score': compliance_score
                         },
                         rfp_filename=session.get('rfp_filename', 'Unknown'),
                         proposal_filename=session.get('proposal_filename', 'Not uploaded'))

@app.route("/export-results", methods=["GET"])
def export_results():
    """Export validation results as JSON"""
    requirements = session.get('requirements', [])
    return jsonify({
        'rfp_filename': session.get('rfp_filename'),
        'proposal_filename': session.get('proposal_filename'),
        'requirements': requirements,
        'export_timestamp': str(uuid.uuid1())
    })

@app.route("/clear")
def clear_session():
    """Clear all session data"""
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True, port=5000)