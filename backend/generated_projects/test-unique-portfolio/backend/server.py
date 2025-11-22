# server.py
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import asyncio

load_dotenv()

# Pydantic Models
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class PhotoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: str = Field(..., min_length=1, max_length=100)
    tags: List[str] = Field(default_factory=list)
    is_featured: bool = Field(default=False)

class PhotoCreate(PhotoBase):
    image_url: str
    thumbnail_url: Optional[str] = None

class PhotoUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    tags: Optional[List[str]] = None
    is_featured: Optional[bool] = None

class PhotoResponse(PhotoBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    image_url: str
    thumbnail_url: Optional[str] = None
    upload_date: datetime
    view_count: int = 0

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    photo_count: int = 0
    created_date: datetime

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class ContactMessage(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)

class ContactMessageResponse(ContactMessage):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    sent_date: datetime
    is_read: bool = False

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class PhotographerProfile(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    bio: str = Field(..., min_length=1, max_length=2000)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    location: Optional[str] = Field(None, max_length=200)
    website: Optional[str] = None
    social_media: Optional[dict] = Field(default_factory=dict)
    profile_image: Optional[str] = None

class PhotographerProfileResponse(PhotographerProfile):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    updated_date: datetime

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# FastAPI App
app = FastAPI(
    title="Photographer Portfolio API",
    description="A comprehensive API for managing a photographer's portfolio website",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "photographer_portfolio")

# Cloudinary Configuration
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# MongoDB Connection
client = AsyncIOMotorClient(MONGODB_URL)
database = client[DATABASE_NAME]

# Collections
photos_collection = database.photos
categories_collection = database.categories
messages_collection = database.messages
profile_collection = database.profile

# Dependency to get database
async def get_database():
    return database

# Utility Functions
def photo_helper(photo) -> dict:
    return {
        "id": str(photo["_id"]),
        "title": photo["title"],
        "description": photo.get("description"),
        "category": photo["category"],
        "tags": photo.get("tags", []),
        "is_featured": photo.get("is_featured", False),
        "image_url": photo["image_url"],
        "thumbnail_url": photo.get("thumbnail_url"),
        "upload_date": photo["upload_date"],
        "view_count": photo.get("view_count", 0)
    }

async def upload_image_to_cloudinary(file: UploadFile, folder: str = "portfolio"):
    try:
        result = cloudinary.uploader.upload(
            file.file,
            folder=folder,
            resource_type="image",
            transformation=[
                {"width": 1200, "height": 800, "crop": "limit"},
                {"quality": "auto", "fetch_format": "auto"}
            ]
        )
        
        # Generate thumbnail
        thumbnail_result = cloudinary.uploader.upload(
            file.file,
            folder=f"{folder}/thumbnails",
            resource_type="image",
            transformation=[
                {"width": 400, "height": 300, "crop": "fill"},
                {"quality": "auto", "fetch_format": "auto"}
            ]
        )
        
        return result["secure_url"], thumbnail_result["secure_url"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image upload failed: {str(e)}")

# Routes

# Health Check
@app.get("/")
async def root():
    return {"message": "Photographer Portfolio API", "status": "active"}

# Photo Routes
@app.get("/api/photos", response_model=List[PhotoResponse])
async def get_photos(
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    limit: int = 20,
    skip: int = 0,
    db: AsyncIOMotorClient = Depends(get_database)
):
    query = {}
    if category:
        query["category"] = category
    if featured is not None:
        query["is_featured"] = featured
    
    cursor = photos_collection.find(query).skip(skip).limit(limit).sort("upload_date", -1)
    photos = []
    async for photo in cursor:
        photos.append(photo_helper(photo))
    return photos

@app.get("/api/photos/{photo_id}", response_model=PhotoResponse)
async def get_photo(photo_id: str, db: AsyncIOMotorClient = Depends(get_database)):
    if not ObjectId.is_valid(photo_id):
        raise HTTPException(status_code=400, detail="Invalid photo ID")
    
    photo = await photos_collection.find_one({"_id": ObjectId(photo_id)})
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    # Increment view count
    await photos_collection.update_one(
        {"_id": ObjectId(photo_id)},
        {"$inc": {"view_count": 1}}
    )
    
    return photo_helper(photo)

@app.post("/api/photos", response_model=PhotoResponse)
async def create_photo(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    category: str = Form(...),
    tags: str = Form(""),  # Comma-separated tags
    is_featured: bool = Form(False),
    file: UploadFile = File(...),
    db: AsyncIOMotorClient = Depends(get_database)
):
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Upload to Cloudinary
    image_url, thumbnail_url = await upload_image_to_cloudinary(file, "portfolio")
    
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    photo_data = {
        "title": title,
        "description": description,
        "category": category,
        "tags": tag_list,
        "is_featured": is_featured,
        "image_url": image_url,
        "thumbnail_url": thumbnail_url,
        "upload_date": datetime.utcnow(),
        "view_count": 0
    }
    
    result = await photos_collection.insert_one(photo_data)
    new_photo = await photos_collection.find_one({"_id": result.inserted_id})
    return photo_helper(new_photo)

@app.put("/api/photos/{photo_id}", response_model=PhotoResponse)
async def update_photo(
    photo_id: str,
    photo_update: PhotoUpdate,
    db: AsyncIOMotorClient = Depends(get_database)
):
    if not ObjectId.is_valid(photo_id):
        raise HTTPException(status_code=400, detail="Invalid photo ID")
    
    update_data = {k: v for k, v in photo_update.dict(exclude_unset=True).items() if v is not None}
    
    if update_data:
        await photos_collection.update_one(
            {"_id": ObjectId(photo_id)},
            {"$set": update_data}
        )
    
    updated_photo = await photos_collection.find_one({"_id": ObjectId(photo_id)})
    if not updated_photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    return photo_helper(updated_photo)

@app.delete("/api/photos/{photo_id}")
async def delete_photo(photo_id: str, db: AsyncIOMotorClient = Depends(get_database)):
    if not ObjectId.is_valid(photo_id):
        raise HTTPException(status_code=400, detail="Invalid photo ID")
    
    result = await photos_collection.delete_one({"_id": ObjectId(photo_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    return {"message": "Photo deleted successfully"}

# Category Routes
@app.get("/api/categories", response_model=List[CategoryResponse])
async def get_categories(db: AsyncIOMotorClient = Depends(get_database)):
    categories = []
    async for category in categories_collection.find():
        # Count photos in each category
        photo_count = await photos_collection.count_documents({"category": category["name"]})
        category_data = {
            "id": str(category["_id"]),
            "name": category["name"],
            "description": category.get("description"),
            "photo_count": photo_count,
            "created_date": category.get("created_date", datetime.utcnow())
        }
        categories.append(category_data)
    return categories

@app.post("/api/categories", response_model=CategoryResponse)
async def create_category(
    category: CategoryCreate,
    db: AsyncIOMotorClient = Depends(get_database)
):
    # Check if category already exists
    existing_category = await categories_collection.find_one({"name": category.name})
    if existing_category:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    category_data = {
        "name": category.name,
        "description": category.description,
        "created_date": datetime.utcnow()
    }
    
    result = await categories_collection.insert_one(category_data)
    new_category = await categories_collection.find_one({"_id": result.inserted_id})
    
    return {
        "id": str(new_category["_id"]),
        "name": new_category["name"],
        "description": new_category.get("description"),
        "photo_count": 0,
        "created_date": new_category["created_date"]
    }

# Contact Routes
@app.post("/api/contact", response_model=ContactMessageResponse)
async def send_contact_message(
    message: ContactMessage,
    db: AsyncIOMotorClient = Depends(get_database)
):
    message_data = {
        "name": message.name,
        "email": message.email,
        "subject": message.subject,
        "message": message.message,
        "sent_date": datetime.utcnow(),
        "is_read": False
    }
    
    result = await messages_collection.insert_one(message_data)
    new_message = await messages_collection.find_one({"_id": result.inserted_id})
    
    return {
        "id": str(new_message["_id"]),
        "name": new_message["name"],
        "email": new_message["email"],
        "subject": new_message["subject"],
        "message": new_message["message"],
        "sent_date": new_message["sent_date"],
        "is_read": new_message["is_read"]
    }

@app.get("/api/contact", response_model=List[ContactMessageResponse])
async def get_contact_messages(
    limit: int = 20,
    skip: int = 0,
    unread_only: bool = False,
    db: AsyncIOMotorClient = Depends(get_database)
):
    query = {}
    if unread_only:
        query["is_read"] = False
    
    messages = []
    cursor = messages_collection.find(query).skip(skip).limit(limit).sort("sent_date", -1)
    async for message in cursor:
        message_data = {
            "id": str(message["_id"]),
            "name": message["name"],
            "email": message["email"],
            "subject": message["subject"],
            "message": message["message"],
            "sent_date": message["sent_date"],
            "is_read": message["is_read"]
        }
        messages.append(message_data)
    
    return messages

# Profile Routes
@app.get("/api/profile", response_model=PhotographerProfileResponse)
async def get_profile(db: AsyncIOMotorClient = Depends(get_database)):
    profile = await profile_collection.find_one()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return {
        "id": str(profile["_id"]),
        "name": profile["name"],
        "bio