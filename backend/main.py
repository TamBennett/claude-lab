from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import json
from anthropic import AsyncAnthropic
from fastapi.responses import StreamingResponse
# import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY from env (load_dotenv already ran)
MODEL = "claude-haiku-4-5-20251001"


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return ChatResponse(reply=f"Echo: {request.message}")


@app.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        try:
            async with client.messages.stream(
                model=MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": request.message}],
            ) as stream:
                async for text in stream.text_stream:
                    yield f"data: {json.dumps(text)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps(f'[ERROR] {e}')}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
