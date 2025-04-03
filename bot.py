from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from pymongo import MongoClient
from pydantic import BaseModel
from typing import List
import pdfplumber
import docx
import jwt
import bcrypt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import os
import datetime
import urllib.parse
import uvicorn


# Initialize App
app = FastAPI()

# MongoDB Connection
db_password = "Nopassword@530"
db_password_encoded = urllib.parse.quote_plus(db_password)
client = MongoClient(f"mongodb+srv://gunakanumuri5:{db_password_encoded}@cluster0.ecqfh.mongodb.net/job_bot?retryWrites=true&w=majority")
db = client["jobbot"]
users_collection = db["users"]
job_results_collection = db["job_results"]

# Secret Key for JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

# Predefined Skill List
skills = ["Python", "Flask", "Docker", "Git", "Azure", "DevOps", "HTML", "CSS", "JavaScript"]

def create_jwt_token(data: dict):
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
    data.update({"exp": expiration})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

# User Model
class User(BaseModel):
    email: str
    password: str

# Function to extract text from resume
def extract_text_from_resume(file_path: str) -> str:
    text = ""
    if file_path.endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    elif file_path.endswith(".docx"):
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    return text

# Function to extract skills from text
def extract_skills(text: str) -> List[str]:
    extracted_skills = [skill for skill in skills if skill.lower() in text.lower()]
    return extracted_skills

@app.get("/")
def read_root():
    return {"message": "JobBot API is running!"}

# Register User
@app.post("/register")
def register(user: User):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="User already exists")
    hashed_password = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt())
    users_collection.insert_one({"email": user.email, "password": hashed_password})
    return {"message": "User registered successfully"}

# Login User & Generate Token
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_collection.find_one({"email": form_data.username})
    if not user or not bcrypt.checkpw(form_data.password.encode(), user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_jwt_token({"sub": form_data.username})
    return {"access_token": token, "token_type": "bearer"}

# Upload Resume & Analyze Skills
@app.post("/upload")
def upload_resume(file: UploadFile = File(...), required_skills: List[str] = [], token: str = Depends(oauth2_scheme)):
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    
    extracted_text = extract_text_from_resume(file_path)
    resume_skills = extract_skills(extracted_text)
    missing_skills = list(set(required_skills) - set(resume_skills))
    
    # Save results in MongoDB
    job_results_collection.insert_one({
        "email": jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"],
        "file_name": file.filename,
        "matched_skills": resume_skills,
        "missing_skills": missing_skills
    })
    
    os.remove(file_path)  # Cleanup uploaded file
    
    return {"extracted_skills": resume_skills, "missing_skills": missing_skills}

# View Uploaded Results
@app.get("/results")
def view_results(token: str = Depends(oauth2_scheme)):
    email = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    results = list(job_results_collection.find({"email": email}, {"_id": 0}))
    return results

# Run the FastAPI app with proper host and port
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
