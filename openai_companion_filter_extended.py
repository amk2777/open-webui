"""
title: OpenAI Responses Companion Filter with Chat Meta Storage
id: openai_responses_companion_filter_extended
description: Handles file uploads for OpenAI with chat-level caching for xlsx/csv files
git_url: https://github.com/jrkropp/open-webui-developer-toolkit.git
required_open_webui_version: 0.6.3
version: 0.2.0
"""

from __future__ import annotations

# ───────────────────────────────────────────────────────────── Imports
import asyncio
import datetime, hashlib, io, logging, mimetypes, os, sys, time
from collections import defaultdict, deque
from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional

import aiohttp, orjson
from pydantic import BaseModel, Field

# Open WebUI imports for database access
try:
    from apps.webui.models.chats import Chats
except ImportError:
    Chats = None

# ───────────────────────────────────────────────────────────── Globals
CHUNK_SIZE = 64 * 1024 * 1024  # 64 MB – OpenAI limit per part
DAY = 86_400
SUPPORTED_FILE_TYPES = {".xlsx", ".csv", ".xls"}  # Supported spreadsheet types


# ───────────────────────────────────────────────────────────── Filter
class Filter:
    # ─────────── Valves
    class Valves(BaseModel):
        BASE_URL: str = Field(
            default=os.getenv("OPENAI_API_BASE_URL", "").strip()
            or "https://api.openai.com/v1",
            description="OpenAI (or LiteLLM) base URL",
        )
        API_KEY: str = Field(
            default=os.getenv("OPENAI_API_KEY", "").strip(),
            description="Bearer token for OpenAI",
        )
        LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
            default=os.getenv("GLOBAL_LOG_LEVEL", "INFO").upper(),
        )
        ENABLE_CHAT_META_CACHE: bool = Field(
            default=True,
            description="Store file IDs in Chat table meta to avoid re-uploads",
        )

    class UserValves(BaseModel):
        LOG_LEVEL: Literal[
            "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "INHERIT"
        ] = "INHERIT"

    # ─────────── Init
    def __init__(self) -> None:
        self.file_handler = True  # WebUI: we'll manage files
        self.citation = False  # we emit logs manually

        self.valves = self.Valves()
        self.session: aiohttp.ClientSession | None = None
        self.logger = SessionLogger.get_logger(__name__)

    # ─────────────────────────────────────────────── public inlet
    async def inlet(
        self,
        body: dict,
        __user__: dict[str, Any],
        __event_emitter__: Optional[Callable] = None,
        __metadata__: Optional[dict] = None,
    ) -> dict:
        v = self._merge_valves(
            self.valves, self.UserValves.model_validate(__user__.get("valves", {}))
        )
        SessionLogger.session_id.set(__metadata__.get("session_id"))
        SessionLogger.log_level.set(getattr(logging, v.LOG_LEVEL, logging.INFO))

        files: List[Dict] = (__metadata__ or {}).get("files") or []
        if not files:
            self.logger.debug("No files in request, skipping")
            return body

        # Filter for xlsx/csv files only
        spreadsheet_files = [
            f for f in files
            if any(f["file"]["filename"].lower().endswith(ext) for ext in SUPPORTED_FILE_TYPES)
        ]

        if not spreadsheet_files:
            self.logger.debug("No xlsx/csv files found, skipping")
            return body

        self.logger.info(f"Found {len(spreadsheet_files)} spreadsheet file(s) to process")

        # Get chat_id from metadata
        chat_id = __metadata__.get("chat_id")

        # Get existing file mappings from Chat meta
        chat_file_cache = {}
        if chat_id and Chats and v.ENABLE_CHAT_META_CACHE:
            chat_file_cache = await self._get_chat_file_cache(chat_id)
            self.logger.debug(f"Loaded {len(chat_file_cache)} cached file(s) from chat {chat_id}")

        await self._ensure_session()

        for w in spreadsheet_files:
            filename = w["file"]["filename"]
            file_hash = w["file"].get("hash") or self._calculate_hash(
                w["file"]["data"]["content"].encode()
            )

            # Check if file is already cached in Chat meta
            cached_entry = chat_file_cache.get(file_hash)
            if cached_entry:
                fid = cached_entry.get("openai_file_id")
                exp_at = cached_entry.get("openai_expires_at", 0)

                if fid and exp_at > time.time() + DAY:  # reuse from chat cache
                    self.logger.info(
                        f"Reusing cached file {filename} → {fid} from chat meta (expires: {exp_at})"
                    )
                    # inject link
                    self._ensure_user_msg(body)["content"].insert(
                        0, {"type": "input_file", "file_id": fid}
                    )
                    continue

            # File not cached or expired - upload to OpenAI
            b = w["file"]["data"]["content"].encode()
            fid, exp_at, raw = await self._upload_file(
                file_bytes=b,
                filename=filename,
                api_key=v.API_KEY,
                base_url=v.BASE_URL,
            )

            # Store in file metadata (backward compatibility)
            meta = w["file"]["meta"].setdefault("data", {})
            meta.update(
                openai_file_id=fid,
                openai_expires_at=exp_at,
                hash=file_hash,
                openai_raw_response=raw,
            )

            # Store in Chat meta for future reuse
            if chat_id and Chats and v.ENABLE_CHAT_META_CACHE:
                await self._save_to_chat_meta(
                    chat_id=chat_id,
                    file_hash=file_hash,
                    filename=filename,
                    openai_file_id=fid,
                    expires_at=exp_at,
                )
                self.logger.info(
                    f"Uploaded and cached {filename} → {fid} in chat {chat_id}"
                )
            else:
                self.logger.info(f"Uploaded {filename} → {fid}")

            # inject link
            self._ensure_user_msg(body)["content"].insert(
                0, {"type": "input_file", "file_id": fid}
            )

        return body

    # ──────────────────────────────────────────────── Chat meta operations
    async def _get_chat_file_cache(self, chat_id: str) -> Dict[str, Dict]:
        """Retrieve file cache from Chat table meta field."""
        try:
            chat = Chats.get_chat_by_id(chat_id)
            if not chat:
                self.logger.debug(f"Chat {chat_id} not found")
                return {}

            meta = chat.meta or {}
            file_cache = meta.get("openai_file_cache", {})
            return file_cache
        except Exception as e:
            self.logger.error(f"Error loading chat file cache: {e}")
            return {}

    async def _save_to_chat_meta(
        self,
        chat_id: str,
        file_hash: str,
        filename: str,
        openai_file_id: str,
        expires_at: int,
    ) -> None:
        """Save file information to Chat table meta field."""
        try:
            chat = Chats.get_chat_by_id(chat_id)
            if not chat:
                self.logger.warning(f"Chat {chat_id} not found, cannot cache file")
                return

            # Get or create meta structure
            meta = chat.meta or {}
            file_cache = meta.get("openai_file_cache", {})

            # Store file info keyed by hash
            file_cache[file_hash] = {
                "filename": filename,
                "openai_file_id": openai_file_id,
                "openai_expires_at": expires_at,
                "uploaded_at": int(time.time()),
            }

            meta["openai_file_cache"] = file_cache

            # Update chat meta
            Chats.update_chat_by_id(chat_id, {"meta": meta})
            self.logger.debug(f"Saved file {filename} to chat {chat_id} meta")

        except Exception as e:
            self.logger.error(f"Error saving to chat meta: {e}")

    # ──────────────────────────────────────────────── HTTP session
    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self.session and not self.session.closed:
            return self.session
        self.logger.debug("Creating aiohttp session")
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(
                limit=50, limit_per_host=10, keepalive_timeout=75, ttl_dns_cache=300
            ),
            timeout=aiohttp.ClientTimeout(connect=30, sock_connect=30, sock_read=3600),
            json_serialize=lambda o: orjson.dumps(o).decode(),
        )
        return self.session

    # ──────────────────────────────────────────────── uploader
    async def _upload_file(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        api_key: str,
        base_url: str,
        purpose: str = "user_data",
    ) -> tuple[str, int, Dict[str, Any]]:
        """
        Upload & return (file_id, expires_at, full_json).  Handles >512 MB multipart.
        """
        s = await self._ensure_session()
        sz = len(file_bytes)
        mt = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        hdr = {"Authorization": f"Bearer {api_key}"}

        # —— one‑shot ———————————————————————————————
        if sz <= 512 * 1024 * 1024:
            fd = aiohttp.FormData()
            fd.add_field("file", file_bytes, filename=filename, content_type=mt)
            fd.add_field("purpose", purpose)
            async with s.post(f"{base_url}/files", data=fd, headers=hdr) as r:
                r.raise_for_status()
                j = await r.json()
                self.logger.debug("OpenAI /files → %s", j)
                return j["id"], j.get("expires_at", 0), j

        # —— multipart ——————————————————————————————
        json_hdr = {**hdr, "Content-Type": "application/json"}
        # 1 create upload
        c = await s.post(
            f"{base_url}/uploads",
            json={
                "purpose": purpose,
                "filename": filename,
                "bytes": sz,
                "mime_type": mt,
            },
            headers=json_hdr,
        )
        c.raise_for_status()
        up = await c.json()
        upload_id = up["id"]
        part_ids = []
        # 2 parts
        rdr = io.BytesIO(file_bytes)
        idx = 0
        while chunk := rdr.read(CHUNK_SIZE):
            idx += 1
            fd = aiohttp.FormData()
            fd.add_field(
                "data",
                chunk,
                filename=f"chunk{idx}",
                content_type="application/octet-stream",
            )
            async with s.post(
                f"{base_url}/uploads/{upload_id}/parts", data=fd, headers=hdr
            ) as pr:
                pr.raise_for_status()
                part_ids.append((await pr.json())["id"])
        # 3 complete
        cmp = await s.post(
            f"{base_url}/uploads/{upload_id}/complete",
            json={"part_ids": part_ids},
            headers=json_hdr,
        )
        cmp.raise_for_status()
        up_done = await cmp.json()
        file_obj = up_done["file"]
        self.logger.debug("OpenAI /uploads complete → %s", up_done)
        return file_obj["id"], file_obj.get("expires_at", 0), up_done

    # ─────────────────────────────────────────────── helpers
    @staticmethod
    def _calculate_hash(content: bytes) -> str:
        """Calculate SHA256 hash of file content."""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _ensure_user_msg(body: dict) -> dict:
        """
        Guarantee the last (or new) user message exists **and**
        its 'content' field is a mutable list of blocks.
        """
        if body.get("messages") and body["messages"][-1]["role"] == "user":
            msg = body["messages"][-1]
        else:
            msg = {"role": "user", "content": []}
            body.setdefault("messages", []).append(msg)

        # 🔑 normalise: wrap plain text into a block list
        if isinstance(msg.get("content"), str):
            msg["content"] = [{"type": "text", "text": msg["content"]}]
        elif msg.get("content") is None:
            msg["content"] = []

        return msg

    async def _emit_citation(
        self,
        emitter: Callable[[dict], Awaitable[None]] | None,
        document: str,
        source: str,
    ) -> None:
        if emitter:
            await emitter(
                {
                    "type": "citation",
                    "data": {
                        "document": [document],
                        "metadata": [
                            {
                                "date_accessed": datetime.datetime.utcnow().isoformat(),
                                "source": source,
                            }
                        ],
                        "source": {"name": source},
                    },
                }
            )

    # ─────────────────────────────────────────────── valves merge
    @staticmethod
    def _merge_valves(global_v, user_v) -> "Filter.Valves":
        upd = {
            k: v
            for k, v in user_v.model_dump().items()
            if v and str(v).lower() != "inherit"
        }
        return global_v.model_copy(update=upd)


# ───────────────────────────────────────────────────────────── Session logger
class SessionLogger:
    session_id = ContextVar("session_id", default=None)
    log_level = ContextVar("log_level", default=logging.INFO)
    logs = defaultdict(lambda: deque(maxlen=500))

    @classmethod
    def get_logger(cls, name="filter"):
        log = logging.getLogger(name)
        log.handlers.clear()
        log.setLevel(logging.DEBUG)
        log.propagate = False

        def _flt(r):
            r.session_id = cls.session_id.get()
            return r.levelno >= cls.log_level.get()

        log.addFilter(_flt)
        h_console = logging.StreamHandler(sys.stdout)
        h_console.setFormatter(
            logging.Formatter("[%(levelname)s] [%(session_id)s] %(message)s")
        )
        log.addHandler(h_console)
        h_mem = logging.Handler()
        h_mem.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        h_mem.emit = lambda r: (
            cls.logs[r.session_id].append(h_mem.format(r)) if r.session_id else None
        )
        log.addHandler(h_mem)
        return log
