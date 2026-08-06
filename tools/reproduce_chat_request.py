import requests
from pathlib import Path

text = (
    'This is a sample learning document about photosynthesis. Plants use sunlight '
    'to convert carbon dioxide and water into glucose and oxygen.'
)
path = Path('tools/tmp_sample_document.txt')
path.write_text(text, encoding='utf-8')

with path.open('rb') as f:
    files = {'file': ('sample.txt', f, 'text/plain')}
    r = requests.post('http://127.0.0.1:5001/upload', files=files)
print('upload status', r.status_code)
print(r.text)
if r.ok:
    data = r.json()
    document_id = data.get('saved_document_id') or data.get('document_id')
    print('doc_id', document_id)
    try:
        r2 = requests.post(
            'http://127.0.0.1:5001/chat',
            json={'message': 'Explain the document in simple words.', 'document_id': document_id},
            timeout=120,
        )
        print('chat status', r2.status_code)
        print(r2.text)
    except Exception as exc:
        print('chat exception', type(exc).__name__, exc)
else:
    print('upload failed, not sending chat request.')
