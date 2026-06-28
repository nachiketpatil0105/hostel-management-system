from flask import Flask, jsonify, render_template

from web.routes.auth import auth_bp
from web.routes.admin import admin_bp
from web.routes.student import student_bp
from web.routes.warden import warden_bp
from web.routes.security import security_bp


def create_app():
    """Application Factory"""

    app = Flask(__name__)

    app.config["JSON_SORT_KEYS"] = False

    # API blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(student_bp, url_prefix="/api/student")
    app.register_blueprint(warden_bp, url_prefix="/api/warden")
    app.register_blueprint(security_bp, url_prefix="/api/security")

    # ==========================================
    # PUBLIC ROUTES
    # ==========================================

    @app.route("/")
    def home():
        return render_template("login.html")

    @app.route("/login")
    def login():
        return render_template("login.html")

    @app.route("/health")
    def health():
        return jsonify({"status": "healthy"}), 200

    # ==========================================
    # ADMIN PAGE ROUTES
    # ==========================================

    @app.route("/admin/dashboard")
    def admin_dashboard():
        return render_template("admin/dashboard.html")

    @app.route("/admin/users")
    def admin_users():
        return render_template("admin/users.html")

    @app.route("/admin/hostels")
    def admin_hostels():
        return render_template("admin/hostels.html")

    @app.route("/admin/rooms")
    def admin_rooms():
        return render_template("admin/rooms.html")

    @app.route("/admin/payments")
    def admin_payments():
        return render_template("admin/payments.html")

    @app.route("/admin/complaints")
    def admin_complaints():
        return render_template("admin/complaints.html")

    @app.route("/admin/visitors")
    def admin_visitors():
        return render_template("admin/visitors.html")

    @app.route("/admin/movement")
    def admin_movement():
        return render_template("admin/movement.html")

    @app.route("/admin/complaint-types")
    def admin_complaint_types():
        return render_template("admin/complaint-types.html")

    @app.route("/admin/maintenance")
    def admin_maintenance():
        return render_template("admin/maintenance.html")

    # ==========================================
    # WARDEN PAGE ROUTES
    # ==========================================

    @app.route("/warden/dashboard")
    def warden_dashboard():
        return render_template("warden/dashboard.html")

    @app.route("/warden/students")
    def warden_students():
        return render_template("warden/students.html")

    @app.route("/warden/complaints")
    def warden_complaints():
        return render_template("warden/complaints.html")

    @app.route("/warden/inventory")
    def warden_inventory():
        return render_template("warden/inventory.html")

    @app.route("/warden/visitors")
    def warden_visitors():
        return render_template("warden/visitors.html")

    @app.route("/warden/maintenance")
    def warden_maintenance():
        return render_template("warden/maintenance.html")

    # ==========================================
    # SECURITY PAGE ROUTES
    # ==========================================

    @app.route("/security/dashboard")
    def security_dashboard():
        return render_template("security/dashboard.html")

    @app.route("/security/visitors")
    def security_visitors():
        return render_template("security/visitors.html")

    @app.route("/security/movement")
    def security_movement():
        return render_template("security/movement.html")

    # ==========================================
    # STUDENT PAGE ROUTES
    # ==========================================

    @app.route("/student/profile")
    def student_profile():
        return render_template("student/profile.html")

    @app.route("/student/complaint")
    def student_complaint():
        return render_template("student/complaint.html")

    @app.route("/student/payments")
    def student_payments():
        return render_template("student/payments.html")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )