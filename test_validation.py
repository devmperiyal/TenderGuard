import psycopg2
from utils.validator import BidValidator

# Get requirements and proposal from DB
conn = psycopg2.connect(
    host='localhost', port=5432, database='tenderguard_db',
    user='postgres', password='dev_user'
)
cur = conn.cursor()

# Get latest project data
cur.execute('SELECT id, proposal_text FROM projects ORDER BY created_at DESC LIMIT 1')
project_id, proposal_text = cur.fetchone()

# Get requirements
cur.execute('''SELECT requirement_id, text, category, confidence, keywords_found, status, 
              matched_proposal_text, match_confidence, validation_status
              FROM requirements WHERE project_id=%s LIMIT 3''', (project_id,))
rows = cur.fetchall()
requirements = []
for row in rows:
    requirements.append({
        'id': row[0],
        'text': row[1],
        'category': row[2],
        'confidence': row[3],
        'keywords_found': [],
        'status': row[5],
        'matched_proposal_text': row[6],
        'match_confidence': row[7],
        'validation_status': row[8]
    })

cur.close()
conn.close()

print(f"Testing validation on {len(requirements)} requirements")
print(f"Proposal text length: {len(proposal_text)}")
print(f"First requirement: {requirements[0]['text'][:80]}")

# Test validator
validator = BidValidator()
validated = validator.validate_proposal(requirements, proposal_text)

for req in validated:
    print(f"REQ {req['id']}: {req['validation_status']} (confidence: {req['match_confidence']:.2f})")
    print(f"  Matched: {req['matched_proposal_text'][:100] if req['matched_proposal_text'] else 'None'}...")
