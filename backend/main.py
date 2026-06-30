from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import json
from anthropic import AsyncAnthropic
from fastapi.responses import StreamingResponse
from datetime import datetime
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


def get_current_time() -> str:
    return datetime.now().isoformat(timespec="seconds")


TOOLS = [
    {
        "name": "get_current_time",
        "description": "Get the current date and time on the server. "
        "Use this whenever the user asks what time or date it is.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    }
]


def run_tool(name: str, tool_input: dict) -> str:
    if name == "get_current_time":
        return get_current_time()
    return f"Unknown tool: {name}"


def sse(obj) -> str:
    return f"data: {json.dumps(obj)}\n\n"


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


MAX_TURNS = 5


@app.post("/api/v1/chat/agent")
async def chat_agent(request: ChatRequest):
    async def event_generator():
        messages = [{"role": "user", "content": request.message}]
        try:
            for _ in range(MAX_TURNS):
                async with client.messages.stream(
                    model=MODEL,
                    max_tokens=1024,
                    tools=TOOLS,
                    messages=messages,
                ) as stream:
                    async for text in stream.text_stream:
                        yield sse({"type": "text", "text": text})
                    final = await stream.get_final_message()

                if final.stop_reason != "tool_use":
                    break

                # run every tool Claude asked for, collect the results
                tool_results = []
                for block in final.content:
                    if block.type == "tool_use":
                        yield sse(
                            {
                                "type": "tool_use",
                                "name": block.name,
                                "input": block.input,
                            }
                        )
                        result = run_tool(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )

                # feed the turn back so Claude can continue
                messages.append({"role": "assistant", "content": final.content})
                messages.append({"role": "user", "content": tool_results})
        except Exception as e:
            yield sse({"type": "error", "error": str(e)})
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
