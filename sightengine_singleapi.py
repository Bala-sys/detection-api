import requests
import json

params = {
  'models': 'genai',
  'api_user': '1749066214',
  'api_secret': 'aBGPTQ9C78qiW792kELUGsQQE7jBSRxQ'
}
files = {'media': open('/Users/shilpa/Downloads/WhatsApp Image 2025-05-29 at 16.33.03 (2).jpeg', 'rb')}
r = requests.post('https://api.sightengine.com/1.0/check.json', files=files, data=params)

output = json.loads(r.text)
print(output)