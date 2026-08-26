"""
Parses F5 syslog-style log lines (/var/log/ltm, /var/log/gtm, /var/log/audit, /var/log/secure)
into structured entries and produces severity/process summaries.

Typical F5 log line:
Aug 26 10:15:32 bigip01 notice logger: ...
Aug 26 10:15:33 bigip01 err tmm[12345]: 01260013:3: ...
"""
import re
from collections import Counter
from typing import List, Dict

LOG_FILE_PATHS = {
    "ltm": "/var/log/ltm",
    "gtm": "/var/log/gtm",
    "audit": "/var/log/audit",
    "secure": "/var/log/secure",
    "apm": "/var/log/apm",
    "asm": "/var/log/asm",
}

SEVERITY_KEYWORDS = ["emerg", "alert", "crit", "err", "error", "warning", "notice", "info", "debug"]

# Matches: "<mon> <day> <time> <host> <severity-or-proc> <proc>[pid]: <message>"
LINE_RE = re.compile(
    r"^(?P<ts>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+"
    r"(?P<rest>.*)$"
)
PROC_RE = re.compile(r"(?P<proc>[\w\-/.]+)(\[(?P<pid>\d+)\])?:")


def _extract_severity(rest: str) -> str:
    lowered = rest.lower()
    for sev in SEVERITY_KEYWORDS:
        if f" {sev} " in f" {lowered} " or lowered.startswith(sev):
            return sev
    return "info"


def parse_log_text(raw_text: str) -> List[Dict]:
    entries = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = LINE_RE.match(line)
        ts, host, rest = None, None, line
        if m:
            ts = m.group("ts")
            host = m.group("host")
            rest = m.group("rest")

        severity = _extract_severity(rest)
        proc_match = PROC_RE.search(rest)
        proc = proc_match.group("proc") if proc_match else "unknown"
        message = rest

        entries.append({
            "raw": line,
            "timestamp": ts,
            "severity": severity,
            "process": proc,
            "message": message,
        })
    return entries


def summarize(entries: List[Dict]) -> Dict:
    sev_counter = Counter(e["severity"] for e in entries)
    proc_counter = Counter(e["process"] for e in entries)
    return {
        "severity_counts": dict(sev_counter.most_common()),
        "process_counts": dict(proc_counter.most_common(15)),
    }
