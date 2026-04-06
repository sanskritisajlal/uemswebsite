"""
=======================================================================
  University Event Management System (UEMS)
  Course  : BCSE301L - Software Engineering
  Use Case: User Registration & Event Registration Module
  Mode    : Interactive Menu-Driven Program
=======================================================================
"""

import hashlib
import datetime
import re
import time
import sys

# ===================================================================
#  IN-MEMORY DATA STORES (simulating a database)
# ===================================================================
users = {}          # email -> { name, password_hash, role, student_id, created_at }
events = {}         # event_id -> { title, date, organizer, capacity, registered[] }
registrations = {}  # (email, event_id) -> timestamp
failed_attempts = {} # email -> [attempt_count, lock_time]

# ===================================================================
#  CONFIGURATION
# ===================================================================
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300

# ===================================================================
#  UTILITY FUNCTIONS
# ===================================================================
def hash_password(pw):
    """Hash password using SHA-256 (NFR1 - Security)"""
    return hashlib.sha256(pw.encode()).hexdigest()

def validate_email(email):
    """Only accept institutional @vit.ac.in email addresses (FR1)"""
    return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@vit\.ac\.in$', email))

def validate_password(pw):
    """
    Password rules (FR1):
    - At least 8 characters
    - At least 1 uppercase letter
    - At least 1 digit
    - At least 1 special character
    """
    return (len(pw) >= 8 and 
            re.search(r'[A-Z]', pw) and
            re.search(r'\d', pw) and
            re.search(r'[!@#$%^&*(),.?":{}|<>]', pw))

def generate_event_id(title):
    """Generate a unique event ID from the title and current timestamp"""
    raw = title + str(datetime.datetime.now().timestamp())
    return "EVT-" + hashlib.md5(raw.encode()).hexdigest()[:6].upper()

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def pause():
    """Pause and wait for user input"""
    input("\nPress Enter to continue...")

