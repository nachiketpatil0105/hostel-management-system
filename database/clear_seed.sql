USE stayease;


-- Delete in reverse FK dependency order so no constraint is violated.

DELETE FROM audit_logs;
DELETE FROM inventory_maintenance;
DELETE FROM inventory_items;
DELETE FROM inventory_categories;
DELETE FROM payments;
DELETE FROM fee_structures;
DELETE FROM complaint_updates;
DELETE FROM complaints;
DELETE FROM complaint_types;
DELETE FROM movement_logs;
DELETE FROM visitor_logs;
DELETE FROM visitors;
DELETE FROM room_allocations;
DELETE FROM rooms;
DELETE FROM floors;
DELETE FROM hostel_security_assignments;
DELETE FROM hostels;
DELETE FROM security_profiles;
DELETE FROM warden_profiles;
DELETE FROM employee_profiles;
DELETE FROM student_profiles;
DELETE FROM user_credentials;
DELETE FROM members;
DELETE FROM roles;


-- Reset all auto-increment counters back to 1.

ALTER TABLE audit_logs AUTO_INCREMENT = 1;
ALTER TABLE inventory_maintenance AUTO_INCREMENT = 1;
ALTER TABLE inventory_items AUTO_INCREMENT = 1;
ALTER TABLE inventory_categories AUTO_INCREMENT = 1;
ALTER TABLE payments AUTO_INCREMENT = 1;
ALTER TABLE fee_structures AUTO_INCREMENT = 1;
ALTER TABLE complaint_updates AUTO_INCREMENT = 1;
ALTER TABLE complaints AUTO_INCREMENT = 1;
ALTER TABLE complaint_types AUTO_INCREMENT = 1;
ALTER TABLE movement_logs AUTO_INCREMENT = 1;
ALTER TABLE visitor_logs AUTO_INCREMENT = 1;
ALTER TABLE visitors AUTO_INCREMENT = 1;
ALTER TABLE room_allocations AUTO_INCREMENT = 1;
ALTER TABLE rooms AUTO_INCREMENT = 1;
ALTER TABLE floors AUTO_INCREMENT = 1;
ALTER TABLE hostel_security_assignments AUTO_INCREMENT = 1;
ALTER TABLE hostels AUTO_INCREMENT = 1;
ALTER TABLE members AUTO_INCREMENT = 1;
ALTER TABLE roles AUTO_INCREMENT = 1;