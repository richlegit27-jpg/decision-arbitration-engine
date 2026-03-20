from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import jwt
import datetime
import os

# Setup Flask and Config
app = Flask(__name__)

# IMPORTANT: use instance folder db (matches what you already discovered)
# This will create/use: C:\Users\Owner\nova\instance\users.db
app.config["SECRET_KEY"] = "your_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "uploads")

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")


# -----------------------
# Models
# -----------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(255), nullable=True)
    password = db.Column(db.String(255), nullable=False)
    avatar = db.Column(db.String(200), nullable=True)
    role = db.Column(db.String(50), default="user")


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    avatar = db.Column(db.String(200), nullable=True)
    text = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now())


with app.app_context():
    db.create_all()


# -----------------------
# Pages (GET routes)  ✅ FIXES YOUR 405
# -----------------------
@app.route("/")
def index():
    # If you want to force login for the chat UI, keep this check.
    # If you want chat visible without login, comment it out.
    token = session.get("token")
    if not token:
        return redirect(url_for("login_page"))

    messages = Message.query.all()
    return render_template("chat.html", messages=messages)


@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


@app.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")


# -----------------------
# Auth endpoints (POST routes)
# -----------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or request.form

    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    email = (data.get("email") or "").strip()
    role = (data.get("role") or "user").strip()

    if not username or not password:
        return jsonify({"message": "username and password required"}), 400

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"message": "Username already exists"}), 400

    # Werkzeug 3+: sha256 is NOT allowed. Use default (scrypt) or pbkdf2:sha256.
    # Default is fine:
    hashed_password = generate_password_hash(password)

    new_user = User(username=username, email=email, password=hashed_password, role=role)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or request.form

    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"message": "username and password required"}), 400

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password, password):
        token = jwt.encode(
            {
                "user_id": user.id,
                "role": user.role or "user",
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            },
            app.config["SECRET_KEY"],
            algorithm="HS256",
        )

        # Store token in session so your GET / (chat) can allow access
        session["token"] = token
        session["user_id"] = user.id

        return jsonify({"token": token}), 200

    return jsonify({"message": "Invalid credentials"}), 401


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("token", None)
    session.pop("user_id", None)
    return jsonify({"message": "Logged out"}), 200


@app.route("/protected", methods=["GET"])
def protected():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"message": "Missing Bearer token"}), 401

    token = auth.split(" ", 1)[1].strip()

    try:
        decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        return jsonify({"message": "Access granted", "user_id": decoded["user_id"], "role": decoded.get("role", "user")}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401


# -----------------------
# WebSocket: messages
# -----------------------
@socketio.on("send_message")
def handle_message(data):
    if not data or "message" not in data:
        return

    username = data.get("username", "user")
    avatar = data.get("avatar")
    text = data.get("message")

    new_message = Message(username=username, avatar=avatar, text=text)
    db.session.add(new_message)
    db.session.commit()

    emit("new_message", data, broadcast=True)


@socketio.on("connect")
def handle_connect():
    print("A user has connected")
    emit("new_message", {"text": "A new user has joined the chat", "username": "System"}, broadcast=True)


@socketio.on("disconnect")
def handle_disconnect():
    print("A user has disconnected")
    emit("new_message", {"text": "A user has left the chat", "username": "System"}, broadcast=True)


# -----------------------
# Avatar Upload (optional)
# -----------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"png", "jpg", "jpeg", "gif"}


@app.route("/upload_avatar", methods=["POST"])
def upload_avatar():
    if "file" not in request.files:
        return jsonify({"message": "No file part"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"message": "No selected file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"message": "Invalid file type"}), 400

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    user_id = session.get("user_id")
    if user_id:
        u = User.query.get(user_id)
        if u:
            u.avatar = filename
            db.session.commit()

    return jsonify({"message": "Avatar uploaded successfully", "avatar": filename}), 200


if __name__ == "__main__":
    socketio.run(app, debug=True)