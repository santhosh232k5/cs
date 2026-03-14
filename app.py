from datetime import datetime, timedelta
from functools import wraps
import math
import os

from bson import ObjectId
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from pymongo import MongoClient
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(mongo_uri)
db = client[os.getenv("MONGO_DB", "smart_home_service_assistant")]

STATUS_FLOW = [
    "Pending",
    "Worker Assigned",
    "Worker On The Way",
    "Job In Progress",
    "Completed",
]

USER_VISIBLE_STATUSES = STATUS_FLOW
WORKER_STATUS_UPDATES = ["Worker On The Way", "Job In Progress", "Completed"]

SERVICE_KEYWORDS = {
    "Electrical repair": ["electrical", "wiring", "switch", "socket", "light", "power", "fuse"],
    "Plumbing": ["pipe", "water", "leak", "drain", "tap", "toilet", "plumbing"],
    "Carpentry": ["wood", "door", "cabinet", "furniture", "carpentry", "shelf"],
    "Painting": ["paint", "wall", "repaint", "stain", "painting"],
    "Masonry": ["brick", "cement", "tile", "masonry", "concrete"],
    "Cleaning": ["clean", "dust", "sanitize", "deep cleaning", "washing"],
    "Appliance repair": ["fridge", "ac", "washing machine", "microwave", "appliance", "repair"],
    "Beauty Services": ["salon", "facial", "beauty", "hair", "spa", "makeup"],
    "Home Repair": ["repair", "fix", "renovation", "maintenance", "broken"],
}


def classify_issue(text: str) -> str:
    text_lower = (text or "").lower()
    best_service = "Home Repair"
    max_hits = 0

    for service, keywords in SERVICE_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in text_lower)
        if hits > max_hits:
            max_hits = hits
            best_service = service

    return best_service


def parse_coordinates(coordinate_text: str):
    try:
        lat_text, lng_text = [part.strip() for part in coordinate_text.split(",", 1)]
        return float(lat_text), float(lng_text)
    except (AttributeError, ValueError):
        return None


def geo_distance_km(origin, destination):
    if not origin or not destination:
        return float("inf")

    lat1, lng1 = origin
    lat2, lng2 = destination
    radius = 6371

    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def create_notification(user_id, role, title, message):
    db.notifications.insert_one(
        {
            "user_id": str(user_id),
            "role": role,
            "title": title,
            "message": message,
            "is_read": False,
            "created_at": datetime.utcnow(),
        }
    )


def get_current_user():
    if not session.get("user_id"):
        return None
    return db.users.find_one({"_id": ObjectId(session["user_id"])})


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


def find_best_worker(service: str, city: str, customer_gps: str):
    candidates = list(
        db.technicians.find(
            {
                "services": service,
                "availability": True,
            }
        )
    )
    if not candidates:
        return None

    city = city.strip().lower()
    preferred = [tech for tech in candidates if city in tech.get("cities", [])] or candidates
    customer_coordinates = parse_coordinates(customer_gps)

    ranked = []
    for tech in preferred:
        worker_coordinates = parse_coordinates(tech.get("base_gps", ""))
        distance = geo_distance_km(customer_coordinates, worker_coordinates)
        active_jobs = db.bookings.count_documents(
            {
                "worker_id": tech.get("_id"),
                "status": {"$in": ["Worker Assigned", "Worker On The Way", "Job In Progress"]},
            }
        )
        ranked.append((distance, active_jobs, -float(tech.get("rating", 4.5)), tech))

    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    return ranked[0][3]


def assign_worker_for_booking(booking):
    worker = find_best_worker(booking["service"], booking["city"], booking.get("gps", ""))
    if not worker:
        return None

    eta_minutes = 20 if booking.get("gps") and worker.get("base_gps") else 35
    assigned_eta = datetime.utcnow() + timedelta(minutes=eta_minutes)

    db.bookings.update_one(
        {"_id": booking["_id"]},
        {
            "$set": {
                "worker_id": worker["_id"],
                "status": "Worker Assigned",
                "eta_minutes": eta_minutes,
                "eta_at": assigned_eta,
                "worker_details": {
                    "name": worker["name"],
                    "phone": worker["phone"],
                    "rating": worker.get("rating", 4.5),
                    "profile_photo": worker.get(
                        "profile_photo",
                        "https://images.unsplash.com/photo-1544723795-3fb6469f5b39?auto=format&fit=crop&w=120&q=60",
                    ),
                },
                "updated_at": datetime.utcnow(),
            }
        },
    )

    create_notification(
        booking["user_id"],
        "user",
        "Worker assigned",
        f"{worker['name']} is assigned to your {booking['service']} booking.",
    )
    create_notification(
        worker["user_id"],
        "technician",
        "New job assigned",
        f"You received a new {booking['service']} job in {booking['city'].title()}.",
    )
    return worker


