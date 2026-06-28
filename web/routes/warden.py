from flask import Blueprint, jsonify, request
from web.utils import get_db_connection, token_required, log_audit

warden_bp = Blueprint("warden", __name__)


# ==========================================================
# WARDEN DASHBOARD
# ==========================================================

@warden_bp.route("/dashboard", methods=["GET"])
@token_required
def warden_dashboard(current_user):

    if current_user["role"].lower() != "warden":
        return jsonify({"success": False, "message": "Warden access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT hostel_id, hostel_name
            FROM hostels
            WHERE warden_member_id = %s
        """, (current_user["member_id"],))

        hostel = cursor.fetchone()

        if not hostel:
            return jsonify({"success": True, "hostel": None}), 200

        hostel_id = hostel["hostel_id"]

        cursor.execute("""
            SELECT COUNT(*) AS total_students
            FROM room_allocations ra
            JOIN rooms r ON ra.room_id = r.room_id
            JOIN floors f ON r.floor_id = f.floor_id
            WHERE f.hostel_id = %s AND ra.status = 'ACTIVE'
        """, (hostel_id,))
        total_students = cursor.fetchone()["total_students"]

        cursor.execute("""
            SELECT COUNT(*) AS pending
            FROM complaints c
            WHERE c.status IN ('OPEN', 'IN_PROGRESS')
            AND c.student_member_id IN (
                SELECT ra.member_id FROM room_allocations ra
                JOIN rooms r ON ra.room_id = r.room_id
                JOIN floors f ON r.floor_id = f.floor_id
                WHERE f.hostel_id = %s
            )
        """, (hostel_id,))
        pending = cursor.fetchone()["pending"]

        cursor.execute("""
            SELECT COUNT(*) AS available_rooms
            FROM rooms r
            JOIN floors f ON r.floor_id = f.floor_id
            WHERE f.hostel_id = %s AND r.status = 'AVAILABLE'
        """, (hostel_id,))
        available = cursor.fetchone()["available_rooms"]

        log_audit(current_user["member_id"], current_user["role"], "Viewed Warden Dashboard")

        return jsonify({
            "success": True,
            "hostel": hostel["hostel_name"],
            "statistics": {
                "students": total_students,
                "pending_complaints": pending,
                "available_rooms": available
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET STUDENTS
# ==========================================================

@warden_bp.route("/students", methods=["GET"])
@token_required
def get_students(current_user):

    if current_user["role"].lower() != "warden":
        return jsonify({"success": False, "message": "Warden access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT hostel_id FROM hostels WHERE warden_member_id = %s
        """, (current_user["member_id"],))

        hostel = cursor.fetchone()

        if not hostel:
            return jsonify({"success": True, "students": []}), 200

        hostel_id = hostel["hostel_id"]

        cursor.execute("""
            SELECT
                m.member_id,
                CONCAT(m.first_name, ' ', m.last_name) AS student_name,
                sp.roll_number,
                sp.department,
                sp.programme,
                sp.academic_year,
                m.phone,
                r.room_number
            FROM members m
            JOIN student_profiles sp ON m.member_id = sp.member_id
            JOIN room_allocations ra ON m.member_id = ra.member_id AND ra.status = 'ACTIVE'
            JOIN rooms r ON ra.room_id = r.room_id
            JOIN floors f ON r.floor_id = f.floor_id
            WHERE f.hostel_id = %s
            ORDER BY r.room_number, m.first_name
        """, (hostel_id,))

        students = cursor.fetchall()

        log_audit(current_user["member_id"], current_user["role"], "Viewed Student List")

        return jsonify({"success": True, "students": students}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET COMPLAINTS
# ==========================================================

@warden_bp.route("/complaints", methods=["GET"])
@token_required
def get_complaints(current_user):

    if current_user["role"].lower() != "warden":
        return jsonify({"success": False, "message": "Warden access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT hostel_id FROM hostels WHERE warden_member_id = %s
        """, (current_user["member_id"],))

        hostel = cursor.fetchone()

        if not hostel:
            return jsonify({"success": True, "complaints": []}), 200

        hostel_id = hostel["hostel_id"]

        # LEFT JOIN so complaints from students without current allocation still show
        cursor.execute("""
            SELECT
                c.complaint_id,
                CONCAT(m.first_name, ' ', m.last_name) AS student_name,
                ct.complaint_type,
                c.title,
                c.priority,
                c.status,
                c.created_at,
                r.room_number
            FROM complaints c
            JOIN members m ON c.student_member_id = m.member_id
            JOIN complaint_types ct ON c.complaint_type_id = ct.complaint_type_id
            LEFT JOIN room_allocations ra ON m.member_id = ra.member_id AND ra.status = 'ACTIVE'
            LEFT JOIN rooms r ON ra.room_id = r.room_id
            LEFT JOIN floors f ON r.floor_id = f.floor_id
            WHERE c.student_member_id IN (
                SELECT ra2.member_id FROM room_allocations ra2
                JOIN rooms r2 ON ra2.room_id = r2.room_id
                JOIN floors f2 ON r2.floor_id = f2.floor_id
                WHERE f2.hostel_id = %s
            )
            ORDER BY c.created_at DESC
        """, (hostel_id,))

        complaints = cursor.fetchall()

        log_audit(current_user["member_id"], current_user["role"], "Viewed Complaints")

        return jsonify({"success": True, "complaints": complaints}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# UPDATE COMPLAINT
# ==========================================================

@warden_bp.route("/complaints/<int:complaint_id>", methods=["PUT"])
@token_required
def update_complaint(current_user, complaint_id):

    if current_user["role"].lower() != "warden":
        return jsonify({"success": False, "message": "Warden access required."}), 403

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        status = data["status"]
        remarks = data.get("remarks", "")

        # Bug 3 fix: verify complaint belongs to a student in this warden's hostel
        cursor.execute("""
            SELECT c.complaint_id
            FROM complaints c
            JOIN room_allocations ra ON c.student_member_id = ra.member_id AND ra.status = 'ACTIVE'
            JOIN rooms r ON ra.room_id = r.room_id
            JOIN floors f ON r.floor_id = f.floor_id
            JOIN hostels h ON f.hostel_id = h.hostel_id
            WHERE c.complaint_id = %s AND h.warden_member_id = %s
        """, (complaint_id, current_user["member_id"]))

        if not cursor.fetchone():
            return jsonify({
                "success": False,
                "message": "This complaint does not belong to your hostel."
            }), 403

        # Bug 7 fix: clear resolved_at when re-opening so schema CHECK constraint is not violated
        cursor.execute("""
            UPDATE complaints
            SET
                status = %s,
                resolved_at = CASE
                    WHEN %s = 'RESOLVED' THEN NOW()
                    WHEN %s IN ('OPEN', 'IN_PROGRESS') THEN NULL
                    ELSE resolved_at
                END
            WHERE complaint_id = %s
        """, (status, status, status, complaint_id))

        cursor.execute("""
            INSERT INTO complaint_updates (complaint_id, updated_by, status, remarks)
            VALUES (%s, %s, %s, %s)
        """, (complaint_id, current_user["member_id"], status, remarks))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Updated Complaint {complaint_id}",
            entity_name="complaints",
            entity_id=complaint_id
        )

        return jsonify({"success": True, "message": "Complaint updated successfully."}), 200

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET INVENTORY
# ==========================================================

@warden_bp.route("/inventory", methods=["GET"])
@token_required
def get_inventory(current_user):

    if current_user["role"].lower() != "warden":
        return jsonify({"success": False, "message": "Warden access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT hostel_id FROM hostels WHERE warden_member_id = %s
        """, (current_user["member_id"],))

        hostel = cursor.fetchone()

        if not hostel:
            return jsonify({"success": True, "inventory": []}), 200

        hostel_id = hostel["hostel_id"]

        cursor.execute("""
            SELECT
                ii.item_id,
                ic.category_name,
                ii.asset_tag,
                r.room_number,
                ii.item_condition,
                ii.status
            FROM inventory_items ii
            JOIN inventory_categories ic ON ii.category_id = ic.category_id
            JOIN rooms r ON ii.room_id = r.room_id
            JOIN floors f ON r.floor_id = f.floor_id
            WHERE f.hostel_id = %s
            ORDER BY r.room_number, ic.category_name
        """, (hostel_id,))

        inventory = cursor.fetchall()

        return jsonify({"success": True, "inventory": inventory}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# REPORT INVENTORY ISSUE
# ==========================================================

@warden_bp.route("/inventory/<int:item_id>", methods=["PUT"])
@token_required
def report_inventory_issue(current_user, item_id):

    if current_user["role"].lower() != "warden":
        return jsonify({"success": False, "message": "Warden access required."}), 403

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        # Bug 4 fix: verify item belongs to a room in this warden's hostel
        cursor.execute("""
            SELECT ii.item_id
            FROM inventory_items ii
            JOIN rooms r ON ii.room_id = r.room_id
            JOIN floors f ON r.floor_id = f.floor_id
            JOIN hostels h ON f.hostel_id = h.hostel_id
            WHERE ii.item_id = %s AND h.warden_member_id = %s
        """, (item_id, current_user["member_id"]))

        if not cursor.fetchone():
            return jsonify({
                "success": False,
                "message": "This item does not belong to your hostel."
            }), 403

        cursor.execute("""
            INSERT INTO inventory_maintenance
            (item_id, reported_by, assigned_to, maintenance_type, issue_description, status, remarks)
            VALUES (%s, %s, NULL, %s, %s, 'OPEN', %s)
        """, (
            item_id,
            current_user["member_id"],
            data["maintenance_type"],
            data["issue_description"],
            data.get("remarks", "")
        ))

        cursor.execute("""
            UPDATE inventory_items SET status = 'UNDER_REPAIR' WHERE item_id = %s
        """, (item_id,))

        conn.commit()

        log_audit(
            current_user["member_id"],
            current_user["role"],
            f"Reported maintenance for Item {item_id}",
            entity_name="inventory_items",
            entity_id=item_id
        )

        return jsonify({"success": True, "message": "Maintenance request created successfully."}), 200

    except Exception as e:

        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET MAINTENANCE REQUESTS (warden's hostel)
# ==========================================================

@warden_bp.route("/maintenance", methods=["GET"])
@token_required
def get_maintenance(current_user):

    if current_user["role"].lower() != "warden":
        return jsonify({"success": False, "message": "Warden access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT hostel_id FROM hostels WHERE warden_member_id = %s
        """, (current_user["member_id"],))

        hostel = cursor.fetchone()

        if not hostel:
            return jsonify({"success": True, "maintenance": []}), 200

        hostel_id = hostel["hostel_id"]

        cursor.execute("""
            SELECT
                im.maintenance_id,
                im.item_id,
                ic.category_name,
                ii.asset_tag,
                r.room_number,
                im.maintenance_type,
                im.issue_description,
                im.status,
                im.reported_at,
                im.completed_at,
                im.remarks,
                CONCAT(m.first_name, ' ', m.last_name) AS reported_by_name
            FROM inventory_maintenance im
            JOIN inventory_items ii ON im.item_id = ii.item_id
            JOIN inventory_categories ic ON ii.category_id = ic.category_id
            JOIN rooms r ON ii.room_id = r.room_id
            JOIN floors f ON r.floor_id = f.floor_id
            JOIN members m ON im.reported_by = m.member_id
            WHERE f.hostel_id = %s
            ORDER BY im.reported_at DESC
        """, (hostel_id,))

        maintenance = cursor.fetchall()

        log_audit(current_user["member_id"], current_user["role"], "Viewed Maintenance Requests")

        return jsonify({"success": True, "maintenance": maintenance}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# GET VISITOR LOGS
# ==========================================================

@warden_bp.route("/visitors", methods=["GET"])
@token_required
def get_visitors(current_user):

    if current_user["role"].lower() != "warden":
        return jsonify({"success": False, "message": "Warden access required."}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT hostel_id FROM hostels WHERE warden_member_id = %s
        """, (current_user["member_id"],))

        hostel = cursor.fetchone()

        if not hostel:
            return jsonify({"success": True, "visitors": []}), 200

        hostel_id = hostel["hostel_id"]

        cursor.execute("""
            SELECT
                vl.log_id,
                CONCAT(v.first_name, ' ', v.last_name) AS visitor_name,
                v.phone,
                CONCAT(m.first_name, ' ', m.last_name) AS student_name,
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
            WHERE f.hostel_id = %s
            ORDER BY vl.check_in DESC
        """, (hostel_id,))

        visitors = cursor.fetchall()

        log_audit(current_user["member_id"], current_user["role"], "Viewed Visitor Logs")

        return jsonify({"success": True, "visitors": visitors}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        cursor.close()
        conn.close()