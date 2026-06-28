USE stayease;

-- ==========================================
-- 1. ROLES
-- ==========================================
INSERT INTO roles (role_id, role_name) VALUES
(1, 'Admin'),
(2, 'Student'),
(3, 'Warden'),
(4, 'Security');

-- ==========================================
-- 2. MEMBERS (1 Admin, 2 Wardens, 4 Security, 25 Students)
-- ==========================================
INSERT INTO members (member_id, role_id, first_name, last_name, email, phone, gender, dob) VALUES
(1, 1, 'System', 'Admin', 'admin@stayease.in', '9000000000', 'Male', '1990-01-01'),
(2, 3, 'Ramesh', 'Iyer', 'ramesh.iyer@stayease.in', '9000000001', 'Male', '1978-04-10'),
(3, 3, 'Geeta', 'Menon', 'geeta.menon@stayease.in', '9000000002', 'Female', '1982-11-20'),
(4, 4, 'Sunil', 'Patil', 'sunil.p@stayease.in', '9000000003', 'Male', '1990-07-22'),
(5, 4, 'Amit', 'Singh', 'amit.s@stayease.in', '9000000004', 'Male', '1988-05-15'),
(6, 4, 'Kavita', 'Rao', 'kavita.r@stayease.in', '9000000005', 'Female', '1992-08-10'),
(7, 4, 'Manoj', 'Kumar', 'manoj.k@stayease.in', '9000000006', 'Male', '1985-12-05');

-- Insert 25 Students (IDs 8 to 32)
INSERT INTO members (member_id, role_id, first_name, last_name, email, phone, gender, dob) VALUES
(8, 2, 'Arjun', 'Mehta', 'arjun@stayease.in', '9100000008', 'Male', '2005-03-15'),
(9, 2, 'Priya', 'Sharma', 'priya@stayease.in', '9100000009', 'Female', '2005-06-20'),
(10, 2, 'Vikram', 'Das', 'vikram@stayease.in', '9100000010', 'Male', '2004-09-01'),
(11, 2, 'Rahul', 'Verma', 'rahul@stayease.in', '9100000011', 'Male', '2003-12-12'),
(12, 2, 'Sneha', 'Reddy', 'sneha@stayease.in', '9100000012', 'Female', '2004-01-25'),
(13, 2, 'Aman', 'Gupta', 'aman@stayease.in', '9100000013', 'Male', '2005-08-08'),
(14, 2, 'Neha', 'Singh', 'neha@stayease.in', '9100000014', 'Female', '2003-11-30'),
(15, 2, 'Karan', 'Patel', 'karan@stayease.in', '9100000015', 'Male', '2004-05-18'),
(16, 2, 'Pooja', 'Joshi', 'pooja@stayease.in', '9100000016', 'Female', '2005-02-14'),
(17, 2, 'Rohan', 'Desai', 'rohan@stayease.in', '9100000017', 'Male', '2003-07-07'),
(18, 2, 'Anjali', 'Nair', 'anjali@stayease.in', '9100000018', 'Female', '2004-04-22'),
(19, 2, 'Vivek', 'Chawla', 'vivek@stayease.in', '9100000019', 'Male', '2005-10-10'),
(20, 2, 'Kirti', 'Agarwal', 'kirti@stayease.in', '9100000020', 'Female', '2003-09-05'),
(21, 2, 'Saurabh', 'Pandey', 'saurabh@stayease.in', '9100000021', 'Male', '2004-06-16'),
(22, 2, 'Riya', 'Sen', 'riya@stayease.in', '9100000022', 'Female', '2005-12-01'),
(23, 2, 'Tarun', 'Garg', 'tarun@stayease.in', '9100000023', 'Male', '2003-03-30'),
(24, 2, 'Meera', 'Rajput', 'meera@stayease.in', '9100000024', 'Female', '2004-08-20'),
(25, 2, 'Nitin', 'Bose', 'nitin@stayease.in', '9100000025', 'Male', '2005-01-11'),
(26, 2, 'Divya', 'Iyer', 'divya@stayease.in', '9100000026', 'Female', '2003-05-28'),
(27, 2, 'Yash', 'Trivedi', 'yash@stayease.in', '9100000027', 'Male', '2004-10-15'),
(28, 2, 'Shruti', 'Hasan', 'shruti@stayease.in', '9100000028', 'Female', '2005-07-09'),
(29, 2, 'Akash', 'Mishra', 'akash@stayease.in', '9100000029', 'Male', '2003-02-18'),
(30, 2, 'Tanya', 'Bhatia', 'tanya@stayease.in', '9100000030', 'Female', '2004-11-25'),
(31, 2, 'Dev', 'Kapoor', 'dev@stayease.in', '9100000031', 'Male', '2005-04-04'),
(32, 2, 'Isha', 'Malhotra', 'isha@stayease.in', '9100000032', 'Female', '2003-08-14');

