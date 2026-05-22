import os
import sqlite3
import threading
import subprocess
import string
import pyautogui
import psutil
from difflib import SequenceMatcher

from core.config import config
import os

APP_INDEX_DB = os.path.join(config.data_dir, "app_index.db")

class SystemLauncher:
    def __init__(self):
        self.db_path = APP_INDEX_DB
        self.app_index_table = "app_index"
        self.alias_table = "app_alias"
        self._init_db()
        
        # Start background indexing if empty
        if self._is_index_empty():
            print("[SystemLauncher] Index empty. Starting background scan...")
            threading.Thread(target=self.scan_and_index_apps, daemon=True).start()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Creates tables if they don't exist."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # App Index
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.app_index_table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    display_name TEXT NOT NULL,
                    normalized TEXT NOT NULL,
                    path TEXT NOT NULL,
                    app_type TEXT,
                    source TEXT
                )
            ''')
            
            # Aliases
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.alias_table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_id INTEGER,
                    alias TEXT NOT NULL,
                    FOREIGN KEY (app_id) REFERENCES {self.app_index_table}(id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[SystemLauncher] DB Init Error: {e}")

    def _is_index_empty(self):
        try:
            conn = self._get_conn()
            count = conn.execute(f"SELECT COUNT(*) FROM {self.app_index_table}").fetchone()[0]
            conn.close()
            return count == 0
        except:
            return True

    def _normalize(self, text):
        """Lower, strip punctuation/spaces."""
        if not text: return ""
        text = text.lower().strip()
        # Remove punctuation
        text = text.translate(str.maketrans('', '', string.punctuation))
        return text

    # --- 1. INDEXING LOGIC ---
    def scan_and_index_apps(self):
        """Scans Start Menu folders for .lnk files."""
        print("[SystemLauncher] Indexing apps...")
        
        start_menu_paths = [
            os.path.join(os.getenv("ProgramData", "C:\\ProgramData"), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.getenv("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")
        ]
        
        apps_found = []
        
        for base_path in start_menu_paths:
            if not os.path.exists(base_path): continue
            
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.lower().endswith(".lnk"):
                        name = os.path.splitext(file)[0]
                        full_path = os.path.join(root, file)
                        
                        apps_found.append({
                            "display_name": name,
                            "normalized": self._normalize(name),
                            "path": full_path,
                            "type": "app",
                            "source": "start_menu"
                        })

        # Insert into DB
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(f"DELETE FROM {self.app_index_table}")
        
        for app in apps_found:
            cursor.execute(f'''
                INSERT INTO {self.app_index_table} (display_name, normalized, path, app_type, source)
                VALUES (?, ?, ?, ?, ?)
            ''', (app["display_name"], app["normalized"], app["path"], app["type"], app["source"]))
            
        conn.commit()
        conn.close()
        print(f"[SystemLauncher] Indexed {len(apps_found)} apps.")
        self._seed_aliases()

    def _seed_aliases(self):
        """Seeds common aliases if not present."""
        defaults = {
            "vscode": ["visual studio code"],
            "code": ["visual studio code"],
            "chrome": ["google chrome"],
            "edge": ["microsoft edge"],
            "ppt": ["powerpoint"],
            "word": ["word"],
            "excel": ["excel"],
            "calc": ["calculator"],
            "notepad": ["notepad"],
            "terminal": ["windows terminal", "command prompt", "powershell"],
            "explorer": ["file explorer", "windows explorer"],
            "photos": ["photos", "gallery"],
            "gallery": ["photos"]
        }
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        for alias, targets in defaults.items():
            for target_name in targets:
                target_norm = self._normalize(target_name)
                row = cursor.execute(f"SELECT id, normalized FROM {self.app_index_table}").fetchall()
                
                best_id = None
                best_score = 0
                
                for r_id, r_norm in row:
                    score = SequenceMatcher(None, target_norm, r_norm).ratio()
                    if score > 0.8 and score > best_score:
                        best_score = score
                        best_id = r_id
                
                if best_id:
                    try:
                        cursor.execute(f"INSERT INTO {self.alias_table} (app_id, alias) VALUES (?, ?)", (best_id, alias))
                    except:
                        pass
                        
        conn.commit()
        conn.close()

    # --- 2. SEARCH & MATCHING ---
    def find_best_app_match(self, query):
        """Returns {path, display_name} or None."""
        q = self._normalize(query)
        conn = self._get_conn()
        
        # 1. Alias Valid Match
        row = conn.execute(f'''
            SELECT i.id, i.display_name, i.path 
            FROM {self.alias_table} a 
            JOIN {self.app_index_table} i ON a.app_id = i.id 
            WHERE a.alias = ?
        ''', (q,)).fetchone()
        
        if row:
            conn.close()
            return {"id": row[0], "display_name": row[1], "path": row[2]}
            
        # 2. Fuzzy Match on App Index
        rows = conn.execute(f"SELECT id, display_name, normalized, path FROM {self.app_index_table}").fetchall()
        conn.close()
        
        best = None
        best_score = 0
        
        for r_id, r_name, r_norm, r_path in rows:
            score = SequenceMatcher(None, q, r_norm).ratio()
            if q in r_norm:
                score += 0.2
                
            if score > best_score:
                best_score = score
                best = {"id": r_id, "display_name": r_name, "path": r_path}
                
        if best and best_score > 0.6:
            return best
            
        return None

launcher = SystemLauncher()

def smart_open_app(app_name):
    """Smart open app using the SystemLauncher."""
    target_name = launcher._normalize(app_name)
    
    # 0. Protocol Handlers (UWP Apps)
    protocols = {
        "whatsapp": "whatsapp:",
        "settings": "ms-settings:",
        "store": "ms-windows-store:",
        "calculator": "calculator:",
        "spotify": "spotify:",
        "netflix": "netflix:",
        "calendar": "outlookcal:",
        "mail": "outlookmail:",
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
    }
    
    for key, uri in protocols.items():
        if key in target_name:
            try:
                os.startfile(uri)
                return f"Opening {key}."
            except Exception:
                pass
    
    # 1. Check for Aliasing/Search
    match = launcher.find_best_app_match(app_name)

    if match:
        try:
            os.startfile(match["path"])
            return f"Opening {match['display_name']}."
        except Exception as e:
            return f"Failed to open {match['display_name']}: {e}"

    # 2. Check if it's a valid path
    if os.path.exists(app_name):
        try:
            os.startfile(app_name)
            return f"Opening {os.path.basename(app_name)}..."
        except: pass

    # 3. Fallback to OS shell (e.g. for "calc", "notepad")
    try:
        subprocess.Popen(app_name, shell=True) 
        return f"Attempting to launch {app_name}..."
    except:
        pass

    return f"I couldn't find an app named '{app_name}'."

def smart_close_app(app_name):
    """Smart close app."""
    target = launcher._normalize(app_name)
    
    # Safe Close Overrides
    safe_list = ["explorer", "folder", "download", "document", "this pc"]
    if any(s in target for s in safe_list):
        pyautogui.hotkey('alt', 'f4')
        return "Closed current window."
        
    # Process Search
    count = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            p_name = proc.info['name'].lower()
            if target in p_name:
                proc.terminate()
                count += 1
        except:
            pass
            
    if count > 0:
        return f"Closed {count} instances of {app_name}."
    
    # Fallback to fuzzy match
    match = launcher.find_best_app_match(app_name)
    if match:
        exe_name = os.path.basename(match["path"]).lower()
        if not exe_name.endswith(".lnk"):
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() == exe_name:
                        proc.terminate()
                        count += 1
                except: pass
                
    if count > 0:
         return f"Closed {app_name} via index lookup."
         
    return f"I couldn't find a running process for {app_name}."
