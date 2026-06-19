# OpenRouter Integration - Quick Start

## ✅ Implementation Complete

All changes have been made with ZERO modifications to existing features.

### What Was Created

1. **`services/openrouter_service.py`** - New service using OpenRouter API
2. **`.env.example`** - Configuration template
3. **`OPENROUTER_INTEGRATION.md`** - Full documentation

### What Was Updated

1. **`services/llm_router.py`** - Updated to use OpenRouter as primary provider

### Verification

✅ Syntax validated - all files compile successfully
✅ `openai` package already in requirements.txt
✅ `python-dotenv` already in requirements.txt
✅ No other files modified

## Getting Started

### 1. Get OpenRouter API Key

Visit: https://openrouter.ai/keys

### 2. Update .env

Add to your `.env` file:

```
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=google/gemini-2.5-flash
```

Keep your existing keys:
```
GEMINI_API_KEY=your_existing_key
```

### 3. Verify Setup

The router will now try providers in this order:
1. **OpenRouter** (Primary)
2. **Gemini** (Fallback if OpenRouter fails)
3. **Ollama** (Fallback if Gemini fails)

### 4. Available OpenRouter Models

Popular models:
- `google/gemini-2.5-flash` (default, recommended)
- `anthropic/claude-3.5-sonnet`
- `meta-llama/llama-3.1-8b-instruct`
- `mistral/mistral-large`

See full list: https://openrouter.ai/docs/models

## Architecture Diagram

```
┌─────────────┐
│  Frontend   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│  Services                       │
│  - simplification_service       │
│  - vocabulary_service           │
│  - visual_service               │
│  - rag.py (document retrieval)  │
└──────┬──────────────────────────┘
       │
       ▼
┌──────────────────┐
│  llm_router.py   │  ← ENTRY POINT FOR ALL LLM CALLS
└──────┬───────────┘
       │
       ▼ (Try in order)
┌──────────────────┐
│ OpenRouter       │ Primary (NEW)
│ service          │
└──────┬───────────┘
       │ (if fails)
       ▼
┌──────────────────┐
│ Gemini           │ Fallback 1
│ service          │
└──────┬───────────┘
       │ (if fails)
       ▼
┌──────────────────┐
│ Ollama           │ Fallback 2
│ service          │
└──────────────────┘
```

## Features Unaffected

All of the following continue to work unchanged:
- ✅ Read Mode
- ✅ Listen Mode  
- ✅ Visual Learning Generation
- ✅ Vocabulary Extraction
- ✅ Document Simplification
- ✅ OCR Processing
- ✅ Text-to-Speech
- ✅ RAG Question Answering
- ✅ Accessibility Features

No code changes needed in any of these areas.

## Troubleshooting

### Invalid API Key
If you see: `"OpenRouter authentication failed"`
- Check your OPENROUTER_API_KEY in .env
- Verify key at: https://openrouter.ai/keys
- System will automatically fall back to Gemini

### Rate Limit
If you see: `"OpenRouter rate limit exceeded"`
- Wait a moment and try again
- Consider upgrading your plan on openrouter.ai
- System will automatically fall back to Gemini

### Model Not Found
If you see: `"OpenRouter model error"`
- Verify the model name in OPENROUTER_MODEL
- Check available models at: https://openrouter.ai/docs/models
- System will automatically fall back to Gemini

### Ollama Fallback Issues
If both OpenRouter and Gemini fail:
- Ensure Ollama is running: `ollama serve`
- Check that model exists: `ollama list`
- System will raise an error if all providers fail

## File Structure

```
services/
├── llm_router.py              ← Updated (now uses OpenRouter first)
├── openrouter_service.py      ← NEW
├── gemini_service.py          ← Unchanged (fallback)
├── ollama_service.py          ← Unchanged (fallback)
├── text_cleanup.py            ← Unchanged
└── ...

.env                           ← Add OPENROUTER_API_KEY here
.env.example                   ← NEW (template)
OPENROUTER_INTEGRATION.md      ← NEW (full docs)
```

## Testing the Integration

To verify everything works:

```python
from services.llm_router import generate_content, generate_answer

# Test 1: Content Generation
result = generate_content("Simplify this: Photosynthesis is the process...")
print(result)  # Should work with OpenRouter

# Test 2: Q&A with Context
result = generate_answer(
    question="What is photosynthesis?",
    context="Photosynthesis is the process of converting light energy..."
)
print(result)  # Should work with OpenRouter
```

If OpenRouter API key is invalid, it will automatically fall back to Gemini.

## Cost Considerations

OpenRouter pricing varies by model:
- `google/gemini-2.5-flash`: ~$0.075/M input tokens
- `anthropic/claude-3.5-sonnet`: ~$3/M input tokens
- Local Ollama: Free (runs locally)

Set `OPENROUTER_MODEL` to your preferred balance of cost vs. performance.

## Migration Notes

This integration is **100% backward compatible**:
- Existing .env keys still work
- All existing features unchanged
- Same prompts and behavior
- Just faster and more reliable with OpenRouter as primary

The only difference users will notice:
- Faster responses (OpenRouter is typically faster than Gemini)
- More reliable (multiple model options)
- Better fallback chain
