from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from datetime import datetime, timedelta
import qrcode, io, base64, uuid

app = Flask(__name__)
app.secret_key = "your_super_secret_key" # Needed for session management

# --- In-memory store for the demo ---
TEACHER_CREDS = {"teacher": "password123"}
STUDENT_CREDS = {"160323737012": "studentpass"}
SESSIONS = {}
current_session_id = None

def generate_qr_code(data):
    qr = qrcode.make(data)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

@app.route("/")
def index():
    user_type = session.get("user_type")
    if user_type == 'teacher':
        # UPDATED REDIRECT: Go to start a session if already logged in
        return redirect(url_for('teacher_start'))
    elif user_type == 'student':
        return redirect(url_for('student_scan'))
    return render_template("index.html")

# --- Login & Logout Routes ---
@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if TEACHER_CREDS.get(username) == password:
            session["user_type"] = "teacher"
            # UPDATED REDIRECT: Go directly to start a session after login
            return redirect(url_for("teacher_start"))
        return render_template("teacher_login.html", error="Invalid credentials")
    return render_template("teacher_login.html")

@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        roll_number = request.form.get("roll_number")
        password = request.form.get("password")
        if STUDENT_CREDS.get(roll_number) == password:
            session["user_type"] = "student"
            session["roll_number"] = roll_number
            return redirect(url_for("student_scan"))
        return render_template("student_login.html", error="Invalid credentials")
    return render_template("student_login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# --- Teacher Routes ---
# The old "/teacher/dashboard" route has been removed to fix the loop.
# "/teacher/start" is now the main destination after login.
@app.route("/teacher/start")
def teacher_start():
    if session.get("user_type") != "teacher":
        return redirect(url_for("teacher_login"))
    
    global current_session_id
    current_session_id = str(uuid.uuid4())[:6]
    SESSIONS[current_session_id] = {
        "attendees": [],
        "created_at": datetime.now()
    }
    qr_data = generate_qr_code(current_session_id)
    return render_template("teacher.html", session_id=current_session_id, qr_data=qr_data)

@app.route("/teacher/check/<session_id>")
def teacher_check(session_id):
    if session.get("user_type") != "teacher":
        return jsonify({"error": "Unauthorized"}), 403
    
    roll_numbers = SESSIONS.get(session_id, {}).get("attendees", [])
    return jsonify(roll_numbers)

# --- Student Routes ---
@app.route("/student/scan")
def student_scan():
    if session.get("user_type") != "student":
        return redirect(url_for("student_login"))

    session_active = False
    if current_session_id and current_session_id in SESSIONS:
        session_data = SESSIONS[current_session_id]
        if datetime.now() < session_data["created_at"] + timedelta(minutes=20):
            session_active = True
            
    return render_template("student.html", roll_number=session.get("roll_number"), session_active=session_active)

@app.route("/student/submit", methods=["POST"])
def student_submit():
    if session.get("user_type") != "student":
        return redirect(url_for("student_login"))
    
    session_id = request.form.get("session_id")
    roll_number = session.get("roll_number")

    if session_id in SESSIONS:
        session_data = SESSIONS[session_id]
        if datetime.now() < session_data["created_at"] + timedelta(minutes=20):
            if roll_number not in session_data["attendees"]:
                session_data["attendees"].append(roll_number)
            return f"✅ Attendance marked for Roll Number: {roll_number}!"
        else:
            return "❌ Session has expired."
    return "❌ Invalid session."

if __name__ == "__main__":
    app.run(debug=True)