# StayEase - Hostel Management System

StayEase is a robust, role-based hostel management system built with Flask and MySQL. Unlike standard CRUD applications, StayEase is specifically engineered to handle high-concurrency environments, preventing data corruption and authorization leaks under heavy load.

It serves four distinct user roles-Admin, Warden, Security, and Student-each with strict data boundaries and tailored workflows for managing room allocations, complaints, inventory, and campus security.

## Engineering Focus: Concurrency & Performance

A major focus of this project was ensuring database integrity during high-traffic events, such as multiple students trying to book the final available room at the exact same millisecond, or multiple wardens attempting to claim the same support ticket.

### The Challenge

Standard database operations are vulnerable to Read-Modify-Write race conditions. Under heavy load, these conditions result in phantom reads, lost updates, and catastrophic system failures like assigning multiple students to a single bed.

### The Solution

* **Pessimistic Row-Level Locking:** Implemented SELECT ... FOR UPDATE SQL constraints across critical endpoints (room allocation, complaint claiming, and movement logging). This enforces strict ACID transaction isolation, forcing concurrent requests to queue rather than overwrite each other.
* **Load Testing & Validation:** The system architecture was stress-tested using Locust. Simulating a spike test of 50 concurrent users aggressively hitting allocation and worker-queue bottlenecks, the API successfully processed over 24,000 requests with a 15ms median latency and zero data collisions. The system successfully returned HTTP 400 and 409 conflict responses to block overbooking attempts.
* **Strict Cross-Hostel Authorization:** Implemented query-level isolation checks. A warden or security guard assigned to Hostel A is cryptographically and programmatically blocked from reading or modifying data for students in Hostel B.

## Features by Role

### Admin

* Full system dashboard and analytics overview.
* Manage users, credentials, and role assignments.
* Create and configure hostels, floors, and room capacities.
* Handle complex room allocations and process fee payments.

### Warden

* Hostel-specific dashboard for tracking room occupancy and student details.
* Worker queue management for claiming and resolving student complaints.
* Manage hostel inventory and report/track maintenance issues.
* Review visitor and exit logs for their specific hostel.

### Security

* Monitor real-time gate movement and active visitors.
* Check-in and check-out visitors with conflict prevention (blocking duplicate active logs).
* Log student exits and returns, restricted strictly to the security guard's assigned hostel.

### Student

* View personal profile, current room allocation, and payment history.
* Submit and track maintenance or disciplinary complaints.
* Securely update contact information.

## Tech Stack

* **Backend:** Python, Flask
* **Database:** MySQL (optimized with indexes, views, and row-level locks)
* **Authentication:** JWT (JSON Web Tokens) for stateless, role-based session management
* **Frontend:** Vanilla HTML, CSS, and JavaScript (Jinja2 Templates)
* **Testing:** Locust (Load and Concurrency Testing)

## Project Structure Overview

* **app.py:** Application factory and route registration.
* **web/routes/:** Modularized Blueprints for each role (admin.py, warden.py, security.py, student.py, auth.py).
* **database/:** SQL scripts for database creation, schema definitions, and robust dummy data seeding for testing.
* **tests/:** Locust load testing scripts and exported performance reports.
* **templates/ & static/:** Frontend UI components and client-side API interaction scripts.

## Installation and Setup

1. Clone the repository and navigate to the project directory.
2. Create and activate a virtual environment:
python3 -m venv venv
source venv/bin/activate
3. Install the required dependencies:
pip install -r requirements.txt
4. Set up the MySQL database:
* Open your MySQL client.
* Execute database/schema.sql to build the tables and constraints.
* Execute database/seed.sql to populate the database with test users, rooms, and concurrent test scenarios.


5. Start the Flask application:
python3 app.py
6. Access the application in your browser at http://localhost:5000.

## Running Load Tests

To verify the concurrency locks on your local machine:

1. Ensure the Flask server is running.
2. Open a new terminal and run Locust:
python3 -m locust -f tests/test_files/locustfile.py --host=http://localhost:5000
3. Navigate to http://localhost:8089 in your browser to configure and launch the spike test.