@app.route("/")
def home():
    return render_template("home.html", services=list(SERVICE_KEYWORDS.keys()))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        if db.users.find_one({"email": email}):
            flash("Email already exists.", "error")
            return redirect(url_for("register"))

        db.users.insert_one(
            {
                "name": request.form["name"].strip(),
                "email": email,
                "password": generate_password_hash(request.form["password"]),
                "phone": request.form["phone"].strip(),
                "role": "user",
                "created_at": datetime.utcnow(),
            }
        )
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
                "phone": request.form["phone"].strip(),
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
                "base_gps": request.form.get("base_gps", ""),
                "profile_photo": request.form.get(
                    "profile_photo",
                    "https://images.unsplash.com/photo-1544723795-3fb6469f5b39?auto=format&fit=crop&w=200&q=80",
                ),
                "availability": True,
                "rating": 4.7,
                "total_earnings": 0,
                "created_at": datetime.utcnow(),
            }
        )

        flash("Worker account created. Please login.", "success")
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
        flash(f"Welcome back, {user['name']}!", "success")
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
    current_user = get_current_user()

    if role == "technician":
        tech = db.technicians.find_one({"user_id": ObjectId(session["user_id"])})
        jobs = list(db.bookings.find({"worker_id": tech.get("_id") if tech else None}).sort("created_at", -1))
        earnings = sum(item.get("price", 0) for item in jobs if item.get("status") == "Completed")
        return render_template(
            "technician_dashboard.html",
            jobs=jobs,
            worker=tech,
            earnings=earnings,
            updatable_statuses=WORKER_STATUS_UPDATES,
        )

    bookings = list(db.bookings.find({"user_id": ObjectId(session["user_id"])}).sort("created_at", -1))
    active = [b for b in bookings if b.get("status") != "Completed"]
    history = [b for b in bookings if b.get("status") == "Completed"]
    return render_template(
        "user_dashboard.html",
        user=current_user,
        bookings=bookings,
        upcoming=active,
        history=history,
        services=list(SERVICE_KEYWORDS.keys()),
        status_flow=USER_VISIBLE_STATUSES,
    )


@app.post("/api/classify")
@login_required("user")
def classify_api():
    text = request.json.get("message", "")
    service = classify_issue(text)
    return jsonify({"service": service})


