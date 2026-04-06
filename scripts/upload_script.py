import requests
import uuid

file_path = r'C:\Users\proma\Downloads\KA1XST26262601C.pdf'
url = 'http://localhost:8000/api/extract/async'
file_id = str(uuid.uuid4())

print(f'> Uploading with ID: {file_id}')
try:
    with open(file_path, 'rb') as f:
        files = {'file': ('KA1XST26262601C.pdf', f, 'application/pdf')}
        data = {'file_id': file_id}
        resp = requests.post(url, files=files, data=data)
        print('> Upload response:', resp.status_code, resp.text)
except Exception as e:
    print('> Failed to upload:', e)
