"""
DRAVION v.9 — Web Server
FastAPI backend: REST chat, session history, system metrics, vision.
"""
import asyncio, json, os, sys, time, warnings, logging, uuid, sqlite3, io, base64
from datetime import datetime
from contextlib import asynccontextmanager

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["POSTHOG_DISABLED"] = "true"
warnings.filterwarnings("ignore")

import types
pm = types.ModuleType("posthog")
pm.capture = lambda *a, **kw: None
pm.Posthog = type("Posthog", (), {"capture": lambda *a, **kw: None})
sys.modules["posthog"] = pm
for lib in ["httpx","chromadb","sentence_transformers","urllib3","posthog","openai._base_client","httpcore"]:
    logging.getLogger(lib).setLevel(logging.CRITICAL)

import psutil
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from brain.cortex import Cortex
from core.config import config

CHAT_DB = os.path.join(config.data_dir, "chat_sessions.db")

def _init_db():
    c = sqlite3.connect(CHAT_DB)
    c.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, title TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE)")
    c.commit(); c.close()

def _db(): return sqlite3.connect(CHAT_DB)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global boot_time
    _init_db()
    
    # Fallback if run standalone (not via main.py)
    if not hasattr(app.state, "cortex"):
        app.state.cortex = Cortex()
    if not hasattr(app.state, "speaker"):
        app.state.speaker = None

    boot_time = time.time()
    # Print omitted so main.py handles it
    yield

app = FastAPI(title="DRAVION v.9", lifespan=lifespan)

# Static files
static_dir = os.path.join(os.path.dirname(__file__), "ui", "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

class ChatReq(BaseModel):
    message: str
    session_id: str | None = None

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    p = os.path.join(os.path.dirname(__file__), "ui", "dravion_ui.html")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f: return HTMLResponse(f.read())
    return HTMLResponse("<h1>UI not found</h1>", status_code=404)

from fastapi import FastAPI, BackgroundTasks

@app.post("/api/chat")
async def chat(req: ChatReq, background_tasks: BackgroundTasks):
    sid = req.session_id
    c = _db()
    if not sid:
        sid = str(uuid.uuid4())[:8]
        title = req.message[:50] + ("..." if len(req.message) > 50 else "")
        c.execute("INSERT INTO sessions (id,title) VALUES (?,?)", (sid, title))
    c.execute("INSERT INTO messages (session_id,role,content) VALUES (?,?,?)", (sid,"user",req.message))
    c.execute("UPDATE sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (sid,))
    c.commit()
    # Print the user's message from UI to the terminal
    print(f"\n\033[93m[UI - You]: {req.message}\033[0m")
    
    try: 
        resp = await app.state.cortex.think(req.message)
    except Exception as e: 
        resp = f"System error: {e}"
        
    c.execute("INSERT INTO messages (session_id,role,content) VALUES (?,?,?)", (sid,"assistant",resp))
    c.commit(); c.close()
    
    # Print the assistant's response to the terminal
    print(f"\n\033[96m[DRAVION]: {resp}\033[0m\n")
    
    # Speak it if speaker is available
    if hasattr(app.state, 'speaker') and app.state.speaker:
        if hasattr(app.state, 'main_loop'):
            import asyncio
            fut = asyncio.run_coroutine_threadsafe(app.state.speaker.speak(resp), app.state.main_loop)
            def on_done(f):
                try: f.result()
                except Exception as e: print(f"\n\033[91m[TTS ERROR]: {e}\033[0m")
            fut.add_done_callback(on_done)
        else:
            background_tasks.add_task(app.state.speaker.speak, resp)
        
    return {"response": resp, "session_id": sid}

@app.get("/api/sessions")
def list_sessions():
    c = _db()
    rows = c.execute("SELECT id,title,created_at,updated_at FROM sessions ORDER BY updated_at DESC").fetchall()
    c.close()
    return [{"id":r[0],"title":r[1],"created_at":r[2],"updated_at":r[3]} for r in rows]

@app.get("/api/sessions/{sid}/messages")
def get_msgs(sid: str):
    c = _db()
    rows = c.execute("SELECT role,content,timestamp FROM messages WHERE session_id=? ORDER BY id", (sid,)).fetchall()
    c.close()
    return [{"role":r[0],"content":r[1],"timestamp":r[2]} for r in rows]

@app.delete("/api/sessions/{sid}")
def del_session(sid: str):
    c = _db()
    c.execute("DELETE FROM messages WHERE session_id=?", (sid,))
    c.execute("DELETE FROM sessions WHERE id=?", (sid,))
    c.commit(); c.close()
    return {"status":"deleted"}

@app.get("/api/system")
def sys_metrics():
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    up = int(time.time() - (boot_time or time.time()))
    h,r = divmod(up,3600); m,s = divmod(r,60)
    return {"cpu_percent":cpu,"ram_used_gb":round(mem.used/(1024**3),1),"ram_total_gb":round(mem.total/(1024**3),1),"ram_percent":mem.percent,"uptime":f"{h:02d}:{m:02d}:{s:02d}","brain_mode":app.state.cortex.mode if hasattr(app.state, 'cortex') else "unknown"}

@app.post("/api/mode/{mode}")
def switch_mode(mode: str):
    if mode in ("auto","cloud","local","gemini"):
        if hasattr(app.state, 'cortex'):
            app.state.cortex.switch_mode(mode)
        return {"mode":mode}
    return {"error":"Invalid mode"}

@app.get("/api/vision/screenshot")
def screenshot():
    try:
        import pyautogui
        img = pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return {"image":f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"}
    except Exception as e:
        return {"error":str(e)}

if __name__ == "__main__":
    uvicorn.run("web_server:app", host="127.0.0.1", port=8000)
