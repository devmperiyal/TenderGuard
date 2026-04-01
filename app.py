from flask import Flask, request
from PyPDF2 import PdfReader

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h2>TenderGuard Upload</h2>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file">
        <input type="submit" value="Upload">
    </form>
    """

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files['file']
    
    if file:
        reader = PdfReader(file)
        text = ""

        for page in reader.pages:
            text += page.extract_text() or ""

        requirements = []
        lines = text.split('\n')

        for line in lines:
            if ("must" in line.lower() or 
                "shall" in line.lower() or 
                "required" in line.lower()):
                requirements.append(line.strip())

        output = "<h3>Extracted Requirements:</h3>"
        for req in requirements:
            output += f"<p>• {req}</p>"

        return output
    
    return "No file uploaded"

if __name__ == "__main__":
    app.run(debug=True)