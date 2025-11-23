# server.py
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, validator
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from typing import List, Optional
import os
from bson import ObjectId
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Renovation Business API",
    description="Modern renovation business backend with services for flooring, bathrooms, kitchens, and full house renovations",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure with specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = "renovation_business"

# Global MongoDB client
mongodb_client: Optional[AsyncIOMotorClient] = None
database = None

# Pydantic Models
class ServiceType(BaseModel):
    name: str
    description: str
    features: List[str]
    price_range: str

class ContactForm(BaseModel):
    name: str
    email: EmailStr
    phone: str
    service_type: str
    message: str
    preferred_contact_method: Optional[str] = "email"
    
    @validator('phone')
    def validate_phone(cls, v):
        # Simple phone validation
        import re
        phone_pattern = re.compile(r'^\+?1?\d{9,15}$')
        if not phone_pattern.match(v.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')):
            raise ValueError('Invalid phone number format')
        return v
    
    @validator('service_type')
    def validate_service_type(cls, v):
        valid_services = ['flooring', 'epoxy_flooring', 'bathrooms', 'kitchens', 'full_house', 'other']
        if v.lower() not in valid_services:
            raise ValueError('Invalid service type')
        return v.lower()

class QuoteRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    service_type: str
    project_details: str
    property_size: Optional[str] = None
    timeline: Optional[str] = None
    budget_range: Optional[str] = None

class ContactResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    service_type: str
    message: str
    status: str
    created_at: datetime
    updated_at: datetime

class QuoteResponse(BaseModel):
    id: str
    name: str
    email: str
    service_type: str
    status: str
    created_at: datetime

# Database connection functions
async def connect_to_mongo():
    """Create database connection"""
    global mongodb_client, database
    try:
        mongodb_client = AsyncIOMotorClient(MONGODB_URL)
        database = mongodb_client[DATABASE_NAME]
        # Test connection
        await database.command("ping")
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """Close database connection"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        logger.info("Disconnected from MongoDB")

# Dependency to get database
async def get_database():
    return database

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

# Routes

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Renovation Business API",
        "version": "1.0.0",
        "services": ["flooring", "epoxy_flooring", "bathrooms", "kitchens", "full_house"],
        "endpoints": {
            "services": "/api/services",
            "contact": "/api/contact",
            "quote": "/api/quote"
        }
    }

@app.get("/api/services", response_model=List[ServiceType])
async def get_services():
    """Get all renovation services"""
    services = [
        {
            "name": "Flooring",
            "description": "Professional flooring installation and renovation services",
            "features": [
                "Hardwood flooring installation",
                "Laminate and vinyl flooring",
                "Tile installation",
                "Floor refinishing",
                "Subfloor repair"
            ],
            "price_range": "$5-15 per sq ft"
        },
        {
            "name": "Epoxy Flooring",
            "description": "Durable and attractive epoxy floor coating solutions",
            "features": [
                "Garage floor coatings",
                "Industrial epoxy solutions",
                "Decorative metallic finishes",
                "Anti-slip coatings",
                "Commercial applications"
            ],
            "price_range": "$3-8 per sq ft"
        },
        {
            "name": "Bathroom Renovation",
            "description": "Complete bathroom remodeling and upgrade services",
            "features": [
                "Complete bathroom remodels",
                "Tile and shower installation",
                "Vanity and fixture installation",
                "Plumbing updates",
                "Accessibility modifications"
            ],
            "price_range": "$8,000-25,000"
        },
        {
            "name": "Kitchen Renovation",
            "description": "Modern kitchen design and renovation solutions",
            "features": [
                "Custom cabinet installation",
                "Countertop installation",
                "Kitchen island construction",
                "Appliance installation",
                "Lighting and electrical updates"
            ],
            "price_range": "$15,000-50,000"
        },
        {
            "name": "Full House Renovation",
            "description": "Complete home transformation and renovation services",
            "features": [
                "Whole house remodeling",
                "Structural modifications",
                "Interior and exterior updates",
                "Systems upgrades (plumbing, electrical)",
                "Project management"
            ],
            "price_range": "$50,000-200,000+"
        }
    ]
    return services

@app.post("/api/contact", response_model=dict)
async def submit_contact_form(
    contact_data: ContactForm,
    db=Depends(get_database)
):
    """Submit contact form"""
    try:
        # Prepare document for insertion
        contact_doc = {
            **contact_data.dict(),
            "status": "new",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Insert into database
        result = await db.contacts.insert_one(contact_doc)
        
        return {
            "message": "Contact form submitted successfully",
            "contact_id": str(result.inserted_id),
            "status": "submitted"
        }
        
    except Exception as e:
        logger.error(f"Error submitting contact form: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit contact form"
        )

@app.post("/api/quote", response_model=dict)
async def submit_quote_request(
    quote_data: QuoteRequest,
    db=Depends(get_database)
):
    """Submit quote request"""
    try:
        # Prepare document for insertion
        quote_doc = {
            **quote_data.dict(),
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Insert into database
        result = await db.quotes.insert_one(quote_doc)
        
        return {
            "message": "Quote request submitted successfully",
            "quote_id": str(result.inserted_id),
            "status": "pending",
            "estimated_response_time": "24-48 hours"
        }
        
    except Exception as e:
        logger.error(f"Error submitting quote request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit quote request"
        )

@app.get("/api/contacts", response_model=List[ContactResponse])
async def get_contacts(
    skip: int = 0,
    limit: int = 50,
    db=Depends(get_database)
):
    """Get contact submissions (admin endpoint)"""
    try:
        cursor = db.contacts.find().skip(skip).limit(limit).sort("created_at", -1)
        contacts = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string and format response
        formatted_contacts = []
        for contact in contacts:
            contact["id"] = str(contact["_id"])
            del contact["_id"]
            formatted_contacts.append(ContactResponse(**contact))
        
        return formatted_contacts
        
    except Exception as e:
        logger.error(f"Error retrieving contacts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve contacts"
        )

@app.get("/api/quotes", response_model=List[QuoteResponse])
async def get_quotes(
    skip: int = 0,
    limit: int = 50,
    db=Depends(get_database)
):
    """Get quote requests (admin endpoint)"""
    try:
        cursor = db.quotes.find().skip(skip).limit(limit).sort("created_at", -1)
        quotes = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string and format response
        formatted_quotes = []
        for quote in quotes:
            quote["id"] = str(quote["_id"])
            del quote["_id"]
            formatted_quotes.append(QuoteResponse(**quote))
        
        return formatted_quotes
        
    except Exception as e:
        logger.error(f"Error retrieving quotes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quotes"
        )

@app.put("/api/contacts/{contact_id}/status")
async def update_contact_status(
    contact_id: str,
    status: str,
    db=Depends(get_database)
):
    """Update contact status (admin endpoint)"""
    try:
        valid_statuses = ["new", "contacted", "in_progress", "completed", "closed"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status"
            )
        
        result = await db.contacts.update_one(
            {"_id": ObjectId(contact_id)},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact not found"
            )
        
        return {"message": "Contact status updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating contact status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update contact status"
        )

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected" if database else "disconnected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )