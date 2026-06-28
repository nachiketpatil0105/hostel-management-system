from flask import Blueprint, jsonify, request
from web.utils import get_db_connection, token_required, log_audit

security_bp = Blueprint('security', __name__)


# ==========================================================
# SECURITY DASHBOARD
# ==========================================================

@security_bp.route("/dashboard", methods=["GET"])
@token_required
def security_dashboard(current_user):

    if current_user["role"].lower() != "security":
        return jsonify({"success": False, "message": "Security access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT h.hostel_id, h.hostel_name
            FROM hostels h
            JOIN hostel_security_assignments hsa ON h.hostel_id = hsa.hostel_id
            WHERE hsa.member_id = %s AND hsa.status = 'ACTIVE'
        """, (current_user["member_id"],))

        hostel = cursor.fetchone()

        if not hostel:
            return jsonify({
                "success": True,
                "hostel_name": "Not Assigned",
                "active_visitors": [],
                "outside_students": []
            }), 200

        hostel_id = hostel["hostel_id"]

        cursor.execute("""
            SELECT
                vl.log_id,
                CONCAT(v.first_name, ' ', v.last_name) AS visitor_name,
                vl.purpose,
                CONCAT(m.first_name, ' ', m.last_name) AS student_name,
                r.room_number,
                vl.check_in
            FROM visitor_logs vl
            JOIN visitors v ON vl.visitor_id = v.visitor_id
            JOIN members m ON vl.student_member_id = m.member_id
            JOIN room_allocations ra ON m.member_id = ra.member_id AND ra.status = 'ACTIVE'
            JOIN rooms r ON ra.room_id = r.room_id
            JOIN floors f ON r.floor_id = f.floor_id
            WHERE f.hostel_id = %s AND vl.status = 'ACTIVE'
        """, (hostel_id,))

        active_visitors = cursor.fetchall()

        cursor.execute("""
            SELECT
                ml.movement_id,
                CONCAT(m.first_name, ' ', m.last_name) AS student_name,
                m.phone,
                ml.remarks,
                ml.exit_time
            FROM movement_logs ml
            JOIN student_profiles sp ON ml.member_id = sp.member_id
            JOIN members m ON sp.member_id = m.member_id
            JOIN room_allocations ra ON m.member_id = ra.member_id AND ra.status = 'ACTIVE'
            JOIN rooms r ON ra.room_id = r.room_id
            JOIN floors f ON r.floor_id = f.floor_id
            WHERE f.hostel_id = %s AND ml.direction = 'OUT' AND ml.return_time IS NULL
        """, (hostel_id,))

        outside_students = cursor.fetchall()

        return jsonify({
            "success": True,
            "hostel_name": hostel["hostel_name"],
            "active_visitors": active_visitors,
            "outside_students": outside_students
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET STUDENTS IN HOSTEL (for dropdown search)
# ==========================================================

@security_bp.route("/hostel-students", methods=["GET"])
@token_required
def get_hostel_students(current_user):

    if current_user["role"].lower() not in ["security", "warden"]:
        return jsonify({"success": False, "message": "Unauthorized."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT hostel_id FROM hostel_security_assignments
            WHERE member_id = %s AND status = 'ACTIVE'
        """, (current_user["member_id"],))

        assignment = cursor.fetchone()

        if not assignment:
            return jsonify({"success": True, "students": []}), 200

        hostel_id = assignment["hostel_id"]

        cursor.execute("""
            SELECT
                m.member_id,
                CONCAT(m.first_name, ' ', m.last_name) AS student_name,
                sp.roll_number,
                r.room_number
            FROM members m
            JOIN student_profiles sp ON m.member_id = sp.member_id
            JOIN room_allocations ra ON m.member_id = ra.member_id AND ra.status = 'ACTIVE'
            JOIN rooms r ON ra.room_id = r.room_id
            JOIN floors f ON r.floor_id = f.floor_id
            WHERE f.hostel_id = %s
            ORDER BY m.first_name
        """, (hostel_id,))

        students = cursor.fetchall()
        return jsonify({"success": True, "students": students}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# VISITOR CHECK-IN
# ==========================================================

@security_bp.route("/visitors", methods=["POST"])
@token_required
def add_new_visitor(current_user):

    if current_user["role"].lower() not in ["security", "warden"]:
        return jsonify({"success": False, "message": "Unauthorized."}), 403

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        role = current_user["role"].lower()
        
        if role == "warden":
            cursor.execute("SELECT hostel_id FROM hostels WHERE warden_member_id = %s", (current_user["member_id"],))
        else:
            cursor.execute("SELECT hostel_id FROM hostel_security_assignments WHERE member_id = %s AND status = 'ACTIVE'", (current_user["member_id"],))

        assignment = cursor.fetchone()

        if not assignment:
            return jsonify({"success": False, "message": "You are not assigned to any hostel."}), 403

        hostel_id = assignment["hostel_id"]

        cursor.execute("""
            SELECT 1 FROM room_allocations ra
            JOIN rooms r ON ra.room_id = r.room_id
            JOIN floors f ON r.floor_id = f.floor_id
            WHERE ra.member_id = %s AND ra.status = 'ACTIVE' AND f.hostel_id = %s
        """, (data["student_member_id"], hostel_id))

        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Student does not belong to your assigned hostel."}), 403

        cursor.execute("""
            SELECT visitor_id FROM visitors
            WHERE id_type = %s AND id_number = %s
        """, (data["id_type"], data["id_number"]))

        visitor = cursor.fetchone()

        if visitor:
            visitor_id = visitor["visitor_id"]
        else:
            cursor.execute("""
                INSERT INTO visitors (first_name, last_name, phone, id_type, id_number)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                data["first_name"],
                data["last_name"],
                data["phone"],
                data["id_type"],
                data["id_number"]
            ))
            visitor_id = cursor.lastrowid

        cursor.execute("""
            SELECT log_id FROM visitor_logs
            WHERE visitor_id = %s AND status = 'ACTIVE'
        """, (visitor_id,))

        if cursor.fetchone():
            return jsonify({
                "success": False,
                "message": "This visitor is already checked in and has not yet exited."
            }), 409

        cursor.execute("""
            INSERT INTO visitor_logs
            (visitor_id, student_member_id, logged_by, purpose, check_in, status)
            VALUES (%s, %s, %s, %s, NOW(), 'ACTIVE')
        """, (
            visitor_id,
            data["student_member_id"],
            current_user["member_id"],
            data["purpose"]
        ))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            "Visitor Check-In",
            entity_name="visitor_logs"
        )

        return jsonify({"success": True, "message": "Visitor checked in successfully."}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# VISITOR CHECK-OUT
# ==========================================================

@security_bp.route("/visitors/<int:log_id>/exit", methods=["PUT"])
@token_required
def mark_visitor_exited(current_user, log_id):

    if current_user["role"].lower() not in ["security", "warden"]:
        return jsonify({"success": False, "message": "Unauthorized."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            UPDATE visitor_logs
            SET check_out = NOW(), status = 'COMPLETED'
            WHERE log_id = %s AND status = 'ACTIVE'
        """, (log_id,))

        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"success": False, "message": "Visitor already checked out or log not found."}), 404

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Visitor Checkout - Log {log_id}",
            entity_name="visitor_logs",
            entity_id=log_id
        )

        return jsonify({"success": True, "message": "Visitor checked out successfully."}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# LOG STUDENT EXIT
# ==========================================================

@security_bp.route("/movement/<int:member_id>/exit", methods=["POST"])
@token_required
def log_student_exit(current_user, member_id):

    if current_user["role"].lower() not in ["security", "warden"]:
        return jsonify({"success": False, "message": "Unauthorized."}), 403

    data = request.get_json() or {}

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        role = current_user["role"].lower()
        
        if role == "warden":
            cursor.execute("SELECT hostel_id FROM hostels WHERE warden_member_id = %s", (current_user["member_id"],))
        else:
            cursor.execute("SELECT hostel_id FROM hostel_security_assignments WHERE member_id = %s AND status = 'ACTIVE'", (current_user["member_id"],))

        assignment = cursor.fetchone()

        if not assignment:
            return jsonify({"success": False, "message": "You are not assigned to any hostel."}), 403

        hostel_id = assignment["hostel_id"]

        cursor.execute("""
            SELECT 1 FROM room_allocations ra
            JOIN rooms r ON ra.room_id = r.room_id
            JOIN floors f ON r.floor_id = f.floor_id
            WHERE ra.member_id = %s AND ra.status = 'ACTIVE' AND f.hostel_id = %s
        """, (data["student_member_id"], hostel_id))

        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Student does not belong to your assigned hostel."}), 403

        cursor.execute("""
            SELECT member_id FROM student_profiles WHERE member_id = %s FOR UPDATE
        """, (member_id,))

        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Student not found."}), 404

        cursor.execute("""
            SELECT movement_id FROM movement_logs
            WHERE member_id = %s AND direction = 'OUT' AND return_time IS NULL
        """, (member_id,))

        if cursor.fetchone():
            return jsonify({
                "success": False,
                "message": "Student already has an unresolved exit. Log return first."
            }), 409

        cursor.execute("""
            INSERT INTO movement_logs
            (member_id, direction, exit_time, gate_name, recorded_by, remarks)
            VALUES (%s, 'OUT', NOW(), %s, %s, %s)
        """, (
            member_id,
            data.get("gate_name", "Main Gate"),
            current_user["member_id"],
            data.get("remarks", "")
        ))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Student Exit - Member {member_id}",
            entity_name="movement_logs"
        )

        return jsonify({"success": True, "message": "Student exit recorded successfully."}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# LOG STUDENT RETURN (ENTRY)
# ==========================================================

@security_bp.route("/movement/<int:member_id>/return", methods=["POST"])
@token_required
def mark_student_returned(current_user, member_id):

    if current_user["role"].lower() not in ["security", "warden"]:
        return jsonify({"success": False, "message": "Unauthorized."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT member_id FROM student_profiles WHERE member_id = %s FOR UPDATE
        """, (member_id,))

        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Student not found."}), 404

        # Bug 5 fix: ensure the student belongs to this user's assigned hostel.
        # Wardens use hostels.warden_member_id; security use hostel_security_assignments.
        role = current_user["role"].lower()
        if role == "warden":
            cursor.execute("""
                SELECT hostel_id FROM hostels WHERE warden_member_id = %s
            """, (current_user["member_id"],))
        else:
            cursor.execute("""
                SELECT hostel_id FROM hostel_security_assignments
                WHERE member_id = %s AND status = 'ACTIVE'
            """, (current_user["member_id"],))

        assignment = cursor.fetchone()

        if not assignment:
            return jsonify({"success": False, "message": "You are not assigned to any hostel."}), 403

        hostel_id = assignment["hostel_id"]

        cursor.execute("""
            SELECT ra.member_id
            FROM room_allocations ra
            JOIN rooms r ON ra.room_id = r.room_id
            JOIN floors f ON r.floor_id = f.floor_id
            WHERE ra.member_id = %s AND ra.status = 'ACTIVE' AND f.hostel_id = %s
        """, (member_id, hostel_id))

        if not cursor.fetchone():
            return jsonify({
                "success": False,
                "message": "Student does not belong to your assigned hostel."
            }), 403

        cursor.execute("""
            UPDATE movement_logs
            SET return_time = NOW(), direction = 'IN'
            WHERE member_id = %s AND direction = 'OUT' AND return_time IS NULL
            ORDER BY exit_time DESC
            LIMIT 1
        """, (member_id,))

        if cursor.rowcount == 0:
            return jsonify({"success": False, "message": "No active exit log found for this student."}), 404

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Student Entry - Member {member_id}",
            entity_name="movement_logs"
        )

        return jsonify({"success": True, "message": "Student entry recorded successfully."}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# SEARCH STUDENT
# ==========================================================

@security_bp.route("/search-student", methods=["GET"])
@token_required
def search_student(current_user):

    if current_user["role"].lower() not in ["security", "warden"]:
        return jsonify({"success": False, "message": "Unauthorized."}), 403

    search = request.args.get("q", "").strip()

    if len(search) < 2:
        return jsonify({"success": True, "students": []}), 200

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT hostel_id FROM hostel_security_assignments
            WHERE member_id = %s AND status = 'ACTIVE'
        """, (current_user["member_id"],))

        assignment = cursor.fetchone()

        if not assignment:
            return jsonify({"success": True, "students": []}), 200

        hostel_id = assignment["hostel_id"]
        like = f"%{search}%"

        cursor.execute("""
            SELECT
                m.member_id,
                CONCAT(m.first_name, ' ', m.last_name) AS student_name,
                sp.roll_number,
                m.phone,
                r.room_number
            FROM members m
            JOIN student_profiles sp ON m.member_id = sp.member_id
            JOIN room_allocations ra ON m.member_id = ra.member_id AND ra.status = 'ACTIVE'
            JOIN rooms r ON ra.room_id = r.room_id
            JOIN floors f ON r.floor_id = f.floor_id
            WHERE f.hostel_id = %s
            AND (
                m.first_name LIKE %s
                OR m.last_name LIKE %s
                OR sp.roll_number LIKE %s
                OR r.room_number LIKE %s
                OR m.phone LIKE %s
            )
            ORDER BY m.first_name
            LIMIT 10
        """, (hostel_id, like, like, like, like, like))

        students = cursor.fetchall()

        return jsonify({"success": True, "students": students}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()