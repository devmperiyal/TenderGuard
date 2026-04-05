from flask import Flask, request, render_template, jsonify, session, redirect, url_for
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import uuid
from typing import List, Dict
import re
import psycopg2
from psycopg2 import sql

# Import our utility modules
from utils.extractor import RequirementExtractor
from utils.validator import BidValidator

# PostgreSQL configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'tenderguard_db',
    'user': 'postgres',
    'password': 'dev_user'  # UPDATE THIS WITH YOUR PASSWORD
}

def get_db_connection():
    """Create and return a PostgreSQL connection"""
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    """Initialize database tables if they don't exist"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create users table WITH EMAIL
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add email column if table already exists (for backward compatibility)
        try:
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE")
        except:
            pass
        
        # Create projects table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                rfp_filename VARCHAR(255),
                rfp_text TEXT,
                proposal_filename VARCHAR(255),
                proposal_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create requirements table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS requirements (
                id SERIAL PRIMARY KEY,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                requirement_id VARCHAR(50),
                text TEXT NOT NULL,
                category VARCHAR(255),
                confidence FLOAT,
                keywords_found TEXT,
                status VARCHAR(50),
                matched_proposal_text TEXT,
                match_confidence FLOAT,
                validation_status VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_requirements_project_id ON requirements(project_id)
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {str(e)}")

# ================= UPDATED USER FUNCTIONS WITH EMAIL =================

def create_user(username, email, password):
    """Create new user with email and hashed password"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Hash password for security
        hashed_password = generate_password_hash(password)
        
        cur.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
            (username, email, hashed_password)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        return False

def get_user_by_credentials(username, password):
    """Get user by username and verify hashed password"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        # Verify password hash
        if user and check_password_hash(user[2], password):
            return (user[0], user[1])  # Return id, username
        return None
    except Exception as e:
        print(f"Error getting user: {str(e)}")
        return None

def user_exists(username, email=None):
    """Check if user exists by username or email"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if email:
            cur.execute("SELECT id FROM users WHERE username=%s OR email=%s", (username, email))
        else:
            cur.execute("SELECT id FROM users WHERE username=%s", (username,))
            
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user is not None
    except Exception as e:
        print(f"Error checking user: {str(e)}")
        return False

def get_user_id_by_username(username):
    """Get user ID by username"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE username=%s", (username,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error getting user ID: {str(e)}")
        return None

# ================= PROJECT FUNCTIONS =================

def create_project(user_id, rfp_filename, rfp_text):
    """Create new project"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO projects (user_id, rfp_filename, rfp_text) VALUES (%s, %s, %s) RETURNING id",
            (user_id, rfp_filename, rfp_text[:5000])
        )
        project_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return project_id
    except Exception as e:
        print(f"Error creating project: {str(e)}")
        return None

