
import os
import json
import uuid
import sqlite3
import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from google import genai
from google.genai import types


# =====================================================
# GEO MIND AI - AGENT ENGINE v0.2
# =====================================================

APP_NAME = "GEO MIND AI"
APP_VERSION = "0.2.0"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv(
    "DATABASE_PATH",
    os.path.join(BASE_DIR, "geo_mind.db")
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

ALLOWED_ORIGINS = [
    item.strip()
    for item in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500"
    ).split(",")
    if item.strip()
]

client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY
    else None
)


# =====================================================
# DATABASE
# =====================================================

def get_db():
    connection = sqlite3.connect(DB_PATH, timeout=20)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                goal TEXT NOT NULL,
                status TEXT NOT NULL,
                plan TEXT NOT NULL,
                result TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_message TEXT NOT NULL,
                assistant_reply TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


# =====================================================
# APP CONFIGURATION
# =====================================================

app = FastAPI(
    title="GEO MIND AI Agent API",
    description="Personal Geomatics and AI Agent",
    version=APP_VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


# =====================================================
# REQUEST MODELS
# =====================================================

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    history: list[dict] = Field(default_factory=list, max_length=20)
    conversation_id: Optional[str] = Field(default=None, max_length=100)


class AgentRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=6000)


class TaskUpdateRequest(BaseModel):
    status: str = Field(
        pattern="^(planned|in_progress|completed|failed|cancelled)$"
    )
    result: Optional[str] = Field(default=None, max_length=12000)


# =====================================================
# AGENT PERSONALITY
# =====================================================

SYSTEM_INSTRUCTION = """
You are GEO MIND AI, a specialized intelligent assistant and agent.

Your expertise includes:
- GIS and Geomatics
- ArcGIS Pro and QGIS
- Remote Sensing
- Sentinel and Landsat imagery
- Land Surveying
- Civil 3D and AutoCAD
- Python, C++, JavaScript and web development
- Project planning and technical problem solving

Rules:
1. Respond in Arabic when the user writes Arabic.
2. Be accurate and explain important technical steps.
3. Never claim that you executed an action unless it actually happened.
4. Never invent file contents, calculations or external results.
5. Ask for clarification when essential information is missing.
6. Do not expose API keys or private configuration.
7. Never execute arbitrary code or shell commands.
8. Distinguish between a proposed plan and completed work.
9. Break complicated goals into clear, ordered steps.
10. Be helpful, professional and concise.
"""


# =====================================================
# GEMINI ENGINE
# =====================================================

def require_model():
    if not client:
        raise HTTPException(
            status_code=503,
            detail="Gemini API غير متصل. أضف GEMINI_API_KEY في إعدادات الخادم."
        )


def generate_ai_response(contents, system_instruction=None):
    require_model()

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction or SYSTEM_INSTRUCTION,
            temperature=0.5,
            max_output_tokens=4096
        )
    )

    answer = response.text

    if not answer:
        raise RuntimeError("Gemini returned an empty response.")

    return answer


async def ask_gemini(contents, system_instruction=None):
    try:
        return await asyncio.to_thread(
            generate_ai_response,
            contents,
            system_instruction
        )
    except HTTPException:
        raise
    except Exception as error:
        print("Gemini error:", str(error))
        raise HTTPException(
            status_code=502,
            detail="تعذر الحصول على رد من Gemini. راجع إعدادات النموذج وحالة الخدمة."
        )


# =====================================================
# HEALTH CHECK
# =====================================================

@app.get("/")
def root():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "engine": "Gemini" if client else "not_configured"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "geo-mind-ai",
        "version": APP_VERSION,
        "model_connected": client is not None,
        "model": GEMINI_MODEL if client else None
    }


# =====================================================
# CHAT ENGINE
# =====================================================

