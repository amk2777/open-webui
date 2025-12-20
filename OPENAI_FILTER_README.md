# OpenAI Companion Filter - Extended with Chat Meta Storage

This is an enhanced version of the OpenAI Responses Companion Filter that adds intelligent caching of uploaded files in the Chat table's meta field.

## Features

### Original Features
- Uploads files to OpenAI's file storage API
- Handles large files (>512 MB) with multipart upload
- Supports file reuse based on expiration time
- Configurable logging levels

### Extended Features ✨
- **Chat-level file caching**: Stores file IDs in the Chat table's `meta` field
- **xlsx/csv filtering**: Only processes spreadsheet files (.xlsx, .csv, .xls)
- **Hash-based deduplication**: Uses file hash to detect identical files
- **Automatic reuse**: Checks chat meta before uploading to avoid duplicates
- **Expiration tracking**: Respects OpenAI file expiration times

## How It Works

### Flow Diagram

```
User uploads xlsx/csv file
         ↓
Filter intercepts request
         ↓
Check: Is it xlsx/csv? → No → Return (do nothing)
         ↓ Yes
Get chat_id from metadata
         ↓
Load chat.meta["openai_file_cache"]
         ↓
Calculate file hash
         ↓
Check: Hash exists in cache? → Yes → Check expiration
         ↓ No                            ↓
Upload to OpenAI                   Valid? → Yes → Reuse file_id
         ↓                                  ↓ No
Get file_id & expires_at                Upload new
         ↓                                  ↓
Save to chat.meta["openai_file_cache"]     │
         ↓←───────────────────────────────┘
Inject file_id into message
         ↓
Continue to OpenAI API
```

## Chat Meta Structure

Files are stored in the Chat table's meta field with this structure:

```json
{
  "openai_file_cache": {
    "<file_hash>": {
      "filename": "data.xlsx",
      "openai_file_id": "file-abc123",
      "openai_expires_at": 1735689600,
      "uploaded_at": 1735603200
    },
    "<another_hash>": {
      "filename": "report.csv",
      "openai_file_id": "file-def456",
      "openai_expires_at": 1735776000,
      "uploaded_at": 1735689600
    }
  }
}
```

## Installation

1. **Copy the filter file** to your Open WebUI functions directory:
   ```bash
   cp openai_companion_filter_extended.py /path/to/open-webui/functions/
   ```

2. **In Open WebUI Admin Panel**:
   - Go to **Admin Settings** → **Functions**
   - Click **"+"** to add a new function
   - Paste the content of `openai_companion_filter_extended.py`
   - Save

3. **Configure the filter**:
   - Set your OpenAI API key in the Valves
   - Optionally set a custom BASE_URL for LiteLLM or other proxies

## Configuration (Valves)

### Global Valves
- **BASE_URL**: OpenAI or LiteLLM base URL (default: `https://api.openai.com/v1`)
- **API_KEY**: Your OpenAI API key (required)
- **LOG_LEVEL**: Debug level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **ENABLE_CHAT_META_CACHE**: Enable/disable chat-level caching (default: `true`)

### User Valves
- **LOG_LEVEL**: Per-user log level override (or INHERIT from global)

## Usage Example

### First Upload (File gets cached)
```
User: [Uploads sales_data.xlsx] "Analyze this sales data"
Filter: → Uploads file → file-abc123 → Saves to chat meta
OpenAI: "I'll analyze the sales data..."
```

### Follow-up Message (File reused from cache)
```
User: [Same sales_data.xlsx] "Now show me the trends"
Filter: → Found file-abc123 in chat meta → Reuses without upload
OpenAI: "Based on the sales data I already have..."
```

### Different File (New upload)
```
User: [Uploads inventory.csv] "Compare with inventory"
Filter: → New hash → Uploads → file-def456 → Saves to chat meta
OpenAI: "Comparing sales and inventory data..."
```

## Benefits

1. **Reduced API Calls**: Files are only uploaded once per chat
2. **Faster Response**: No re-upload delay for existing files
3. **Cost Savings**: Fewer file storage operations
4. **Better UX**: Users can reference the same file multiple times
5. **Automatic Cleanup**: Old entries are naturally cleaned when files expire

## Debugging

Enable DEBUG logging to see detailed information:

```python
# In Global Valves
LOG_LEVEL = "DEBUG"
```

Debug logs will show:
- File hash calculations
- Cache hits/misses
- Upload operations
- Chat meta updates

## Database Schema

The filter uses the existing Chat model:

```python
from apps.webui.models.chats import Chats

# Get chat
chat = Chats.get_chat_by_id(chat_id)

# Update meta
Chats.update_chat_by_id(chat_id, {"meta": updated_meta})
```

## Supported File Types

Currently only processes:
- `.xlsx` (Excel)
- `.xls` (Excel legacy)
- `.csv` (CSV)

To add more file types, modify the `SUPPORTED_FILE_TYPES` constant:

```python
SUPPORTED_FILE_TYPES = {".xlsx", ".csv", ".xls", ".json", ".txt"}
```

## Limitations

1. **Chat-scoped caching**: Files are cached per chat, not globally
2. **Expiration**: Files expire after OpenAI's expiration time (typically 24-48 hours)
3. **Hash-based**: File content changes create new uploads (by design)
4. **Requires chat_id**: Only works when `chat_id` is available in metadata

## Troubleshooting

### Files keep re-uploading
- Check if `ENABLE_CHAT_META_CACHE` is `true`
- Verify `chat_id` exists in metadata
- Check if files are expiring (look at `openai_expires_at`)

### Import errors
- Ensure Open WebUI version ≥ 0.6.3
- Verify `apps.webui.models.chats` is accessible

### Chat meta not saving
- Check database permissions
- Look for errors in logs with DEBUG level
- Verify Chat model is available

## Version History

- **v0.2.0**: Added chat meta caching, file type filtering, hash-based deduplication
- **v0.1.1**: Original version with basic file upload

## Credits

- Original filter by: [jrkropp/open-webui-developer-toolkit](https://github.com/jrkropp/open-webui-developer-toolkit)
- Extended by: Claude (Anthropic)
