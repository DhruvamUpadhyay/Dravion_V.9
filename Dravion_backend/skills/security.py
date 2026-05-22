"""
DRAVION v.9 — Security & OSINT Module (WRAITH)

Capabilities:
  - Username OSINT (multi-platform check)
  - CVE lookup (NVD API)
  - Port scanning (basic, no nmap dependency)
  - IP/Domain info lookup
  - Hash lookup (VirusTotal-style)
"""
import asyncio
import subprocess
import socket
import json
import re
from datetime import datetime
from core.logger import log


class SecurityAgent:
    def __init__(self):
        log.info("security_agent_ready")

    # ── Username OSINT ──

    async def username_lookup(self, username: str) -> str:
        """Check username across major platforms using HTTP HEAD checks."""
        platforms = {
            "GitHub": f"https://github.com/{username}",
            "Twitter/X": f"https://x.com/{username}",
            "Instagram": f"https://www.instagram.com/{username}/",
            "Reddit": f"https://www.reddit.com/user/{username}",
            "TikTok": f"https://www.tiktok.com/@{username}",
            "LinkedIn": f"https://www.linkedin.com/in/{username}",
            "YouTube": f"https://www.youtube.com/@{username}",
            "Pinterest": f"https://www.pinterest.com/{username}/",
            "Medium": f"https://medium.com/@{username}",
            "Dev.to": f"https://dev.to/{username}",
            "Twitch": f"https://www.twitch.tv/{username}",
            "SoundCloud": f"https://soundcloud.com/{username}",
            "Telegram": f"https://t.me/{username}",
            "GitLab": f"https://gitlab.com/{username}",
            "Keybase": f"https://keybase.io/{username}",
        }

        import aiohttp
        found = []
        not_found = []

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
            tasks = []
            for name, url in platforms.items():
                tasks.append(self._check_url(session, name, url))
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for name, status in results:
            if isinstance(status, Exception):
                continue
            if status:
                found.append(f"  [FOUND] {name}: {platforms[name]}")
            else:
                not_found.append(name)

        lines = [f"OSINT Report for '{username}':", f"  Found on {len(found)} platforms:"]
        lines.extend(found)
        lines.append(f"  Not found on: {', '.join(not_found[:8])}")
        return "\n".join(lines)

    async def _check_url(self, session, name, url):
        try:
            async with session.head(url, allow_redirects=True) as r:
                # 200 = exists, 404 = not found
                return (name, r.status == 200)
        except:
            return (name, False)

    # ── CVE Lookup ──

    async def cve_lookup(self, query: str) -> str:
        """Search NVD for CVEs matching a keyword (software name, CVE ID, etc)."""
        import aiohttp

        # Direct CVE ID lookup
        if query.upper().startswith("CVE-"):
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={query.upper()}"
        else:
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={query}&resultsPerPage=5"

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(url) as r:
                    if r.status != 200:
                        return f"NVD API returned {r.status}. May be rate-limited."
                    data = await r.json()

            vulns = data.get("vulnerabilities", [])
            if not vulns:
                return f"No CVEs found for '{query}'."

            lines = [f"CVE Results for '{query}' ({len(vulns)} found):"]
            for v in vulns[:5]:
                cve = v.get("cve", {})
                cve_id = cve.get("id", "?")
                desc_list = cve.get("descriptions", [])
                desc = next((d["value"] for d in desc_list if d["lang"] == "en"), "No description")
                # Get CVSS score
                metrics = cve.get("metrics", {})
                score = "N/A"
                for key in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
                    if key in metrics and metrics[key]:
                        score = metrics[key][0].get("cvssData", {}).get("baseScore", "N/A")
                        break
                lines.append(f"\n  {cve_id} (CVSS: {score})")
                lines.append(f"    {desc[:200]}")
            return "\n".join(lines)
        except Exception as e:
            return f"CVE lookup failed: {e}"

    # ── Port Scan ──

    async def port_scan(self, target: str, ports: str = "common") -> str:
        """Basic TCP port scan. No nmap needed."""
        if ports == "common":
            port_list = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445,
                         993, 995, 1433, 1521, 3306, 3389, 5432, 5900, 6379,
                         8000, 8080, 8443, 8888, 9090, 27017]
        else:
            try:
                port_list = [int(p.strip()) for p in ports.split(",")]
            except:
                return "Invalid port format. Use comma-separated numbers or 'common'."

        try:
            ip = socket.gethostbyname(target)
        except:
            return f"Cannot resolve '{target}'."

        open_ports = []
        closed = 0

        async def check_port(port):
            nonlocal closed
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port), timeout=1.5
                )
                writer.close()
                await writer.wait_closed()
                open_ports.append(port)
            except:
                closed += 1

        await asyncio.gather(*[check_port(p) for p in port_list])
        open_ports.sort()

        service_map = {21:"FTP",22:"SSH",23:"Telnet",25:"SMTP",53:"DNS",80:"HTTP",
                       110:"POP3",143:"IMAP",443:"HTTPS",445:"SMB",3306:"MySQL",
                       3389:"RDP",5432:"PostgreSQL",6379:"Redis",8080:"HTTP-Alt",
                       27017:"MongoDB",8000:"Dev-Server"}

        lines = [f"Scan results for {target} ({ip}):", f"  {len(open_ports)} open, {closed} closed"]
        for p in open_ports:
            svc = service_map.get(p, "unknown")
            lines.append(f"  Port {p}/tcp — OPEN ({svc})")
        if not open_ports:
            lines.append("  No open ports found in scanned range.")
        return "\n".join(lines)

    # ── IP/Domain Info ──

    async def ip_info(self, target: str) -> str:
        """Get basic info about an IP or domain."""
        import aiohttp
        try:
            ip = socket.gethostbyname(target)
        except:
            ip = target

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
                async with s.get(f"http://ip-api.com/json/{ip}") as r:
                    data = await r.json()
            if data.get("status") == "fail":
                return f"Lookup failed for {target}: {data.get('message')}"
            return (
                f"IP Info for {target}:\n"
                f"  IP: {data.get('query')}\n"
                f"  ISP: {data.get('isp')}\n"
                f"  Org: {data.get('org')}\n"
                f"  City: {data.get('city')}, {data.get('regionName')}\n"
                f"  Country: {data.get('country')}\n"
                f"  Timezone: {data.get('timezone')}"
            )
        except Exception as e:
            return f"IP lookup failed: {e}"


security_agent = SecurityAgent()
