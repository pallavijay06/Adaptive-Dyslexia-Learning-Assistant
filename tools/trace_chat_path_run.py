import logging
import time
import sys
from pathlib import Path
from functools import wraps

sys.path.insert(0, str(Path.cwd()))
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('trace_chat_run')

import backend.chat_routes as chat_routes
import backend.rag as rag
import services.llm_router as llm_router
import services.openrouter_service as openrouter
import services.gemini_service as gemini
import services.ollama_service as ollama
import services.document_context as document_context
import database.db as db
import backend.chunker as chunker
import backend.retriever as retriever
import backend.vector_store as vector_store

WRAPPED = []

def trace_function(module, fn_name):
    orig = getattr(module, fn_name)

    @wraps(orig)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        logger.info('ENTER: %s.%s args=%s kwargs=%s', module.__name__.split('.')[-1], fn_name, args[:5], kwargs)
        try:
            result = orig(*args, **kwargs)
            elapsed = time.perf_counter() - start
            logger.info('EXIT:  %s.%s elapsed=%.4fs result_type=%s', module.__name__.split('.')[-1], fn_name, elapsed, type(result).__name__)
            return result
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.info('ERROR: %s.%s elapsed=%.4fs exception=%s', module.__name__.split('.')[-1], fn_name, elapsed, repr(exc))
            raise

    setattr(module, fn_name, wrapper)
    WRAPPED.append((module.__name__, fn_name))

for mod, name in [
    (chat_routes, 'chat'),
    (chat_routes, '_resolve_user_id'),
    (document_context, 'get_document_text'),
    (db, 'get_document'),
    (rag, 'ask_document'),
    (chunker, 'chunk_text'),
    (vector_store, 'build_index'),
    (retriever, 'retrieve_relevant_chunks_for_question'),
    (llm_router, 'generate_answer'),
    (openrouter, 'generate_answer'),
    (gemini, 'generate_answer'),
    (ollama, 'generate_answer'),
]:
    if hasattr(mod, name):
        trace_function(mod, name)

from backend.flask_app import create_app
app = create_app()
client = app.test_client()

try:
    print('TRACE START', flush=True)
    response = client.post(
        '/chat',
        json={'message': 'Explain the document in simple words.', 'document_id': 178},
        environ_overrides={'REMOTE_ADDR': '127.0.0.1'},
    )
    print('HTTP STATUS', response.status_code, flush=True)
    print(response.get_data(as_text=True), flush=True)
except Exception as exc:
    print('UNCAUGHT EXCEPTION', type(exc).__name__, exc, flush=True)
    import traceback
    traceback.print_exc()
finally:
    print('TRACE END', flush=True)
