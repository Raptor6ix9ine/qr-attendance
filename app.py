from flask import Flask, render_template, request, redirect, url_for, jsonify
import qrcode, io, base64, uuid

app = Flask(__name__)

# in-memory store (prototype only!)
sessions = {}
current_session = None

def generate_qr_code(data):
    qr = qrcode.make(data)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/teacher/start")
def teacher_start():
    global current_session
    session_id = str(uuid.uuid4())[:6]
    sessions[session_id] = []
    current_session = session_id
    qr_data = generate_qr_code(session_id)
    return render_template("teacher.html", session_id=session_id, qr_data=qr_data)

@app.route("/student")
def student():
    return render_template("student.html")

@app.route("/student/submit", methods=["POST"])
def student_submit():
    session_id = request.form.get("session_id")
    name = request.form.get("name")
    if session_id in sessions:
        if name not in sessions[session_id]:
            sessions[session_id].append(name)
        return f"✅ Attendance marked for {name}!"
    return "❌ Invalid or expired session."

@app.route("/teacher/check/<session_id>")
def teacher_check(session_id):
    names = sessions.get(session_id, [])
    return jsonify(names)

if __name__ == "__main__":
    app.run(debug=True)
