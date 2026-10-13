"""Report text, e-mail drafts (Outlook / default mail client) and printing."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import webbrowser
from datetime import datetime
from typing import Sequence
from urllib.parse import quote

from . import core

MAILTO_LIMIT = 1900   # Windows ShellExecute rejects URLs much beyond ~2000 chars


def time_report(line_minutes: Sequence[int]) -> str:
    total = sum(line_minutes)
    h, m = core.split_hm(total)
    lines = ["Time Calculation", datetime.now().strftime("%d %b %Y %H:%M"), ""]
    used = [x for x in line_minutes if x > 0]
    if used:
        lines.append("Entries:")
        for i, mins in enumerate(used, 1):
            eh, em = core.split_hm(mins)
            lines.append(f"  {i:>2}.  {eh:02d}:{em:02d}")
        lines.append("")
    lines.append(f"Total (hours:minutes): {h:02d}:{m:02d}")
    lines.append(f"Total (decimal hours): {core.format_decimal(total)}")
    return "\n".join(lines)


def open_email_draft(subject: str, body: str, to: str = "") -> str:
    """Open a pre-filled, unsent draft. Returns 'outlook' or 'default'."""
    if sys.platform == "win32":
        try:                                    # classic Outlook via COM (needs pywin32)
            import win32com.client              # type: ignore
            outlook = win32com.client.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)
            mail.To, mail.Subject, mail.Body = to, subject, body
            mail.Display(False)
            return "outlook"
        except Exception:
            pass                                # fall back to the default mail client

    def build(text: str) -> str:
        return ("mailto:" + quote(to) + "?subject=" + quote(subject, safe="")
                + "&body=" + quote(text.replace("\n", "\r\n"), safe=""))

    url, text = build(body), body
    while len(url) > MAILTO_LIMIT and len(text) > 20:
        text = text[: int(len(text) * 0.9)].rstrip() + "\n[...]"
        url = build(text)
    if sys.platform == "win32":
        os.startfile(url)                       # type: ignore[attr-defined]
    elif not webbrowser.open(url):
        raise OSError("No default e-mail client is configured.")
    return "default"


def print_text(text: str) -> None:
    fd, path = tempfile.mkstemp(prefix="TimeCalc_", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    if sys.platform == "win32":
        os.startfile(path, "print")             # type: ignore[attr-defined]
    else:
        subprocess.run(["lp", path], check=True)
