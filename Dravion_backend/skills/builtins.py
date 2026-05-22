"""
DRAVION v.9 — Built-in Skills
Real capabilities: Task management, Gmail, Google APIs, system control.
"""
import os, json, subprocess, platform, psutil, webbrowser, sqlite3
from datetime import datetime
from core.logger import log
from core.audit import audit
from skills import google_suite
from skills import os_control
from skills.browser_auto import browser_agent
from skills.reminders import reminder_system
from skills.security import security_agent
from skills import sandbox
from skills import clipboard_intel
from skills import desktop_automation
from skills import document_intel
from vision import perception
from memory.adaptive import adaptive_memory
from skills.screen_agent import screen_agent

# ─── Helper to build tool defs ───
def _fn(name, desc, params=None):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": params or {"type": "object", "properties": {}}}}

def _p(props, required=None):
    d = {"type": "object", "properties": props}
    if required: d["required"] = required
    return d

# ─── Tool Definitions ───
TOOL_DEFINITIONS = [
    # Time
    _fn("get_datetime", "Get current date, time, day of week."),

    # System
    _fn("get_system_info", "Get full system info: CPU, RAM, battery, disk, uptime, process count, OS version."),
    _fn("list_processes", "List top running processes by CPU or memory.",
        _p({"sort_by": {"type": "string", "description": "'cpu' or 'memory'"}})),
    _fn("wifi_info", "Get WiFi network name, signal, and IP address."),

    # Apps & Windows
    _fn("open_app", "Open an app: chrome, vscode, spotify, notepad, explorer, discord, telegram, whatsapp, settings, calculator, task manager.",
        _p({"app_name": {"type": "string", "description": "App to open"}}, ["app_name"])),
    _fn("close_app", "Close/kill a running application.",
        _p({"app_name": {"type": "string", "description": "App to close (e.g. chrome, notepad)"}}, ["app_name"])),
    _fn("switch_window", "Switch to another open window/app. Like Alt+Tab but smarter.",
        _p({"app_name": {"type": "string", "description": "App to switch to (e.g. chrome, vscode, explorer)"}}, ["app_name"])),
    _fn("minimize_all", "Minimize all windows. Show desktop."),
    _fn("close_current_window", "Close the currently active/focused window."),

    # PC Control
    _fn("lock_pc", "Lock Boss's PC."),
    _fn("shutdown_pc", "Shutdown PC.", _p({"delay": {"type": "integer", "description": "Seconds. Default: 30"}})),
    _fn("restart_pc", "Restart PC.", _p({"delay": {"type": "integer", "description": "Seconds. Default: 30"}})),
    _fn("sleep_pc", "Put PC to sleep."),
    _fn("set_volume", "Set volume 0-100.", _p({"level": {"type": "integer", "description": "Volume 0-100"}}, ["level"])),

    # Shell
    _fn("run_shell_command", "Execute an actual PowerShell system command (e.g. ipconfig, ping, ls, Get-Process). ONLY for real shell commands — NEVER for answering questions or explaining concepts.",
        _p({"command": {"type": "string", "description": "A valid PowerShell command (NOT natural language)"}}, ["command"])),

    # Screenshots, Vision & Clipboard
    _fn("take_screenshot", "Take screenshot, save to Desktop."),
    _fn("analyze_screen", "Look at Boss's screen and describe what's on it. Can answer questions about what's visible.",
        _p({"question": {"type": "string", "description": "Specific question about the screen. Default: describe everything"}})),
    _fn("see_webcam", "Look through the webcam camera and describe what you see.",
        _p({"question": {"type": "string", "description": "Specific question about what the camera sees"}})),
    _fn("ocr_screen", "Read/extract all text visible on Boss's screen using OCR."),
    _fn("clipboard_read", "Read clipboard content."),
    _fn("clipboard_write", "Copy text to clipboard.",
        _p({"text": {"type": "string", "description": "Text to copy"}}, ["text"])),

    # Files
    _fn("search_files", "Search for files by name on PC.",
        _p({"query": {"type": "string", "description": "File name/pattern"}, "directory": {"type": "string", "description": "Where to search. Default: home"}}, ["query"])),
    _fn("create_file", "Create a new file with content on Desktop.",
        _p({"filename": {"type": "string", "description": "File name (saved to Desktop)"}, "content": {"type": "string", "description": "File content"}}, ["filename", "content"])),
    _fn("read_file", "Read a file's contents.",
        _p({"path": {"type": "string", "description": "Full file path"}}, ["path"])),
    _fn("list_directory", "List files in a folder.",
        _p({"path": {"type": "string", "description": "Folder path. Default: Desktop"}})),

    # Task List
    _fn("add_task", "Add a task to Boss's to-do list.",
        _p({"task": {"type": "string", "description": "The task to add"}, "priority": {"type": "string", "description": "high, medium, or low. Default: medium"}}, ["task"])),
    _fn("list_tasks", "Show all pending tasks on Boss's to-do list."),
    _fn("complete_task", "Mark a task as done by its number or name.",
        _p({"task_id": {"type": "string", "description": "Task number or partial name to match"}}, ["task_id"])),
    _fn("delete_task", "Delete a task from the list.",
        _p({"task_id": {"type": "string", "description": "Task number or partial name"}}, ["task_id"])),

    # Adaptive Memory
    _fn("what_do_you_know", "Show what DRAVION has learned about Boss — preferences, habits, facts, behaviors."),
    _fn("remember_this", "Manually teach DRAVION a fact about Boss.",
        _p({"fact": {"type": "string", "description": "The fact to remember"}, "category": {"type": "string", "description": "preference, behavior, fact, dislike, habit, project. Default: fact"}}, ["fact"])),

    # Web & Search
    _fn("open_url", "Open a URL in browser.",
        _p({"url": {"type": "string", "description": "URL"}}, ["url"])),
    _fn("google_search_open", "Google search in browser.",
        _p({"query": {"type": "string", "description": "Search query"}}, ["query"])),
    _fn("youtube_play", "Play a song, music, or video on YouTube. ALWAYS use this for 'play [song]' requests — NOT screen_do. Opens the video directly in browser.",
        _p({"query": {"type": "string", "description": "Song name or video to search and play"}}, ["query"])),
    _fn("web_search", "Search web and return results (not just open browser).",
        _p({"query": {"type": "string", "description": "Search query"}}, ["query"])),

    # Weather
    _fn("get_weather", "Get current weather for a city.",
        _p({"city": {"type": "string", "description": "City. Default: Banswara"}})),

    # Gmail
    _fn("read_gmail", "Read Boss's recent Gmail emails. Shows sender, subject, and snippet.",
        _p({"count": {"type": "integer", "description": "Number of emails. Default: 5"}})),
    _fn("send_email", "Send an email using Gmail.",
        _p({"to": {"type": "string", "description": "Recipient email"}, "subject": {"type": "string", "description": "Email subject"}, "body": {"type": "string", "description": "Email body content"}}, ["to", "subject", "body"])),

    # Google Calendar
    _fn("read_calendar", "Read Boss's upcoming Google Calendar events.",
        _p({"count": {"type": "integer", "description": "Number of events. Default: 5"}})),

    # Google Translate
    _fn("translate_text", "Translate text between languages.",
        _p({"text": {"type": "string", "description": "Text to translate"}, "to_lang": {"type": "string", "description": "Target language code (hi, es, fr, etc). Default: hi (Hindi)"}, "from_lang": {"type": "string", "description": "Source language. Default: auto-detect"}}, ["text"])),

    # Google Maps
    _fn("get_directions", "Get directions/distance between two places.",
        _p({"origin": {"type": "string", "description": "Starting location"}, "destination": {"type": "string", "description": "Destination"}}, ["origin", "destination"])),

    # ── Browser Automation ──
    _fn("browse_page", "Navigate to a URL and get the page text content.",
        _p({"url": {"type": "string", "description": "URL to visit"}}, ["url"])),
    _fn("screenshot_url", "Take a screenshot of a webpage.",
        _p({"url": {"type": "string", "description": "URL to screenshot"}}, ["url"])),
    _fn("extract_links", "Extract all links from a webpage.",
        _p({"url": {"type": "string", "description": "URL to extract from"}}, ["url"])),

    # ── Reminders & Alarms ──
    _fn("set_reminder", "Set a reminder for Boss. Supports: 'in 30 minutes', 'at 7:30 PM'.",
        _p({"reminder_text": {"type": "string", "description": "Full reminder text including time, e.g. 'in 30 minutes call mom'"}}, ["reminder_text"])),
    _fn("list_reminders", "Show all pending reminders and alarms."),
    _fn("cancel_reminder", "Cancel a reminder by its ID number.",
        _p({"reminder_id": {"type": "integer", "description": "Reminder ID to cancel"}}, ["reminder_id"])),

    # ── Security / OSINT ──
    _fn("username_osint", "Run OSINT on a username — check which platforms it exists on.",
        _p({"username": {"type": "string", "description": "Username to investigate"}}, ["username"])),
    _fn("cve_lookup", "Search for CVE vulnerabilities by software name or CVE ID.",
        _p({"query": {"type": "string", "description": "Software name or CVE ID (e.g. 'apache' or 'CVE-2024-1234')"}}, ["query"])),
    _fn("port_scan", "Scan ports on a target IP or domain.",
        _p({"target": {"type": "string", "description": "IP or domain to scan"}, "ports": {"type": "string", "description": "Comma-separated ports or 'common'. Default: common"}}, ["target"])),
    _fn("ip_lookup", "Get ISP, location, and org info for an IP or domain.",
        _p({"target": {"type": "string", "description": "IP or domain"}}, ["target"])),

    # ── Code Execution ──
    _fn("run_python", "Execute Python code safely in a sandbox.",
        _p({"code": {"type": "string", "description": "Python code to execute"}}, ["code"])),

    # ── Clipboard Intelligence ──
    _fn("smart_clipboard", "Analyze what's in the clipboard — detect type and suggest actions."),

    # ── Desktop Automation ──
    _fn("mouse_move", "Move mouse to x, y coordinates.",
        _p({"x": {"type": "integer"}, "y": {"type": "integer"}}, ["x", "y"])),
    _fn("mouse_click", "Click mouse button.",
        _p({"x": {"type": "integer"}, "y": {"type": "integer"}, "button": {"type": "string", "description": "left, right, or middle"}})),
    _fn("keyboard_type", "Type text.",
        _p({"text": {"type": "string"}}, ["text"])),
    _fn("keyboard_press", "Press a single key (e.g., enter, esc, win).",
        _p({"key": {"type": "string"}}, ["key"])),
    _fn("keyboard_hotkey", "Press a combination of keys (e.g., ctrl, c).",
        _p({"keys": {"type": "array", "items": {"type": "string"}}}, ["keys"])),
        
    # ── Document Intelligence ──
    _fn("read_document", "Read text from a PDF or DOCX file.",
        _p({"path": {"type": "string", "description": "Absolute path to the document"}}, ["path"])),

    # ── Screen Agent (Vision-Guided GUI Automation) ──
    _fn("screen_do", "Autonomously operate ANY app on screen using vision. Dravion sees the screen, clicks, types, scrolls — like a human. Use for complex multi-step GUI tasks: 'open YouTube and play lofi music', 'go to Gmail and reply to the latest email', 'open VS Code and create a new file'. Narrates progress in real time.",
        _p({"instruction": {"type": "string", "description": "Natural language instruction for what to do on screen, e.g. 'open Chrome, go to YouTube, search for lofi music and play the first result'"}}, ["instruction"])),
    _fn("screen_stop", "Emergency stop the Screen Agent if it's doing something wrong."),

    # ── Memory & Audit ──
    _fn("consolidate_memory", "Run memory consolidation — promote important conversations to long-term memory."),
    _fn("activity_report", "Show what DRAVION did today — full audit log."),
]