def get_latest_project(user_id):
    """Get user's latest project"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM projects WHERE user_id=%s ORDER BY created_at DESC LIMIT 1", (user_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error getting project: {str(e)}")
        return None

def save_requirements(project_id, requirements):
    """Save requirements to database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Delete existing requirements for this project
        cur.execute("DELETE FROM requirements WHERE project_id=%s", (project_id,))
        
        # Insert new requirements
        for req in requirements:
            cur.execute(
                """INSERT INTO requirements 
                   (project_id, requirement_id, text, category, confidence, keywords_found, status, 
                    matched_proposal_text, match_confidence, validation_status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    project_id,
                    req.get('id'),
                    req.get('text'),
                    req.get('category'),
                    req.get('confidence'),
                    json.dumps(req.get('keywords_found', [])),
                    req.get('status'),
                    req.get('matched_proposal_text'),
                    req.get('match_confidence'),
                    req.get('validation_status')
                )
            )
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving requirements: {str(e)}")
        return False

def get_requirements(project_id):
    """Get all requirements for a project"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT requirement_id, text, category, confidence, keywords_found, status, 
                      matched_proposal_text, match_confidence, validation_status
               FROM requirements WHERE project_id=%s""",
            (project_id,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        requirements = []
        for row in rows:
            requirements.append({
                'id': row[0],
                'text': row[1],
                'category': row[2],
                'confidence': row[3],
                'keywords_found': json.loads(row[4]) if row[4] else [],
                'status': row[5],
                'matched_proposal_text': row[6],
                'match_confidence': row[7],
                'validation_status': row[8]
            })
        return requirements
    except Exception as e:
        print(f"Error getting requirements: {str(e)}")
        return []

def update_project(project_id, proposal_filename=None, proposal_text=None):
    """Update project with proposal data"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if proposal_filename and proposal_text:
            cur.execute(
                "UPDATE projects SET proposal_filename=%s, proposal_text=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                (proposal_filename, proposal_text[:3000], project_id)
            )
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating project: {str(e)}")
        return False

def get_project_data(project_id):
    """Get project data"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT rfp_filename, rfp_text, proposal_filename, proposal_text FROM projects WHERE id=%s",
            (project_id,)
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            return {
                'rfp_filename': result[0],
                'rfp_text': result[1],
                'proposal_filename': result[2],
                'proposal_text': result[3]
            }
        return None
    except Exception as e:
        print(f"Error getting project data: {str(e)}")
        return None

# ================= FLASK APP SETUP =================

app = Flask(__name__)
app.secret_key = 'tender-compliance-validator-secret-key'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Initialize database on startup
init_db()

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
    
# ================= AUTH ROUTES (UPDATED WITH EMAIL) =================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")  # NOW CAPTURED!
        password = request.form.get("password")

        # Validate inputs
        if not username or not email or not password:
            return "All fields are required!", 400
            
        if user_exists(username, email):
            return "Username or email already exists!", 400

        if create_user(username, email, password):
            return redirect(url_for("login"))
        else:
            return "Registration error. Please try again.", 500

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = get_user_by_credentials(username, password)
        if user:
            session['user'] = username
            session['user_id'] = user[0]
            return redirect(url_for("home"))
        else:
            return "Invalid credentials"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    session.pop('project_id', None)
    return redirect(url_for("login"))

# ================= MAIN APPLICATION ROUTES =================

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
    
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Extract text from PDF
    file.seek(0)
    text = extract_text_from_pdf(file)
    
    if not text:
        return jsonify({'error': 'Could not extract text from PDF'}), 400
    
    # Extract requirements using NLP
    requirements = extractor.extract_requirements(text)
    
    # Create project in database
    project_id = create_project(session['user_id'], secure_filename(file.filename), text)
    
    if not project_id:
        return jsonify({'error': 'Failed to save project'}), 500
    
    # Save requirements to database
    save_requirements(project_id, requirements)
    
    # Store project_id in session for subsequent operations
    session['project_id'] = project_id
    
    return jsonify({
        'success': True,
        'requirements_count': len(requirements),
        'redirect': url_for('dashboard')
    })

@app.route("/dashboard")
def dashboard():
    """Display extracted requirements in editable table"""
    if 'project_id' not in session:
        return redirect(url_for('home'))
    
    requirements = get_requirements(session['project_id'])
    project_data = get_project_data(session['project_id'])
    
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
                         rfp_filename=project_data.get('rfp_filename', 'Unknown') if project_data else 'Unknown')

@app.route("/update-requirement", methods=["POST"])
def update_requirement():
    """Update a requirement (edit, delete, or confirm)"""
    if 'project_id' not in session:
        return jsonify({'error': 'No project loaded'}), 400
    
    data = request.get_json()
    req_id = data.get('id')
    action = data.get('action')
    
    requirements = get_requirements(session['project_id'])
    
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
    
    # Save updated requirements to database
    save_requirements(session['project_id'], requirements)
    
    return jsonify({'success': True, 'requirements': requirements})

@app.route("/upload-proposal", methods=["POST"])
def upload_proposal():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    if 'project_id' not in session:
        return jsonify({'error': 'No project loaded'}), 400
    
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400
    
    # Get current requirements from database
    requirements = get_requirements(session['project_id'])
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

        # Update project with proposal data
        update_project(session['project_id'], secure_filename(file.filename), proposal_text)
        
        # Save validated requirements to database
        save_requirements(session['project_id'], validated_requirements)

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

@app.route("/results")
def results():
    """Display validation results"""
    if 'project_id' not in session:
        return redirect(url_for('home'))
    
    requirements = get_requirements(session['project_id'])
    project_data = get_project_data(session['project_id'])
    
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
        'Fully Addressed': [r for r in requirements if r['validation_status'] == 'Fully Addressed'],
        'Partially Addressed': [r for r in requirements if r['validation_status'] == 'Partially Addressed'],
        'Missing/Insufficient': [r for r in requirements if r['validation_status'] in ('Missing', 'Insufficiently Addressed')],
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
                         rfp_filename=project_data.get('rfp_filename', 'Unknown') if project_data else 'Unknown',
                         proposal_filename=project_data.get('proposal_filename', 'Not uploaded') if project_data else 'Not uploaded')

@app.route("/export-results", methods=["GET"])
def export_results():
    """Export validation results as JSON"""
    if 'project_id' not in session:
        return jsonify({'error': 'No project loaded'}), 400
    
    requirements = get_requirements(session['project_id'])
    project_data = get_project_data(session['project_id'])
    
    return jsonify({
        'rfp_filename': project_data.get('rfp_filename') if project_data else None,
        'proposal_filename': project_data.get('proposal_filename') if project_data else None,
        'requirements': requirements,
        'export_timestamp': str(uuid.uuid1())
    })

@app.route("/clear")
def clear_session():
    """Clear current project from session"""
    session.pop('project_id', None)
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True, port=5000)