-- ==========================================
-- 3. CREDENTIALS (All passwords: "password123")
-- ==========================================
INSERT INTO user_credentials (member_id, username, password_hash)
SELECT member_id, 
       CONCAT(LOWER(first_name), '.', LOWER(last_name)), 
       'scrypt:32768:8:1$AaOMFQUU0pOTnk5g$566976c024a3db2853d215205876b82f2e72a2057a8347272056dee4141e207fdd26e41b4fada6986d1a9a3d45f688adc01da35e27fd1e31c51b489eab9d5d9e'
FROM members;

-- Update the admin to just 'admin'
UPDATE user_credentials SET username = 'admin' WHERE member_id = 1;

-- ==========================================
-- 4. PROFILES (Employees & Students)
-- ==========================================
INSERT INTO employee_profiles (member_id, employee_code, designation, joining_date) VALUES
(2, 'EMP001', 'Chief Warden (Boys)', '2015-06-01'),
(3, 'EMP002', 'Chief Warden (Girls)', '2016-08-10'),
(4, 'EMP003', 'Security Guard', '2019-03-15'),
(5, 'EMP004', 'Security Guard', '2019-04-20'),
(6, 'EMP005', 'Security Guard', '2020-01-10'),
(7, 'EMP006', 'Security Guard', '2021-06-05');

INSERT INTO warden_profiles (member_id, office_phone) VALUES
(2, '02712-123456'),
(3, '02712-123457');

INSERT INTO security_profiles (member_id, agency, shift, gate_assigned) VALUES
(4, 'SafeGuard Pvt Ltd', 'Morning', 'Main Gate'),
(5, 'SafeGuard Pvt Ltd', 'Evening', 'Boys Hostel Gate'),
(6, 'SecureTech', 'Morning', 'Girls Hostel Gate'),
(7, 'SecureTech', 'Night', 'Main Gate');

-- Insert Student Profiles (Alternating departments & blood groups for variety)
INSERT INTO student_profiles (member_id, roll_number, department, programme, academic_year, guardian_name, guardian_phone, blood_group)
SELECT 
    member_id, 
    CONCAT('24CS', LPAD(member_id, 3, '0')), 
    IF(member_id % 2 = 0, 'Computer Science', 'Electrical Engg'), 
    'B.Tech', 
    (member_id % 4) + 1, 
    CONCAT('Guardian of ', first_name), 
    CONCAT('98000', LPAD(member_id, 5, '0')), 
    ELT((member_id % 4) + 1, 'A+', 'O+', 'B+', 'AB+')
FROM members WHERE role_id = 2;

-- ==========================================
-- 5. HOSTELS & INFRASTRUCTURE
-- ==========================================
INSERT INTO hostels (hostel_id, hostel_name, hostel_type, address, total_floors, warden_member_id) VALUES
(1, 'Brahmaputra Boys Hostel', 'BOYS', 'North Campus', 3, 2),
(2, 'Ganga Girls Hostel', 'GIRLS', 'South Campus', 3, 3);

