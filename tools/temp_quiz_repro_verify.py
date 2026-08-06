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

for key in ['document_id', 'saved_document_id']:
    if upload.get(key) is None:
        print(key, 'missing; skipping')
        continue
    payload = {'document_id': upload[key], 'num_mcqs': 4, 'num_short_questions': 4}
    req = urllib.request.Request(f'{BASE}/quiz/generate', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        res = urllib.request.urlopen(req, timeout=120)
        body = res.read().decode()
        print('GENERATE', key, 'HTTP', res.status)
        print(body)
    except urllib.error.HTTPError as e:
        print('GENERATE', key, 'ERROR', e.code)
        print(e.read().decode())
    except Exception as e:
        print('GENERATE', key, 'EXCEPTION', type(e).__name__, e)
