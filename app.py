from datetime import datetime
from functools import wraps
import os

from flask import Flask, jsonify, redirect, render_template, request, session, url_for, flash
from pymongo import MongoClient
from werkzeug.security import check_password_hash, generate_password_hash
from bson import ObjectId

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(mongo_uri)
db = client[os.getenv("MONGO_DB", "smart_home_service_assistant")]

SERVICE_KEYWORDS = {
    "Electrical repair": ["electrical", "wiring", "switch", "socket", "light", "power", "fuse"],
    "Plumbing": ["pipe", "water", "leak", "drain", "tap", "toilet", "plumbing"],
    "Carpentry": ["wood", "door", "cabinet", "furniture", "carpentry", "shelf"],
    "Painting": ["paint", "wall color", "repaint", "stain", "painting"],
    "Masonry": ["brick", "cement", "wall crack", "tile", "masonry", "concrete"],
    "Cleaning": ["clean", "dust", "sanitize", "deep cleaning", "washing"],
    "Appliance repair": ["fridge", "ac", "washing machine", "microwave", "appliance", "repair"],
}


def classify_issue(text: str) -> str:
    text_lower = text.lower()
    best_service = "General assistance"
    max_hits = 0

    for service, keywords in SERVICE_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in text_lower)
        if hits > max_hits:
            max_hits = hits
            best_service = service

    return best_service


def login_required(role=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in first.", "error")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("Unauthorized action.", "error")
                return redirect(url_for("dashboard"))
            return func(*args, **kwargs)

        return wrapper

    return decorator


def find_technician(service: str, location: str):
    return db.technicians.find_one(
        {
            "services": service,
            "cities": {"$in": [location.strip().lower()]},
            "availability": True,
        }
    ) or db.technicians.find_one({"services": service, "availability": True})


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        if db.users.find_one({"email": email}):
            flash("Email already exists.", "error")
            return redirect(url_for("register"))

        user = {
            "name": request.form["name"].strip(),
            "email": email,
            "password": generate_password_hash(request.form["password"]),
            "role": "user",
            "created_at": datetime.utcnow(),
        }
        db.users.insert_one(user)
        flash("User registered successfully. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", mode="user")


@app.route("/technician/register", methods=["GET", "POST"])
def technician_register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        if db.users.find_one({"email": email}):
            flash("Email already exists.", "error")
            return redirect(url_for("technician_register"))

        selected_services = request.form.getlist("services")
        cities = [c.strip().lower() for c in request.form["cities"].split(",") if c.strip()]

        user_id = db.users.insert_one(
            {
                "name": request.form["name"].strip(),
                "email": email,
                "password": generate_password_hash(request.form["password"]),
                "role": "technician",
                "created_at": datetime.utcnow(),
            }
        ).inserted_id

        db.technicians.insert_one(
            {
                "user_id": user_id,
                "name": request.form["name"].strip(),
                "phone": request.form["phone"].strip(),
                "services": selected_services,
                "cities": cities,
                "availability": True,
                "rating": 4.5,
                "created_at": datetime.utcnow(),
            }
        )

        flash("Technician account created. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", mode="technician", services=list(SERVICE_KEYWORDS.keys()))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        user = db.users.find_one({"email": email})
        if not user or not check_password_hash(user["password"], request.form["password"]):
            flash("Invalid credentials.", "error")
            return redirect(url_for("login"))

        session["user_id"] = str(user["_id"])
        session["name"] = user["name"]
        session["role"] = user["role"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required()
def dashboard():
    role = session.get("role")
    current_user_id = ObjectId(session["user_id"])

    if role == "technician":
        technician = db.technicians.find_one({"user_id": current_user_id})
        requests_data = list(
            db.service_requests.find(
                {
                    "assigned_technician_id": technician["_id"] if technician else None,
                }
            ).sort("created_at", -1)
        )
        return render_template("technician_dashboard.html", requests_data=requests_data)

    requests_data = list(db.service_requests.find({"user_id": current_user_id}).sort("created_at", -1))
    return render_template(
        "user_dashboard.html",
        requests_data=requests_data,
        services=list(SERVICE_KEYWORDS.keys()),
    )


@app.post("/api/classify")
@login_required("user")
def classify_api():
    text = request.json.get("message", "")
    service = classify_issue(text)
    return jsonify({"service": service})


@app.post("/request-service")
@login_required("user")
def request_service():
    issue_text = request.form["issue_text"]
    location = request.form["location"].strip()
    service = request.form.get("service") or classify_issue(issue_text)

    technician = find_technician(service, location)
    service_request = {
        "user_id": ObjectId(session["user_id"]),
        "user_name": session.get("name"),
        "service": service,
        "issue_text": issue_text,
        "location": location,
        "gps": request.form.get("gps", ""),
        "status": "Pending" if technician else "Waiting for assignment",
        "assigned_technician_name": technician["name"] if technician else "Not assigned",
        "assigned_technician_id": technician["_id"] if technician else None,
        "created_at": datetime.utcnow(),
    }

    db.service_requests.insert_one(service_request)
    flash("Service request submitted successfully.", "success")
    return redirect(url_for("dashboard"))


@app.post("/request/<request_id>/status")
@login_required("technician")
def update_status(request_id):
    technician = db.technicians.find_one({"user_id": ObjectId(session["user_id"])})
    if not technician:
        flash("Technician profile not found.", "error")
        return redirect(url_for("dashboard"))

    new_status = request.form.get("status", "In Progress")
    update_result = db.service_requests.update_one(
        {"_id": ObjectId(request_id), "assigned_technician_id": technician["_id"]},
        {"$set": {"status": new_status}},
    )
    if update_result.modified_count:
        flash("Service status updated.", "success")
    else:
        flash("Unable to update status for this request.", "error")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
