import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check if the key is set
api_key = os.getenv('NVIDIA_API_KEY')
if api_key:
    print("NVIDIA_API_KEY is set")
    print(f"Key starts with: {api_key[:10]}...")
else:
    print("NVIDIA_API_KEY is not set")