from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash
from web.utils import get_db_connection, token_required, log_audit

admin_bp = Blueprint('admin', __name__)


# ==========================================================
# ADMIN DASHBOARD
# ==========================================================

@admin_bp.route("/dashboard", methods=["GET"])
@token_required
def admin_dashboard(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("SELECT COUNT(*) AS total_students FROM student_profiles")
        total_students = cursor.fetchone()["total_students"]

        cursor.execute("SELECT COUNT(*) AS total_wardens FROM warden_profiles")
        total_wardens = cursor.fetchone()["total_wardens"]

        cursor.execute("SELECT COUNT(*) AS total_security FROM security_profiles")
        total_security = cursor.fetchone()["total_security"]

        cursor.execute("SELECT COUNT(*) AS total_hostels FROM hostels")
        total_hostels = cursor.fetchone()["total_hostels"]

        cursor.execute("SELECT COUNT(*) AS total_rooms FROM rooms")
        total_rooms = cursor.fetchone()["total_rooms"]

        cursor.execute("SELECT COUNT(*) AS available_rooms FROM rooms WHERE status = 'AVAILABLE'")
        available_rooms = cursor.fetchone()["available_rooms"]

        cursor.execute("SELECT COUNT(*) AS pending_complaints FROM complaints WHERE status IN ('OPEN', 'IN_PROGRESS')")
        pending_complaints = cursor.fetchone()["pending_complaints"]

        log_audit(current_user["member_id"], current_user["role"], "Viewed Admin Dashboard")

        return jsonify({
            "success": True,
            "statistics": {
                "students": total_students,
                "wardens": total_wardens,
                "security": total_security,
                "hostels": total_hostels,
                "rooms": total_rooms,
                "available_rooms": available_rooms,
                "pending_complaints": pending_complaints
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET ALL USERS
# ==========================================================

@admin_bp.route("/users", methods=["GET"])
@token_required
def get_users(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        conditions = []
        params = []

        role_filter = request.args.get("role", "").strip()
        if role_filter:
            conditions.append("r.role_name = %s")
            params.append(role_filter.capitalize())

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        cursor.execute(f"""
            SELECT
                m.member_id,
                CONCAT(m.first_name, ' ', m.last_name) AS full_name,
                r.role_name,
                m.email,
                m.phone,
                m.gender
            FROM members m
            JOIN roles r ON m.role_id = r.role_id
            {where}
            ORDER BY r.role_name, m.first_name
        """, params)

        users = cursor.fetchall()

        log_audit(current_user["member_id"], current_user["role"], "Viewed Users")

        return jsonify({"success": True, "users": users}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# CREATE USER
# ==========================================================

@admin_bp.route("/users", methods=["POST"])
@token_required
def create_user(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        conn.start_transaction()

        cursor.execute("""
            SELECT role_id FROM roles WHERE role_name = %s
        """, (data["role"].capitalize(),))

        role = cursor.fetchone()

        if not role:
            return jsonify({"success": False, "message": "Invalid role."}), 400

        role_id = role["role_id"]

        cursor.execute("""
            INSERT INTO members
            (role_id, first_name, last_name, email, phone, gender, dob)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            role_id,
            data["first_name"],
            data["last_name"],
            data["email"],
            data["phone"],
            data["gender"],
            data["dob"]
        ))

        member_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO user_credentials (member_id, username, password_hash)
            VALUES (%s, %s, %s)
        """, (
            member_id,
            data["username"],
            generate_password_hash(data["password"])
        ))

        role_upper = data["role"].upper()

        if role_upper == "STUDENT":

            cursor.execute("""
                INSERT INTO student_profiles
                (member_id, roll_number, department, programme, academic_year,
                guardian_name, guardian_phone, blood_group)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                member_id,
                data["roll_number"],
                data["department"],
                data["programme"],
                data["academic_year"],
                data["guardian_name"],
                data["guardian_phone"],
                data["blood_group"]
            ))

        elif role_upper in ["WARDEN", "SECURITY"]:

            cursor.execute("""
                INSERT INTO employee_profiles
                (member_id, employee_code, designation, joining_date)
                VALUES (%s, %s, %s, %s)
            """, (
                member_id,
                data["employee_code"],
                data["designation"],
                data["joining_date"]
            ))

            if role_upper == "WARDEN":

                cursor.execute("""
                    INSERT INTO warden_profiles (member_id, office_phone)
                    VALUES (%s, %s)
                """, (member_id, data.get("office_phone")))

            else:

                cursor.execute("""
                    INSERT INTO security_profiles
                    (member_id, agency, shift, gate_assigned)
                    VALUES (%s, %s, %s, %s)
                """, (
                    member_id,
                    data.get("agency"),
                    data["shift"],
                    data.get("gate_assigned")
                ))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Created {data['role']} ({member_id})",
            entity_name="members",
            entity_id=member_id
        )

        return jsonify({
            "success": True,
            "message": "User created successfully.",
            "member_id": member_id
        }), 201

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# UPDATE USER
# ==========================================================

@admin_bp.route("/users/<int:member_id>", methods=["PUT"])
@token_required
def update_user(current_user, member_id):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        conn.start_transaction()

        cursor.execute("""
            SELECT r.role_name
            FROM members m
            JOIN roles r ON m.role_id = r.role_id
            WHERE m.member_id = %s
        """, (member_id,))

        user = cursor.fetchone()

        if not user:
            return jsonify({"success": False, "message": "User not found."}), 404

        role = user["role_name"].upper()

        cursor.execute("""
            UPDATE members
            SET first_name = %s, last_name = %s, email = %s,
                phone = %s, gender = %s, dob = %s
            WHERE member_id = %s
        """, (
            data["first_name"],
            data["last_name"],
            data["email"],
            data["phone"],
            data["gender"],
            data["dob"],
            member_id
        ))

        if role == "STUDENT":

            cursor.execute("""
                UPDATE student_profiles
                SET department = %s, programme = %s, academic_year = %s,
                    guardian_name = %s, guardian_phone = %s, blood_group = %s
                WHERE member_id = %s
            """, (
                data["department"],
                data["programme"],
                data["academic_year"],
                data["guardian_name"],
                data["guardian_phone"],
                data["blood_group"],
                member_id
            ))

        elif role == "WARDEN":

            cursor.execute("""
                UPDATE warden_profiles SET office_phone = %s WHERE member_id = %s
            """, (data.get("office_phone"), member_id))

        elif role == "SECURITY":

            cursor.execute("""
                UPDATE security_profiles
                SET agency = %s, shift = %s, gate_assigned = %s
                WHERE member_id = %s
            """, (
                data.get("agency"),
                data["shift"],
                data.get("gate_assigned"),
                member_id
            ))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Updated User {member_id}",
            entity_name="members",
            entity_id=member_id
        )

        return jsonify({"success": True, "message": "User updated successfully."}), 200

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# DELETE USER (HARD DELETE)
# ==========================================================

@admin_bp.route("/users/<int:member_id>", methods=["DELETE"])
@token_required
def delete_user(current_user, member_id):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    if current_user["member_id"] == member_id:
        return jsonify({"success": False, "message": "You cannot delete your own account."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("SELECT member_id FROM members WHERE member_id = %s", (member_id,))

        if not cursor.fetchone():
            return jsonify({"success": False, "message": "User not found."}), 404

        cursor.execute("DELETE FROM members WHERE member_id = %s", (member_id,))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Deleted User {member_id}",
            entity_name="members",
            entity_id=member_id
        )

        return jsonify({"success": True, "message": "User deleted successfully."}), 200

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET HOSTELS
# ==========================================================

@admin_bp.route("/hostels", methods=["GET"])
@token_required
def get_hostels(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                h.hostel_id,
                h.hostel_name,
                h.hostel_type,
                h.address,
                h.total_floors,
                CONCAT(w.first_name, ' ', w.last_name) AS warden,
                GROUP_CONCAT(
                    CONCAT(s.first_name, ' ', s.last_name)
                    ORDER BY s.first_name
                    SEPARATOR ', '
                ) AS security_staff
            FROM hostels h
            LEFT JOIN members w ON h.warden_member_id = w.member_id
            LEFT JOIN hostel_security_assignments hsa
                ON h.hostel_id = hsa.hostel_id AND hsa.status = 'ACTIVE'
            LEFT JOIN members s ON hsa.member_id = s.member_id
            GROUP BY
                h.hostel_id, h.hostel_name, h.hostel_type,
                h.address, h.total_floors, w.first_name, w.last_name
            ORDER BY h.hostel_name
        """)

        hostels = cursor.fetchall()

        return jsonify({"success": True, "hostels": hostels}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# CREATE HOSTEL
# ==========================================================

@admin_bp.route("/hostels", methods=["POST"])
@token_required
def create_hostel(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        conn.start_transaction()

        cursor.execute("""
            INSERT INTO hostels
            (hostel_name, hostel_type, address, total_floors, warden_member_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data["hostel_name"],
            data["hostel_type"],
            data.get("address"),
            data["total_floors"],
            data.get("warden_member_id")
        ))

        hostel_id = cursor.lastrowid

        security_member_id = data.get("security_member_id")
        if security_member_id:
            cursor.execute("""
                INSERT INTO hostel_security_assignments (hostel_id, member_id, status)
                VALUES (%s, %s, 'ACTIVE')
            """, (hostel_id, security_member_id))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Created Hostel {data['hostel_name']}",
            entity_name="hostels",
            entity_id=hostel_id
        )

        return jsonify({
            "success": True,
            "message": "Hostel created successfully.",
            "hostel_id": hostel_id
        }), 201

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# UPDATE HOSTEL
# ==========================================================

@admin_bp.route("/hostels/<int:hostel_id>", methods=["PUT"])
@token_required
def update_hostel(current_user, hostel_id):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            UPDATE hostels
            SET hostel_name = %s, hostel_type = %s,
                address = %s, total_floors = %s, warden_member_id = %s
            WHERE hostel_id = %s
        """, (
            data["hostel_name"],
            data["hostel_type"],
            data.get("address"),
            data["total_floors"],
            data.get("warden_member_id"),
            hostel_id
        ))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Updated Hostel {hostel_id}",
            entity_name="hostels",
            entity_id=hostel_id
        )

        return jsonify({"success": True, "message": "Hostel updated successfully."}), 200

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# ASSIGN SECURITY TO HOSTEL
# ==========================================================

@admin_bp.route("/hostels/<int:hostel_id>/security", methods=["POST"])
@token_required
def assign_security(current_user, hostel_id):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            INSERT INTO hostel_security_assignments (hostel_id, member_id, status)
            VALUES (%s, %s, 'ACTIVE')
        """, (hostel_id, data["member_id"]))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Assigned Security {data['member_id']} to Hostel {hostel_id}"
        )

        return jsonify({"success": True, "message": "Security guard assigned successfully."}), 201

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# REMOVE SECURITY FROM HOSTEL
# ==========================================================

@admin_bp.route("/hostels/<int:hostel_id>/security/<int:member_id>", methods=["DELETE"])
@token_required
def remove_security(current_user, hostel_id, member_id):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            UPDATE hostel_security_assignments
            SET status = 'INACTIVE'
            WHERE hostel_id = %s AND member_id = %s AND status = 'ACTIVE'
        """, (hostel_id, member_id))

        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"success": False, "message": "Active assignment not found."}), 404

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Removed Security {member_id} from Hostel {hostel_id}"
        )

        return jsonify({"success": True, "message": "Security guard removed successfully."}), 200

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET FLOORS
# ==========================================================

@admin_bp.route("/floors", methods=["GET"])
@token_required
def get_floors(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                f.floor_id,
                h.hostel_name,
                f.floor_number
            FROM floors f
            JOIN hostels h ON f.hostel_id = h.hostel_id
            ORDER BY h.hostel_name, f.floor_number
        """)

        floors = cursor.fetchall()

        return jsonify({"success": True, "floors": floors}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET ROOMS
# ==========================================================

@admin_bp.route("/rooms", methods=["GET"])
@token_required
def get_rooms(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                r.room_id,
                h.hostel_name,
                f.floor_number,
                r.room_number,
                r.room_type,
                r.capacity,
                vo.occupied_count,
                vo.available_slots,
                r.status
            FROM rooms r
            JOIN floors f ON r.floor_id = f.floor_id
            JOIN hostels h ON f.hostel_id = h.hostel_id
            JOIN v_room_occupancy vo ON r.room_id = vo.room_id
            ORDER BY h.hostel_name, f.floor_number, r.room_number
        """)

        rooms = cursor.fetchall()

        return jsonify({"success": True, "rooms": rooms}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# CREATE ROOM
# ==========================================================

@admin_bp.route("/rooms", methods=["POST"])
@token_required
def create_room(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            INSERT INTO rooms (floor_id, room_number, room_type, capacity, status)
            VALUES (%s, %s, %s, %s, 'AVAILABLE')
        """, (
            data["floor_id"],
            data["room_number"],
            data["room_type"],
            data["capacity"]
        ))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Created Room {data['room_number']}",
            entity_name="rooms"
        )

        return jsonify({"success": True, "message": "Room created successfully."}), 201

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# ALLOCATE ROOM
# ==========================================================

@admin_bp.route("/allocate-room", methods=["POST"])
@token_required
def allocate_room(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        conn.start_transaction()

        # Bug 6 fix: verify member_id is actually a student
        cursor.execute("""
            SELECT member_id FROM student_profiles WHERE member_id = %s
        """, (data["member_id"],))

        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Provided member is not a student."}), 400

        cursor.execute("""
            SELECT 
                r.capacity, 
                r.status,
                (SELECT COUNT(*) FROM room_allocations ra WHERE ra.room_id = r.room_id AND ra.status = 'ACTIVE') as occupied_count
            FROM rooms r
            WHERE r.room_id = %s
            FOR UPDATE
        """, (data["room_id"],))

        room = cursor.fetchone()

        if not room:
            return jsonify({"success": False, "message": "Room not found."}), 404

        if room["status"] == "UNDER_MAINTENANCE":
            return jsonify({"success": False, "message": "Room is under maintenance."}), 400

        if room["occupied_count"] >= room["capacity"]:
            return jsonify({"success": False, "message": "Room is already full."}), 400

        cursor.execute("""
            UPDATE room_allocations
            SET status = 'VACATED', vacated_on = CURDATE()
            WHERE member_id = %s AND status = 'ACTIVE'
        """, (data["member_id"],))

        cursor.execute("""
            INSERT INTO room_allocations (member_id, room_id, allocated_on, status)
            VALUES (%s, %s, CURDATE(), 'ACTIVE')
        """, (data["member_id"], data["room_id"]))

        cursor.execute("""
            UPDATE rooms
            SET status = CASE
                WHEN (
                    SELECT COUNT(*) FROM room_allocations
                    WHERE room_id = %s AND status = 'ACTIVE'
                ) >= capacity THEN 'FULL'
                ELSE 'AVAILABLE'
            END
            WHERE room_id = %s
        """, (data["room_id"], data["room_id"]))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Allocated Room {data['room_id']} to Student {data['member_id']}",
            entity_name="room_allocations"
        )

        return jsonify({"success": True, "message": "Room allocated successfully."}), 201

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET ALL COMPLAINTS (Admin)
# ==========================================================

@admin_bp.route("/complaints", methods=["GET"])
@token_required
def get_all_complaints(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        conditions = []
        params = []

        status_filter = request.args.get("status", "").strip()
        if status_filter:
            conditions.append("c.status = %s")
            params.append(status_filter)

        hostel_filter = request.args.get("hostel_id", "").strip()
        if hostel_filter:
            conditions.append("h.hostel_id = %s")
            params.append(hostel_filter)

        priority_filter = request.args.get("priority", "").strip()
        if priority_filter:
            conditions.append("c.priority = %s")
            params.append(priority_filter)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        cursor.execute(f"""
            SELECT
                c.complaint_id,
                CONCAT(m.first_name, ' ', m.last_name) AS student_name,
                h.hostel_name,
                r.room_number,
                ct.complaint_type,
                c.title,
                c.priority,
                c.status,
                c.created_at,
                c.resolved_at
            FROM complaints c
            JOIN members m ON c.student_member_id = m.member_id
            JOIN complaint_types ct ON c.complaint_type_id = ct.complaint_type_id
            LEFT JOIN room_allocations ra ON m.member_id = ra.member_id AND ra.status = 'ACTIVE'
            LEFT JOIN rooms r ON ra.room_id = r.room_id
            LEFT JOIN floors f ON r.floor_id = f.floor_id
            LEFT JOIN hostels h ON f.hostel_id = h.hostel_id
            {where}
            ORDER BY c.created_at DESC
        """, params)

        complaints = cursor.fetchall()

        return jsonify({"success": True, "complaints": complaints}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# MANAGE COMPLAINT TYPES (Admin)
# ==========================================================

@admin_bp.route("/complaint-types", methods=["GET", "POST"])
@token_required
def manage_complaint_types(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        if request.method == "GET":
            cursor.execute("SELECT * FROM complaint_types ORDER BY complaint_type")
            return jsonify({"success": True, "complaint_types": cursor.fetchall()}), 200

        data = request.get_json()
        cursor.execute("""
            INSERT INTO complaint_types (complaint_type, description)
            VALUES (%s, %s)
        """, (data["complaint_type"], data.get("description", "")))
        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            "Created complaint type",
            entity_name="complaint_types"
        )

        return jsonify({"success": True, "message": "Complaint type created."}), 201

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


@admin_bp.route("/complaint-types/<int:type_id>", methods=["DELETE"])
@token_required
def delete_complaint_type(current_user, type_id):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("DELETE FROM complaint_types WHERE complaint_type_id = %s", (type_id,))
        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Deleted complaint type {type_id}",
            entity_name="complaint_types",
            entity_id=type_id
        )

        return jsonify({"success": True, "message": "Complaint type deleted."}), 200

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET ALL VISITOR LOGS (Admin)
# ==========================================================

@admin_bp.route("/visitors", methods=["GET"])
@token_required
def get_all_visitors(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        conditions = []
        params = []

        status_filter = request.args.get("status", "").strip()
        if status_filter:
            conditions.append("vl.status = %s")
            params.append(status_filter)

        hostel_filter = request.args.get("hostel_id", "").strip()
        if hostel_filter:
            conditions.append("h.hostel_id = %s")
            params.append(hostel_filter)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        cursor.execute(f"""
            SELECT
                vl.log_id,
                CONCAT(v.first_name, ' ', v.last_name) AS visitor_name,
                v.phone,
                v.id_type,
                v.id_number,
                CONCAT(m.first_name, ' ', m.last_name) AS student_name,
                h.hostel_name,
                r.room_number,
                vl.purpose,
                vl.check_in,
                vl.check_out,
                vl.status
            FROM visitor_logs vl
            JOIN visitors v ON vl.visitor_id = v.visitor_id
            JOIN members m ON vl.student_member_id = m.member_id
            LEFT JOIN room_allocations ra ON m.member_id = ra.member_id AND ra.status = 'ACTIVE'
            LEFT JOIN rooms r ON ra.room_id = r.room_id
            LEFT JOIN floors f ON r.floor_id = f.floor_id
            LEFT JOIN hostels h ON f.hostel_id = h.hostel_id
            {where}
            ORDER BY vl.check_in DESC
        """, params)

        return jsonify({"success": True, "visitors": cursor.fetchall()}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET ALL MOVEMENT LOGS (Admin)
# ==========================================================

@admin_bp.route("/movement", methods=["GET"])
@token_required
def get_all_movement(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        conditions = []
        params = []

        direction_filter = request.args.get("direction", "").strip()
        if direction_filter:
            conditions.append("ml.direction = %s")
            params.append(direction_filter)

        hostel_filter = request.args.get("hostel_id", "").strip()
        if hostel_filter:
            conditions.append("h.hostel_id = %s")
            params.append(hostel_filter)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        cursor.execute(f"""
            SELECT
                ml.movement_id,
                CONCAT(m.first_name, ' ', m.last_name) AS student_name,
                m.phone,
                h.hostel_name,
                r.room_number,
                ml.direction,
                ml.exit_time,
                ml.return_time,
                ml.gate_name,
                ml.remarks
            FROM movement_logs ml
            JOIN members m ON ml.member_id = m.member_id
            LEFT JOIN room_allocations ra ON m.member_id = ra.member_id AND ra.status = 'ACTIVE'
            LEFT JOIN rooms r ON ra.room_id = r.room_id
            LEFT JOIN floors f ON r.floor_id = f.floor_id
            LEFT JOIN hostels h ON f.hostel_id = h.hostel_id
            {where}
            ORDER BY ml.exit_time DESC
        """, params)

        return jsonify({"success": True, "movement_logs": cursor.fetchall()}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET ALL MAINTENANCE REQUESTS (Admin)
# ==========================================================

@admin_bp.route("/maintenance", methods=["GET"])
@token_required
def get_all_maintenance(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        conditions = []
        params = []

        status_filter = request.args.get("status", "").strip()
        if status_filter:
            conditions.append("im.status = %s")
            params.append(status_filter)

        hostel_filter = request.args.get("hostel_id", "").strip()
        if hostel_filter:
            conditions.append("f.hostel_id = %s")
            params.append(hostel_filter)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        cursor.execute(f"""
            SELECT
                im.maintenance_id,
                im.item_id,
                ic.category_name,
                ii.asset_tag,
                r.room_number,
                h.hostel_name,
                im.maintenance_type,
                im.issue_description,
                im.status,
                im.reported_at,
                im.completed_at,
                im.remarks,
                CONCAT(reporter.first_name, ' ', reporter.last_name) AS reported_by_name,
                CONCAT(assignee.first_name, ' ', assignee.last_name) AS assigned_to_name
            FROM inventory_maintenance im
            JOIN inventory_items ii ON im.item_id = ii.item_id
            JOIN inventory_categories ic ON ii.category_id = ic.category_id
            JOIN rooms r ON ii.room_id = r.room_id
            JOIN floors f ON r.floor_id = f.floor_id
            JOIN hostels h ON f.hostel_id = h.hostel_id
            JOIN members reporter ON im.reported_by = reporter.member_id
            LEFT JOIN members assignee ON im.assigned_to = assignee.member_id
            {where}
            ORDER BY im.reported_at DESC
        """, params)

        maintenance = cursor.fetchall()

        return jsonify({"success": True, "maintenance": maintenance}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# UPDATE MAINTENANCE REQUEST (Admin)
# ==========================================================

@admin_bp.route("/maintenance/<int:maintenance_id>", methods=["PUT"])
@token_required
def update_maintenance(current_user, maintenance_id):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT maintenance_id FROM inventory_maintenance WHERE maintenance_id = %s
        """, (maintenance_id,))

        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Maintenance request not found."}), 404

        status = data["status"]
        assigned_to = data.get("assigned_to")

        cursor.execute("""
            UPDATE inventory_maintenance
            SET
                status = %s,
                assigned_to = %s,
                completed_at = CASE
                    WHEN %s = 'COMPLETED' THEN NOW()
                    ELSE NULL
                END
            WHERE maintenance_id = %s
        """, (status, assigned_to, status, maintenance_id))

        # If completed, restore item to IN_USE
        if status == "COMPLETED":
            cursor.execute("""
                UPDATE inventory_items ii
                JOIN inventory_maintenance im ON ii.item_id = im.item_id
                SET ii.status = 'IN_USE'
                WHERE im.maintenance_id = %s
            """, (maintenance_id,))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Updated Maintenance Request {maintenance_id}",
            entity_name="inventory_maintenance",
            entity_id=maintenance_id
        )

        return jsonify({"success": True, "message": "Maintenance request updated successfully."}), 200

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET FEE STRUCTURES
# ==========================================================

@admin_bp.route("/fee-structures", methods=["GET"])
@token_required
def get_fee_structures(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT fee_id, fee_name, academic_year, semester, amount, due_date
            FROM fee_structures
            ORDER BY academic_year DESC, semester
        """)

        return jsonify({"success": True, "fee_structures": cursor.fetchall()}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET PAYMENTS
# ==========================================================

@admin_bp.route("/payments", methods=["GET"])
@token_required
def get_payments(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        conditions = []
        params = []

        status_filter = request.args.get("payment_status", "").strip()
        if status_filter:
            conditions.append("p.payment_status = %s")
            params.append(status_filter)

        member_filter = request.args.get("member_id", "").strip()
        if member_filter:
            conditions.append("p.member_id = %s")
            params.append(member_filter)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        cursor.execute(f"""
            SELECT
                p.payment_id,
                CONCAT(m.first_name, ' ', m.last_name) AS student_name,
                fs.fee_name,
                fs.academic_year,
                fs.semester,
                p.amount_paid,
                p.payment_method,
                p.payment_status,
                p.transaction_id,
                p.receipt_number,
                p.paid_at
            FROM payments p
            JOIN members m ON p.member_id = m.member_id
            JOIN fee_structures fs ON p.fee_id = fs.fee_id
            {where}
            ORDER BY p.paid_at DESC
        """, params)

        payments = cursor.fetchall()

        return jsonify({"success": True, "payments": payments}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# ADD PAYMENT
# ==========================================================

@admin_bp.route("/payments", methods=["POST"])
@token_required
def add_payment(current_user):

    if current_user["role"].lower() != "admin":
        return jsonify({"success": False, "message": "Admin access required."}), 403

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            INSERT INTO payments
            (member_id, fee_id, allocation_id, amount_paid,
            payment_method, transaction_id, receipt_number, payment_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data["member_id"],
            data["fee_id"],
            data.get("allocation_id"),
            data["amount_paid"],
            data["payment_method"],
            data.get("transaction_id"),
            data.get("receipt_number"),
            data.get("payment_status", "PENDING")
        ))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            "Recorded Payment",
            entity_name="payments"
        )

        return jsonify({"success": True, "message": "Payment recorded successfully."}), 201

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()