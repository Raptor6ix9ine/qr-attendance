from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import qrcode, io, base64, uuid, csv

app = Flask(__name__)
app.secret_key = "hackathon_secret" # For session management

# --- Database Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Models (Tables) ---
class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(10), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(10), nullable=False)
    roll_number = db.Column(db.String(50), nullable=False)

# --- QR Code Function (Unchanged) ---
def generate_qr_code(data):
    qr = qrcode.make(data)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# --- URL Routes ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == "teacher" and password == "1234":
            session['user'] = username
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/teacher/start")
def teacher_start():
    if 'user' not in session: # Protects this route
        return redirect(url_for("login"))
        
    session_id = str(uuid.uuid4())[:6]
    new_session = Session(session_id=session_id) # Create new session in DB
    db.session.add(new_session)
    db.session.commit()
    
    qr_data = generate_qr_code(session_id)
    return render_template("teacher.html", session_id=session_id, qr_data=qr_data)

@app.route("/student")
def student():
    return render_template("student.html")

@app.route("/student/submit", methods=["POST"])
def student_submit():
    session_id = request.form.get("session_id")
    roll_number = request.form.get("roll_number")
    
    # Check if session exists and is not expired (e.g., 30 minutes)
    active_session = Session.query.filter_by(session_id=session_id).first()
    if not active_session:
        return "❌ Invalid session ID."
    
    # Session Expiry check
    if datetime.utcnow() > active_session.created_at + timedelta(minutes=30):
        return "❌ This session has expired."

    # Check for duplicate attendance
    existing = Attendance.query.filter_by(session_id=session_id, roll_number=roll_number).first()
    if not existing:
        new_entry = Attendance(session_id=session_id, roll_number=roll_number)
        db.session.add(new_entry)
        db.session.commit()
    
    return f"✅ Attendance marked for Roll Number: {roll_number}!"

@app.route("/teacher/check/<session_id>")
def teacher_check(session_id):
    if 'user' not in session: # Protects this route
        return jsonify({"error": "unauthorized"}), 401
    
    records = Attendance.query.filter_by(session_id=session_id).all()
    roll_numbers = [record.roll_number for record in records]
    return jsonify(roll_numbers)

@app.route("/teacher/download/<session_id>")
def download_attendance(session_id):
    if 'user' not in session: # Protects this route
        return redirect(url_for("login"))
    
    records = Attendance.query.filter_by(session_id=session_id).all()
    roll_numbers = [record.roll_number for record in records]
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["Roll Number"])
    for r in roll_numbers:
        cw.writerow([r])
    
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=attendance_{session_id}.csv"}
    )

# --- Create Database and Run App ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all() # This creates your database tables
    app.run(debug=True)