import json
import pathlib
import urllib.request
import urllib.error
import time

BASE = 'http://127.0.0.1:5000'
FILE_PATH = pathlib.Path('frontend/test_upload.txt')
print('TEST_UPLOAD exists', FILE_PATH.exists(), FILE_PATH)
if not FILE_PATH.exists():
    raise SystemExit('Missing test_upload.txt')
with FILE_PATH.open('rb') as f:
    data = f.read()

for run in range(1, 4):
    print('=== RUN', run, '===')
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
        body_text = res.read().decode('utf-8')
        upload = json.loads(body_text)
        print('UPLOAD', res.status, upload)
    except urllib.error.HTTPError as e:
        print('UPLOAD HTTP ERROR', e.code, e.read().decode())
        continue
    except Exception as e:
        print('UPLOAD EXCEPTION', type(e).__name__, e)
        continue
    upload_id = upload.get('saved_document_id') or upload.get('document_id')
    payload = {'document_id': upload_id, 'num_mcqs': 4, 'num_short_questions': 4}
    req = urllib.request.Request(f'{BASE}/quiz/generate', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        t0 = time.perf_counter(); res = urllib.request.urlopen(req, timeout=120); t1 = time.perf_counter()
        body_text = res.read().decode('utf-8')
        quiz = json.loads(body_text)
        print('GENERATE', res.status, 'time', round(t1-t0,3), 'keys', list(quiz.keys()))
        print('  mcqs', len(quiz.get('mcqs') or []), 'shorts', len(quiz.get('short_questions') or []))
    except urllib.error.HTTPError as e:
        print('GENERATE HTTP ERROR', e.code, e.read().decode())
        continue
    except Exception as e:
        print('GENERATE EXCEPTION', type(e).__name__, e)
        continue
    if not quiz.get('success'):
        continue
    mcq_data = quiz['mcqs']; short_data = quiz['short_questions']
    mcq_answers = [''] * len(mcq_data)
    short_answers = [''] * len(short_data)
    payload = {'mcq_answers': mcq_answers, 'mcq_data': mcq_data, 'short_answers': short_answers, 'short_data': short_data, 'user_id': None, 'document_id': upload_id, 'document_name': upload.get('filename')}
    req = urllib.request.Request(f'{BASE}/quiz/submit-full', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        t0 = time.perf_counter(); res = urllib.request.urlopen(req, timeout=180); t1 = time.perf_counter()
        body_text = res.read().decode('utf-8')
        submit = json.loads(body_text)
        print('SUBMIT', res.status, 'time', round(t1-t0,3), 'score', submit.get('report', {}).get('score'), 'total', submit.get('report', {}).get('total'))
    except urllib.error.HTTPError as e:
        print('SUBMIT HTTP ERROR', e.code, e.read().decode())
    except Exception as e:
        print('SUBMIT EXCEPTION', type(e).__name__, e)
