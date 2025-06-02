import requests
import time
import os

def test_api_connection(api_url):
    """Test basic API connectivity"""
    try:
        # First, test if the server is up
        response = requests.get(api_url)
        print(f"Server status: {response.status_code}")
    except Exception as e:
        print(f"Server connection error: {str(e)}")

def test_single_image(image_path, api_url):
    # First test basic connectivity
    test_api_connection(api_url)

        
    # Check file size
    file_size = os.path.getsize(image_path)
    print(f"\nFile size: {file_size/1024/1024:.2f}MB")

    # API endpoint
    url = f"{api_url}/detect"
    
    # Prepare the file
    try:
        with open(image_path, 'rb') as image_file:
            files = {
                'file': (image_path, image_file, 'image/jpeg')
            }
            
            # Add timeout and retry logic
            max_retries = 3
            retry_delay = 5  # seconds
            
            for attempt in range(max_retries):
                try:
                    # Make the request with increased timeout
                    response = requests.post(
                        url, 
                        files=files,
                        timeout=30  # 30 seconds timeout
                    )

                                # Print response details for debugging
                    print(f"\nResponse status code: {response.status_code}")
                    print(f"Response headers: {response.headers}")
                    
                    # Check if request was successful
                    response.raise_for_status()
                    
                    # Print the results
                    result = response.json()
                    print("\nResults:")
                    print(f"Filename: {result['filename']}")
                    print(f"Is AI Generated: {result['is_ai_generated']}")
                    print(f"Confidence: {result['confidence']}%")
                    print(f"Confidence Score: {result['confidence_score']}")
                    print(f"Message: {result['message']}")
                    return  # Success, exit the function
                    
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:  # If not the last attempt
                        print(f"Attempt {attempt + 1} failed: {str(e)}")
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        print(f"All attempts failed. Last error: {str(e)}")
                        raise  # Re-raise the last exception
                        
    except FileNotFoundError:
        print(f"Error: File {image_path} not found")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

# Replace these with your actual values
RENDER_URL = "https://aigeneration-detector-api.onrender.com"  # Replace with your Render URL
IMAGE_PATH = "/Users/shilpa/Desktop/Screenshot 2025-05-29 at 4.10.28 PM.png"  # Replace with your image path

# Test the image
test_single_image(IMAGE_PATH, RENDER_URL)