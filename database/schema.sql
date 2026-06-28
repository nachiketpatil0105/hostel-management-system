DROP DATABASE IF EXISTS stayease;
CREATE DATABASE stayease
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE stayease;


CREATE TABLE roles (
    role_id TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(30) NOT NULL UNIQUE
);


CREATE TABLE members (
    member_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    role_id TINYINT UNSIGNED NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    phone VARCHAR(15) NOT NULL UNIQUE,
    gender ENUM('Male', 'Female', 'Other') NOT NULL,
    dob DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_member_role
        FOREIGN KEY (role_id) REFERENCES roles (role_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);


CREATE TABLE user_credentials (
    member_id BIGINT UNSIGNED PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    last_login TIMESTAMP NULL,

    CONSTRAINT fk_credentials_member
        FOREIGN KEY (member_id) REFERENCES members (member_id)
        ON DELETE CASCADE
);


CREATE TABLE student_profiles (
    member_id BIGINT UNSIGNED PRIMARY KEY,
    roll_number VARCHAR(30) NOT NULL UNIQUE,
    department VARCHAR(100) NOT NULL,
    programme VARCHAR(100) NOT NULL,
    academic_year TINYINT UNSIGNED NOT NULL,
    guardian_name VARCHAR(100) NOT NULL,
    guardian_phone VARCHAR(15) NOT NULL,
    blood_group ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'),

    CONSTRAINT fk_student_member
        FOREIGN KEY (member_id) REFERENCES members (member_id)
        ON DELETE CASCADE
);


CREATE TABLE employee_profiles (
    member_id BIGINT UNSIGNED PRIMARY KEY,
    employee_code VARCHAR(25) NOT NULL UNIQUE,
    designation VARCHAR(60) NOT NULL,
    joining_date DATE NOT NULL,

    CONSTRAINT fk_employee_member
        FOREIGN KEY (member_id) REFERENCES members (member_id)
        ON DELETE CASCADE
);


CREATE TABLE warden_profiles (
    member_id BIGINT UNSIGNED PRIMARY KEY,
    office_phone VARCHAR(15),

    CONSTRAINT fk_warden_employee
        FOREIGN KEY (member_id) REFERENCES employee_profiles (member_id)
        ON DELETE CASCADE
);


CREATE TABLE security_profiles (
    member_id BIGINT UNSIGNED PRIMARY KEY,
    agency VARCHAR(100),
    shift ENUM('Morning', 'Evening', 'Night') NOT NULL,
    gate_assigned VARCHAR(50),

    CONSTRAINT fk_security_employee
        FOREIGN KEY (member_id) REFERENCES employee_profiles (member_id)
        ON DELETE CASCADE
);


CREATE TABLE hostels (
    hostel_id SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    hostel_name VARCHAR(80) NOT NULL UNIQUE,
    hostel_type ENUM('BOYS', 'GIRLS', 'MIXED') NOT NULL,
    address TEXT,
    total_floors TINYINT UNSIGNED NOT NULL,
    warden_member_id BIGINT UNSIGNED UNIQUE,

    CONSTRAINT fk_hostel_warden
        FOREIGN KEY (warden_member_id) REFERENCES warden_profiles (member_id)
        ON DELETE RESTRICT
);


CREATE TABLE hostel_security_assignments (
    assignment_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    hostel_id SMALLINT UNSIGNED NOT NULL,
    member_id BIGINT UNSIGNED NOT NULL,
    status ENUM('ACTIVE', 'INACTIVE') DEFAULT 'ACTIVE',

    CONSTRAINT fk_hsa_hostel
        FOREIGN KEY (hostel_id) REFERENCES hostels (hostel_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_hsa_security
        FOREIGN KEY (member_id) REFERENCES security_profiles (member_id)
        ON DELETE CASCADE
);


CREATE TABLE floors (
    floor_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    hostel_id SMALLINT UNSIGNED NOT NULL,
    floor_number TINYINT UNSIGNED NOT NULL,

    UNIQUE (hostel_id, floor_number),

    CONSTRAINT fk_floor_hostel
        FOREIGN KEY (hostel_id) REFERENCES hostels (hostel_id)
        ON DELETE CASCADE
);


CREATE TABLE rooms (
    room_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    floor_id INT UNSIGNED NOT NULL,
    room_number VARCHAR(20) NOT NULL,
    room_type ENUM('Single', 'Double', 'Triple', 'Quad') NOT NULL,
    capacity TINYINT UNSIGNED NOT NULL,
    status ENUM('AVAILABLE', 'FULL', 'UNDER_MAINTENANCE') DEFAULT 'AVAILABLE',

    UNIQUE (floor_id, room_number),

    CONSTRAINT chk_capacity
        CHECK (capacity > 0),

    CONSTRAINT fk_room_floor
        FOREIGN KEY (floor_id) REFERENCES floors (floor_id)
        ON DELETE CASCADE
);


CREATE TABLE room_allocations (
    allocation_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    member_id BIGINT UNSIGNED NOT NULL,
    room_id INT UNSIGNED NOT NULL,
    allocated_on DATE NOT NULL,
    vacated_on DATE NULL,
    status ENUM('ACTIVE', 'VACATED') DEFAULT 'ACTIVE',

    CONSTRAINT chk_vacated_after_allocated
        CHECK (vacated_on IS NULL OR vacated_on >= allocated_on),

    CONSTRAINT fk_allocation_student
        FOREIGN KEY (member_id) REFERENCES student_profiles (member_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_allocation_room
        FOREIGN KEY (room_id) REFERENCES rooms (room_id)
        ON DELETE RESTRICT
);

CREATE INDEX idx_active_allocations
    ON room_allocations (member_id, status);


CREATE VIEW v_room_occupancy AS
SELECT
    r.room_id,
    r.room_number,
    r.capacity,
    COUNT(ra.allocation_id) AS occupied_count,
    r.capacity - COUNT(ra.allocation_id) AS available_slots
FROM rooms r
LEFT JOIN room_allocations ra
    ON ra.room_id = r.room_id AND ra.status = 'ACTIVE'
GROUP BY r.room_id, r.room_number, r.capacity;


CREATE TABLE visitors (
    visitor_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50),
    phone VARCHAR(15) NOT NULL,
    id_type ENUM('AADHAR', 'PAN', 'PASSPORT', 'DRIVING_LICENSE', 'OTHER') NOT NULL,
    id_number VARCHAR(50) NOT NULL,

    UNIQUE (id_type, id_number)
);


CREATE TABLE visitor_logs (
    log_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    visitor_id BIGINT UNSIGNED NOT NULL,
    student_member_id BIGINT UNSIGNED NOT NULL,
    logged_by BIGINT UNSIGNED NOT NULL,
    purpose VARCHAR(255),
    check_in DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    check_out DATETIME NULL,
    status ENUM('ACTIVE', 'COMPLETED', 'DENIED') DEFAULT 'ACTIVE',

    CONSTRAINT chk_checkout_after_checkin
        CHECK (check_out IS NULL OR check_out > check_in),

    CONSTRAINT fk_vlog_visitor
        FOREIGN KEY (visitor_id) REFERENCES visitors (visitor_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_vlog_student
        FOREIGN KEY (student_member_id) REFERENCES student_profiles (member_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_vlog_logged_by
        FOREIGN KEY (logged_by) REFERENCES members (member_id)
        ON DELETE RESTRICT
);


CREATE TABLE movement_logs (
    movement_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    member_id BIGINT UNSIGNED NOT NULL,
    direction ENUM('IN', 'OUT') NOT NULL,
    exit_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    return_time DATETIME NULL,
    gate_name VARCHAR(50) NOT NULL,
    recorded_by BIGINT UNSIGNED NOT NULL,
    remarks VARCHAR(255),

    CONSTRAINT chk_return_after_exit
        CHECK (return_time IS NULL OR return_time > exit_time),

    CONSTRAINT fk_movement_member
        FOREIGN KEY (member_id) REFERENCES student_profiles (member_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_movement_recorded_by
        FOREIGN KEY (recorded_by) REFERENCES members (member_id)
        ON DELETE RESTRICT
);


CREATE TABLE complaint_types (
    complaint_type_id SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    complaint_type VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255)
);


CREATE TABLE complaints (
    complaint_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    student_member_id BIGINT UNSIGNED NOT NULL,
    complaint_type_id SMALLINT UNSIGNED NOT NULL,
    assigned_to BIGINT UNSIGNED NULL,
    priority ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') DEFAULT 'MEDIUM',
    status ENUM('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED') DEFAULT 'OPEN',
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,

    CONSTRAINT chk_resolved_at
        CHECK (status NOT IN ('RESOLVED', 'CLOSED') OR resolved_at IS NOT NULL),

    CONSTRAINT fk_complaint_student
        FOREIGN KEY (student_member_id) REFERENCES student_profiles (member_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_complaint_type
        FOREIGN KEY (complaint_type_id) REFERENCES complaint_types (complaint_type_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_complaint_assigned
        FOREIGN KEY (assigned_to) REFERENCES members (member_id)
        ON DELETE SET NULL
);


CREATE TABLE complaint_updates (
    update_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    complaint_id BIGINT UNSIGNED NOT NULL,
    updated_by BIGINT UNSIGNED NOT NULL,
    status ENUM('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED') NOT NULL,
    remarks TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_update_complaint
        FOREIGN KEY (complaint_id) REFERENCES complaints (complaint_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_update_member
        FOREIGN KEY (updated_by) REFERENCES members (member_id)
        ON DELETE RESTRICT
);


CREATE TABLE fee_structures (
    fee_id SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    fee_name VARCHAR(100) NOT NULL,
    academic_year SMALLINT UNSIGNED NOT NULL,
    semester ENUM('ODD', 'EVEN') NOT NULL,
    amount DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
    due_date DATE NOT NULL,

    UNIQUE (fee_name, academic_year, semester)
);


CREATE TABLE payments (
    payment_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    member_id BIGINT UNSIGNED NOT NULL,
    fee_id SMALLINT UNSIGNED NOT NULL,
    allocation_id BIGINT UNSIGNED NULL,
    amount_paid DECIMAL(10, 2) NOT NULL CHECK (amount_paid > 0),
    payment_method ENUM('CASH', 'UPI', 'CARD', 'BANK_TRANSFER') NOT NULL,
    transaction_id VARCHAR(100),
    receipt_number VARCHAR(50) UNIQUE,
    payment_status ENUM('PENDING', 'SUCCESS', 'FAILED', 'REFUNDED') DEFAULT 'PENDING',
    paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_payment_member
        FOREIGN KEY (member_id) REFERENCES student_profiles (member_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_payment_fee
        FOREIGN KEY (fee_id) REFERENCES fee_structures (fee_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_payment_allocation
        FOREIGN KEY (allocation_id) REFERENCES room_allocations (allocation_id)
        ON DELETE SET NULL
);


CREATE TABLE inventory_categories (
    category_id SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255)
);


CREATE TABLE inventory_items (
    item_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    room_id INT UNSIGNED NOT NULL,
    category_id SMALLINT UNSIGNED NOT NULL,
    asset_tag VARCHAR(50) NOT NULL UNIQUE,
    purchase_date DATE,
    item_condition ENUM('GOOD', 'FAIR', 'DAMAGED') DEFAULT 'GOOD',
    status ENUM('IN_USE', 'UNDER_REPAIR', 'REPLACED', 'DISCARDED') DEFAULT 'IN_USE',

    CONSTRAINT fk_inventory_room
        FOREIGN KEY (room_id) REFERENCES rooms(room_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_inventory_category
        FOREIGN KEY (category_id) REFERENCES inventory_categories(category_id)
        ON DELETE RESTRICT
);


CREATE TABLE inventory_maintenance (
    maintenance_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    item_id BIGINT UNSIGNED NOT NULL,
    reported_by BIGINT UNSIGNED NOT NULL,
    assigned_to BIGINT UNSIGNED NULL,
    maintenance_type ENUM('REPAIR', 'REPLACEMENT', 'INSPECTION') NOT NULL,
    issue_description TEXT NOT NULL,
    status ENUM('OPEN', 'IN_PROGRESS', 'COMPLETED') DEFAULT 'OPEN',
    reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    remarks TEXT,

    CONSTRAINT fk_maintenance_item
        FOREIGN KEY (item_id) REFERENCES inventory_items(item_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_maintenance_reporter
        FOREIGN KEY (reported_by) REFERENCES members(member_id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_maintenance_assignee
        FOREIGN KEY (assigned_to) REFERENCES members(member_id)
        ON DELETE SET NULL
);


CREATE TABLE audit_logs (
    audit_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    member_id BIGINT UNSIGNED NULL,
    action VARCHAR(100) NOT NULL,
    entity_name VARCHAR(50) NOT NULL,
    entity_id BIGINT UNSIGNED NULL,
    ip_address VARCHAR(45),
    action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_audit_member
        FOREIGN KEY (member_id) REFERENCES members (member_id)
        ON DELETE SET NULL
);


CREATE INDEX idx_members_role ON members (role_id);
CREATE INDEX idx_floor_hostel ON floors (hostel_id);
CREATE INDEX idx_rooms_floor ON rooms (floor_id);
CREATE INDEX idx_alloc_member ON room_allocations (member_id);
CREATE INDEX idx_alloc_room ON room_allocations (room_id);
CREATE INDEX idx_hsa_hostel ON hostel_security_assignments (hostel_id);
CREATE INDEX idx_hsa_member ON hostel_security_assignments (member_id);
CREATE INDEX idx_movement_member ON movement_logs (member_id);
CREATE INDEX idx_movement_exit ON movement_logs (exit_time);
CREATE INDEX idx_vlog_student ON visitor_logs (student_member_id);
CREATE INDEX idx_vlog_status ON visitor_logs (status);
CREATE INDEX idx_complaint_student ON complaints (student_member_id);
CREATE INDEX idx_complaint_status ON complaints (status);
CREATE INDEX idx_complaint_assigned ON complaints (assigned_to);
CREATE INDEX idx_payment_member ON payments (member_id);
CREATE INDEX idx_payment_status ON payments (payment_status);
CREATE INDEX idx_payment_allocation ON payments (allocation_id);
CREATE INDEX idx_inventory_room ON inventory_items (room_id);
CREATE INDEX idx_inventory_status ON inventory_items (status);
CREATE INDEX idx_audit_member ON audit_logs (member_id);
CREATE INDEX idx_audit_time ON audit_logs (action_time);
