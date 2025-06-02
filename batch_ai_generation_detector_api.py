import requests
import json
import os
import csv
from pathlib import Path
import time
import argparse

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

def process_directory(directory_path, output_csv, threshold=0.016):
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
    print(f"Using threshold: {threshold}")
    
    # Create CSV file and write header
    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['filename', 'ai_generated_score', 'is_ai_generated'])
        writer.writeheader()
        
        # Process each image
        for image_path in image_files:
            print(f"Processing {image_path.name}...")
            result = process_image(image_path, params)
            result['is_ai_generated'] = 'Yes' if float(result['ai_generated_score']) > threshold else 'No'
            writer.writerow(result)
            
            # Add a small delay to avoid hitting rate limits
            time.sleep(0.5)
    
    print(f"Results saved to {output_csv}")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Process images for AI generation detection')
    parser.add_argument('--directory', '-d', 
                       required=True,
                       help='Directory containing images to process')
    parser.add_argument('--output', '-o',
                       default="ai_generation_results.csv",
                       help='Output CSV file name')
    parser.add_argument('--threshold', '-t',
                       type=float,
                       default=0.016,
                       help='Threshold for AI generation detection (default: 0.016)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Process all images
    process_directory(args.directory, args.output, args.threshold)