INSERT INTO hostel_security_assignments (hostel_id, member_id, status) VALUES
(1, 5, 'ACTIVE'),
(2, 6, 'ACTIVE');

-- Floors (3 per hostel)
INSERT INTO floors (floor_id, hostel_id, floor_number) VALUES
(1, 1, 0), (2, 1, 1), (3, 1, 2), -- Boys
(4, 2, 0), (5, 2, 1), (6, 2, 2); -- Girls

-- Rooms (Setup for Concurrency Testing)
-- We mix Singles, Doubles, Triples. Some are FULL, some AVAILABLE.
INSERT INTO rooms (room_id, floor_id, room_number, room_type, capacity, status) VALUES
-- Boys Hostel Rooms (Floor 1 & 2)
(1, 1, '001', 'Single', 1, 'AVAILABLE'),
(2, 1, '002', 'Double', 2, 'AVAILABLE'),
(3, 1, '003', 'Triple', 3, 'AVAILABLE'),
(4, 1, '004', 'Double', 2, 'AVAILABLE'),
(5, 2, '101', 'Single', 1, 'UNDER_MAINTENANCE'),
(6, 2, '102', 'Triple', 3, 'FULL'),
(7, 2, '103', 'Double', 2, 'AVAILABLE'),
-- Girls Hostel Rooms (Floor 4 & 5)
(8, 4, '001', 'Single', 1, 'AVAILABLE'),
(9, 4, '002', 'Double', 2, 'AVAILABLE'),
(10, 4, '003', 'Triple', 3, 'AVAILABLE'),
(11, 4, '004', 'Double', 2, 'AVAILABLE'),
(12, 5, '101', 'Single', 1, 'AVAILABLE'),
(13, 5, '102', 'Triple', 3, 'FULL'),
(14, 5, '103', 'Double', 2, 'AVAILABLE');

-- ==========================================
-- 6. ROOM ALLOCATIONS (The Concurrency Trap)
-- ==========================================
-- CONCURRENCY TARGET: Rooms 2, 4, 7, 9, 11, 14 are 'Double' (Capacity 2). 
-- We assign exactly ONE student to them, leaving exactly ONE spot left. 
-- Locust scripts can test booking these exact rooms concurrently.
INSERT INTO room_allocations (member_id, room_id, allocated_on, status) VALUES
(8, 2, '2024-07-01', 'ACTIVE'),  -- Room 2 has 1 spot left
(10, 4, '2024-07-01', 'ACTIVE'), -- Room 4 has 1 spot left
(11, 7, '2024-07-01', 'ACTIVE'), -- Room 7 has 1 spot left
(13, 6, '2024-07-01', 'ACTIVE'), -- Room 6 is FULL (3/3)
(15, 6, '2024-07-01', 'ACTIVE'),
(17, 6, '2024-07-01', 'ACTIVE'),
(9, 9, '2024-07-01', 'ACTIVE'),  -- Room 9 has 1 spot left (Girls)
(12, 11, '2024-07-01', 'ACTIVE'),-- Room 11 has 1 spot left (Girls)
(14, 14, '2024-07-01', 'ACTIVE'),-- Room 14 has 1 spot left (Girls)
(16, 13, '2024-07-01', 'ACTIVE'),-- Room 13 is FULL (3/3)
(18, 13, '2024-07-01', 'ACTIVE'),
(20, 13, '2024-07-01', 'ACTIVE');

-- Sync Room Status for fully occupied rooms
UPDATE rooms SET status = 'FULL' WHERE room_id IN (6, 13);

-- ==========================================
-- 7. FEES & PAYMENTS (Load Testing Targets)
-- ==========================================
INSERT INTO fee_structures (fee_id, fee_name, academic_year, semester, amount, due_date) VALUES
(1, 'Hostel Accommodation Fee', 2024, 'ODD',  25000.00, '2024-07-31'),
(2, 'Hostel Accommodation Fee', 2024, 'EVEN', 25000.00, '2025-01-31'),
(3, 'Security Deposit',         2024, 'ODD',   5000.00, '2024-07-31');