@app.post("/api/chat")
async def chat(payload: ChatRequest):

    contents = []

    for item in payload.history[-20:]:
        role = item.get("role")
        text = item.get("text", "")

        if role not in ("user", "model"):
            continue

        if not isinstance(text, str) or not text.strip():
            continue

        contents.append({
            "role": role,
            "parts": [{"text": text[:12000]}]
        })

    contents.append({
        "role": "user",
        "parts": [{"text": payload.message}]
    })

    reply = await ask_gemini(contents)

    conversation_id = payload.conversation_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with get_db() as db:
        db.execute(
            """
            INSERT INTO conversations
            (id, user_message, assistant_reply, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                conversation_id,
                payload.message,
                reply,
                now
            )
        )
        db.commit()

    return {
        "reply": reply,
        "model_connected": True,
        "model": GEMINI_MODEL,
        "conversation_id": conversation_id
    }


# =====================================================
# AGENT PLANNER
# =====================================================

PLANNER_INSTRUCTION = """
You are the planning engine of GEO MIND AI.

Convert the user's goal into a structured JSON plan.

Return ONLY valid JSON using this structure:

{
  "title": "short task title",
  "summary": "short explanation",
  "steps": [
    {
      "id": 1,
      "title": "step title",
      "description": "what needs to happen",
      "tool": "none",
      "status": "planned"
    }
  ]
}

Rules:
- Create between 2 and 8 steps.
- Use Arabic when the goal is Arabic.
- Do not claim that any step has been executed.
- Use tool="none" unless a registered tool is explicitly available.
- Never suggest executing arbitrary shell commands or unknown code.
- Make the steps specific and achievable.
"""


def extract_json(text):
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start < 0 or end < start:
        raise ValueError("Invalid JSON plan")

    return json.loads(cleaned[start:end + 1])


@app.post("/api/agent/plan")
async def create_agent_plan(payload: AgentRequest):

    raw = await ask_gemini(
        [
            {
                "role": "user",
                "parts": [{"text": payload.goal}]
            }
        ],
        PLANNER_INSTRUCTION
    )

    try:
        plan = extract_json(raw)

        if not isinstance(plan.get("steps"), list):
            raise ValueError("Missing steps")

        if not 2 <= len(plan["steps"]) <= 8:
            raise ValueError("Invalid step count")

    except (ValueError, TypeError, json.JSONDecodeError):
        raise HTTPException(
            status_code=502,
            detail="تعذر إنشاء خطة منظمة. حاول صياغة الهدف بطريقة أوضح."
        )

    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    plan["steps"] = [
        {
            **step,
            "status": "planned",
            "tool": "none"
        }
        for step in plan["steps"]
    ]

    with get_db() as db:
        db.execute(
            """
            INSERT INTO tasks
            (id, title, goal, status, plan, result, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                str(plan.get("title", "GEO MIND Task"))[:200],
                payload.goal,
                "planned",
                json.dumps(plan, ensure_ascii=False),
                None,
                now,
                now
            )
        )
        db.commit()

    return {
        "success": True,
        "task_id": task_id,
        "status": "planned",
        "plan": plan
    }


# =====================================================
# TASK MANAGEMENT
# =====================================================

@app.get("/api/tasks")
def list_tasks():

    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, title, goal, status, created_at, updated_at
            FROM tasks
            ORDER BY created_at DESC
            LIMIT 50
            """
        ).fetchall()

    return {
        "tasks": [dict(row) for row in rows]
    }


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):

    with get_db() as db:
        row = db.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Task not found")

    task = dict(row)
    task["plan"] = json.loads(task["plan"])

    return task


@app.post("/api/tasks/{task_id}/status")
def update_task(task_id: str, payload: TaskUpdateRequest):

    now = datetime.now(timezone.utc).isoformat()

    with get_db() as db:
        cursor = db.execute(
            """
            UPDATE tasks
            SET status = ?, result = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload.status,
                payload.result,
                now,
                task_id
            )
        )

        db.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")

    return {
        "success": True,
        "task_id": task_id,
        "status": payload.status
    }


# =====================================================
# CONVERSATION MEMORY
# =====================================================

@app.get("/api/memory/recent")
def recent_memory():

    with get_db() as db:
        rows = db.execute(
            """
            SELECT id, user_message, assistant_reply, created_at
            FROM conversations
            ORDER BY created_at DESC
            LIMIT 30
            """
        ).fetchall()

    return {
        "memory": [dict(row) for row in rows]
    }


@app.delete("/api/memory")
def clear_memory():

    with get_db() as db:
        db.execute("DELETE FROM conversations")
        db.commit()

    return {
        "success": True,
        "message": "Conversation memory cleared."
    }


# =====================================================
# SAFE TOOL REGISTRY
# =====================================================

@app.get("/api/tools")
def list_tools():

    return {
        "tools": [
            {
                "name": "task_planner",
                "description": "Create a structured task plan.",
                "enabled": True
            },
            {
                "name": "conversation_memory",
                "description": "Store and retrieve conversation history.",
                "enabled": True
            },
            {
                "name": "project_workspace",
                "description": "Manage future project operations.",
                "enabled": False
            },
            {
                "name": "code_execution",
                "description": "Arbitrary code execution is disabled.",
                "enabled": False
            },
            {
                "name": "shell_commands",
                "description": "Shell command execution is disabled.",
                "enabled": False
            }
        ]
    }
