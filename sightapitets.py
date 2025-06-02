# this example uses requests
import requests
import json
import os
import csv
from pathlib import Path
import time

def process_image(image_path, params):
    """Process a single image and return the results"""
    try:
        files = {'media': open(image_path, 'rb')}
        r = requests.post('https://api.sightengine.com/1.0/check.json', 
                         files=files, 
                         data=params)
        output = json.loads(r.text)
        
        # Extract the AI generation score
        ai_score = output.get('type', {}).get('ai_generated', 0)
        return {
            'filename': os.path.basename(image_path),
            'ai_generated_score': ai_score
        }
    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")
        return {
            'filename': os.path.basename(image_path),
            'ai_generated_score': 'ERROR'
        }
    finally:
        files['media'].close()

def process_directory(directory_path, output_csv):
    """Process all images in a directory and save results to CSV"""
    # API parameters
    params = {
        'models': 'genai',
        'api_user': '1749066214',
        'api_secret': 'aBGPTQ9C78qiW792kELUGsQQE7jBSRxQ'
    }
    
    # Supported image extensions
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp')
    
    # Get all image files in the directory
    image_files = [f for f in Path(directory_path).glob('*') 
                  if f.suffix.lower() in image_extensions]
    
    print(f"Found {len(image_files)} images to process")
    
    # Create CSV file and write header
    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['filename', 'ai_generated_score'])
        writer.writeheader()
        
        # Process each image
        for image_path in image_files:
            print(f"Processing {image_path.name}...")
            result = process_image(image_path, params)
            writer.writerow(result)
            
            # Add a small delay to avoid hitting rate limits
            time.sleep(0.5)
    
    print(f"Results saved to {output_csv}")

# Usage
if __name__ == "__main__":
    # Directory containing images
    image_directory = "/Users/shilpa/Downloads/AI"  # Replace with your directory path
    
    # Output CSV file
    output_csv = "ai_generation_results.csv"
    
    # Process all images
    process_directory(image_directory, output_csv)
