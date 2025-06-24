from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import bcrypt
import jwt
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = "motech_secret_key_12345"  # In production, use environment variable
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Create the main app without a prefix
app = FastAPI(title="MoTech Learning Platform", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    STUDENT = "student"

class CourseCategory(str, Enum):
    PROGRAMMING = "programming"
    DESIGN = "design"
    BUSINESS = "business"
    SCIENCE = "science"
    MATHEMATICS = "mathematics"
    OTHER = "other"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    role: UserRole
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: UserRole = UserRole.STUDENT

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Course(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    category: CourseCategory
    video_link: str
    created_by: str  # admin user id
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

class CourseCreate(BaseModel):
    title: str
    description: str
    category: CourseCategory
    video_link: str

class Enrollment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    course_id: str
    enrolled_at: datetime = Field(default_factory=datetime.utcnow)
    progress_percentage: float = 0.0
    completed_at: Optional[datetime] = None

class ProgressUpdate(BaseModel):
    course_id: str
    progress_percentage: float

class ContactForm(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: EmailStr
    subject: str
    message: str
    submitted_at: datetime = Field(default_factory=datetime.utcnow)

class ContactFormCreate(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str

# Utility Functions
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user: User) -> str:
    payload = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_data = await db.users.find_one({"id": user_id})
        if user_data is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user_data)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Routes
@api_router.get("/")
async def root():
    return {"message": "Welcome to MoTech Learning Platform API"}

# Authentication Routes
@api_router.post("/auth/register")
async def register_user(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create user
    user = User(
        email=user_data.email,
        name=user_data.name,
        role=user_data.role
    )
    
    # Store user in database
    user_dict = user.dict()
    user_dict["password"] = hashed_password
    await db.users.insert_one(user_dict)
    
    # Create JWT token
    token = create_jwt_token(user)
    
    return {
        "user": user,
        "token": token,
        "message": "User registered successfully"
    }

@api_router.post("/auth/login")
async def login_user(login_data: UserLogin):
    # Find user
    user_data = await db.users.find_one({"email": login_data.email})
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not verify_password(login_data.password, user_data["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create user object (without password)
    user = User(**{k: v for k, v in user_data.items() if k != "password"})
    
    # Create JWT token
    token = create_jwt_token(user)
    
    return {
        "user": user,
        "token": token,
        "message": "Login successful"
    }

@api_router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# Course Management Routes (Admin only)
@api_router.post("/courses", response_model=Course)
async def create_course(course_data: CourseCreate, admin_user: User = Depends(get_admin_user)):
    course = Course(**course_data.dict(), created_by=admin_user.id)
    await db.courses.insert_one(course.dict())
    return course

@api_router.get("/courses", response_model=List[Course])
async def get_all_courses():
    courses = await db.courses.find({"is_active": True}).to_list(1000)
    return [Course(**course) for course in courses]

@api_router.get("/courses/{course_id}", response_model=Course)
async def get_course(course_id: str):
    course_data = await db.courses.find_one({"id": course_id, "is_active": True})
    if not course_data:
        raise HTTPException(status_code=404, detail="Course not found")
    return Course(**course_data)

@api_router.put("/courses/{course_id}", response_model=Course)
async def update_course(course_id: str, course_data: CourseCreate, admin_user: User = Depends(get_admin_user)):
    existing_course = await db.courses.find_one({"id": course_id})
    if not existing_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    update_data = course_data.dict()
    await db.courses.update_one({"id": course_id}, {"$set": update_data})
    
    updated_course = await db.courses.find_one({"id": course_id})
    return Course(**updated_course)

@api_router.delete("/courses/{course_id}")
async def delete_course(course_id: str, admin_user: User = Depends(get_admin_user)):
    result = await db.courses.update_one({"id": course_id}, {"$set": {"is_active": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"message": "Course deleted successfully"}

# Student Enrollment Routes
@api_router.post("/enrollments")
async def enroll_in_course(course_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can enroll in courses")
    
    # Check if course exists
    course = await db.courses.find_one({"id": course_id, "is_active": True})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if already enrolled
    existing_enrollment = await db.enrollments.find_one({
        "student_id": current_user.id,
        "course_id": course_id
    })
    if existing_enrollment:
        raise HTTPException(status_code=400, detail="Already enrolled in this course")
    
    # Create enrollment
    enrollment = Enrollment(student_id=current_user.id, course_id=course_id)
    await db.enrollments.insert_one(enrollment.dict())
    
    return {"message": "Enrolled successfully", "enrollment": enrollment}

@api_router.get("/my-courses", response_model=List[dict])
async def get_my_courses(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students have enrolled courses")
    
    # Get enrollments
    enrollments = await db.enrollments.find({"student_id": current_user.id}).to_list(1000)
    
    # Get course details for each enrollment
    my_courses = []
    for enrollment in enrollments:
        course_data = await db.courses.find_one({"id": enrollment["course_id"], "is_active": True})
        if course_data:
            my_courses.append({
                "course": Course(**course_data),
                "enrollment": Enrollment(**enrollment)
            })
    
    return my_courses

@api_router.put("/progress")
async def update_progress(progress_data: ProgressUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can update progress")
    
    # Find enrollment
    enrollment = await db.enrollments.find_one({
        "student_id": current_user.id,
        "course_id": progress_data.course_id
    })
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Update progress
    update_data = {"progress_percentage": progress_data.progress_percentage}
    if progress_data.progress_percentage >= 100:
        update_data["completed_at"] = datetime.utcnow()
    
    await db.enrollments.update_one(
        {"student_id": current_user.id, "course_id": progress_data.course_id},
        {"$set": update_data}
    )
    
    return {"message": "Progress updated successfully"}

# Contact Form Route
@api_router.post("/contact")
async def submit_contact_form(contact_data: ContactFormCreate):
    contact = ContactForm(**contact_data.dict())
    await db.contact_forms.insert_one(contact.dict())
    return {"message": "Contact form submitted successfully"}

@api_router.get("/contact", response_model=List[ContactForm])
async def get_contact_forms(admin_user: User = Depends(get_admin_user)):
    contacts = await db.contact_forms.find().to_list(1000)
    return [ContactForm(**contact) for contact in contacts]

# Initialize default admin user
@api_router.post("/init-admin")
async def initialize_admin():
    # Check if admin already exists
    existing_admin = await db.users.find_one({"role": "admin"})
    if existing_admin:
        return {"message": "Admin already exists"}
    
    # Create default admin
    admin_data = UserCreate(
        email="admin@motech.com",
        password="admin123",
        name="MoTech Admin",
        role=UserRole.ADMIN
    )
    
    hashed_password = hash_password(admin_data.password)
    admin = User(
        email=admin_data.email,
        name=admin_data.name,
        role=admin_data.role
    )
    
    admin_dict = admin.dict()
    admin_dict["password"] = hashed_password
    await db.users.insert_one(admin_dict)
    
    return {
        "message": "Default admin created",
        "email": "admin@motech.com",
        "password": "admin123"
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()