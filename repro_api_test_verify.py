import json
import pathlib
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:5000'
FILE_PATH = pathlib.Path(r'c:\Users\Prakruthi\Desktop\Adaptive-Dyslexia-Learning-Assistant\frontend\test_upload.txt')

print('HEALTH:')
print(urllib.request.urlopen(f'{BASE}/health').read().decode())
print('FILE EXISTS:', FILE_PATH.exists(), FILE_PATH)

with FILE_PATH.open('rb') as f:
    data = f.read()

boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = b''
body += b'--' + boundary.encode() + b'\r\n'
body += b'Content-Disposition: form-data; name="file"; filename="test_upload.txt"\r\n'
body += b'Content-Type: text/plain\r\n\r\n'
body += data + b'\r\n'
body += b'--' + boundary.encode() + b'--\r\n'

req = urllib.request.Request(f'{BASE}/upload', data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
try:
    res = urllib.request.urlopen(req, timeout=120)
    upload = json.loads(res.read().decode())
    print('UPLOAD STATUS', res.status)
    print('UPLOAD BODY', json.dumps(upload, indent=2))
except urllib.error.HTTPError as e:
    print('UPLOAD HTTP ERROR', e.code)
    print(e.read().decode())
    raise

# Use the integer saved_document_id (DB id) for chat payload
doc_db_id = upload.get('saved_document_id') or (upload.get('document') or {}).get('id')
print('Using saved_document_id for chat:', doc_db_id)

chat_payload = json.dumps({'message': 'Explain the main idea of the document in simple words.', 'document_id': int(doc_db_id)}).encode('utf-8')
req = urllib.request.Request(f'{BASE}/chat', data=chat_payload, headers={'Content-Type': 'application/json'})
try:
    res = urllib.request.urlopen(req, timeout=120)
    chat = json.loads(res.read().decode())
    print('CHAT STATUS', res.status)
    print('CHAT BODY', json.dumps(chat)[:4000])
except urllib.error.HTTPError as e:
    print('CHAT HTTP ERROR', e.code)
    print(e.read().decode())
    raise
