# Multi-Agent System: OpenRouter → OpenAI Migration

## Summary of Changes

This document outlines the changes made to convert the multi-agent system from using OpenRouter to OpenAI.

## Key Changes

### 1. API Key Configuration

**Before (OpenRouter)**:
```python
OPENROUTER_API_KEY: str = Field(
    default="",
    description="API key for authenticating requests to the OpenRouter AI models via OpenRouter.ai.",
)
```

**After (OpenAI)**:
```python
OPENAI_API_KEY: str = Field(
    default="",
    description="API key for authenticating requests to OpenAI API.",
)
```

### 2. Client Initialization

**Before (OpenRouter)**:
```python
self.client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=self.valves.OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://open-webui.com",
        "X-Title": "OpenWebUI Agent System",
    },
)
```

**After (OpenAI)**:
```python
self.client = OpenAI(
    api_key=self.valves.OPENAI_API_KEY,
)
```

### 3. Model Names

**Before (OpenRouter format)**:
```python
COORDINATOR_MODEL: str = Field(
    default="google/gemini-2.0-flash-lite-001",
    ...
)
THINKING_MODEL: str = Field(
    default="google/gemini-2.5-flash-preview-05-20:thinking",
    ...
)
EXECUTION_MODEL: str = Field(
    default="deepseek/deepseek-chat-v3-0324",
    ...
)
SUMMARIZER_MODEL: str = Field(
    default="google/gemini-2.5-flash-preview-05-20",
    ...
)
```

**After (OpenAI models)**:
```python
COORDINATOR_MODEL: str = Field(
    default="gpt-4o-mini",  # Fast and efficient for coordination
    ...
)
THINKING_MODEL: str = Field(
    default="o1-mini",  # Deep thinking model
    ...
)
EXECUTION_MODEL: str = Field(
    default="gpt-4o",  # Full capability model
    ...
)
SUMMARIZER_MODEL: str = Field(
    default="gpt-4o-mini",  # Fast summarization
    ...
)
```

### 4. Fallback Model

**Before (OpenRouter)**:
```python
fallback_model = "openai/gpt-3.5-turbo"
```

**After (OpenAI)**:
```python
fallback_model = "gpt-3.5-turbo"
```

### 5. Error Messages and References

**Before**:
- "OpenRouter API Key Missing"
- "Error initializing OpenAI client" (referring to OpenRouter)

**After**:
- "OpenAI API Key Missing"
- References to OpenRouter removed

### 6. Display Name

**Before**:
```python
"name": "🤖 Multi-Agent System",
```

**After**:
```python
"name": "🤖 Multi-Agent System (OpenAI)",
```

## OpenAI Model Recommendations

### Model Selection Guide

| Use Case | Recommended Model | Alternative |
|----------|------------------|-------------|
| **Coordination & Synthesis** | `gpt-4o-mini` | `gpt-3.5-turbo` |
| **Deep Thinking & Reasoning** | `o1-mini` | `o1-preview` |
| **Complex Execution** | `gpt-4o` | `gpt-4-turbo` |
| **Fast Summarization** | `gpt-4o-mini` | `gpt-3.5-turbo` |

### Available OpenAI Models (as of Dec 2024)

**Reasoning Models**:
- `o1` - Most capable reasoning model
- `o1-mini` - Faster reasoning model
- `o1-preview` - Preview of o1 capabilities

**Chat Models**:
- `gpt-4o` - Most capable multimodal model
- `gpt-4o-mini` - Fast, affordable, intelligent
- `gpt-4-turbo` - Previous generation, still very capable
- `gpt-3.5-turbo` - Fast and affordable for simple tasks

**Note**: The `o1` models use extended thinking time and are best for complex reasoning tasks.

## Configuration for Open WebUI

### Installation Steps

1. **Copy the file** to your Open WebUI functions directory or paste into the UI
2. **Configure Valves**:
   - Set `OPENAI_API_KEY` to your OpenAI API key
   - Optionally configure `JINA_API_KEY` for web browsing
   - Adjust model selections based on your needs

### Cost Optimization Tips

1. **Use `gpt-4o-mini`** for coordination and summarization (cheaper)
2. **Use `o1-mini`** instead of `o1` for thinking tasks (faster, cheaper)
3. **Use `gpt-3.5-turbo`** as fallback for simple tasks
4. **Enable caching** (`ENABLE_CACHING=true`) to save on repeated queries

### Performance vs Cost Tradeoff

**High Performance (More Expensive)**:
```python
COORDINATOR_MODEL = "gpt-4o"
THINKING_MODEL = "o1"
EXECUTION_MODEL = "gpt-4o"
SUMMARIZER_MODEL = "gpt-4o"
```

**Balanced (Recommended)**:
```python
COORDINATOR_MODEL = "gpt-4o-mini"
THINKING_MODEL = "o1-mini"
EXECUTION_MODEL = "gpt-4o"
SUMMARIZER_MODEL = "gpt-4o-mini"
```

**Budget-Friendly**:
```python
COORDINATOR_MODEL = "gpt-4o-mini"
THINKING_MODEL = "gpt-4o-mini"
EXECUTION_MODEL = "gpt-4o-mini"
SUMMARIZER_MODEL = "gpt-3.5-turbo"
```

## What Stayed the Same

- ✅ Jina AI integration for web browsing (unchanged)
- ✅ Agent architecture and workflow (unchanged)
- ✅ Caching mechanism (unchanged)
- ✅ Event emitter for visualization (unchanged)
- ✅ Multi-phase execution logic (unchanged)
- ✅ Research query planning (unchanged)

## Migration Checklist

- [ ] Get OpenAI API key from https://platform.openai.com/api-keys
- [ ] Replace the function code in Open WebUI
- [ ] Set `OPENAI_API_KEY` in Valves
- [ ] (Optional) Adjust model selections based on budget/performance needs
- [ ] (Optional) Configure Jina AI key for web browsing
- [ ] Test with a simple query
- [ ] Monitor costs in OpenAI dashboard

## Notes

- OpenAI has rate limits based on your tier (check your dashboard)
- The `o1` models don't support system messages the same way (handled by the library)
- All models support streaming (though not implemented in this version)
- Consider implementing token tracking for cost monitoring
