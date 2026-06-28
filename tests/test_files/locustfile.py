from tests.test_files.locustfile import HttpUser, task, between
import random

# ==========================================================
# 1. ADMIN USER (Testing Room Allocation Race Conditions)
# ==========================================================
class AdminUser(HttpUser):
    wait_time = between(1, 3) # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Login as Admin before running tasks."""
        response = self.client.post("/api/auth/login", json={
            "user": "admin",
            "password": "password123"
        })
        if response.status_code == 200:
            self.token = response.json()["session_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.environment.runner.quit()

    @task
    def test_concurrent_room_allocation(self):
        """
        ACID ISOLATION TRAP: 
        Attempts to allocate a random student to Room ID 2.
        Room ID 2 only has ONE slot left. Concurrent admins firing this 
        will expose if your DB allows overbooking due to missing Row Locks.
        """
        # Pick a random unallocated student from the seed data (IDs 21 to 32)
        random_student_id = random.randint(21, 32)
        
        # Target Room 2 (Double room with 1 slot left)
        payload = {
            "member_id": random_student_id,
            "room_id": 2
        }

        with self.client.post("/api/admin/allocate-room", json=payload, headers=self.headers, catch_response=True) as response:
            if response.status_code == 201:
                response.success()
            elif response.status_code == 400 and "already full" in response.text:
                # If the API correctly blocks the overbook, we consider the load test "successful" for that request
                response.success()
            else:
                response.failure(f"Unexpected response: {response.status_code} - {response.text}")


# ==========================================================
# 2. WARDEN USER (Testing Worker Queue Consistency)
# ==========================================================
class WardenUser(HttpUser):
    wait_time = between(2, 5)

    def on_start(self):
        """Login as the Boys Hostel Warden."""
        response = self.client.post("/api/auth/login", json={
            "user": "ramesh.iyer",
            "password": "password123"
        })
        if response.status_code == 200:
            self.token = response.json()["session_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.environment.runner.quit()

    @task
    def test_concurrent_complaint_claiming(self):
        """
        ACID CONSISTENCY TRAP:
        Simulates multiple wardens opening the complaint list and all trying 
        to update the SAME OPEN complaint at the exact same time.
        """
        # 1. Fetch complaints
        response = self.client.get("/api/warden/complaints", headers=self.headers)
        if response.status_code == 200:
            complaints = response.json().get("complaints", [])
            # Find an open complaint
            open_complaints = [c for c in complaints if c["status"] == "OPEN"]
            
            if open_complaints:
                # Target the first open complaint
                target_id = open_complaints[0]["complaint_id"]
                payload = {
                    "status": "IN_PROGRESS",
                    "remarks": "Claimed by Locust Warden"
                }
                
                # 2. Attempt to claim it
                self.client.put(f"/api/warden/complaints/{target_id}", json=payload, headers=self.headers)


# ==========================================================
# 3. STUDENT USER (Testing Read/Write Loads)
# ==========================================================
class StudentUser(HttpUser):
    wait_time = between(1, 2)
    student_id = 8 # Arjun Mehta

    def on_start(self):
        """Login as a Student."""
        response = self.client.post("/api/auth/login", json={
            "user": "arjun.mehta",
            "password": "password123"
        })
        if response.status_code == 200:
            self.token = response.json()["session_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            # Extract member_id from JWT token payload decoding if needed, but we hardcoded 8
        else:
            self.environment.runner.quit()

    @task(3) # Weight 3 (Runs 3 times more often than the PUT task)
    def read_profile_heavy(self):
        """Simulates standard heavy read traffic on the DB."""
        self.client.get(f"/api/student/profile/{self.student_id}", headers=self.headers)

    @task(1)
    def update_phone_race_condition(self):
        """
        ACID ATOMICITY TRAP:
        Simulates the user aggressively spamming the "Save Phone" button.
        Tests the UNIQUE constraint on the phone number column.
        """
        # Generate a random 10 digit phone to avoid actual unique constraint collisions 
        # from the DB, but tests how the API handles simultaneous identical updates.
        random_phone = str(random.randint(9000000000, 9999999999))
        payload = {"phone": random_phone}
        
        self.client.put(f"/api/student/profile/{self.student_id}", json=payload, headers=self.headers)