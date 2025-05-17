from fastapi import FastAPI, HTTPException, Request, Header
import os
import json
from google.oauth2 import service_account
from google.cloud import firestore
from pydantic import BaseModel

app = FastAPI()

# Initialize Firestore client
try:
    firebase_key_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")
    if firebase_key_json:
        creds_dict = json.loads(firebase_key_json)
    else:
        with open("secrets/serviceAccountKey.json", "r") as f:
            creds_dict = json.load(f)

    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    db = firestore.Client(credentials=credentials, project=creds_dict["project_id"])
except Exception as e:
    # Fail fast if Firestore cannot initialize
    print(f"Failed to initialize Firestore: {e}")
    raise


class DeviceLog(BaseModel):
    status_int: int
    created_at: int
    
    
async def validate_token(device_id: str, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization.split(" ")[1]
    doc = db.collection("device_tokens").document(token).get()

    if not doc.exists:
        raise HTTPException(status_code=401, detail="Token not found")

    data = doc.to_dict()

    if not data.get("active", False):
        raise HTTPException(status_code=403, detail="Token inactive")

    if data.get("device_id") != device_id:
        raise HTTPException(status_code=403, detail="Token not valid for this device")

    return True    
    


@app.get("/")
async def root():
    
    return {"message": "Hello this is Group 19's Portalet API"}



@app.get("/deviceTable")
async def get_devices():
    try:
        deviceTable_ref = db.collection("device")
        docs = deviceTable_ref.stream()
        devices = [doc.to_dict() for doc in docs]
        return {"deviceTable": devices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching devices: {e}")
    
@app.get("/deviceTable/{device_id}")
async def get_device(device_id: str):
    try:
        device_ref = db.collection("device").document(device_id)
        docs = device_ref.get()
        if docs.exists:
            return {"device": docs.to_dict()}
        else:
            raise HTTPException(status_code=404, detail="Device not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching device: {e}")
    
@app.get("/deviceTable/{device_id}/deviceLog")
async def get_logs(device_id: str):
    try:
        logs_ref = db.collection("device").document(device_id).collection("device_log")
        logs = logs_ref.stream()
        return [log.to_dict() for log in logs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching Logs for device {device_id}: {e}")

@app.post("/deviceTable/{device_id}/deviceLog")
async def add_device_log(device_id: str, log: DeviceLog, authorization: str = Header(...)):
    await validate_token(device_id, authorization)    
    try:
        device_doc = db.collection("device").document(device_id).get()
        if not device_doc.exists:
            raise HTTPException(status_code=404, detail="Device not found")

        logs_ref = db.collection("device").document(device_id).collection("device_log")
        new_log = logs_ref.document()
        new_log.set(log.dict())

        return {"success": True, "log_id": new_log.id}


    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add log: {e}")