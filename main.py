import os
import json
import jwt
import secrets
from datetime import datetime, timezone, timedelta
from google.oauth2 import service_account
from google.cloud import firestore
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request, Header


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
    
class dev_auth(BaseModel):
    device_id: str
    created_at: int
    signature: str
    
    
async def validate_token(device_id: str, authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization.split(" ")[1]
    doc = db.collection("device_tokens").document(device_id).get()
    if not doc.exists:
        raise HTTPException(status_code=401, detail="Unauthorized access")

    data = doc.to_dict()
    if not data.get("active", False):
        raise HTTPException(status_code=403, detail="Token inactive")
    SECRET_KEY=data.get("secret_key")
    
 
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    

    if decoded["device_id"] != device_id:
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
    
    
@app.post("/deviceTable/{device_id}/auth")
async def add_device_log(device_id: str,auth: dev_auth,):
   
    try:
        token_doc_ref = db.collection("device_tokens").document(device_id)
        token_doc=token_doc_ref.get()
        if not token_doc.exists:
            raise HTTPException(status_code=404, detail="Unauthorized Access")
        device_secret=token_doc.to_dict()["sharedKey"]
        token=auth.dict()["signature"]
        
        try:
            decoded = jwt.decode(token, device_secret, algorithms=["HS256"])
            print("Valid token. Payload:", decoded)
            print(decoded["device_id"])
        except jwt.ExpiredSignatureError as e:
            raise Exception("Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise Exception("Invalid token") from e
        now_utc = datetime.now(timezone.utc)
        current_time = int(now_utc.timestamp())  # iat
        expires_at_access = int((now_utc + timedelta(minutes=15)).timestamp())  # exp for access token
        expires_at_refresh = int((now_utc + timedelta(hours=1)).timestamp()) 
        
            
        # Access Token Generation
        accessTK_payload={
            "type":"Bearer ",
            "device_id":device_id,
            "iat": current_time,
            "exp": expires_at_access
        }
        accessTK_ref = db.collection("device_tokens").document(device_id).collection("AR_Tokens").document("accessToken")
        accessTK_ref.set(accessTK_payload)
        
        accessTK_signed = jwt.encode(accessTK_payload, device_secret, algorithm="HS256")
                
        # Refresh Token Generation
        refreshTK_payload={
            "type":"Bearer ",
            "device_id":device_id,
            "iat": current_time,
            "exp": expires_at_refresh
        }
        
        refreshTK_ref = db.collection("device_tokens").document(device_id).collection("AR_Tokens").document("refreshToken")
        refreshTK_ref.set(refreshTK_payload)
        refreshTK_signed = jwt.encode(refreshTK_payload, device_secret, algorithm="HS256")
        try:
            decoded = jwt.decode(refreshTK_signed, device_secret, algorithms=["HS256"])
            print("Valid token. Payload:", decoded)
            print(decoded["device_id"])
        except jwt.ExpiredSignatureError:
            print("Token expired")
        except jwt.InvalidTokenError:
            print("Invalid token")

        

        return {"success": True,  "message": "General Kenobi", "refreshTK": refreshTK_signed,"accessTK": accessTK_signed}


    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unauthorized Access: {e}")
    
