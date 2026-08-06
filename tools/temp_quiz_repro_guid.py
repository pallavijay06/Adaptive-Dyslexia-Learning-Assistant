import json
import pathlib
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:5000'
FILE_PATH = pathlib.Path('frontend/test_upload.txt')

print('FILE_EXISTS:', FILE_PATH.exists(), FILE_PATH)
if not FILE_PATH.exists():
    raise SystemExit('Missing frontend/test_upload.txt')

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
res = urllib.request.urlopen(req, timeout=120)
upload = json.loads(res.read().decode())
print('UPLOAD', upload)

guid = upload.get('document_id')
if guid is None:
    raise SystemExit('Missing document_id GUID from upload')

payload = {'document_id': guid, 'num_mcqs': 2, 'num_short_questions': 2}
req = urllib.request.Request(f'{BASE}/quiz/generate', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
res = urllib.request.urlopen(req, timeout=120)
quiz = json.loads(res.read().decode())
print('QUIZ GENERATE', quiz)

mcq_data = quiz['mcqs']
short_data = quiz['short_questions']
mcq_answers = [''] * len(mcq_data)
short_answers = [''] * len(short_data)
payload = {
    'mcq_answers': mcq_answers,
    'mcq_data': mcq_data,
    'short_answers': short_answers,
    'short_data': short_data,
    'user_id': None,
    'document_id': guid,
    'document_name': upload.get('filename'),
}
req = urllib.request.Request(f'{BASE}/quiz/submit-full', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
res = urllib.request.urlopen(req, timeout=180)
submit = json.loads(res.read().decode())
print('QUIZ SUBMIT', submit)
