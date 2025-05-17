from typing import Optional
from fastapi import FastAPI, HTTPException
import os
import json
from google.oauth2 import service_account
from google.cloud import firestore

app = FastAPI()

# Initialize Firestore client
try:
    firebase_key_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if not firebase_key_json:
        raise Exception("Missing FIREBASE_SERVICE_ACCOUNT environment variable")

    creds_dict = json.loads(firebase_key_json)
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    db = firestore.Client(credentials=credentials, project=creds_dict["project_id"])
except Exception as e:
    # Fail fast if Firestore cannot initialize
    print(f"Failed to initialize Firestore: {e}")
    raise

@app.get("/")
async def root():
    
    return {"message": "Hello World"}



@app.get("/deviceTable")
async def get_devices():
    try:
        device_ref = db.collection("device")
        docs = device_ref.stream()
        devices = [doc.to_dict() for doc in docs]
        return {"devices": devices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching devices: {e}")