# ===================================================================
#  FR1 - USER REGISTRATION
# ===================================================================
def register_user(name, email, password, role, student_id=""):
    """
    Functional Requirement 1: Register a new user.
    Validates all inputs before storing the account.
    """
    # Validation checks
    if not name or not name.strip():
        return {"success": False, "message": "❌ Name cannot be empty."}
    
    if not validate_email(email):
        return {"success": False, "message": "❌ Email must end with @vit.ac.in"}
    
    if email in users:
        return {"success": False, "message": "❌ Account with this email already exists."}
    
    if not validate_password(password):
        return {"success": False, "message": "❌ Password too weak! (min 8 chars, 1 uppercase, 1 digit, 1 special character)"}
    
    if role not in ["student", "faculty", "admin"]:
        return {"success": False, "message": "❌ Invalid role. Choose: student, faculty, or admin"}
    
    if role == "student" and (not student_id or not student_id.strip()):
        return {"success": False, "message": "❌ Student ID required for student accounts."}
    
    # Store user
    users[email] = {
        "name": name.strip(),
        "email": email,  # Added email field
        "password_hash": hash_password(password),
        "role": role,
        "student_id": student_id.strip() if role == "student" else "",
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return {"success": True, "message": f"✅ '{name}' registered successfully as {role}!"}

# ===================================================================
#  FR2 - EVENT CREATION
# ===================================================================
def create_event(organizer_email, title, date_str, capacity):
    """
    Functional Requirement 2: Create a new event.
    Only faculty or admin can create events.
    """
    if organizer_email not in users:
        return {"success": False, "message": "❌ Organizer account not found."}
    
    if users[organizer_email]["role"] not in ["faculty", "admin"]:
        return {"success": False, "message": "❌ Only faculty or admin can create events."}
    
    if not title or not title.strip():
        return {"success": False, "message": "❌ Event title cannot be empty."}
    
    # Validate date
    try:
        event_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        if event_date.date() < datetime.date.today():
            return {"success": False, "message": "❌ Event date cannot be in the past."}
    except ValueError:
        return {"success": False, "message": "❌ Invalid date format. Use YYYY-MM-DD"}
    
    # Validate capacity
    try:
        capacity = int(capacity)
        if capacity <= 0:
            raise ValueError
    except ValueError:
        return {"success": False, "message": "❌ Capacity must be a positive whole number."}
    
    # Create event
    eid = generate_event_id(title)
    events[eid] = {
        "title": title.strip(),
        "date": date_str,
        "organizer": organizer_email,
        "capacity": capacity,
        "registered": []
    }
    
    return {"success": True, "message": f"✅ Event '{title}' created successfully!\n   Event ID: {eid}", "event_id": eid}

# ===================================================================
#  FR2 - EVENT REGISTRATION
# ===================================================================
def register_for_event(user_email, event_id):
    """
    Functional Requirement 2: Enrol a student in an event.
    Checks role, duplicate registration, and capacity.
    """
    if user_email not in users:
        return {"success": False, "message": "❌ User not found. Please login first."}
    
    if users[user_email]["role"] != "student":
        return {"success": False, "message": "❌ Only students can register for events!"}
    
    if event_id not in events:
        return {"success": False, "message": "❌ Event not found. Please check the Event ID."}
    
    ev = events[event_id]
    
    if user_email in ev["registered"]:
        return {"success": False, "message": "❌ You are already registered for this event!"}
    
    if len(ev["registered"]) >= ev["capacity"]:
        return {"success": False, "message": f"❌ Event is fully booked! (Capacity: {ev['capacity']})"}
    
    # Register student
    ev["registered"].append(user_email)
    registrations[(user_email, event_id)] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return {"success": True, "message": f"✅ Successfully enrolled in '{ev['title']}'! Seat #{len(ev['registered'])}/{ev['capacity']}"}

# ===================================================================
#  NFR1 - SECURE LOGIN WITH BRUTE-FORCE PROTECTION
# ===================================================================
def login_user(email, password):
    """
    Non-Functional Requirement 1: Secure login.
    Locks account after 5 consecutive failed attempts within 5 minutes.
    """
    now = time.time()
    
    # Check for lockout
    if email in failed_attempts:
        attempts, lock_time = failed_attempts[email]
        if attempts >= MAX_ATTEMPTS and (now - lock_time) < LOCKOUT_SECONDS:
            remaining = int(LOCKOUT_SECONDS - (now - lock_time))
            return {"success": False, "message": f"🔒 Account locked! Try again in {remaining} seconds."}
        elif attempts >= MAX_ATTEMPTS:
            # Reset after lockout period
            failed_attempts[email] = [0, now]
    
    # Validate credentials
    if email not in users or users[email]["password_hash"] != hash_password(password):
        if email not in failed_attempts:
            failed_attempts[email] = [1, now]
        else:
            failed_attempts[email][0] += 1
            failed_attempts[email][1] = now
        
        remaining = MAX_ATTEMPTS - failed_attempts[email][0]
        return {"success": False, "message": f"❌ Invalid credentials! {remaining} attempt(s) remaining before lockout."}
    
    # Successful login - reset attempts
    failed_attempts[email] = [0, now]
    
    # Return user object with email included
    user_obj = users[email].copy()
    user_obj["email"] = email  # Ensure email is in the user object
    
    return {"success": True, "message": f"✅ Welcome back, {users[email]['name']}!", "user": user_obj}

# ===================================================================
#  DISPLAY FUNCTIONS
# ===================================================================
def view_all_events():
    """Display all available events"""
    if not events:
        print("\n📋 No events available at the moment.")
        return
    
    print("\n" + "─" * 80)
    print(f"{'Event ID':<12} {'Title':<30} {'Date':<12} {'Capacity':<10} {'Registered':<10} {'Seats Left':<10}")
    print("─" * 80)
    
    for eid, ev in events.items():
        registered_count = len(ev["registered"])
        seats_left = ev["capacity"] - registered_count
        print(f"{eid:<12} {ev['title']:<30} {ev['date']:<12} {ev['capacity']:<10} {registered_count:<10} {seats_left:<10}")
    print("─" * 80)

def view_my_registrations(user_email):
    """View events user has registered for"""
    my_events = [(eid, ev) for eid, ev in events.items() if user_email in ev["registered"]]
    
    if not my_events:
        print("\n📋 You haven't registered for any events yet.")
        return
    
    print("\n" + "─" * 60)
    print(f"{'Event ID':<12} {'Title':<30} {'Date':<12}")
    print("─" * 60)
    
    for eid, ev in my_events:
        print(f"{eid:<12} {ev['title']:<30} {ev['date']:<12}")
    print("─" * 60)

def view_all_users():
    """Display all registered users (Admin only)"""
    if not users:
        print("\n📋 No users registered.")
        return
    
    print("\n" + "─" * 80)
    print(f"{'Name':<20} {'Email':<35} {'Role':<12} {'Student ID':<12}")
    print("─" * 80)
    
    for email, user in users.items():
        print(f"{user['name']:<20} {email:<35} {user['role']:<12} {user['student_id']:<12}")
    print("─" * 80)
    print(f"\nTotal: {len(users)} user(s) registered.")

# ===================================================================
#  NFR2 - PERFORMANCE BENCHMARK
# ===================================================================
def performance_benchmark(n=1000):
    """
    Non-Functional Requirement 2: Performance.
    Registers n users and verifies the operation completes in under 2 seconds.
    """
    print(f"\n📊 Running performance benchmark with {n} registrations...")
    start = time.time()
    
    success_count = 0
    for i in range(n):
        result = register_user(
            f"Benchmark User {i}", 
            f"bench{i:04d}@vit.ac.in",
            f"Bench@{i:04d}",
            "student", 
            f"22BCE{i:04d}"
        )
        if result["success"]:
            success_count += 1
    
    elapsed = time.time() - start
    
    print(f"\n📈 Performance Results:")
    print(f"   • Registrations attempted: {n}")
    print(f"   • Successful: {success_count}")
    print(f"   • Time taken: {elapsed:.4f} seconds")
    print(f"   • Threshold: < 2.0 seconds")
    
    if elapsed < 2.0:
        print(f"   ✅ PASSED! ({elapsed:.4f}s < 2.0s)")
        return {"passed": True, "elapsed": elapsed}
    else:
        print(f"   ❌ FAILED! ({elapsed:.4f}s >= 2.0s)")
        return {"passed": False, "elapsed": elapsed}

# ===================================================================
#  TEST CASES RUNNER (Matches the case study exactly)
# ===================================================================
def run_all_tests():
    """
    Runs all test cases from the case study document
    """
    # Reset data stores
    global users, events, registrations, failed_attempts
    users = {}
    events = {}
    registrations = {}
    failed_attempts = {}
    
    print("\n" + "═" * 70)
    print("   AUTOMATED TEST SUITE - UEMS")
    print("═" * 70)
    
    test_results = []
    
    # ========== FR1 - USER REGISTRATION TESTS ==========
    print("\n━━  FR1  ·  USER REGISTRATION  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  ✔  VALID CASES  – Correct inputs that should succeed")
    
    # TC-FR1-V1: Valid student registration
    result = register_user("Arjun Sharma", "arjun.sharma@vit.ac.in", "SecureP@ss1", "student", "22BCE1001")
    status = "PASS" if result["success"] else "FAIL"
    test_results.append(("TC-FR1-V1", "Valid student registration", status, result["message"]))
    print(f"  TC-FR1-V1  Valid student registration          Status: {status}")
    
    # TC-FR1-V2: Valid faculty registration
    result = register_user("Dr. Priya Nair", "priya.nair@vit.ac.in", "Faculty#99", "faculty")
    status = "PASS" if result["success"] else "FAIL"
    test_results.append(("TC-FR1-V2", "Valid faculty registration", status, result["message"]))
    print(f"  TC-FR1-V2  Valid faculty registration          Status: {status}")
    
    print("  ✘  INVALID CASES  – Bad inputs that the system must reject")
    
    # TC-FR1-I1: Empty name field
    result = register_user("", "blank@vit.ac.in", "SecureP@ss1", "student", "22BCE1099")
    status = "PASS" if not result["success"] else "FAIL"
    test_results.append(("TC-FR1-I1", "Empty name field", status, result["message"]))
    print(f"  TC-FR1-I1  Empty name field                    Status: {status}")
    
    # TC-FR1-I2: Non-institutional email
    result = register_user("Test User", "test@gmail.com", "SecureP@ss1", "student", "22BCE1100")
    status = "PASS" if not result["success"] else "FAIL"
    test_results.append(("TC-FR1-I2", "Non-institutional email", status, result["message"]))
    print(f"  TC-FR1-I2  Non-institutional email             Status: {status}")
    
    # TC-FR1-I3: Weak password
    result = register_user("Test User", "testpass@vit.ac.in", "weakpass", "student", "22BCE1101")
    status = "PASS" if not result["success"] else "FAIL"
    test_results.append(("TC-FR1-I3", "Weak password", status, result["message"]))
    print(f"  TC-FR1-I3  Weak password                       Status: {status}")
    
    # TC-FR1-I4: Duplicate email
    result = register_user("Arjun Sharma", "arjun.sharma@vit.ac.in", "SecureP@ss1", "student", "22BCE1001")
    status = "PASS" if not result["success"] else "FAIL"
    test_results.append(("TC-FR1-I4", "Duplicate email", status, result["message"]))
    print(f"  TC-FR1-I4  Duplicate email                     Status: {status}")
    
    # TC-FR1-I5: Student with no Student ID
    result = register_user("No ID Student", "noid@vit.ac.in", "SecureP@ss1", "student", "")
    status = "PASS" if not result["success"] else "FAIL"
    test_results.append(("TC-FR1-I5", "Student with no Student ID", status, result["message"]))
    print(f"  TC-FR1-I5  Student with no Student ID          Status: {status}")
    
    # ========== FR2 - EVENT REGISTRATION TESTS ==========
    print("\n━━  FR2  ·  EVENT REGISTRATION  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  ✔  VALID CASES")
    
    # TC-FR2-V1: Faculty creates a new event
    result = create_event("priya.nair@vit.ac.in", "TechFest 2026", "2026-05-15", 100)
    event_id = result.get("event_id", "")
    status = "PASS" if result["success"] else "FAIL"
    test_results.append(("TC-FR2-V1", "Faculty creates TechFest 2026", status, result["message"]))
    print(f"  TC-FR2-V1  Faculty creates TechFest 2026       Status: {status}")
    
    # TC-FR2-V2: Student enrols in available event
    result = register_for_event("arjun.sharma@vit.ac.in", event_id)
    status = "PASS" if result["success"] else "FAIL"
    test_results.append(("TC-FR2-V2", "Student enrols in TechFest 2026", status, result["message"]))
    print(f"  TC-FR2-V2  Student enrols in TechFest 2026     Status: {status}")
    
    print("  ✘  INVALID CASES")
    
    # TC-FR2-I1: Duplicate registration
    result = register_for_event("arjun.sharma@vit.ac.in", event_id)
    status = "PASS" if not result["success"] else "FAIL"
    test_results.append(("TC-FR2-I1", "Duplicate registration", status, result["message"]))
    print(f"  TC-FR2-I1  Duplicate registration              Status: {status}")
    
    # TC-FR2-I2: Faculty tries to enrol as attendee
    result = register_for_event("priya.nair@vit.ac.in", event_id)
    status = "PASS" if not result["success"] else "FAIL"
    test_results.append(("TC-FR2-I2", "Faculty tries to enrol as attendee", status, result["message"]))
    print(f"  TC-FR2-I2  Faculty tries to enrol as attendee  Status: {status}")
    
    # TC-FR2-I3: Non-existent event ID
    result = register_for_event("arjun.sharma@vit.ac.in", "EVT-ZZZZZZ")
    status = "PASS" if not result["success"] else "FAIL"
    test_results.append(("TC-FR2-I3", "Non-existent event ID", status, result["message"]))
    print(f"  TC-FR2-I3  Non-existent event ID               Status: {status}")
    
    # TC-FR2-I4: Event at full capacity
    ev2 = create_event("priya.nair@vit.ac.in", "Mini Workshop", "2026-06-01", 1)
    eid2 = ev2.get("event_id", "")
    register_user("Meena Raj", "meena.raj@vit.ac.in", "Hello@123", "student", "22BCE2001")
    register_for_event("meena.raj@vit.ac.in", eid2)
    result = register_for_event("arjun.sharma@vit.ac.in", eid2)
    status = "PASS" if not result["success"] else "FAIL"
    test_results.append(("TC-FR2-I4", "Event at full capacity", status, result["message"]))
    print(f"  TC-FR2-I4  Event at full capacity              Status: {status}")
    
    # ========== NFR1 - SECURITY TESTS ==========
    print("\n━━  NFR1  ·  SECURITY  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # TC-NFR1-I1: Account locked after 5 failed attempts
    for _ in range(5):
        login_user("arjun.sharma@vit.ac.in", "WrongPassword!")
    result = login_user("arjun.sharma@vit.ac.in", "SecureP@ss1")
    status = "PASS" if not result["success"] and "locked" in result["message"].lower() else "FAIL"
    test_results.append(("TC-NFR1-I1", "Account locked after 5 failed attempts", status, result["message"]))
    print(f"  TC-NFR1-I1  Account locked after 5 failed attempts  {status}")
    
    # TC-NFR1-V1: Valid login on fresh account
    register_user("Sneha Patel", "sneha.patel@vit.ac.in", "Secure@789", "student", "22BCE3001")
    result = login_user("sneha.patel@vit.ac.in", "Secure@789")
    status = "PASS" if result["success"] else "FAIL"
    test_results.append(("TC-NFR1-V1", "Valid credentials on fresh account", status, result["message"]))
    print(f"  TC-NFR1-V1  Valid credentials on fresh account    {status}")
    
    # TC-NFR1-I2: Wrong password shows remaining attempts
    result = login_user("sneha.patel@vit.ac.in", "WRONGPASS")
    status = "PASS" if not result["success"] and "attempt" in result["message"].lower() else "FAIL"
    test_results.append(("TC-NFR1-I2", "Wrong password, attempts remaining shown", status, result["message"]))
    print(f"  TC-NFR1-I2  Wrong password, attempts remaining shown {status}")
    
    # ========== NFR2 - PERFORMANCE TEST ==========
    print("\n━━  NFR2  ·  PERFORMANCE  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    perf_result = performance_benchmark(1000)
    status = "PASS" if perf_result["passed"] else "FAIL"
    test_results.append(("TC-NFR2-V1", "Throughput within 2-second limit", status, f"{perf_result['elapsed']:.4f}s"))
    print(f"  TC-NFR2-V1  Throughput within 2-second limit?  {status}")
    
    # Summary
    print("\n  ✔  ALL 17 TEST CASES EXECUTED")
    passed = sum(1 for _, _, s, _ in test_results if s == "PASS")
    failed = len(test_results) - passed
    print(f"  Passed: {passed}, Failed: {failed}")
    
    return passed, failed

# ===================================================================
#  MENU FUNCTIONS
# ===================================================================
def registration_menu():
    """User registration menu"""
    print_header("USER REGISTRATION")
    
    print("\nPlease enter the following details:")
    name = input("   Full Name: ").strip()
    email = input("   Email (@vit.ac.in): ").strip().lower()
    password = input("   Password: ").strip()
    print("   (Password: min 8 chars, 1 uppercase, 1 digit, 1 special char)")
    
    print("\n   Role Options:")
    print("      1. Student")
    print("      2. Faculty")
    print("      3. Admin")
    role_choice = input("   Choose role (1-3): ").strip()
    
    role_map = {"1": "student", "2": "faculty", "3": "admin"}
    role = role_map.get(role_choice, "student")
    
    student_id = ""
    if role == "student":
        student_id = input("   Student ID: ").strip()
    
    result = register_user(name, email, password, role, student_id)
    print(f"\n{result['message']}")
    pause()

def login_menu():
    """User login menu"""
    print_header("USER LOGIN")
    
    email = input("   Email: ").strip().lower()
    password = input("   Password: ").strip()
    
    result = login_user(email, password)
    print(f"\n{result['message']}")
    
    if result["success"]:
        return result["user"]
    else:
        pause()
        return None

def event_menu(user):
    """Event management menu for logged-in users"""
    while True:
        # Clear screen effect
        print("\n" * 2)
        print_header(f"WELCOME, {user['name'].upper()}!")
        print(f"   Role: {user['role'].upper()}")
        print(f"   Email: {user['email']}")
        
        print("\n   📌 MAIN MENU")
        print("   " + "─" * 20)
        print("   1. View All Events")
        print("   2. Register for an Event")
        print("   3. View My Registrations")
        
        if user["role"] in ["faculty", "admin"]:
            print("   4. Create New Event")
        
        if user["role"] == "admin":
            print("   5. View All Users")
            print("   6. Run Performance Test")
        
        print("   0. Logout")
        
        choice = input("\n   Enter your choice: ").strip()
        
        if choice == "1":
            view_all_events()
            pause()
        
        elif choice == "2":
            view_all_events()
            if events:
                event_id = input("\n   Enter Event ID to register: ").strip().upper()
                result = register_for_event(user["email"], event_id)
                print(f"\n{result['message']}")
            else:
                print("\n❌ No events available to register for!")
            pause()
        
        elif choice == "3":
            view_my_registrations(user["email"])
            pause()
        
        elif choice == "4" and user["role"] in ["faculty", "admin"]:
            print_header("CREATE NEW EVENT")
            title = input("   Event Title: ").strip()
            date = input("   Event Date (YYYY-MM-DD): ").strip()
            capacity = input("   Maximum Capacity: ").strip()
            
            result = create_event(user["email"], title, date, capacity)
            print(f"\n{result['message']}")
            pause()
        
        elif choice == "5" and user["role"] == "admin":
            view_all_users()
            pause()
        
        elif choice == "6" and user["role"] == "admin":
            performance_benchmark(1000)
            pause()
        
        elif choice == "0":
            print("\n👋 Logging out... Goodbye!")
            time.sleep(1)
            return False
        
        else:
            print("\n❌ Invalid choice! Please try again.")
            time.sleep(1)

# ===================================================================
#  MAIN FUNCTION
# ===================================================================
def main():
    """Main program entry point"""
    # Seed some sample data for testing
    register_user("Admin User", "admin@vit.ac.in", "Admin@123", "admin", "")
    register_user("Dr. Smith", "smith@vit.ac.in", "Faculty@123", "faculty", "")
    register_user("John Doe", "john.doe@vit.ac.in", "Student@123", "student", "22BCE1001")
    
    create_event("smith@vit.ac.in", "TechFest 2026", "2026-05-15", 100)
    create_event("admin@vit.ac.in", "Hackathon 2026", "2026-06-20", 50)
    
    while True:
        # Clear screen effect
        print("\n" * 2)
        print_header("UNIVERSITY EVENT MANAGEMENT SYSTEM (UEMS)")
        print("   🎓 CSE Department | Software Engineering Lab")
        print("   BCSE301L - Case Study: User & Event Registration\n")
        print("   ┌─────────────────────────────────────────┐")
        print("   │  1. Register New Account                 │")
        print("   │  2. Login                                │")
        print("   │  3. Run All Test Cases                   │")
        print("   │  4. Run Performance Test (NFR2)          │")
        print("   │  0. Exit                                 │")
        print("   └─────────────────────────────────────────┘")
        
        choice = input("\n   Enter your choice: ").strip()
        
        if choice == "1":
            registration_menu()
        elif choice == "2":
            user = login_menu()
            if user:
                event_menu(user)
        elif choice == "3":
            run_all_tests()
            pause()
        elif choice == "4":
            performance_benchmark(1000)
            pause()
        elif choice == "0":
            print("\n👋 Thank you for using UEMS!")
            print("   Exiting...")
            sys.exit(0)
        else:
            print("\n❌ Invalid choice!")
            time.sleep(1)

if __name__ == "__main__":
    main()