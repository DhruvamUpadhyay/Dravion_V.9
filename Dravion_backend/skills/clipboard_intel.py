"""
DRAVION v.9 — Clipboard Intelligence

Smart clipboard actions:
  - Auto-detect content type (URL, code, email, phone, JSON, plain text)
  - Offer context-aware actions
  - Quick copy/paste with type detection
"""
import subprocess
import re
from core.logger import log


def read_clipboard() -> str:
    r = subprocess.run(["powershell", "-Command", "Get-Clipboard"], capture_output=True, text=True, timeout=5)
    return r.stdout.strip()


def detect_type(text: str) -> dict:
    """Detect what kind of content is in the clipboard."""
    if not text:
        return {"type": "empty", "content": "", "summary": "Clipboard is empty."}

    result = {"content": text[:500], "type": "text"}

    # URL
    if re.match(r'https?://\S+', text):
        result["type"] = "url"
        result["summary"] = f"URL detected: {text[:100]}"
        result["actions"] = "I can open it, scrape it, or screenshot it."
        return result

    # Email
    if re.match(r'^[\w.+-]+@[\w-]+\.[\w.]+$', text.strip()):
        result["type"] = "email"
        result["summary"] = f"Email address: {text.strip()}"
        result["actions"] = "I can compose a draft or look up this contact."
        return result

    # IP address
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', text.strip()):
        result["type"] = "ip_address"
        result["summary"] = f"IP address: {text.strip()}"
        result["actions"] = "I can scan ports, lookup geo/ISP info, or check reputation."
        return result

    # JSON
    try:
        import json
        json.loads(text)
        result["type"] = "json"
        result["summary"] = f"JSON data ({len(text)} chars)"
        result["actions"] = "I can format, validate, or extract fields."
        return result
    except:
        pass

    # Code (heuristic)
    code_signals = ["def ", "class ", "import ", "function ", "const ", "var ", "let ", "if (", "for (", "=>", "print(", "console.log"]
    if any(sig in text for sig in code_signals):
        result["type"] = "code"
        result["summary"] = f"Code snippet ({len(text)} chars)"
        result["actions"] = "I can review, execute, explain, or fix it."
        return result

    # Phone number
    if re.match(r'^[\+\d\s\-\(\)]{8,15}$', text.strip()):
        result["type"] = "phone"
        result["summary"] = f"Phone number: {text.strip()}"
        return result

    # File path
    if re.match(r'^[A-Z]:\\|^/[a-z]', text.strip()):
        result["type"] = "file_path"
        result["summary"] = f"File path: {text.strip()}"
        result["actions"] = "I can open, read, or check if it exists."
        return result

    # Default text
    word_count = len(text.split())
    result["summary"] = f"Plain text ({word_count} words)"
    result["actions"] = "I can summarize, translate, or search for related content."
    return result


def smart_clipboard_analyze() -> str:
    """Read clipboard and return intelligent analysis."""
    text = read_clipboard()
    info = detect_type(text)

    lines = [f"Clipboard: {info['summary']}"]
    if info.get("actions"):
        lines.append(f"  {info['actions']}")
    if info["type"] != "empty":
        preview = info["content"][:200]
        if len(info["content"]) > 200:
            preview += "..."
        lines.append(f"  Content: {preview}")
    return "\n".join(lines)
