import pathlib

css_path = pathlib.Path(r'c:\Users\Prakruthi\Desktop\Adaptive-Dyslexia-Learning-Assistant\frontend\src\styles.css')
addition = """
/* ── Word Explorer divider inside Simplified Notes ──────────────────────── */

.notes-word-explorer-divider {
  height: 2px;
  background: #e2e8f0;
  border-radius: 1px;
  margin: 0.5rem 0;
}
"""
content = css_path.read_text(encoding='utf-8')
if '.notes-word-explorer-divider' not in content:
    css_path.write_text(content + addition, encoding='utf-8')
    print('APPENDED')
else:
    print('ALREADY PRESENT')
