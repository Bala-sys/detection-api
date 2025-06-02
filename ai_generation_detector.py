from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import base64
import tempfile
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from pathlib import Path

# Get the absolute path to the .env file
env_path = Path('.') / '.env'

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Generation Detection API Wrapper")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your client's domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NVIDIA API Configuration
HEADER_AUTH = f"Bearer {os.getenv('NVIDIA_API_KEY')}"
INVOKE_URL = "https://ai.api.nvidia.com/v1/cv/hive/ai-generated-image-detection"
ASSETS_URL = "https://api.nvcf.nvidia.com/v2/nvcf/assets"

def upload_asset(path: str, desc: str, mime_type: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": HEADER_AUTH,
        "accept": "application/json",
    }
    payload = {
        "contentType": mime_type,
        "description": desc
    }
    
    response = requests.post(ASSETS_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    
    current_pre_signed_url = response.json()["uploadUrl"]
    asset_id = response.json()["assetId"]
    
    headers_put = {
        "Content-Type": mime_type,
        "x-amz-meta-nvcf-asset-description": desc,
    }
    
    with open(path, "rb") as input_data:
        upload_response = requests.put(
            current_pre_signed_url,
            data=input_data,
            headers=headers_put,
            timeout=300
        )
        upload_response.raise_for_status()
    
    return asset_id

@app.post("/detect")
async def detect_deepfake(
    file: UploadFile = File(...),
    threshold: float = 0.016
):
    try:
        # Log the start of the request
        logger.info(f"Starting request for file: {file.filename}")
        
        # Validate threshold
        if not 0 <= threshold <= 1:
            raise HTTPException(
                status_code=400,
                detail="Threshold must be between 0 and 1"
            )

        # Validate file extension
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png']:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only jpg, jpeg, and png are supported."
            )

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
            logger.info(f"Saved temporary file: {tmp_path}")

        try:
            # Get mime type
            mime_type = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else 'image/png'
            logger.info(f"Using mime type: {mime_type}")

            # Read file and encode
            with open(tmp_path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode()
            logger.info(f"Image encoded, length: {len(image_b64)}")

            # Check NVIDIA API key
            if not os.getenv('NVIDIA_API_KEY'):
                logger.error("NVIDIA_API_KEY environment variable is not set")
                raise HTTPException(
                    status_code=500,
                    detail="Server configuration error: NVIDIA API key not set"
                )

            # Log the API key (first few characters only)
            api_key = os.getenv('NVIDIA_API_KEY')
            logger.info(f"Using API key starting with: {api_key[:10]}...")

            if len(image_b64) < 180_000:
                logger.info("Using base64 encoding for small image")
                payload = {
                    "input": [f"data:{mime_type};base64,{image_b64}"]
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": HEADER_AUTH,
                    "Accept": "application/json",
                }
            else:
                logger.info("Using asset upload for large image")
                asset_id = upload_asset(tmp_path, "Input Image", mime_type)
                payload = {
                    "input": [f"data:{mime_type};asset_id,{asset_id}"]
                }
                headers = {
                    "Content-Type": "application/json",
                    "NVCF-INPUT-ASSET-REFERENCES": asset_id,
                    "Authorization": HEADER_AUTH,
                }

            logger.info("Sending request to NVIDIA API")
            response = requests.post(INVOKE_URL, headers=headers, json=payload)
            logger.info(f"NVIDIA API Response Status: {response.status_code}")
            logger.info(f"NVIDIA API Response: {response.text}")
            
            response.raise_for_status()
            result = response.json()
            
            # Get the AI generation score
            if 'data' in result and len(result['data']) > 0:
                detection_data = result['data'][0]
                ai_generated_score = detection_data.get('is_ai_generated', 0)
                possible_sources = detection_data.get('possible_sources', {})
                
                # Get the top 3 most likely sources
                top_sources = sorted(
                    possible_sources.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:3]
                
                # Convert score to percentage for display
                confidence_percentage = round(ai_generated_score * 100, 2)
                confidence_score = round(ai_generated_score, 3)
                
                # Create a message with the top sources
                sources_message = ", ".join([f"{source} ({score*100:.2f}%)" for source, score in top_sources])
                
                return {
                    'filename': file.filename,
                    'is_ai_generated': ai_generated_score > threshold,
                    'confidence': confidence_percentage,
                    'confidence_score': confidence_score,
                    'threshold': threshold,
                    'status': 'success',
                    'message': f"This image is {'likely' if ai_generated_score > threshold else 'unlikely'} to be AI-generated with {confidence_percentage}% confidence (threshold: {threshold})",
                    'top_sources': top_sources,
                    'sources_message': f"Top sources: {sources_message}"
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Invalid response format from NVIDIA API"
                )

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                logger.info(f"Removed temporary file: {tmp_path}")

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# # nvidia_api_wrapper.py
# from fastapi import FastAPI, UploadFile, File, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# import requests
# import base64
# import tempfile
# import os
# import logging
# from pathlib import Path

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# app = FastAPI(title="NVIDIA Deepfake Detection API Wrapper")

# # Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # In production, restrict this to your client's domains
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # NVIDIA API Configuration
# HEADER_AUTH = "Bearer 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"
# INVOKE_URL = "https://ai.api.nvidia.com/v1/cv/hive/deepfake-image-detection"

# def upload_asset(path: str, desc: str, mime_type: str) -> str:
#     assets_url = "https://api.nvcf.nvidia.com/v2/nvcf/assets"
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": HEADER_AUTH,
#         "accept": "application/json",
#     }
#     payload = {
#         "contentType": mime_type,
#         "description": desc
#     }
#     response = requests.post(assets_url, headers=headers, json=payload, timeout=30)
#     response.raise_for_status()
#     current_pre_signed_url = response.json()["uploadUrl"]
#     asset_id = response.json()["assetId"]
    
#     headers_put = {
#         "Content-Type": mime_type,
#         "x-amz-meta-nvcf-asset-description": desc,
#     }
    
#     with open(path, "rb") as input_data:
#         upload_response = requests.put(current_pre_signed_url, data=input_data, headers=headers_put, timeout=300)
#         upload_response.raise_for_status()
#     return asset_id

# @app.post("/detect")
# async def detect_deepfake(file: UploadFile = File(...)):
#     try:
#         # Validate file extension
#         ext = os.path.splitext(file.filename)[1].lower()
#         if ext not in ['.jpg', '.jpeg', '.png']:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Invalid file type. Only jpg, jpeg, and png are supported."
#             )

#         # Save uploaded file temporarily
#         with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
#             content = await file.read()
#             tmp.write(content)
#             tmp_path = tmp.name

#         try:
#             # Get mime type
#             mime_type = 'jpeg' if ext in ['.jpg', '.jpeg'] else 'png'

#             # Read file and encode
#             with open(tmp_path, "rb") as f:
#                 image_b64 = base64.b64encode(f.read()).decode()

#             if len(image_b64) < 180_000:
#                 payload = {
#                     "input": [f"data:image/{mime_type};base64,{image_b64}"]
#                 }
#                 headers = {
#                     "Content-Type": "application/json",
#                     "Authorization": HEADER_AUTH,
#                     "Accept": "application/json",
#                 }
#             else:
#                 asset_id = upload_asset(tmp_path, "Input Image", f"image/{mime_type}")
#                 payload = {
#                     "input": [f"data:image/{mime_type};asset_id,{asset_id}"]
#                 }
#                 headers = {
#                     "Content-Type": "application/json",
#                     "NVCF-INPUT-ASSET-REFERENCES": asset_id,
#                     "Authorization": HEADER_AUTH,
#                 }

#             response = requests.post(INVOKE_URL, headers=headers, json=payload)
#             response.raise_for_status()
            
#             result = response.json()
#             deepfake_score = result['data'][0]['bounding_boxes'][0]['is_deepfake']
            
#             return {
#                 'filename': file.filename,
#                 'is_deepfake': deepfake_score > 0.02,
#                 'confidence': deepfake_score,
#                 'status': 'success'
#             }

#         finally:
#             # Clean up temporary file
#             if os.path.exists(tmp_path):
#                 os.remove(tmp_path)

#     except Exception as e:
#         logger.error(f"Error processing image: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
