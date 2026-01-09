# Model Switching Guide

**TL;DR**: Switching models requires **ZERO code changes**. Just edit `config/config.yaml`.

## Quick Start

Edit `config/config.yaml`:

```yaml
models:
  primary_model: "databricks-gpt-oss-20b"  # Change this line
  provider: "databricks"                    # Change if using external providers
```

Restart the application. Done! ✅

---

## Supported Models

### Databricks Foundation Models (Default)

No API keys needed. Available via Databricks Model Serving:

```yaml
models:
  primary_model: "databricks-gpt-oss-20b"    # ⭐ Recommended: balanced
  # primary_model: "databricks-dbrx-instruct"  # Best quality, slower
  # primary_model: "databricks-meta-llama-3-1-70b-instruct"  # Good quality
  # primary_model: "databricks-mixtral-8x7b-instruct"  # Fastest, lower quality
  provider: "databricks"
```

### OpenAI Models

Requires API key in `.env`:

```yaml
models:
  primary_model: "gpt-4"                     # Best quality
  # primary_model: "gpt-3.5-turbo"          # Fast and cheap
  provider: "openai"
```

Setup:
```bash
# In .env file
OPENAI_API_KEY=sk-...

# Install package
pip install openai
```

### Anthropic Claude

Requires API key in `.env`:

```yaml
models:
  primary_model: "claude-3-opus-20240229"    # Best quality
  # primary_model: "claude-3-sonnet-20240229" # Balanced
  # primary_model: "claude-3-haiku-20240307"  # Fast and cheap
  provider: "anthropic"
```

Setup:
```bash
# In .env file
ANTHROPIC_API_KEY=sk-ant-...

# Install package
pip install anthropic
```

### Google Gemini

Requires API key in `.env`:

```yaml
models:
  primary_model: "gemini-pro"
  provider: "google"
```

Setup:
```bash
# In .env file
GOOGLE_API_KEY=...

# Install package
pip install google-generativeai
```

---

## Advanced: Task-Specific Models

Use different models for different tasks:

```yaml
models:
  primary_model: "databricks-gpt-oss-20b"
  provider: "databricks"

  # Override for specific tasks (null = use primary_model)
  analysis_model: "databricks-dbrx-instruct"  # Use best model for analysis
  qa_model: null                              # Use primary_model for Q&A
  classification_model: "databricks-mixtral-8x7b-instruct"  # Use fast model
```

---

## Does Switching Models Require Code Changes?

### ❌ NO code changes needed:

1. **Switching between Databricks models**
   - `databricks-gpt-oss-20b` → `databricks-dbrx-instruct`
   - Just change config, no code changes

2. **Switching to OpenAI, Anthropic, or Google**
   - `databricks-gpt-oss-20b` → `gpt-4` or `claude-3-opus` or `gemini-pro`
   - Just change config + add API key, no code changes

3. **Switching model parameters**
   - Temperature, max_tokens, etc.
   - Just change config, no code changes

### ✅ Why no code changes?

The system uses a **universal LLM client** (`src/llm_client.py`) that:
- Reads model configuration from `config.yaml`
- Detects the provider (Databricks, OpenAI, etc.)
- Routes requests to the appropriate API
- Standardizes responses across providers

All prompts are **provider-agnostic** (plain text in, text out). No special formatting or function calling.

---

## Model Compatibility Matrix

| Feature | Databricks | OpenAI | Anthropic | Google |
|---------|------------|--------|-----------|--------|
| Text generation | ✅ | ✅ | ✅ | ✅ |
| Investment analysis | ✅ | ✅ | ✅ | ✅ |
| Q&A / RAG | ✅ | ✅ | ✅ | ✅ |
| Document classification | ✅ | ✅ | ✅ | ✅ |
| JSON extraction | ✅ | ✅ | ✅ | ✅ |
| Code changes required | ❌ | ❌ | ❌ | ❌ |

---

## Model Selection Recommendations

### For Development / Testing
- **databricks-gpt-oss-20b**: Good balance, free on Databricks
- **gpt-3.5-turbo**: Cheap, fast (requires API key)

### For Production
- **databricks-dbrx-instruct**: Best quality on Databricks
- **gpt-4**: Best overall quality (expensive)
- **claude-3-opus**: Excellent reasoning, handles long docs well

### For Cost Optimization
- Use **databricks-mixtral-8x7b-instruct** for classification
- Use **databricks-dbrx-instruct** only for investment analysis
- Use **databricks-gpt-oss-20b** for Q&A

Example multi-model setup:
```yaml
models:
  primary_model: "databricks-gpt-oss-20b"
  provider: "databricks"

  analysis_model: "databricks-dbrx-instruct"  # Best quality for critical task
  qa_model: null                               # Use primary (gpt-oss-20b)
  classification_model: "databricks-mixtral-8x7b-instruct"  # Fastest for simple task
```

---

## Testing Model Changes

After changing the model:

1. **Restart the application**
   ```bash
   # If running Streamlit UI
   # Press Ctrl+C and restart
   streamlit run ui/app.py
   ```

2. **Test with a simple question**
   ```python
   from src.llm_client import create_llm_client

   llm = create_llm_client()
   response = llm.generate("What is 2+2?")
   print(response)
   ```

3. **Verify the model is working**
   - Check logs for model name
   - Ensure responses are coherent
   - Test with your actual data

---

## Troubleshooting

### Error: "Model not found"
- **Databricks**: Ensure model is available in your workspace
- **External**: Check API key is correct and has access

### Error: "Provider not supported"
- Check `provider` field in config.yaml is one of: `databricks`, `openai`, `anthropic`, `google`

### Error: "API key not found"
- Create `.env` file from `.env.example`
- Add your API key: `OPENAI_API_KEY=sk-...`

### Poor quality responses
- Try a more capable model (e.g., DBRX instead of Mixtral)
- Increase `max_tokens` in config
- Adjust `temperature` (lower = more deterministic)

---

## Summary

✅ **Switching models is easy**: Edit one line in `config.yaml`

✅ **No code changes needed**: Universal LLM client handles all providers

✅ **Flexible**: Use different models for different tasks

✅ **Cost-effective**: Mix cheap and expensive models strategically

Need help? Check the main README or open an issue.
