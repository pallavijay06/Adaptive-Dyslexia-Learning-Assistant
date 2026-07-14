"""Temporary diagnostic script — delete after diagnosis."""
import sys, os
sys.path.insert(0, ".")
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(".env").resolve()
print(f"[1] .env path : {env_path}")
print(f"[2] .env exists: {env_path.exists()}")
load_dotenv(env_path, override=True)

key   = os.getenv("OPENROUTER_API_KEY", "").strip()
model = os.getenv("OPENROUTER_MODEL", "").strip()
print(f"[3] OPENROUTER_MODEL   = {repr(model)}")
print(f"[4] KEY prefix (20ch)  = {repr(key[:20])}")

# Also check what _get_model_name() returns via the actual module
from services.openrouter_service import _get_model_name, _load_api_key, DEFAULT_MODEL_NAME
print(f"[5] DEFAULT_MODEL_NAME = {repr(DEFAULT_MODEL_NAME)}")
print(f"[6] _get_model_name()  = {repr(_get_model_name())}")
print(f"[7] _load_api_key()[:20] = {repr(_load_api_key()[:20])}")

# Check for competing .env files
for p in [".env.local", "services/.env", "services/.env.local"]:
    print(f"[8] {p} exists: {Path(p).exists()}")

# Make the live call
from openai import OpenAI
client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1", timeout=30)

print(f"\n[9] Sending request — model={repr(model)}")
try:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say hello in one word."}],
        max_tokens=10,
    )
    print("[10] SUCCESS — raw response dump:")
    print(repr(response))
    print()
    msg = response.choices[0].message
    print("[11] choices[0].message type:", type(msg))
    print("[12] message.__dict__:", vars(msg) if hasattr(msg, '__dict__') else 'no __dict__')
    print("[13] message fields via model_fields (pydantic):", list(msg.model_fields.keys()) if hasattr(msg, 'model_fields') else 'N/A')
    for attr in ('content','reasoning','reasoning_content','tool_calls','refusal','function_call','audio'):
        val = getattr(msg, attr, '__MISSING__')
        print(f"[14] msg.{attr} = {repr(val)}")
    # Also dump finish_reason and model
    print("[15] finish_reason:", response.choices[0].finish_reason)
    print("[16] response.model:", response.model)
except Exception as exc:
    print("[10] EXCEPTION TYPE :", type(exc).__name__)
    print("[11] repr(exc)       :", repr(exc))
    print("[12] str(exc)        :", str(exc))
    for attr in ("status_code", "body", "message", "code", "type"):
        if hasattr(exc, attr):
            print(f"[13] exc.{attr} = {getattr(exc, attr)!r}")
    if hasattr(exc, "response"):
        r = exc.response
        print("[14] exc.response.status_code:", getattr(r, "status_code", "N/A"))
        print("[14] exc.response.text       :", getattr(r, "text", "N/A"))
