import os
import time
from contextlib import asynccontextmanager
from typing import Optional

import litellm
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from litellm import completion
from litellm.caching.caching import Cache
from pydantic import BaseModel, Field, field_validator

from database import init_db, get_messages, save_message

load_dotenv()

LLM_KEYS = [
    key.strip()
    for key in os.getenv("LLM_API_KEYS", "").split(",")
    if key.strip()
]

LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "gemini/gemini-3.5-flash-lite"
)

ENABLE_FAILURE_SIMULATION = (
    os.getenv("ENABLE_FAILURE_SIMULATION", "false").lower() == "true"
)

litellm.cache = Cache(type="local")

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, concise AI assistant."
)

def parse_failure_simulation(header_value: Optional[str]):
    failures = {}

    if not ENABLE_FAILURE_SIMULATION or not header_value:
        return failures

    for item in header_value.split(","):
        item = item.strip()

        if "=" not in item:
            continue

        key_id, status_text = item.split("=", 1)

        key_id = key_id.strip()
        status_text = status_text.strip()

        try:
            status = int(status_text)
        except ValueError:
            continue

        if status in {429, 500, 502, 503}:
            failures[key_id] = status

    return failures

class ChatRequest(BaseModel):
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=128
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000
    )

    system_prompt: Optional[str] = None

    @field_validator("session_id", "message")
    @classmethod
    def must_not_be_blank(cls, value: str):
        value = value.strip()

        if not value:
            raise ValueError("must not be empty")

        return value


@asynccontextmanager
async def lifespan(app: FastAPI):

    init_db()

    yield


app = FastAPI(
    title="Lyftr AI Chatbot API",
    version="1.0.0",
    lifespan=lifespan
)

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173"
    ).split(",")
    if origin.strip()
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():

    return {
        "message": "Lyftr AI Chatbot backend is running"
    }


@app.get("/health")
def health():

    return {
        "status": "ok",
        "keys_configured": len(LLM_KEYS),
        "cache_enabled": True
    }


@app.get("/sessions/{session_id}/messages")
def session_messages(session_id: str):

    messages = get_messages(session_id)

    if not messages:
        raise HTTPException(
            status_code=404,
            detail="session not found"
        )

    return {
        "session_id": session_id,
        "messages": messages
    }

@app.post("/chat")
def chat(
    request: ChatRequest,
    x_simulate_failure: Optional[str] = Header(
        default=None,
        alias="X-Simulate-Failure"
    )
):
    history = get_messages(request.session_id)

    system_prompt = (
        request.system_prompt
        if request.system_prompt
        else DEFAULT_SYSTEM_PROMPT
    )

    llm_messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    for message in history:
        llm_messages.append(
            {
                "role": message["role"],
                "content": message["content"]
            }
        )

    llm_messages.append(
        {
            "role": "user",
            "content": request.message
        }
    )

    simulated_failures = parse_failure_simulation(
        x_simulate_failure
    )

    start_time = time.perf_counter()

    response = None
    successful_key_id = None
    fallback_attempts = 0
    cache_hit = False

    # Try every configured key in order.
    for index, api_key in enumerate(LLM_KEYS):

        key_id = f"key_{index + 1}"

        # Check whether this key should fail for this request.
        simulated_status = simulated_failures.get(
            key_id,
            simulated_failures.get("*")
        )

        if simulated_status is not None:
            fallback_attempts += 1
            continue

        try:
            response = completion(
                model=LLM_MODEL,
                messages=llm_messages,
                api_key=api_key,
                caching=True
            )

# LiteLLM marks cached responses in hidden response metadata.
            hidden_params = getattr(response, "_hidden_params", {}) or {}

            cache_hit = bool(
                hidden_params.get("cache_hit")
                or hidden_params.get("cached_response")
            )

            if cache_hit:
                successful_key_id = None
            else:
                successful_key_id = key_id

            break

        except Exception as e:
            print(f"LiteLLM error for {key_id}: {type(e).__name__}: {e}")
            fallback_attempts += 1
            continue

    # Every key failed.
    if response is None:
        raise HTTPException(
            status_code=503,
            detail="all providers unavailable"
        )

    latency_ms = int(
        (time.perf_counter() - start_time) * 1000
    )

    reply = response.choices[0].message.content

    usage = response.usage

    input_tokens = getattr(
        usage,
        "prompt_tokens",
        0
    ) or 0

    output_tokens = getattr(
        usage,
        "completion_tokens",
        0
    ) or 0

    metadata = {
    "resolution_source": (
        "LLM_CACHE"
        if cache_hit
        else "LIVE_INFERENCE"
    ),
    "model": LLM_MODEL,
    "latency_ms": latency_ms,
    "input_tokens": input_tokens,
    "output_tokens": output_tokens,
    "key_id": (
        None
        if cache_hit
        else successful_key_id
    ),
    "fallback_attempts": (
        0
        if cache_hit
        else fallback_attempts
    )
}

    # Only save after successful inference.
    save_message(
        session_id=request.session_id,
        role="user",
        content=request.message
    )

    save_message(
        session_id=request.session_id,
        role="assistant",
        content=reply,
        metadata=metadata
    )

    return {
        "session_id": request.session_id,
        "reply": reply,
        "metadata": metadata
    }
