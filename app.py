from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from transformers import pipeline
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Database Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# AI Models
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
question_generator = pipeline("text2text-generation", model="google/flan-t5-base")

# -----------------------
# Database Models
# -----------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    summary = db.Column(db.Text, nullable=False)

# Create tables (Flask 3 compatible)
with app.app_context():
    db.create_all()

# -----------------------
# Register
# -----------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "User already exists"

        hashed_password = generate_password_hash(password)

        user = User(username=username, password=hashed_password)

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")

# -----------------------
# Login
# -----------------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))
        else:
            return "Invalid username or password"

    return render_template("login.html")

# -----------------------
# Dashboard
# -----------------------

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    summary = ""
    questions = ""

    if request.method == "POST":

        text = request.form["text"]

        # Generate summary
        summary = summarizer(
            text,
            max_length=100,
            min_length=30,
            do_sample=False
        )[0]['summary_text']

        # Generate questions
        questions = question_generator(
            "Generate questions from this text: " + text,
            max_length=100
        )[0]['generated_text']

        # Save history
        history = History(
            user_id=session["user_id"],
            summary=summary
        )

        db.session.add(history)
        db.session.commit()

    # Fetch user history
    user_history = History.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template(
        "dashboard.html",
        summary=summary,
        questions=questions,
        history=user_history
    )

# -----------------------
# Logout
# -----------------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login.html"))

# -----------------------
# Run App
# -----------------------

if __name__ == "__main__":
    app.run(debug=True)