@app.post("/bookings")
@login_required("user")
def request_service():
    issue_text = request.form["issue_text"]
    city = request.form["location"].strip()
    service = request.form.get("service") or classify_issue(issue_text)

    booking = {
        "user_id": ObjectId(session["user_id"]),
        "user_name": session.get("name"),
        "service": service,
        "issue_text": issue_text,
        "city": city,
        "gps": request.form.get("gps", ""),
        "address": request.form.get("address", ""),
        "status": "Pending",
        "worker_id": None,
        "worker_details": None,
        "eta_minutes": None,
        "price": int(request.form.get("estimated_price") or 699),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    booking_id = db.bookings.insert_one(booking).inserted_id
    booking["_id"] = booking_id

    create_notification(session["user_id"], "user", "Booking confirmed", "Your request has been confirmed.")

    worker = assign_worker_for_booking(booking)
    if worker:
        flash("Booking created and worker assigned.", "success")
    else:
        flash("Booking created. We will assign a worker soon.", "success")

    return redirect(url_for("dashboard"))


@app.post("/bookings/<booking_id>/cancel")
@login_required("user")
def cancel_booking(booking_id):
    booking = db.bookings.find_one({"_id": ObjectId(booking_id), "user_id": ObjectId(session["user_id"])})
    if not booking:
        flash("Booking not found.", "error")
        return redirect(url_for("dashboard"))

    db.bookings.update_one(
        {"_id": booking["_id"]},
        {"$set": {"status": "Cancelled", "updated_at": datetime.utcnow()}},
    )
    create_notification(session["user_id"], "user", "Booking cancelled", "Your booking was cancelled.")
    if booking.get("worker_details"):
        worker = db.technicians.find_one({"_id": booking.get("worker_id")})
        if worker:
            create_notification(worker["user_id"], "technician", "Job cancelled", "A customer cancelled the assigned job.")
    flash("Booking cancelled.", "success")
    return redirect(url_for("dashboard"))


@app.post("/bookings/<booking_id>/accept")
@login_required("technician")
def worker_accept_job(booking_id):
    worker = db.technicians.find_one({"user_id": ObjectId(session["user_id"])})
    booking = db.bookings.find_one({"_id": ObjectId(booking_id), "worker_id": worker.get("_id") if worker else None})
    if not booking:
        flash("Assigned job not found.", "error")
        return redirect(url_for("dashboard"))

    db.bookings.update_one(
        {"_id": booking["_id"]},
        {"$set": {"status": "Worker On The Way", "updated_at": datetime.utcnow()}},
    )
    create_notification(booking["user_id"], "user", "Worker on the way", "Your worker is now on the way.")
    flash("Job accepted and marked as on the way.", "success")
    return redirect(url_for("dashboard"))


@app.post("/bookings/<booking_id>/reject")
@login_required("technician")
def worker_reject_job(booking_id):
    worker = db.technicians.find_one({"user_id": ObjectId(session["user_id"])})
    booking = db.bookings.find_one({"_id": ObjectId(booking_id), "worker_id": worker.get("_id") if worker else None})
    if not booking:
        flash("Assigned job not found.", "error")
        return redirect(url_for("dashboard"))

    db.bookings.update_one(
        {"_id": booking["_id"]},
        {
            "$set": {
                "status": "Pending",
                "worker_id": None,
                "worker_details": None,
                "eta_minutes": None,
                "updated_at": datetime.utcnow(),
            }
        },
    )
    assign_worker_for_booking(booking)
    flash("Job rejected. Reassigning another worker.", "success")
    return redirect(url_for("dashboard"))


@app.post("/bookings/<booking_id>/status")
@login_required("technician")
def update_status(booking_id):
    new_status = request.form.get("status")
    if new_status not in WORKER_STATUS_UPDATES:
        flash("Invalid status.", "error")
        return redirect(url_for("dashboard"))

    worker = db.technicians.find_one({"user_id": ObjectId(session["user_id"])})
    booking = db.bookings.find_one({"_id": ObjectId(booking_id), "worker_id": worker.get("_id") if worker else None})
    if not booking:
        flash("Assigned job not found.", "error")
        return redirect(url_for("dashboard"))

    db.bookings.update_one(
        {"_id": booking["_id"]},
        {"$set": {"status": new_status, "updated_at": datetime.utcnow()}},
    )

    notice = {
        "Worker On The Way": "Worker on the way",
        "Job In Progress": "Job in progress",
        "Completed": "Job completed",
    }[new_status]
    create_notification(booking["user_id"], "user", notice, f"Your {booking['service']} booking is now {new_status}.")
    if new_status == "Completed":
        db.technicians.update_one(
            {"_id": worker["_id"]},
            {"$inc": {"total_earnings": booking.get("price", 0)}},
        )
        create_notification(session["user_id"], "technician", "Payment received", "Payment for completed job is processed.")

    flash("Booking status updated.", "success")
    return redirect(url_for("dashboard"))


@app.get("/api/notifications")
@login_required()
def notifications_api():
    notices = list(
        db.notifications.find({"user_id": session["user_id"]}).sort("created_at", -1).limit(15)
    )
    unread_count = db.notifications.count_documents({"user_id": session["user_id"], "is_read": False})

    payload = [
        {
            "id": str(item["_id"]),
            "title": item["title"],
            "message": item["message"],
            "is_read": item["is_read"],
            "created_at": item["created_at"].strftime("%d %b %I:%M %p"),
        }
        for item in notices
    ]
    return jsonify({"items": payload, "unread": unread_count})


@app.post("/api/notifications/read")
@login_required()
def notifications_read_api():
    db.notifications.update_many({"user_id": session["user_id"], "is_read": False}, {"$set": {"is_read": True}})
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True)