# ─── Task DB Setup ───
TASK_DB = os.path.join(os.path.expanduser("~"), ".dravion_tasks.db")

def _get_task_db():
    conn = sqlite3.connect(TASK_DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT NOT NULL,
        priority TEXT DEFAULT 'medium',
        status TEXT DEFAULT 'pending',
        created_at TEXT,
        completed_at TEXT
    )""")
    conn.commit()
    return conn

# ─── Tool Execution ───
async def execute_tool(name: str, args: dict) -> str:
    if args is None:
        args = {}
    try:
        if name == "get_datetime":
            now = datetime.now()
            return json.dumps({"date": now.strftime("%d %B %Y"), "day": now.strftime("%A"), "time": now.strftime("%I:%M %p")})

        elif name == "get_system_info":
            disk = psutil.disk_usage('C:\\')
            boot = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot
            h, m = divmod(int(uptime.total_seconds()) // 60, 60)
            info = {
                "os": f"{platform.system()} {platform.release()} ({platform.version()})",
                "cpu": f"{psutil.cpu_percent(interval=1)}% ({psutil.cpu_count()} cores)",
                "ram": f"{psutil.virtual_memory().percent}% of {psutil.virtual_memory().total // (1024**3)} GB",
                "disk_C": f"{disk.free // (1024**3)} GB free of {disk.total // (1024**3)} GB",
                "uptime": f"{h}h {m}m",
                "processes": len(psutil.pids()),
            }
            try:
                bat = psutil.sensors_battery()
                if bat: info["battery"] = f"{bat.percent}%{' (charging)' if bat.power_plugged else ''}"
            except: pass
            return json.dumps(info)

        elif name == "list_processes":
            sort_by = args.get("sort_by", "cpu")
            procs = []
            for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
                try: procs.append(p.info)
                except: pass
            key = 'cpu_percent' if sort_by == 'cpu' else 'memory_percent'
            procs.sort(key=lambda x: x.get(key, 0) or 0, reverse=True)
            lines = [f"{p['name']}: CPU {p.get('cpu_percent',0):.1f}% | RAM {p.get('memory_percent',0):.1f}%" for p in procs[:10]]
            return "\n".join(lines)

        elif name == "wifi_info":
            r = subprocess.run(["powershell", "-Command", "netsh wlan show interfaces | Select-String 'SSID|Signal|State'"], capture_output=True, text=True, timeout=5)
            ip = subprocess.run(["powershell", "-Command", "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -like '*Wi-Fi*'}).IPAddress"], capture_output=True, text=True, timeout=5)
            return f"{r.stdout.strip()}\nIP: {ip.stdout.strip()}"

        # ── Apps & Windows ──
        elif name == "open_app":
            app = args["app_name"].lower().strip()
            return os_control.smart_open_app(app)

        elif name == "close_app":
            app = args["app_name"].lower().strip()
            return os_control.smart_close_app(app)

        elif name == "switch_window":
            app = args["app_name"].lower().strip()
            # Use PowerShell to bring window to front
            ps = f"""
            $p = Get-Process | Where-Object {{$_.MainWindowTitle -ne '' -and $_.ProcessName -like '*{app}*'}} | Select-Object -First 1
            if ($p) {{
                $sig = '[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);'
                Add-Type -MemberDefinition $sig -Name Win -Namespace Native
                [Native.Win]::SetForegroundWindow($p.MainWindowHandle)
                $p.ProcessName
            }} else {{ 'not_found' }}
            """
            r = subprocess.run(["powershell", "-Command", ps], capture_output=True, text=True, timeout=5)
            out = r.stdout.strip()
            if out == "not_found":
                return f"No window found for '{app}'. Try opening it first."
            return f"Switched to {out}."

        elif name == "minimize_all":
            subprocess.run(["powershell", "-Command", "(New-Object -ComObject Shell.Application).MinimizeAll()"], capture_output=True, timeout=5)
            return "All windows minimized. Desktop shown."

        elif name == "close_current_window":
            import pyautogui
            pyautogui.hotkey('alt', 'F4')
            return "Closed the active window."

        # ── PC Control ──
        elif name == "lock_pc":
            subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "PC locked."

        elif name == "shutdown_pc":
            d = args.get("delay", 30)
            subprocess.Popen(f"shutdown /s /t {d}", shell=True)
            return f"Shutting down in {d}s. Say 'cancel shutdown' or run 'shutdown /a'."

        elif name == "restart_pc":
            d = args.get("delay", 30)
            subprocess.Popen(f"shutdown /r /t {d}", shell=True)
            return f"Restarting in {d}s."

        elif name == "sleep_pc":
            subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return "PC going to sleep."

        elif name == "set_volume":
            level = args["level"]
            ps = f'$wshell = New-Object -ComObject WScript.Shell; 1..50 | ForEach-Object {{ $wshell.SendKeys([char]174) }}; $steps = [math]::Round({level} / 2); 1..$steps | ForEach-Object {{ $wshell.SendKeys([char]175) }}'
            subprocess.run(["powershell", "-Command", ps], capture_output=True, timeout=10)
            return f"Volume set to ~{level}%."

        elif name == "run_shell_command":
            cmd = args["command"]
            # Guard: reject natural language masquerading as shell commands
            words = cmd.split()
            has_shell_chars = any(c in cmd for c in ['|', '>', '<', '$', '-', '\\', '/', '.', ':', '='])
            if len(words) > 8 and not has_shell_chars:
                return "(Rejected: that looks like natural language, not a shell command. Answer knowledge questions directly without tools.)"
            log.info("shell_exec", cmd=cmd[:60])
            r = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=30)
            return (r.stdout.strip() or r.stderr.strip() or "(no output)")[:2000]

        # ── Screenshot & Vision ──
        elif name == "take_screenshot":
            return perception.save_last_capture() if perception._last_capture else (perception.capture("screen") and perception.save_last_capture())

        elif name == "analyze_screen":
            question = args.get("question", "Describe what's on this screen in detail.")
            return await perception.analyze_screen(question)

        elif name == "see_webcam":
            question = args.get("question", "Describe what you see from this camera.")
            return await perception.analyze_webcam(question)

        elif name == "ocr_screen":
            return perception.ocr_screen()

        elif name == "clipboard_read":
            r = subprocess.run(["powershell", "-Command", "Get-Clipboard"], capture_output=True, text=True, timeout=5)
            return r.stdout.strip() or "(clipboard empty)"

        elif name == "clipboard_write":
            import pyperclip
            pyperclip.copy(args["text"])
            return f"Copied to clipboard."

        # ── Files ──
        elif name == "search_files":
            q = args["query"]
            d = args.get("directory", os.path.expanduser("~"))
            r = subprocess.run(["powershell", "-Command", f"Get-ChildItem -Path '{d}' -Recurse -Filter '*{q}*' -ErrorAction SilentlyContinue | Select-Object -First 10 FullName | Format-Table -HideTableHeaders"], capture_output=True, text=True, timeout=15)
            return r.stdout.strip() or f"No files matching '{q}'."

        elif name == "create_file":
            path = os.path.join(os.path.expanduser("~"), "Desktop", args["filename"])
            with open(path, "w", encoding="utf-8") as f:
                f.write(args["content"])
            return f"Created: {path}"

        elif name == "read_file":
            path = args["path"]
            if not os.path.exists(path): return f"File not found: {path}"
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(5000) or "(empty)"

        elif name == "list_directory":
            path = args.get("path", os.path.join(os.path.expanduser("~"), "Desktop"))
            if not os.path.isdir(path): return f"Not a directory: {path}"
            items = sorted(os.listdir(path))[:30]
            return "\n".join(f"{'[DIR] ' if os.path.isdir(os.path.join(path, i)) else '      '}{i}" for i in items)

        # ── Task List ──
        elif name == "add_task":
            conn = _get_task_db()
            conn.execute("INSERT INTO tasks (task, priority, created_at) VALUES (?, ?, ?)",
                         (args["task"], args.get("priority", "medium"), datetime.now().isoformat()))
            conn.commit(); conn.close()
            return f"Task added: {args['task']}"

        elif name == "list_tasks":
            conn = _get_task_db()
            rows = conn.execute("SELECT id, task, priority, created_at FROM tasks WHERE status='pending' ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END").fetchall()
            conn.close()
            if not rows: return "No pending tasks, Boss. You're free."
            lines = [f"{r[0]}. [{r[2].upper()}] {r[1]}" for r in rows]
            return f"Pending tasks:\n" + "\n".join(lines)

        elif name == "complete_task":
            conn = _get_task_db()
            tid = args["task_id"]
            if tid.isdigit():
                conn.execute("UPDATE tasks SET status='done', completed_at=? WHERE id=?", (datetime.now().isoformat(), int(tid)))
            else:
                conn.execute("UPDATE tasks SET status='done', completed_at=? WHERE task LIKE ? AND status='pending'", (datetime.now().isoformat(), f"%{tid}%"))
            conn.commit(); conn.close()
            return f"Task marked done."

        elif name == "delete_task":
            conn = _get_task_db()
            tid = args["task_id"]
            if tid.isdigit():
                conn.execute("DELETE FROM tasks WHERE id=?", (int(tid),))
            else:
                conn.execute("DELETE FROM tasks WHERE task LIKE ?", (f"%{tid}%",))
            conn.commit(); conn.close()
            return f"Task deleted."

        # ── Web ──
        elif name == "open_url":
            webbrowser.open(args["url"])
            return f"Opened: {args['url']}"

        elif name == "google_search_open":
            webbrowser.open(f"https://www.google.com/search?q={args['query'].replace(' ', '+')}")
            return f"Searching Google for: {args['query']}"

        elif name == "youtube_play":
            import urllib.request, urllib.parse, re
            query = args['query']
            try:
                # Fetch YouTube search results and extract first video ID
                search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
                req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
                html = urllib.request.urlopen(req, timeout=8).read().decode("utf-8", errors="ignore")
                match = re.search(r'watch\?v=([a-zA-Z0-9_-]{11})', html)
                if match:
                    video_id = match.group(1)
                    webbrowser.open(f"https://www.youtube.com/watch?v={video_id}&autoplay=1")
                    return f"Playing: {query}"
            except Exception:
                pass
            # Fallback: just open search results
            webbrowser.open(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}")
            return f"Opened YouTube search for: {query}"

        elif name == "web_search":
            import aiohttp
            q = args["query"]
            api_key = os.environ.get("SERPAPI_KEY", "")
            if not api_key:
                webbrowser.open(f"https://www.google.com/search?q={q.replace(' ', '+')}")
                return f"No SerpAPI key. Opened Google for: {q}"
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(f"https://serpapi.com/search.json?q={q}&api_key={api_key}&num=5") as r:
                        if r.status == 200:
                            data = await r.json()
                            results = []
                            if "answer_box" in data:
                                ab = data["answer_box"]
                                results.append(f"Answer: {ab.get('answer', ab.get('snippet', ''))}")
                            for item in data.get("organic_results", [])[:3]:
                                results.append(f"- {item.get('title','')}: {item.get('snippet','')}")
                            return "\n".join(results) or "No results."
                        return f"Search error {r.status}"
            except Exception as e:
                return f"Search failed: {e}"

        # ── Weather ──
        elif name == "get_weather":
            import aiohttp
            city = args.get("city", "Banswara")
            city_map = {"khoran": "Banswara", "sabla": "Dungarpur"}
            city = city_map.get(city.lower(), city)
            api_key = os.environ.get("WEATHER_API_KEY", "")
            if not api_key: return "WEATHER_API_KEY not set in .env"
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric") as r:
                        if r.status == 200:
                            d = await r.json()
                            return json.dumps({"city": city, "temp": f"{d['main']['temp']}°C", "feels_like": f"{d['main']['feels_like']}°C", "desc": d["weather"][0]["description"], "humidity": f"{d['main']['humidity']}%", "wind": f"{d['wind']['speed']} m/s"})
                        return f"Weather error {r.status} for {city}"
            except Exception as e:
                return f"Weather failed: {e}"

        # ── Gmail ──
        elif name == "read_gmail":
            count = args.get("count", 5)
            return google_suite.get_recent_emails(count)
            
        elif name == "send_email":
            return google_suite.send_email(args["to"], args["subject"], args["body"])
            
        # ── Calendar ──
        elif name == "read_calendar":
            count = args.get("count", 5)
            return google_suite.get_upcoming_calendar_events(count)

        # ── Translate ──
        elif name == "translate_text":
            import aiohttp
            text = args["text"]
            to_lang = args.get("to_lang", "hi")
            from_lang = args.get("from_lang", "auto")
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(f"https://api.mymemory.translated.net/get?q={text[:500]}&langpair={from_lang}|{to_lang}") as r:
                        if r.status == 200:
                            d = await r.json()
                            translated = d.get("responseData", {}).get("translatedText", "")
                            return f"Translation ({to_lang}): {translated}"
                        return "Translation API error."
            except Exception as e:
                return f"Translation failed: {e}"

        # ── Directions ──
        elif name == "get_directions":
            import aiohttp
            origin = args["origin"]
            dest = args["destination"]
            api_key = os.environ.get("GOOGLE_MAPS_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
            if not api_key: return "GOOGLE_MAPS_API_KEY not set in .env"
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={dest}&key={api_key}") as r:
                        if r.status == 200:
                            d = await r.json()
                            if d["routes"]:
                                leg = d["routes"][0]["legs"][0]
                                return json.dumps({"from": leg["start_address"], "to": leg["end_address"], "distance": leg["distance"]["text"], "duration": leg["duration"]["text"], "steps": len(leg["steps"])})
                            return f"No route found from {origin} to {dest}."
                        return f"Maps API error {r.status}"
            except Exception as e:
                return f"Directions failed: {e}"

        # ── Adaptive Memory ──
        elif name == "what_do_you_know":
            stats = adaptive_memory.get_stats()
            facts = adaptive_memory.get_all_facts(min_confidence=0.3)
            if not facts:
                return "I haven't learned anything about you yet, Boss. Talk to me more."
            lines = [f"READ THIS LIST TO BOSS EXACTLY — {stats['total_facts']} learned facts:"]
            for i, f in enumerate(facts[:20], 1):
                lines.append(f"{i}. [{f['category'].upper()}] {f['content']} (confidence: {f['confidence']:.0%}, seen {f['reinforced']}x)")
            return "\n".join(lines)

        elif name == "remember_this":
            fact = args["fact"]
            category = args.get("category", "fact")
            adaptive_memory.store_fact(category, fact, source="manual")
            return f"Noted, Boss. I'll remember that."

        # ── Browser Automation ──
        elif name == "browse_page":
            return await browser_agent.get_page_text(args["url"])

        elif name == "screenshot_url":
            return await browser_agent.screenshot_url(args["url"])

        elif name == "extract_links":
            return await browser_agent.extract_links(args["url"])

        # ── Reminders ──
        elif name == "set_reminder":
            return reminder_system.parse_and_add(args["reminder_text"])

        elif name == "list_reminders":
            return reminder_system.list_pending()

        elif name == "cancel_reminder":
            return reminder_system.cancel(args["reminder_id"])

        # ── Security / OSINT ──
        elif name == "username_osint":
            return await security_agent.username_lookup(args["username"])

        elif name == "cve_lookup":
            return await security_agent.cve_lookup(args["query"])

        elif name == "port_scan":
            return await security_agent.port_scan(args["target"], args.get("ports", "common"))

        elif name == "ip_lookup":
            return await security_agent.ip_info(args["target"])

        # ── Code Sandbox ──
        elif name == "run_python":
            return sandbox.execute_python(args["code"])

        # ── Clipboard Intelligence ──
        elif name == "smart_clipboard":
            return clipboard_intel.smart_clipboard_analyze()

        # ── Desktop Automation ──
        elif name == "mouse_move":
            return desktop_automation.move_mouse(args["x"], args["y"])
        elif name == "mouse_click":
            return desktop_automation.click(args.get("x"), args.get("y"), args.get("button", "left"))
        elif name == "keyboard_type":
            return desktop_automation.type_text(args["text"])
        elif name == "keyboard_press":
            return desktop_automation.press_key(args["key"])
        elif name == "keyboard_hotkey":
            return desktop_automation.hotkey(*args["keys"])
            
        # ── Document Intelligence ──
        elif name == "read_document":
            return document_intel.read_document(args["path"])

        # ── Screen Agent (Vision-Guided GUI Automation) ──
        elif name == "screen_do":
            instruction = args["instruction"]
            return await screen_agent.execute(instruction)

        elif name == "screen_stop":
            screen_agent.stop()
            return "Screen Agent stopped. All automation halted."

        # ── Memory Consolidation ──
        elif name == "consolidate_memory":
            from memory.consolidation import consolidate_memories
            from memory.memory_manager import MemoryManager
            mm = MemoryManager()
            return await consolidate_memories(mm)

        # ── Audit ──
        elif name == "activity_report":
            return audit.get_today()

        else:
            return f"Unknown tool: {name}"

    except Exception as e:
        log.error("tool_error", tool=name, error=str(e))
        audit.log_action("tool_call", name, str(args)[:100], str(e)[:100], "error")
        return f"Tool error: {e}"

    finally:
        # Audit every tool call
        try:
            audit.log_action("tool_call", name, str(args)[:100], result[:100] if isinstance(result, str) else "", "success")
        except:
            pass

