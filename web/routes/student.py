from flask import Blueprint, request, jsonify
import mysql.connector

from web.utils import get_db_connection, token_required, log_audit


student_bp = Blueprint("student", __name__)


# ==========================================================
# VIEW / UPDATE PROFILE
# ==========================================================

@student_bp.route("/profile/<int:member_id>", methods=["GET", "PUT"])
@token_required
def manage_profile(current_user, member_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        is_admin = current_user["role"].lower() == "admin"
        is_warden = current_user["role"].lower() == "warden"

        if not is_admin and current_user["member_id"] != member_id:
            if is_warden:
                cursor.execute("""
                    SELECT 1
                    FROM room_allocations ra
                    JOIN rooms r ON ra.room_id = r.room_id
                    JOIN floors f ON r.floor_id = f.floor_id
                    JOIN hostels h ON f.hostel_id = h.hostel_id
                    WHERE ra.member_id = %s AND ra.status = 'ACTIVE' AND h.warden_member_id = %s
                """, (member_id, current_user["member_id"]))

                if not cursor.fetchone():
                    return jsonify({"success": False, "message": "Access denied."}), 403
            else:
                return jsonify({"success": False, "message": "Access denied."}), 403


        if request.method == "GET":

            cursor.execute("""
                SELECT
                    m.member_id,
                    CONCAT(m.first_name, ' ', m.last_name) AS full_name,
                    m.email,
                    m.phone,
                    m.gender,
                    sp.roll_number,
                    sp.department,
                    sp.programme,
                    sp.academic_year,
                    h.hostel_name,
                    r.room_number
                FROM members m
                LEFT JOIN student_profiles sp ON m.member_id = sp.member_id
                LEFT JOIN room_allocations ra ON m.member_id = ra.member_id AND ra.status = 'ACTIVE'
                LEFT JOIN rooms r ON ra.room_id = r.room_id
                LEFT JOIN floors f ON r.floor_id = f.floor_id
                LEFT JOIN hostels h ON f.hostel_id = h.hostel_id
                WHERE m.member_id = %s
            """, (member_id,))

            profile = cursor.fetchone()

            if not profile:
                return jsonify({"success": False, "message": "Student not found."}), 404

            cursor.execute("""
                SELECT
                    c.complaint_id,
                    ct.complaint_type,
                    c.title,
                    c.priority,
                    c.status,
                    c.created_at
                FROM complaints c
                JOIN complaint_types ct ON c.complaint_type_id = ct.complaint_type_id
                WHERE c.student_member_id = %s
                ORDER BY c.created_at DESC
            """, (member_id,))

            complaints = cursor.fetchall()

            cursor.execute("""
                SELECT
                    fs.fee_name,
                    p.amount_paid,
                    p.payment_status,
                    p.paid_at
                FROM payments p
                JOIN fee_structures fs ON p.fee_id = fs.fee_id
                WHERE p.member_id = %s
                ORDER BY p.paid_at DESC
            """, (member_id,))

            payments = cursor.fetchall()

            return jsonify({
                "success": True,
                "profile": profile,
                "complaints": complaints,
                "payments": payments
            }), 200


        data = request.get_json()

        phone = data.get("phone", "").strip()

        if not phone:
            return jsonify({"success": False, "message": "Phone number cannot be empty."}), 400

        if not phone.isdigit() or len(phone) != 10:
            return jsonify({"success": False, "message": "Invalid phone number format. Must be 10 digits."}), 400

        cursor.execute(
            "SELECT member_id FROM members WHERE phone = %s AND member_id != %s",
            (phone, member_id)
        )
        if cursor.fetchone():
            return jsonify({"success": False, "message": "This phone number is already in use."}), 409

        cursor.execute("""
            UPDATE members
            SET phone = %s
            WHERE member_id = %s
        """, (phone, member_id))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Updated profile {member_id}",
            entity_name="members",
            entity_id=member_id
        )

        return jsonify({"success": True, "message": "Profile updated successfully."}), 200

    except mysql.connector.Error as err:

        conn.rollback()

        return jsonify({"success": False, "message": str(err)}), 500

    finally:

        cursor.close()
        conn.close()

# ==========================================================
# GET COMPLAINT TYPES (for dropdown)
# ==========================================================

@student_bp.route("/complaint-types", methods=["GET"])
@token_required
def get_complaint_types(current_user):

    if current_user["role"].lower() != "student":
        return jsonify({"success": False, "message": "Access denied."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT complaint_type_id, complaint_type, description
            FROM complaint_types
            ORDER BY complaint_type
        """)
        types = cursor.fetchall()
        return jsonify({"success": True, "complaint_types": types}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# RAISE COMPLAINT
# ==========================================================

@student_bp.route("/complaints", methods=["POST"])
@token_required
def raise_complaint(current_user):

    if current_user["role"].lower() != "student":
        return jsonify({
            "success": False,
            "message": "Only students can raise complaints."
        }), 403

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # Validate complaint_type_id exists
        cursor.execute(
            "SELECT complaint_type_id FROM complaint_types WHERE complaint_type_id = %s",
            (data["complaint_type_id"],)
        )
        if not cursor.fetchone():
            return jsonify({"success": False, "message": "Invalid complaint type."}), 400

        cursor.execute("""
            INSERT INTO complaints
            (student_member_id, complaint_type_id, priority, status, title, description)
            VALUES (%s, %s, %s, 'OPEN', %s, %s)
        """, (
            current_user["member_id"],
            data["complaint_type_id"],
            data["priority"],
            data["title"],
            data["description"]
        ))

        complaint_id = cursor.lastrowid
        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            "Raised complaint",
            entity_name="complaints",
            entity_id=complaint_id
        )

        return jsonify({
            "success": True,
            "message": "Complaint submitted successfully."
        }), 201

    except mysql.connector.Error as err:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": str(err)
        }), 500

    finally:

        cursor.close()
        conn.close()