-- CONCURRENCY TARGET: Massive blocks of PENDING payments.
-- Locust can simulate payment gateway callbacks hitting your API concurrently.
INSERT INTO payments (member_id, fee_id, allocation_id, amount_paid, payment_method, transaction_id, receipt_number, payment_status)
SELECT member_id, 1, NULL, 25000.00, 'UPI', CONCAT('UPI24', member_id, '001'), CONCAT('RCP-', member_id), 'SUCCESS'
FROM members WHERE role_id = 2 AND member_id <= 15;

-- The next 10 students have PENDING payments
INSERT INTO payments (member_id, fee_id, allocation_id, amount_paid, payment_method, transaction_id, receipt_number, payment_status)
SELECT member_id, 1, NULL, 25000.00, 'CARD', CONCAT('TXN-PEND-', member_id), NULL, 'PENDING'
FROM members WHERE role_id = 2 AND member_id > 15;

-- All students have pending Security Deposit fees
INSERT INTO payments (member_id, fee_id, allocation_id, amount_paid, payment_method, transaction_id, receipt_number, payment_status)
SELECT member_id, 3, NULL, 5000.00, 'BANK_TRANSFER', CONCAT('DEP-PEND-', member_id), NULL, 'PENDING'
FROM members WHERE role_id = 2;

-- ==========================================
-- 8. COMPLAINTS & WORKER QUEUES
-- ==========================================
INSERT INTO complaint_types (complaint_type_id, complaint_type, description) VALUES
(1, 'Plumbing', 'Leakages, blocked drains, water supply issues'),
(2, 'Electrical', 'Power cuts, faulty wiring, broken switches'),
(3, 'Furniture', 'Broken or missing furniture items'),
(4, 'Housekeeping', 'Cleanliness and sanitation issues'),
(5, 'Internet / WiFi', 'Network connectivity problems');

-- CONCURRENCY TARGET: Lots of OPEN complaints. 
-- In Locust, simulate Warden/Admin roles fetching OPEN complaints and trying to claim (IN_PROGRESS) them concurrently.
INSERT INTO complaints (student_member_id, complaint_type_id, assigned_to, priority, status, title, description)
SELECT 
    member_id, 
    (member_id % 5) + 1, 
    NULL, 
    ELT((member_id % 3) + 1, 'LOW', 'MEDIUM', 'HIGH'), 
    'OPEN', 
    CONCAT('Issue with ', ELT((member_id % 5) + 1, 'Tap', 'Fan', 'Chair', 'Cleaning', 'WiFi')), 
    'Please fix this issue as soon as possible. It is causing inconvenience.'
FROM members WHERE role_id = 2; 
-- (Generates 25 open complaints instantly)

-- Add a few resolved ones for historical data reads
INSERT INTO complaints (student_member_id, complaint_type_id, assigned_to, priority, status, title, description, resolved_at) VALUES
(8, 2, 2, 'HIGH', 'RESOLVED', 'No power in room', 'Fixed MCB trip.', NOW()),
(9, 1, 3, 'MEDIUM', 'CLOSED', 'Leaking pipe', 'Plumber fixed it.', NOW());

-- ==========================================
-- 9. INVENTORY 
-- ==========================================
INSERT INTO inventory_categories (category_id, category_name, description) VALUES
(1, 'Furniture', 'Beds, chairs, tables, wardrobes'),
(2, 'Electronics', 'Fans, lights, geysers');

-- Seed 1 item per room to test inventory updates under load
INSERT INTO inventory_items (room_id, category_id, asset_tag, purchase_date, item_condition, status)
SELECT room_id, (room_id % 2) + 1, CONCAT('AST-', room_id, '-', floor_id), '2023-01-01', 'GOOD', 'IN_USE'
FROM rooms;