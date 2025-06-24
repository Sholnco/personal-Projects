import requests
import json
import time
from typing import Dict, Any, Optional

# Base URL from frontend/.env
BASE_URL = "https://e981bee6-4ffc-4c01-a7b3-d6c3e1c108ea.preview.emergentagent.com/api"

# Test data
admin_credentials = {
    "email": "admin@motech.com",
    "password": "admin123"
}

student_data = {
    "email": "student@example.com",
    "password": "Student123!",
    "name": "Test Student",
    "role": "student"
}

course_data = {
    "title": "Python Programming",
    "description": "Learn Python programming from scratch",
    "category": "programming",
    "video_link": "https://example.com/python-course"
}

updated_course_data = {
    "title": "Advanced Python Programming",
    "description": "Learn advanced Python programming concepts",
    "category": "programming",
    "video_link": "https://example.com/advanced-python"
}

contact_data = {
    "name": "John Doe",
    "email": "john@example.com",
    "subject": "Course Inquiry",
    "message": "I'm interested in learning more about your Python course."
}

progress_data = {
    "progress_percentage": 50.0
}

# Global variables to store tokens and IDs
admin_token = None
student_token = None
course_id = None

class TestResult:
    def __init__(self):
        self.success_count = 0
        self.failure_count = 0
        self.results = []
    
    def add_result(self, test_name: str, success: bool, response: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        result = {
            "test_name": test_name,
            "success": success,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if response:
            result["response"] = response
        
        if error:
            result["error"] = error
            
        self.results.append(result)
        
        if success:
            self.success_count += 1
            print(f"✅ {test_name}: PASSED")
        else:
            self.failure_count += 1
            print(f"❌ {test_name}: FAILED - {error}")
    
    def summary(self):
        print("\n=== TEST SUMMARY ===")
        print(f"Total tests: {self.success_count + self.failure_count}")
        print(f"Passed: {self.success_count}")
        print(f"Failed: {self.failure_count}")
        
        if self.failure_count > 0:
            print("\nFailed tests:")
            for result in self.results:
                if not result["success"]:
                    print(f"- {result['test_name']}: {result.get('error', 'Unknown error')}")

# Initialize test results
test_results = TestResult()

def make_request(method: str, endpoint: str, data: Optional[Dict[str, Any]] = None, 
                 token: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Make an HTTP request to the API"""
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method.lower() == "get":
            response = requests.get(url, headers=headers, params=params)
        elif method.lower() == "post":
            response = requests.post(url, json=data, headers=headers, params=params)
        elif method.lower() == "put":
            response = requests.put(url, json=data, headers=headers)
        elif method.lower() == "delete":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        # Try to parse JSON response
        try:
            result = response.json()
        except json.JSONDecodeError:
            result = {"text": response.text}
        
        # Add status code to result
        result["status_code"] = response.status_code
        
        return result
    except requests.RequestException as e:
        return {"error": str(e), "status_code": 0}

def test_init_admin():
    """Test initializing the default admin user"""
    response = make_request("post", "/init-admin")
    
    if response.get("status_code") in [200, 201]:
        test_results.add_result("Initialize Admin", True, response)
        return True
    else:
        error = f"Failed to initialize admin. Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Initialize Admin", False, response, error)
        return False

def test_admin_login():
    """Test admin login"""
    global admin_token
    
    response = make_request("post", "/auth/login", admin_credentials)
    
    if response.get("status_code") == 200 and "token" in response:
        admin_token = response["token"]
        test_results.add_result("Admin Login", True, response)
        return admin_token
    else:
        error = f"Failed to login as admin. Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Admin Login", False, response, error)
        return None

def test_get_current_user(token, expected_role):
    """Test getting current user info"""
    response = make_request("get", "/auth/me", token=token)
    
    if (response.get("status_code") == 200 and 
        "role" in response and 
        response["role"] == expected_role):
        test_results.add_result(f"Get Current User ({expected_role})", True, response)
        return True
    else:
        error = f"Failed to get current user or wrong role. Expected: {expected_role}, Got: {response.get('role')}. Status code: {response.get('status_code')}"
        test_results.add_result(f"Get Current User ({expected_role})", False, response, error)
        return False

def test_user_registration():
    """Test user registration"""
    global student_token
    
    response = make_request("post", "/auth/register", student_data)
    
    if response.get("status_code") in [200, 201] and "token" in response:
        student_token = response["token"]
        test_results.add_result("User Registration", True, response)
        return student_token
    else:
        error = f"Failed to register user. Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("User Registration", False, response, error)
        return None

def test_student_login():
    """Test student login"""
    global student_token
    
    login_data = {
        "email": student_data["email"],
        "password": student_data["password"]
    }
    
    response = make_request("post", "/auth/login", login_data)
    
    if response.get("status_code") == 200 and "token" in response:
        student_token = response["token"]
        test_results.add_result("Student Login", True, response)
        return student_token
    else:
        error = f"Failed to login as student. Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Student Login", False, response, error)
        return None

def test_create_course(token):
    """Test creating a new course"""
    global course_id
    
    response = make_request("post", "/courses", course_data, token)
    
    if response.get("status_code") in [200, 201] and "id" in response:
        course_id = response["id"]
        test_results.add_result("Create Course", True, response)
        return course_id
    else:
        error = f"Failed to create course. Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Create Course", False, response, error)
        return None

def test_get_all_courses():
    """Test getting all courses"""
    response = make_request("get", "/courses")
    
    if response.get("status_code") == 200 and isinstance(response, list):
        test_results.add_result("Get All Courses", True, {"count": len(response), "status_code": response.get("status_code")})
        return True
    else:
        error = f"Failed to get courses. Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Get All Courses", False, response, error)
        return False

def test_get_course(course_id):
    """Test getting a specific course"""
    response = make_request("get", f"/courses/{course_id}")
    
    if response.get("status_code") == 200 and "id" in response and response["id"] == course_id:
        test_results.add_result("Get Course", True, response)
        return True
    else:
        error = f"Failed to get course. Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Get Course", False, response, error)
        return False

def test_update_course(course_id, token):
    """Test updating a course"""
    response = make_request("put", f"/courses/{course_id}", updated_course_data, token)
    
    if response.get("status_code") == 200 and "id" in response and response["id"] == course_id:
        test_results.add_result("Update Course", True, response)
        return True
    else:
        error = f"Failed to update course. Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Update Course", False, response, error)
        return False

def test_student_course_access(token):
    """Test student trying to create a course (should fail)"""
    response = make_request("post", "/courses", course_data, token)
    
    if response.get("status_code") == 403:
        test_results.add_result("Student Course Access (Expected Failure)", True, response)
        return True
    else:
        error = f"Student was able to create a course (should be forbidden). Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Student Course Access (Expected Failure)", False, response, error)
        return False

def test_enroll_in_course(course_id, token):
    """Test enrolling in a course"""
    response = make_request("post", "/enrollments", params={"course_id": course_id}, token=token)
    
    if response.get("status_code") in [200, 201] and "message" in response and "enrollment" in response:
        test_results.add_result("Enroll in Course", True, response)
        return True
    else:
        error = f"Failed to enroll in course. Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Enroll in Course", False, response, error)
        return False

def test_get_my_courses(token):
    """Test getting enrolled courses"""
    response = make_request("get", "/my-courses", token=token)
    
    if response.get("status_code") == 200 and isinstance(response, list):
        test_results.add_result("Get My Courses", True, {"count": len(response), "status_code": response.get("status_code")})
        return True
    else:
        error = f"Failed to get enrolled courses. Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Get My Courses", False, response, error)
        return False

def test_update_progress(course_id, token):
    """Test updating course progress"""
    progress_data["course_id"] = course_id
    response = make_request("put", "/progress", progress_data, token)
    
    if response.get("status_code") == 200 and "message" in response:
        test_results.add_result("Update Progress", True, response)
        return True
    else:
        error = f"Failed to update progress. Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Update Progress", False, response, error)
        return False

def test_admin_update_progress(course_id, token):
    """Test admin trying to update progress (should fail)"""
    progress_data["course_id"] = course_id
    response = make_request("put", "/progress", progress_data, token)
    
    if response.get("status_code") == 403:
        test_results.add_result("Admin Update Progress (Expected Failure)", True, response)
        return True
    else:
        error = f"Admin was able to update progress (should be forbidden). Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Admin Update Progress (Expected Failure)", False, response, error)
        return False

def test_submit_contact_form():
    """Test submitting a contact form"""
    response = make_request("post", "/contact", contact_data)
    
    if response.get("status_code") in [200, 201] and "message" in response:
        test_results.add_result("Submit Contact Form", True, response)
        return True
    else:
        error = f"Failed to submit contact form. Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Submit Contact Form", False, response, error)
        return False

def test_get_contact_forms(token):
    """Test getting all contact forms"""
    response = make_request("get", "/contact", token=token)
    
    if response.get("status_code") == 200 and isinstance(response, list):
        test_results.add_result("Get Contact Forms", True, {"count": len(response), "status_code": response.get("status_code")})
        return True
    else:
        error = f"Failed to get contact forms. Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Get Contact Forms", False, response, error)
        return False

def test_student_get_contact_forms(token):
    """Test student trying to get contact forms (should fail)"""
    response = make_request("get", "/contact", token=token)
    
    if response.get("status_code") == 403:
        test_results.add_result("Student Get Contact Forms (Expected Failure)", True, response)
        return True
    else:
        error = f"Student was able to get contact forms (should be forbidden). Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Student Get Contact Forms (Expected Failure)", False, response, error)
        return False

def test_delete_course(course_id, token):
    """Test deleting a course"""
    response = make_request("delete", f"/courses/{course_id}", token=token)
    
    if response.get("status_code") == 200 and "message" in response:
        test_results.add_result("Delete Course", True, response)
        return True
    else:
        error = f"Failed to delete course. Status code: {response.get('status_code')}, Response: {response}"
        test_results.add_result("Delete Course", False, response, error)
        return False

def run_all_tests():
    """Run all tests in sequence"""
    print("Starting MoTech Backend API Tests...")
    print("=" * 50)
    
    # Initialize admin
    test_init_admin()
    
    # Test authentication
    admin_token = test_admin_login()
    if admin_token:
        test_get_current_user(admin_token, "admin")
    
    student_token = test_user_registration()
    if not student_token:
        student_token = test_student_login()
    
    if student_token:
        test_get_current_user(student_token, "student")
    
    # Test course management
    if admin_token:
        course_id = test_create_course(admin_token)
        if course_id:
            test_get_all_courses()
            test_get_course(course_id)
            test_update_course(course_id, admin_token)
    
    # Test role-based access
    if student_token:
        test_student_course_access(student_token)
    
    # Test enrollment
    if student_token and course_id:
        test_enroll_in_course(course_id, student_token)
        test_get_my_courses(student_token)
        test_update_progress(course_id, student_token)
    
    # Test admin trying to update progress (should fail)
    if admin_token and course_id:
        test_admin_update_progress(course_id, admin_token)
    
    # Test contact form
    test_submit_contact_form()
    
    if admin_token:
        test_get_contact_forms(admin_token)
    
    if student_token:
        test_student_get_contact_forms(student_token)
    
    # Test course deletion
    if admin_token and course_id:
        test_delete_course(course_id, admin_token)
    
    # Print summary
    test_results.summary()

if __name__ == "__main__":
    run_all_tests()