#!/usr/bin/env python3
"""
CLIFM v3.0 - CLI File Manager
ASCII icon grid + list view, full file ops, zero heavy dependencies.
Pure Python stdlib only.
"""

import os, sys, re, shutil, stat, platform, subprocess, readline
import fnmatch, tarfile, zipfile, gzip, bz2, lzma, tty, termios
from pathlib import Path
from datetime import datetime
from collections import deque

# ─── ANSI ────────────────────────────────────────────────────────────────────
class C:
    RESET="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"
    BLACK="\033[30m"; RED="\033[31m"; GREEN="\033[32m"; YELLOW="\033[33m"
    BLUE="\033[34m"; MAGENTA="\033[35m"; CYAN="\033[36m"; WHITE="\033[37m"
    BBLACK="\033[90m"; BRED="\033[91m"; BGREEN="\033[92m"; BYELLOW="\033[93m"
    BBLUE="\033[94m"; BMAGENTA="\033[95m"; BCYAN="\033[96m"; BWHITE="\033[97m"
    BG_BLACK="\033[40m"; BG_BBLACK="\033[100m"; BG_BLUE="\033[44m"
    BG_GREEN="\033[42m"

ANSI_RE = re.compile(r'\033\[[0-9;]*m')

def vlen(s):
    """Visible length of string (strips ANSI codes)."""
    return len(ANSI_RE.sub("", s))

def pad_to(s, width):
    """Pad string to visible width."""
    return s + " " * max(0, width - vlen(s))

# ─── RAW KEY READER ──────────────────────────────────────────────────────────
def read_key():
    """
    Read one keypress using os.read(fd,1) — kernel fd directly.
    os.read bypasses ALL Python buffering (BufferedReader, TextIOWrapper).
    This is the only reliable method after browse_results/realtime_path_input
    have used the same terminal fd.
    """
    import select as _sel
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        b = os.read(fd, 1)
        if not b: return ""
        c = b[0]
        if c == 0x1b:
            rdy = _sel.select([fd], [], [], 0.08)[0]
            if not rdy: return "ESC"
            b2 = os.read(fd, 1)
            if b2 == b"[":
                rdy2 = _sel.select([fd], [], [], 0.08)[0]
                if not rdy2: return "ESC"
                b3 = os.read(fd, 1)
                MAP = {b"A":"UP", b"B":"DOWN", b"C":"RIGHT", b"D":"LEFT",
                       b"H":"HOME", b"F":"END"}
                if b3 in MAP: return MAP[b3]
                if b3 in (b"5", b"6", b"3"):
                    _sel.select([fd], [], [], 0.05)
                    os.read(fd, 1)
                    return {"5":"PAGEUP","6":"PAGEDOWN","3":"DELETE"}.get(chr(b3[0]),"ESC")
                return "ESC"
            elif b2 == b"O":
                rdy2 = _sel.select([fd], [], [], 0.08)[0]
                if not rdy2: return "ESC"
                b3 = os.read(fd, 1)
                MAP = {b"A":"UP", b"B":"DOWN", b"C":"RIGHT", b"D":"LEFT",
                       b"H":"HOME", b"F":"END"}
                return MAP.get(b3, "ESC")
            return "ESC"
        elif c in (0x0d, 0x0a): return "ENTER"
        elif c in (0x7f, 0x08): return "BACKSPACE"
        elif c == 0x03: raise KeyboardInterrupt
        elif c == 0x04: raise EOFError
        elif c == 0x20: return "SPACE"
        elif c == 0x09: return "TAB"
        elif 0x20 <= c <= 0x7e: return chr(c)
        return ""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

# ─── OS DETECTION ─────────────────────────────────────────────────────────────
class OSInfo:
    def __init__(self):
        self.name = platform.system().lower()
        self.distro = self._distro()
        self.pkg = self._pkg()

    def _distro(self):
        try:
            for line in open("/etc/os-release"):
                if line.startswith("ID="):
                    return line.strip().split("=")[1].strip('"').lower()
        except: pass
        return platform.system().lower()

    def _pkg(self):
        for name, cmd in [
            ("pacman", ["pacman","-S","--noconfirm"]),
            ("apt",    ["apt","install","-y"]),
            ("apt-get",["apt-get","install","-y"]),
            ("dnf",    ["dnf","install","-y"]),
            ("yum",    ["yum","install","-y"]),
            ("zypper", ["zypper","install","-y"]),
            ("apk",    ["apk","add"]),
            ("brew",   ["brew","install"]),
        ]:
            if shutil.which(name):
                return {"name": name, "cmd": cmd}
        return None

    def install(self, pkg):
        if self.pkg:
            return ["sudo"] + self.pkg["cmd"] + [pkg]
        return None

OS = OSInfo()

# ─── TERMINAL ────────────────────────────────────────────────────────────────
def term_size():
    try:
        c, r = os.get_terminal_size()
        return c, r
    except:
        return 80, 24

def clear():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

# ─── FILE ICONS ───────────────────────────────────────────────────────────────
# 5-line tall ASCII art icons for grid view
def big_icon(path: Path, is_dir: bool):
    """Returns a list of 5 strings (lines) for the big icon."""
    if is_dir:
        col = C.BBLUE
        label = "DIR"
        top = f"{col}┌─────────┐{C.RESET}"
        m1  = f"{col}│         │{C.RESET}"
        mid = f"{col}│  {C.BOLD}[{label}]{C.RESET}{col}  │{C.RESET}"
        m2  = f"{col}│         │{C.RESET}"
        bot = f"{col}└─────────┘{C.RESET}"
        return [top, m1, mid, m2, bot]

    ext = path.suffix.lower()
    # Color + label mapping
    MAP = {
        ".py":   (C.BGREEN,   ".PY "),
        ".sh":   (C.BGREEN,   ".SH "),
        ".bash": (C.BGREEN,   ".SH "),
        ".zsh":  (C.BGREEN,   ".ZSH"),
        ".js":   (C.BYELLOW,  ".JS "),
        ".ts":   (C.BBLUE,    ".TS "),
        ".c":    (C.BCYAN,    " .C "),
        ".cpp":  (C.BCYAN,    "CPP "),
        ".rs":   (C.BRED,     ".RS "),
        ".go":   (C.BCYAN,    ".GO "),
        ".rb":   (C.BRED,     ".RB "),
        ".php":  (C.BMAGENTA, "PHP "),
        ".java": (C.BRED,     "JAVA"),
        ".html": (C.BYELLOW,  "HTML"),
        ".css":  (C.BBLUE,    "CSS "),
        ".json": (C.BYELLOW,  "JSON"),
        ".xml":  (C.BYELLOW,  "XML "),
        ".yaml": (C.BCYAN,    "YML "),
        ".yml":  (C.BCYAN,    "YML "),
        ".toml": (C.BCYAN,    "TOML"),
        ".md":   (C.BWHITE,   " .MD"),
        ".txt":  (C.WHITE,    "TXT "),
        ".log":  (C.BBLACK,   "LOG "),
        ".conf": (C.CYAN,     "CONF"),
        ".ini":  (C.CYAN,     ".INI"),
        ".env":  (C.CYAN,     ".ENV"),
        ".zip":  (C.BYELLOW,  "ZIP "),
        ".tar":  (C.BYELLOW,  ".TAR"),
        ".gz":   (C.BYELLOW,  " .GZ"),
        ".bz2":  (C.BYELLOW,  "BZ2 "),
        ".xz":   (C.BYELLOW,  " .XZ"),
        ".7z":   (C.BYELLOW,  " .7Z"),
        ".rar":  (C.BYELLOW,  "RAR "),
        ".zst":  (C.BYELLOW,  "ZST "),
        ".pdf":  (C.BRED,     "PDF "),
        ".doc":  (C.BBLUE,    "DOC "),
        ".docx": (C.BBLUE,    "DOCX"),
        ".xls":  (C.BGREEN,   "XLS "),
        ".xlsx": (C.BGREEN,   "XLSX"),
        ".csv":  (C.BGREEN,   "CSV "),
        ".png":  (C.BBLUE,    "PNG "),
        ".jpg":  (C.BBLUE,    "JPG "),
        ".jpeg": (C.BBLUE,    "JPG "),
        ".gif":  (C.BBLUE,    "GIF "),
        ".svg":  (C.BBLUE,    "SVG "),
        ".webp": (C.BBLUE,    "WEBP"),
        ".mp3":  (C.BMAGENTA, "MP3 "),
        ".flac": (C.BMAGENTA, "FLAC"),
        ".wav":  (C.BMAGENTA, "WAV "),
        ".ogg":  (C.BMAGENTA, "OGG "),
        ".mp4":  (C.BMAGENTA, "MP4 "),
        ".mkv":  (C.BMAGENTA, "MKV "),
        ".avi":  (C.BMAGENTA, "AVI "),
        ".mov":  (C.BMAGENTA, "MOV "),
        ".deb":  (C.BRED,     "DEB "),
        ".rpm":  (C.BRED,     "RPM "),
        ".iso":  (C.BRED,     "ISO "),
        ".exe":  (C.BRED,     "EXE "),
        ".bin":  (C.BRED,     "BIN "),
        ".db":   (C.BCYAN,    " DB "),
        ".sql":  (C.BCYAN,    "SQL "),
    }
    col, label = MAP.get(ext, (C.BBLACK, "??? "))
    if os.access(path, os.X_OK):
        col, label = C.BYELLOW, "EXE "
    # Archive decoration
    arc = ext in (".zip",".tar",".gz",".bz2",".xz",".7z",".rar",".zst",".iso")
    if arc:
        top = f"{col}┌──┬──────┐{C.RESET}"
        m1  = f"{col}│▓▓│      │{C.RESET}"
        mid = f"{col}│▓▓│{C.BOLD}{label}{C.RESET}{col}  │{C.RESET}"
        m2  = f"{col}│▓▓│      │{C.RESET}"
        bot = f"{col}└──┴──────┘{C.RESET}"
    else:
        top = f"{col}┌───────┐{C.RESET}"
        m1  = f"{col}│ .___. │{C.RESET}"
        mid = f"{col}│ {C.BOLD}{label}{C.RESET}{col} │{C.RESET}"
        m2  = f"{col}│       │{C.RESET}"
        bot = f"{col}└───────┘{C.RESET}"
    return [top, m1, mid, m2, bot]

# Small inline icon for list view
def small_icon(path: Path, is_dir: bool):
    if is_dir:             return f"{C.BBLUE}[DIR]{C.RESET}"
    ext = path.suffix.lower()
    M = {".py":f"{C.BGREEN}[.PY]{C.RESET}",".sh":f"{C.BGREEN}[.SH]{C.RESET}",
         ".js":f"{C.BYELLOW}[.JS]{C.RESET}",".ts":f"{C.BBLUE}[.TS]{C.RESET}",
         ".c":f"{C.BCYAN}[.C ]{C.RESET}",".cpp":f"{C.BCYAN}[CPP]{C.RESET}",
         ".rs":f"{C.BRED}[.RS]{C.RESET}",".go":f"{C.BCYAN}[.GO]{C.RESET}",
         ".html":f"{C.BYELLOW}[HTM]{C.RESET}",".css":f"{C.BBLUE}[CSS]{C.RESET}",
         ".json":f"{C.BYELLOW}[JSN]{C.RESET}",".yaml":f"{C.BCYAN}[YML]{C.RESET}",
         ".yml":f"{C.BCYAN}[YML]{C.RESET}",".toml":f"{C.BCYAN}[TOM]{C.RESET}",
         ".md":f"{C.BWHITE}[.MD]{C.RESET}",".txt":f"{C.WHITE}[TXT]{C.RESET}",
         ".log":f"{C.BBLACK}[LOG]{C.RESET}",".conf":f"{C.CYAN}[CNF]{C.RESET}",
         ".zip":f"{C.BYELLOW}[ZIP]{C.RESET}",".tar":f"{C.BYELLOW}[TAR]{C.RESET}",
         ".gz":f"{C.BYELLOW}[.GZ]{C.RESET}",".bz2":f"{C.BYELLOW}[BZ2]{C.RESET}",
         ".xz":f"{C.BYELLOW}[.XZ]{C.RESET}",".7z":f"{C.BYELLOW}[.7Z]{C.RESET}",
         ".rar":f"{C.BYELLOW}[RAR]{C.RESET}",".zst":f"{C.BYELLOW}[ZST]{C.RESET}",
         ".pdf":f"{C.BRED}[PDF]{C.RESET}",".doc":f"{C.BBLUE}[DOC]{C.RESET}",
         ".docx":f"{C.BBLUE}[DOC]{C.RESET}",".xls":f"{C.BGREEN}[XLS]{C.RESET}",
         ".csv":f"{C.BGREEN}[CSV]{C.RESET}",".png":f"{C.BBLUE}[PNG]{C.RESET}",
         ".jpg":f"{C.BBLUE}[JPG]{C.RESET}",".jpeg":f"{C.BBLUE}[JPG]{C.RESET}",
         ".gif":f"{C.BBLUE}[GIF]{C.RESET}",".mp3":f"{C.BMAGENTA}[MP3]{C.RESET}",
         ".flac":f"{C.BMAGENTA}[FLC]{C.RESET}",".mp4":f"{C.BMAGENTA}[MP4]{C.RESET}",
         ".mkv":f"{C.BMAGENTA}[MKV]{C.RESET}",".avi":f"{C.BMAGENTA}[AVI]{C.RESET}",
         ".iso":f"{C.BRED}[ISO]{C.RESET}",".deb":f"{C.BRED}[DEB]{C.RESET}",
         ".sql":f"{C.BCYAN}[SQL]{C.RESET}",".db":f"{C.BCYAN}[DB ]{C.RESET}",
    }
    if os.access(path, os.X_OK) and path.is_file():
        return f"{C.BYELLOW}[EXE]{C.RESET}"
    return M.get(ext, f"{C.BBLACK}[   ]{C.RESET}")

# ─── FORMATTING ───────────────────────────────────────────────────────────────
def fmt_size(n):
    for u in ["  B"," KB"," MB"," GB"," TB"]:
        if n < 1024: return f"{n:6.1f}{u}"
        n /= 1024
    return f"{n:6.1f} PB"

def fmt_time(ts):
    if not ts: return "                "
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")

def fmt_perms(mode):
    p = ""
    for r,w,x in [(stat.S_IRUSR,stat.S_IWUSR,stat.S_IXUSR),
                  (stat.S_IRGRP,stat.S_IWGRP,stat.S_IXGRP),
                  (stat.S_IROTH,stat.S_IWOTH,stat.S_IXOTH)]:
        p += ("r" if mode&r else "-") + ("w" if mode&w else "-") + ("x" if mode&x else "-")
    return p

# ─── CLIPBOARD & HISTORY ─────────────────────────────────────────────────────
class Clipboard:
    def __init__(self): self.items=[]; self.mode=None
    def set(self,items,mode): self.items=list(items); self.mode=mode
    def clear(self): self.items=[]; self.mode=None
    def has(self): return bool(self.items)
    def label(self):
        if not self.items: return ""
        ic = "©" if self.mode=="copy" else "✂"
        ns = ", ".join(i.name for i in self.items[:2])
        if len(self.items)>2: ns += f" +{len(self.items)-2}"
        return f"{ic} {ns}"

class NavHistory:
    def __init__(self): self.back=deque(maxlen=50); self.fwd=deque(maxlen=50); self.cur=Path.home()
    def go(self,p):
        if self.cur!=p: self.back.append(self.cur); self.fwd.clear()
        self.cur=p
    def go_back(self):
        if self.back: self.fwd.append(self.cur); self.cur=self.back.pop()
        return self.cur
    def go_fwd(self):
        if self.fwd: self.back.append(self.cur); self.cur=self.fwd.pop()
        return self.cur

CLIP = Clipboard()
HIST = NavHistory()

# ─── DIRECTORY READER ─────────────────────────────────────────────────────────
SORT_MODES = ["name","name_r","size","size_r","time","time_r","ext"]
SORT_LABEL = {"name":"Name↑","name_r":"Name↓","size":"Size↑","size_r":"Size↓",
               "time":"Time↑","time_r":"Time↓","ext":"Ext "}

def read_dir(path, show_hidden, sort_mode, filter_str=""):
    entries = []
    try:
        for item in path.iterdir():
            if not show_hidden and item.name.startswith("."): continue
            if filter_str and filter_str.lower() not in item.name.lower(): continue
            try:
                st = item.lstat()
                is_link = stat.S_ISLNK(st.st_mode)
                real_st = item.stat() if is_link else st
                entries.append({
                    "path": item, "is_dir": item.is_dir(), "is_link": is_link,
                    "size": real_st.st_size, "mtime": real_st.st_mtime,
                    "perms": fmt_perms(st.st_mode), "name_lower": item.name.lower(),
                })
            except:
                entries.append({
                    "path": item, "is_dir": item.is_dir(), "is_link": False,
                    "size": 0, "mtime": 0, "perms": "---------",
                    "name_lower": item.name.lower(),
                })
    except PermissionError:
        return []

    key_map = {
        "name":   lambda e: (not e["is_dir"], e["name_lower"]),
        "name_r": lambda e: (not e["is_dir"], e["name_lower"]),
        "size":   lambda e: (not e["is_dir"], e["size"]),
        "size_r": lambda e: (not e["is_dir"], -e["size"]),
        "time":   lambda e: (not e["is_dir"], -e["mtime"]),
        "time_r": lambda e: (not e["is_dir"], e["mtime"]),
        "ext":    lambda e: (not e["is_dir"], e["path"].suffix.lower(), e["name_lower"]),
    }
    rev = sort_mode == "name_r"
    entries.sort(key=key_map.get(sort_mode, key_map["name"]), reverse=rev and sort_mode=="name_r")
    return entries

# ─── RENDERING: HEADER ───────────────────────────────────────────────────────
def render_header(cwd, cols, clip, sort_mode, show_hidden, view_mode, filter_str):
    inner = cols - 2
    # Row 1: title
    title = f" {C.BBLUE}{C.BOLD}CLIFM{C.RESET} {C.BBLACK}v3.0{C.RESET} {C.BBLACK}─{C.RESET} {C.BCYAN}{OS.distro.upper()}{C.RESET} {C.BBLACK}[{OS.pkg['name'] if OS.pkg else '?'}]{C.RESET}"
    flags = f" {C.BBLACK}[{'H' if show_hidden else '.'}] [{SORT_LABEL[sort_mode]}] [{'GRID' if view_mode=='grid' else 'LIST'}]{C.RESET}"
    gap = inner - vlen(title) - vlen(flags)
    print(f"{C.BBLACK}╔{'═'*inner}╗{C.RESET}")
    print(f"{C.BBLACK}║{C.RESET}{title}{' '*max(0,gap)}{flags}{C.BBLACK}║{C.RESET}")
    # Row 2: path
    path_s = str(cwd)
    if len(path_s) > inner - 4:
        path_s = "…" + path_s[-(inner-5):]
    clip_s = f" {C.BYELLOW}{clip.label()}{C.RESET}" if clip.has() else ""
    filter_s = f" {C.BCYAN}filter:{filter_str}{C.RESET}" if filter_str else ""
    pathline = f" {C.BBLUE}>{C.RESET} {C.BWHITE}{path_s}{C.RESET}{clip_s}{filter_s}"
    print(f"{C.BBLACK}║{C.RESET}{pad_to(pathline, inner)}{C.BBLACK}║{C.RESET}")
    print(f"{C.BBLACK}╠{'═'*inner}╣{C.RESET}")

# ─── RENDERING: FOOTER ───────────────────────────────────────────────────────
def render_footer(cols, status):
    inner = cols - 2
    print(f"{C.BBLACK}╠{'═'*inner}╣{C.RESET}")
    k = [
        (f"{C.BWHITE}↑↓{C.RESET}","Nav"),
        (f"{C.BGREEN}Enter{C.RESET}","Open"),
        (f"{C.BYELLOW}C{C.RESET}","Copy"),
        (f"{C.BYELLOW}X{C.RESET}","Cut"),
        (f"{C.BYELLOW}P{C.RESET}","Paste"),
        (f"{C.BRED}D{C.RESET}","Del"),
        (f"{C.BCYAN}R{C.RESET}","Rename"),
        (f"{C.BCYAN}N{C.RESET}","New"),
        (f"{C.BMAGENTA}Z{C.RESET}","Compress"),
        (f"{C.BMAGENTA}E{C.RESET}","Extract"),
        (f"{C.BBLUE}I{C.RESET}","Info"),
        (f"{C.BWHITE}/{C.RESET}","Search"),
        (f"{C.BWHITE}G{C.RESET}","GoPath"),
        (f"{C.BBLACK}.{C.RESET}","Hidden"),
        (f"{C.BWHITE}V{C.RESET}","View"),
        (f"{C.BWHITE}T{C.RESET}","Sort"),
        (f"{C.BWHITE}!{C.RESET}","Shell"),
        (f"{C.BRED}Q{C.RESET}","Quit"),
    ]
    mid = len(k)//2
    def row(keys):
        parts = [f"{a}{C.BBLACK}:{C.RESET}{C.DIM}{b}{C.RESET}" for a,b in keys]
        line = "  ".join(parts)
        return f"{C.BBLACK}║{C.RESET} {line}{' '*max(0,inner-1-vlen(line))}{C.BBLACK}║{C.RESET}"
    print(row(k[:mid]))
    print(row(k[mid:]))
    # Status
    sv = pad_to(f" {status}", inner)
    print(f"{C.BBLACK}║{C.RESET}{sv}{C.BBLACK}║{C.RESET}")
    print(f"{C.BBLACK}╚{'═'*inner}╝{C.RESET}")

# ─── RENDERING: GRID VIEW ─────────────────────────────────────────────────────
ICON_W_DIR  = 11   # ┌─────────┐ = 11 chars wide
ICON_W_FILE = 9    # ┌───────┐  = 9 chars wide
CARD_W      = 14   # card slot width (icon + padding)
CARD_H      = 7    # 5 icon lines + 1 label + 1 gap

def render_grid(entries, selected_idx, cols, rows, marked, scroll_offset):
    inner = cols - 2
    avail_rows = max(4, rows - 11)  # rows available for content area

    # How many cards per row
    per_row = max(1, inner // CARD_W)
    card_w = inner // per_row  # actual card width (fills evenly)

    # Total rows of cards
    total_card_rows = (len(entries) + per_row - 1) // per_row if entries else 0
    avail_card_rows = avail_rows // CARD_H

    # Scroll in terms of card-rows
    sel_card_row = selected_idx // per_row
    if sel_card_row < scroll_offset:
        scroll_offset = sel_card_row
    elif sel_card_row >= scroll_offset + avail_card_rows:
        scroll_offset = sel_card_row - avail_card_rows + 1

    if not entries:
        empty = pad_to(f" {C.BBLACK}(empty directory){C.RESET}", inner)
        print(f"{C.BBLACK}║{C.RESET}{empty}{C.BBLACK}║{C.RESET}")
        for _ in range(avail_rows - 1):
            print(f"{C.BBLACK}║{C.RESET}{' '*inner}{C.BBLACK}║{C.RESET}")
        return scroll_offset

    lines_printed = 0

    for card_row_i in range(scroll_offset, scroll_offset + avail_card_rows):
        if card_row_i >= total_card_rows: break
        start = card_row_i * per_row
        row_entries = entries[start : start + per_row]

        # Build 5-line icon + label for each card in this row
        cards = []
        for j, e in enumerate(row_entries):
            ei = start + j
            path = e["path"]
            is_dir = e["is_dir"]
            is_sel = (ei == selected_idx)
            is_marked = path in marked

            icon_lines = big_icon(path, is_dir)
            name = path.name
            if len(name) > card_w - 2:
                name = name[:card_w-4] + "…"

            if is_sel:
                name_col = f"{C.BG_BBLACK}{C.BGREEN}{C.BOLD} {name} {C.RESET}"
            elif is_marked:
                name_col = f"{C.BYELLOW}*{name}{C.RESET}"
            elif is_dir:
                name_col = f"{C.BBLUE}{name}{C.RESET}"
            else:
                name_col = f"{C.WHITE}{name}{C.RESET}"

            cards.append({
                "icon": icon_lines,
                "label": name_col,
                "label_raw": name,
                "is_sel": is_sel,
                "is_marked": is_marked,
            })

        # Print 5 icon lines + label line + blank separator
        for line_i in range(5):
            row_str = ""
            for ci, card in enumerate(cards):
                icon_line = card["icon"][line_i]
                # Center icon within card_w
                iv = vlen(icon_line)
                lpad = (card_w - iv) // 2
                rpad = card_w - iv - lpad
                seg = " "*lpad + icon_line + " "*rpad
                if card["is_sel"]:
                    seg = f"{C.BG_BBLACK}{seg}{C.RESET}"
                row_str += seg
            # Pad the whole row
            rv = vlen(row_str)
            row_str += " " * max(0, inner - rv)
            print(f"{C.BBLACK}║{C.RESET}{row_str}{C.BBLACK}║{C.RESET}")
            lines_printed += 1

        # Label line
        row_str = ""
        for ci, card in enumerate(cards):
            lv = vlen(card["label"])
            lpad = (card_w - lv) // 2
            rpad = card_w - lv - lpad
            seg = " "*max(0,lpad) + card["label"] + " "*max(0,rpad)
            if card["is_sel"]:
                seg = f"{C.BG_BBLACK}{seg}{C.RESET}"
            row_str += seg
        rv = vlen(row_str)
        row_str += " " * max(0, inner - rv)
        print(f"{C.BBLACK}║{C.RESET}{row_str}{C.BBLACK}║{C.RESET}")
        lines_printed += 1

        # Gap line between card rows
        print(f"{C.BBLACK}║{C.RESET}{' '*inner}{C.BBLACK}║{C.RESET}")
        lines_printed += 1

    # Fill remaining
    while lines_printed < avail_rows:
        print(f"{C.BBLACK}║{C.RESET}{' '*inner}{C.BBLACK}║{C.RESET}")
        lines_printed += 1

    # Scroll/count bar
    total = len(entries)
    pct = int((selected_idx / max(1, total-1)) * 100)
    info = f"  {C.BBLACK}[{selected_idx+1}/{total}  row {sel_card_row+1}/{total_card_rows}  {pct}%]{C.RESET}"
    print(f"{C.BBLACK}║{C.RESET}{pad_to(info, inner)}{C.BBLACK}║{C.RESET}")

    return scroll_offset

# ─── RENDERING: LIST VIEW ────────────────────────────────────────────────────
def render_list(entries, selected_idx, cols, rows, marked, scroll_offset):
    inner = cols - 2
    avail = max(5, rows - 11)

    if selected_idx < scroll_offset:
        scroll_offset = selected_idx
    elif selected_idx >= scroll_offset + avail:
        scroll_offset = selected_idx - avail + 1

    if not entries:
        empty = pad_to(f" {C.BBLACK}(empty directory){C.RESET}", inner)
        print(f"{C.BBLACK}║{C.RESET}{empty}{C.BBLACK}║{C.RESET}")
        for _ in range(avail - 1):
            print(f"{C.BBLACK}║{C.RESET}{' '*inner}{C.BBLACK}║{C.RESET}")
        print(f"{C.BBLACK}║{C.RESET}{pad_to(f'  {C.BBLACK}[0 items]{C.RESET}', inner)}{C.BBLACK}║{C.RESET}")
        return scroll_offset

    # Column widths
    name_w = max(10, inner - 45)  # perm(9)+size(10)+time(16)+icon(5)+gaps

    for i in range(scroll_offset, min(scroll_offset + avail, len(entries))):
        e = entries[i]
        path = e["path"]
        is_dir = e["is_dir"]
        is_sel = (i == selected_idx)
        is_marked = path in marked

        num  = f"{C.BBLACK}{i+1:>3}{C.RESET}"
        mark = f"{C.BYELLOW}*{C.RESET}" if is_marked else " "
        icon = small_icon(path, is_dir)
        perm = f"{C.BBLACK}{e['perms']}{C.RESET}"
        size = f"{C.BBLACK}{'   <DIR>' if is_dir else fmt_size(e['size'])}{C.RESET}"
        time = f"{C.BBLACK}{fmt_time(e['mtime'])}{C.RESET}"

        name = path.name
        if e["is_link"]:
            try: name += f" → {os.readlink(path)}"
            except: pass
        if len(name) > name_w: name = name[:name_w-1] + "…"

        # Name colour: green if selected, else normal colours
        if is_sel:
            name_col = f"{C.BOLD}{C.BGREEN}{name}{C.RESET}"
        elif is_dir:
            name_col = f"{C.BOLD}{C.BBLUE}{name}{C.RESET}"
        elif os.access(path, os.X_OK) and path.is_file():
            name_col = f"{C.BYELLOW}{name}{C.RESET}"
        else:
            name_col = f"{C.WHITE}{name}{C.RESET}"

        # Left side: num mark icon name
        left = f" {num} {mark} {icon} {name_col}"
        lv = vlen(left)
        # Right side: perm size time
        right = f"  {perm}  {size}  {time} "
        rv = vlen(right)
        gap = max(1, inner - lv - rv)
        line = left + " "*gap + right

        # Selected row: just the name is green, no background change
        print(f"{C.BBLACK}║{C.RESET}{line}{' '*max(0,inner-vlen(line))}{C.BBLACK}║{C.RESET}")

    filled = min(scroll_offset + avail, len(entries)) - scroll_offset
    for _ in range(avail - filled):
        print(f"{C.BBLACK}║{C.RESET}{' '*inner}{C.BBLACK}║{C.RESET}")

    total = len(entries)
    pct = int((selected_idx / max(1, total-1)) * 100)
    info = f"  {C.BBLACK}[{selected_idx+1}/{total}  {pct}%]{C.RESET}"
    print(f"{C.BBLACK}║{C.RESET}{pad_to(info, inner)}{C.BBLACK}║{C.RESET}")

    return scroll_offset

# ─── INPUT LINE (for prompts, restores cooked mode) ──────────────────────────
def ask(msg, default=""):
    # Restore terminal to cooked mode explicitly before reading input.
    # After read_key() uses sys.stdin.read(1) in raw mode, Python's
    # TextIOWrapper has a dirty internal buffer. Reopening stdin via
    # /proc/self/fd/0 gives a clean line-buffered stream every time.
    try:
        fd = sys.stdin.fileno()
        attrs = termios.tcgetattr(fd)
        attrs[3] |= termios.ECHO | termios.ICANON   # enable echo + line mode
        termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
        clean_stdin = open('/proc/self/fd/0', 'r', buffering=1)
    except Exception:
        clean_stdin = sys.stdin
    sys.stdout.write(f"\n  {C.BCYAN}?{C.RESET} {msg}")
    if default: sys.stdout.write(f" [{C.BBLACK}{default}{C.RESET}]")
    sys.stdout.write(": ")
    sys.stdout.flush()
    try:
        val = clean_stdin.readline().strip()
        return val or default
    except (KeyboardInterrupt, EOFError):
        return ""

def ask_choice(msg, choices):
    print(f"\n  {C.BCYAN}?{C.RESET} {msg}")
    for i, c in enumerate(choices):
        print(f"    {C.BWHITE}{i+1:>2}{C.RESET}. {c}")
    try:
        v = input(f"  Choice [1-{len(choices)}]: ").strip()
        idx = int(v) - 1
        if 0 <= idx < len(choices):
            return choices[idx]
    except: pass
    return ""

def ask_confirm(msg):
    sys.stdout.write(f"\n  {C.BRED}!{C.RESET} {msg} [y/N]: ")
    sys.stdout.flush()
    try:
        return input().strip().lower() == "y"
    except: return False

# ─── FILE OPERATIONS ─────────────────────────────────────────────────────────
def safe_copy(src, dst_dir):
    dst = dst_dir / src.name
    if dst.exists():
        s, e, n = src.stem, src.suffix, 1
        while dst.exists():
            dst = dst_dir / f"{s}_copy{n}{e}"; n+=1
    if src.is_dir(): shutil.copytree(str(src), str(dst))
    else:            shutil.copy2(str(src), str(dst))
    return dst

def safe_move(src, dst_dir):
    dst = dst_dir / src.name
    if dst.exists() and dst != src:
        s, e, n = src.stem, src.suffix, 1
        while dst.exists():
            dst = dst_dir / f"{s}_mv{n}{e}"; n+=1
    shutil.move(str(src), str(dst))

def get_dir_size(path):
    total = 0
    try:
        for f in path.rglob("*"):
            try:
                if f.is_file(): total += f.stat().st_size
            except: pass
    except: pass
    return total

# ─── TOOL CHECK ──────────────────────────────────────────────────────────────
def need_tool(tool, pkg_arch, pkg_deb):
    if shutil.which(tool): return True
    pkg = pkg_arch if OS.distro in ("arch","manjaro","endeavouros","artix") else pkg_deb
    print(f"\n  {C.BYELLOW}[!]{C.RESET} '{tool}' not found.")
    cmd = OS.install(pkg)
    if cmd:
        print(f"  Install: {C.BGREEN}{' '.join(cmd)}{C.RESET}")
        if ask_confirm("Install now?"):
            try:
                subprocess.run(cmd, check=True)
                return shutil.which(tool) is not None
            except: pass
    else:
        print(f"  Install '{pkg}' manually.")
    return False

# ─── COMPRESSION ─────────────────────────────────────────────────────────────
def do_compress(items, dest, fmt):
    try:
        if fmt in (".tar",".tar.gz",".tgz",".tar.bz2",".tar.xz",".tar.zst"):
            m = {".tar":"w",".tar.gz":"w:gz",".tgz":"w:gz",".tar.bz2":"w:bz2",".tar.xz":"w:xz"}.get(fmt,"w")
            with tarfile.open(str(dest), m) as t:
                for i in items: t.add(str(i), arcname=i.name)
            return True, None
        elif fmt == ".zip":
            with zipfile.ZipFile(str(dest),"w",zipfile.ZIP_DEFLATED) as z:
                for item in items:
                    if item.is_dir():
                        for f in item.rglob("*"): z.write(str(f), str(f.relative_to(item.parent)))
                    else: z.write(str(item), item.name)
            return True, None
        elif fmt == ".gz" and len(items)==1 and items[0].is_file():
            with open(items[0],"rb") as fi, gzip.open(str(dest),"wb") as fo:
                shutil.copyfileobj(fi,fo)
            return True, None
        elif fmt == ".bz2" and len(items)==1 and items[0].is_file():
            with open(items[0],"rb") as fi, bz2.open(str(dest),"wb") as fo:
                shutil.copyfileobj(fi,fo)
            return True, None
        elif fmt in (".xz",".lzma") and len(items)==1 and items[0].is_file():
            with open(items[0],"rb") as fi, lzma.open(str(dest),"wb") as fo:
                shutil.copyfileobj(fi,fo)
            return True, None
        elif fmt == ".7z":
            if not need_tool("7z","p7zip","p7zip-full"): return False,"7z unavailable"
            r = subprocess.run(["7z","a",str(dest)]+[str(i) for i in items], capture_output=True)
            return r.returncode==0, r.stderr.decode() if r.returncode else None
        elif fmt == ".zst":
            if not need_tool("zstd","zstd","zstd"): return False,"zstd unavailable"
            if len(items)==1 and items[0].is_file():
                r = subprocess.run(["zstd",str(items[0]),"-o",str(dest)], capture_output=True)
                return r.returncode==0, r.stderr.decode() if r.returncode else None
            return False,"Use .tar.zst for multiple files"
        return False, f"Unsupported: {fmt}"
    except Exception as e: return False, str(e)

def do_extract(archive, dest_dir):
    name = archive.name.lower()
    try:
        if any(name.endswith(x) for x in (".tar.gz",".tgz",".tar.bz2",".tar.xz",".tar.zst",".tar")):
            with tarfile.open(str(archive)) as t: t.extractall(str(dest_dir))
            return True, None
        elif name.endswith(".zip"):
            with zipfile.ZipFile(str(archive)) as z: z.extractall(str(dest_dir))
            return True, None
        elif name.endswith(".gz"):
            with gzip.open(str(archive),"rb") as fi, open(str(dest_dir/archive.stem),"wb") as fo:
                shutil.copyfileobj(fi,fo)
            return True, None
        elif name.endswith(".bz2"):
            with bz2.open(str(archive),"rb") as fi, open(str(dest_dir/archive.stem),"wb") as fo:
                shutil.copyfileobj(fi,fo)
            return True, None
        elif name.endswith(".xz"):
            with lzma.open(str(archive),"rb") as fi, open(str(dest_dir/archive.stem),"wb") as fo:
                shutil.copyfileobj(fi,fo)
            return True, None
        elif name.endswith(".7z"):
            if not need_tool("7z","p7zip","p7zip-full"): return False,"7z unavailable"
            r = subprocess.run(["7z","x",str(archive),f"-o{dest_dir}","-y"], capture_output=True)
            return r.returncode==0, r.stderr.decode() if r.returncode else None
        elif name.endswith(".rar"):
            tool = "unrar" if shutil.which("unrar") else ("rar" if shutil.which("rar") else None)
            if not tool:
                need_tool("unrar","unrar","unrar")
                tool = "unrar" if shutil.which("unrar") else None
            if not tool: return False,"unrar unavailable"
            r = subprocess.run([tool,"x",str(archive),str(dest_dir)+"/"], capture_output=True)
            return r.returncode==0, r.stderr.decode() if r.returncode else None
        elif name.endswith(".zst"):
            if not need_tool("zstd","zstd","zstd"): return False,"zstd unavailable"
            r = subprocess.run(["zstd","-d",str(archive),"-o",str(dest_dir/archive.stem)], capture_output=True)
            return r.returncode==0, r.stderr.decode() if r.returncode else None
        return False, f"Unknown format: {archive.suffix}"
    except Exception as e: return False, str(e)

# ─── FILE OPENER ─────────────────────────────────────────────────────────────
def open_file(path):
    ext = path.suffix.lower()
    text_ext = {".txt",".md",".rst",".log",".cfg",".conf",".ini",".env",".py",
                ".js",".ts",".c",".cpp",".h",".rs",".go",".sh",".bash",".zsh",
                ".rb",".php",".java",".html",".css",".json",".xml",".yaml",".yml",
                ".toml",".csv",".sql","",".gitignore",".gitattributes",".Makefile"}
    img_ext  = {".png",".jpg",".jpeg",".gif",".bmp",".svg",".webp",".ico"}
    media_ext= {".mp3",".flac",".wav",".ogg",".mp4",".mkv",".avi",".mov",".webm"}
    pdf_ext  = {".pdf"}

    def try_cmds(cmds):
        for c in cmds:
            if shutil.which(c): subprocess.run([c, str(path)]); return True
        return False

    if ext in text_ext or not path.suffix:
        if not try_cmds(["nvim","vim","nano","micro","helix","emacs"]):
            if not try_cmds(["bat","less","more"]):
                print(f"\n{C.BBLACK}--- {path.name} ---{C.RESET}")
                try:
                    with open(path) as f:
                        for i, line in enumerate(f):
                            if i >= 60: print(f"{C.BBLACK}...(truncated){C.RESET}"); break
                            print(line, end="")
                except: print(f"{C.BRED}Cannot read.{C.RESET}")
                input(f"\n{C.BBLACK}[Enter]{C.RESET}")
        return
    if ext in img_ext:
        if not try_cmds(["chafa","feh","sxiv","nsxiv","imv"]):
            print(f"{C.BYELLOW}No image viewer. Try: pacman -S chafa{C.RESET}")
            input(f"{C.BBLACK}[Enter]{C.RESET}")
        return
    if ext in media_ext:
        if not try_cmds(["mpv","vlc","mplayer"]):
            print(f"{C.BYELLOW}No media player. Try: pacman -S mpv{C.RESET}")
            input(f"{C.BBLACK}[Enter]{C.RESET}")
        return
    if ext in pdf_ext:
        if not try_cmds(["zathura","mupdf","evince","okular"]):
            print(f"{C.BYELLOW}No PDF viewer. Try: pacman -S zathura{C.RESET}")
            input(f"{C.BBLACK}[Enter]{C.RESET}")
        return
    if shutil.which("xdg-open"): subprocess.Popen(["xdg-open", str(path)]); return
    open_file.__wrapped__ = True  # fallback to text
    try_cmds(["less","more","cat"])

# ─── PROPERTIES ──────────────────────────────────────────────────────────────
def show_properties(path, cols):
    clear()
    inner = cols - 2
    print(f"{C.BBLACK}╔{'═'*inner}╗{C.RESET}")
    title = pad_to(f" {C.BCYAN}{C.BOLD}Properties:{C.RESET} {C.BWHITE}{path.name}{C.RESET}", inner)
    print(f"{C.BBLACK}║{C.RESET}{title}{C.BBLACK}║{C.RESET}")
    print(f"{C.BBLACK}╠{'═'*inner}╣{C.RESET}")
    def row(k, v, vc=C.BWHITE):
        line = pad_to(f"  {C.BBLACK}{k:<22}{C.RESET}{vc}{v}{C.RESET}", inner)
        print(f"{C.BBLACK}║{C.RESET}{line}{C.BBLACK}║{C.RESET}")
    try:
        st = path.lstat()
        is_link = stat.S_ISLNK(st.st_mode)
        rs = path.stat() if is_link else st
        row("Name:", path.name)
        row("Path:", str(path))
        row("Type:", "Directory" if path.is_dir() else "Symlink" if is_link else "File")
        if is_link:
            try: row("Link Target:", os.readlink(path))
            except: pass
        row("Size:", f"{fmt_size(rs.st_size).strip()}  ({rs.st_size} bytes)")
        if path.is_dir():
            try:
                items = list(path.iterdir())
                row("Contents:", f"{sum(1 for i in items if i.is_file())} files, {sum(1 for i in items if i.is_dir())} dirs")
                total = get_dir_size(path)
                row("Total Size:", f"{fmt_size(total).strip()}  ({total} bytes)")
            except: pass
        row("Permissions:", f"{fmt_perms(st.st_mode)}  ({oct(st.st_mode)[-4:]})")
        row("Owner UID:", str(st.st_uid)); row("Group GID:", str(st.st_gid))
        row("Modified:", fmt_time(rs.st_mtime)); row("Accessed:", fmt_time(rs.st_atime))
        row("Changed:", fmt_time(rs.st_ctime))
        if path.is_file():
            row("Extension:", path.suffix or "(none)")
            row("Executable:", f"{C.BGREEN}Yes{C.RESET}" if os.access(path, os.X_OK) else "No")
            if shutil.which("file"):
                r = subprocess.run(["file","--brief",str(path)], capture_output=True, text=True)
                row("MIME:", r.stdout.strip())
        row("Inode:", str(st.st_ino)); row("Hard Links:", str(st.st_nlink))
    except Exception as e:
        row("Error:", str(e), C.BRED)
    print(f"{C.BBLACK}╠{'═'*inner}╣{C.RESET}")
    print(f"{C.BBLACK}║{C.RESET}{pad_to(f'  {C.BBLACK}[Press Enter to return]{C.RESET}', inner)}{C.BBLACK}║{C.RESET}")
    print(f"{C.BBLACK}╚{'═'*inner}╝{C.RESET}")
    input()

# ─── SEARCH ──────────────────────────────────────────────────────────────────
def do_search(base, pattern, max_r=300):
    results = []
    try:
        for item in base.rglob("*"):
            if fnmatch.fnmatch(item.name.lower(), f"*{pattern.lower()}*"):
                results.append(item)
                if len(results) >= max_r: break
    except: pass
    return results

def do_find(pattern):
    """
    Find files/folders by name.
    Step 1: search ~/  (fast, most likely location)
    Step 2: if nothing found, search systemwide from /
    Skips /proc /sys /dev to avoid hangs.
    Returns list of Path objects.
    """
    SKIP = {"/proc", "/sys", "/dev", "/run", "/snap"}
    max_r = 200

    def search_tree(base, pat, results):
        try:
            for item in Path(base).rglob("*"):
                # Skip noisy system dirs
                try:
                    parts = item.parts
                    if any(("/" + p) in SKIP or p in SKIP for p in parts[:3]):
                        continue
                except:
                    continue
                if fnmatch.fnmatch(item.name.lower(), f"*{pat.lower()}*"):
                    results.append(item)
                if len(results) >= max_r:
                    return True  # cap hit
        except (KeyboardInterrupt, PermissionError):
            pass
        return False

    results = []
    print(f"  {C.BBLACK}Searching ~/ ...{C.RESET}", end="\r", flush=True)
    try:
        capped = search_tree(Path.home(), pattern, results)
    except KeyboardInterrupt:
        return results

    if results:
        return results  # found in home, done

    # Nothing in ~/ — go systemwide
    print(f"  {C.BBLACK}Not found in ~/  Searching system (Ctrl+C to stop)...{C.RESET}", flush=True)
    try:
        search_tree("/", pattern, results)
    except KeyboardInterrupt:
        pass

    return results


def browse_results(results, cols):
    """
    Scrollable result browser.
    Shows PAGE_SIZE results at a time.
    UP arrow / U = previous page, DOWN arrow / D = next page.
    Type a number + Enter to jump there, or Enter alone to cancel.
    Returns chosen Path or None.
    """
    PAGE = 7
    offset = 0
    total = len(results)
    inner = cols - 2

    while True:
        clear()
        page_results = results[offset : offset + PAGE]
        print(f"\n  {C.BBLUE}Results: {total} found{C.RESET}  "
              f"{C.BBLACK}showing {offset+1}–{min(offset+PAGE, total)}{C.RESET}")
        print(f"  {C.BBLACK}{'─'*min(inner-4,60)}{C.RESET}")
        for i, r in enumerate(page_results):
            abs_i = offset + i
            try:
                isd = r.is_dir()
                icon = small_icon(r, isd)
                name = f"{C.BBLUE}{r.name}{C.RESET}" if isd else f"{C.WHITE}{r.name}{C.RESET}"
                parent = f"{C.BBLACK}{str(r.parent)}{C.RESET}"
                print(f"  {C.BWHITE}{abs_i+1:>4}{C.RESET}  {icon}  {name}  {parent}")
            except Exception:
                print(f"  {C.BBLACK}{abs_i+1:>4}{C.RESET}  {C.BRED}(inaccessible){C.RESET}")
        print(f"  {C.BBLACK}{'─'*min(inner-4,60)}{C.RESET}")
        nav = []
        if offset > 0: nav.append(f"{C.BWHITE}↑/U{C.RESET}=prev")
        if offset + PAGE < total: nav.append(f"{C.BWHITE}↓/D{C.RESET}=next")
        nav.append(f"{C.BWHITE}#Enter{C.RESET}=go  {C.BWHITE}Enter{C.RESET}=cancel")
        print("  " + "  ".join(nav))
        sys.stdout.write("\n  Choice: ")
        sys.stdout.flush()

        # Read input using os.read(fd,1) — bypasses ALL Python buffering
        fd = sys.stdin.fileno()
        old_attrs = termios.tcgetattr(fd)
        tty.setraw(fd)
        inp = ""
        try:
            import select as _bsel
            while True:
                b = os.read(fd, 1)
                if not b: break
                n = b[0]
                if n in (10, 13):    # Enter
                    break
                elif n == 27:        # escape sequence
                    rdy = _bsel.select([fd],[],[],0.05)[0]
                    if not rdy: continue
                    b2 = os.read(fd, 1)
                    if b2 == b"[":
                        rdy2 = _bsel.select([fd],[],[],0.05)[0]
                        if not rdy2: continue
                        b3 = os.read(fd, 1)
                        if b3 == b"A":    # UP arrow
                            if offset > 0:
                                offset = max(0, offset - PAGE)
                                inp = "__NAV__"; break
                        elif b3 == b"B":  # DOWN arrow
                            if offset + PAGE < total:
                                offset = min(total-PAGE, offset+PAGE)
                                offset = max(0, offset)
                                inp = "__NAV__"; break
                elif n in (127, 8):  # Backspace
                    if inp:
                        inp = inp[:-1]
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                elif n == 3:         # Ctrl+C
                    inp = ""; break
                elif 48 <= n <= 57:  # digit 0-9
                    inp += chr(n)
                    sys.stdout.write(chr(n))
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)
        sys.stdout.write("\n")
        sys.stdout.flush()

        if inp == "__NAV__":
            continue
        if not inp:
            return None
        try:
            idx = int(inp) - 1
            if 0 <= idx < total:
                return results[idx]
        except Exception:
            pass

def show_search_results(results, cols):
    """Legacy wrapper — now uses browse_results."""
    browse_results(results, cols)

# ─── HELP ────────────────────────────────────────────────────────────────────
def show_help(cols):
    clear()
    inner = cols - 2
    print(f"{C.BBLACK}╔{'═'*inner}╗{C.RESET}")
    print(f"{C.BBLACK}║{C.RESET}{pad_to(f' {C.BCYAN}{C.BOLD}CLIFM v3.0  Help{C.RESET}', inner)}{C.BBLACK}║{C.RESET}")
    print(f"{C.BBLACK}╠{'═'*inner}╣{C.RESET}")
    sections = [
        ("Navigation", [
            ("↑ / K / W",      "Move cursor up"),
            ("↓ / J / S",      "Move cursor down"),
            ("Enter",          "Open file or enter directory"),
            ("← / Backspace",  "Go back (parent dir / history)"),
            ("→",              "Go forward (history)"),
            ("PageUp / U",     "Jump up one page"),
            ("PageDown / O",   "Jump down one page"),
            ("Home / gg",      "First item"),
            ("End / ge",       "Last item"),
            ("H",              "Jump to Home directory"),
            ("G",              "Go to typed path (tab completion)"),
            ("1-9 or :N",      "Jump to item by number"),
        ]),
        ("Selection & Clipboard", [
            ("Space",          "Mark/unmark item, advance cursor"),
            ("A",              "Select all  /  deselect all"),
            ("C",              "Copy marked/current to clipboard"),
            ("X",              "Cut  (move on paste)"),
            ("P",              "Paste clipboard into current directory"),
            ("Esc",            "Clear all marks"),
        ]),
        ("File Operations", [
            ("D",              "Delete (confirm required)"),
            ("R",              "Rename"),
            ("N",              "New file or directory"),
            ("Z",              "Compress  (zip/tar.gz/tar.xz/7z/zst…)"),
            ("E",              "Extract archive"),
            ("L",              "chmod  (change permissions)"),
            ("O",              "Open with specific command"),
            ("!",              "Open shell in current directory"),
        ]),
        ("View & Search", [
            ("V",              "Toggle icon grid ↔ list view"),
            ("T",              "Cycle sort mode"),
            (".",              "Toggle hidden files"),
            ("/ or F",         "Search & filter"),
            ("I",              "Properties panel"),
            ("F5",             "Refresh directory"),
            ("?",              "This help screen"),
            ("Q",              "Quit"),
        ]),
    ]
    for sec, items in sections:
        hdr = pad_to(f"  {C.BBLUE}{sec}{C.RESET}", inner)
        print(f"{C.BBLACK}║{C.RESET}{hdr}{C.BBLACK}║{C.RESET}")
        for key, desc in items:
            line = pad_to(f"    {C.BYELLOW}{key:<22}{C.RESET} {desc}", inner)
            print(f"{C.BBLACK}║{C.RESET}{line}{C.BBLACK}║{C.RESET}")
        print(f"{C.BBLACK}║{C.RESET}{' '*inner}{C.BBLACK}║{C.RESET}")
    print(f"{C.BBLACK}╠{'═'*inner}╣{C.RESET}")
    print(f"{C.BBLACK}║{C.RESET}{pad_to(f'  {C.BBLACK}[Press any key]{C.RESET}', inner)}{C.BBLACK}║{C.RESET}")
    print(f"{C.BBLACK}╚{'═'*inner}╝{C.RESET}")
    read_key()

# ─── MAIN LOOP ───────────────────────────────────────────────────────────────
def realtime_path_input():
    """
    Real-time path input with live completion display.
    Shows matching paths as you type. Tab to complete. Enter to go. Esc to cancel.
    Reads sys.stdin.buffer directly — no TextIOWrapper, no input(), guaranteed to work.
    Returns (path_string, cancelled).
    """
    import select as _rsel

    def get_completions(text):
        try:
            exp = os.path.expanduser(text)
            if exp.endswith('/') or exp == '':
                base, prefix = (exp or '.'), ''
            else:
                base  = os.path.dirname(exp) or '.'
                prefix = os.path.basename(exp)
            items = []
            try:
                for name in sorted(os.listdir(base)):
                    if name.lower().startswith(prefix.lower()):
                        full = os.path.join(base, name)
                        items.append(full + ('/' if os.path.isdir(full) else ''))
            except PermissionError:
                pass
            return items
        except Exception:
            return []

    def redraw(text, comps):
        cols, _ = term_size()
        sys.stdout.write('\r\033[J')  # cursor to col 0, clear below
        sys.stdout.write('  > ' + text)
        if comps:
            sys.stdout.write('\n')
            shown = comps[:8]
            for c in shown:
                name = os.path.basename(c.rstrip('/')) + ('/' if c.endswith('/') else '')
                col  = C.BBLUE if c.endswith('/') else C.BBLACK
                sys.stdout.write('    ' + col + name + C.RESET + '\n')
            if len(comps) > 8:
                sys.stdout.write('    ' + C.BBLACK + '... and ' + str(len(comps)-8) + ' more' + C.RESET + '\n')
            lines_below = len(shown) + (1 if len(comps) > 8 else 0) + 1
            sys.stdout.write('\033[' + str(lines_below) + 'A')
            sys.stdout.write('\r  > ' + text)
        sys.stdout.flush()

    clear()
    print('\n  ' + C.BCYAN + 'Go to Path' + C.RESET +
          '  ' + C.BBLACK + 'Type path, Tab=complete, Enter=go, Esc=cancel, Ctrl+U=clear' + C.RESET)
    print()
    sys.stdout.write('  > ')
    sys.stdout.flush()

    fd  = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setraw(fd)

    text      = ''
    comps     = []
    cancelled = False

    try:
        while True:
            b = os.read(fd, 1)
            if not b:
                break
            n = b[0]

            if n in (10, 13):       # Enter — done
                comps = []
                redraw(text, comps)
                break

            elif n == 27:           # ESC or arrow key sequence
                rdy = _rsel.select([fd], [], [], 0.05)[0]
                if rdy:
                    b2 = os.read(fd, 1)
                    if b2 == b'[':
                        rdy2 = _rsel.select([fd], [], [], 0.05)[0]
                        if rdy2:
                            os.read(fd, 1)  # swallow A/B/C/D etc
                    # arrow key — ignore, just redraw
                    redraw(text, comps)
                else:
                    # bare ESC = cancel
                    cancelled = True
                    break

            elif n == 9:            # Tab
                new_comps = get_completions(text)
                if not new_comps:
                    pass
                elif len(new_comps) == 1:
                    text  = new_comps[0]
                    comps = []
                    redraw(text, comps)
                else:
                    common = os.path.commonprefix(new_comps)
                    if len(common) > len(text):
                        text  = common
                        comps = []
                        redraw(text, comps)
                    else:
                        comps = new_comps
                        redraw(text, comps)

            elif n in (127, 8):    # Backspace
                if text:
                    text = text[:-1]
                comps = []
                redraw(text, comps)

            elif n == 3:            # Ctrl+C
                cancelled = True
                break

            elif n == 21:           # Ctrl+U — clear line
                text  = ''
                comps = []
                redraw(text, comps)

            elif 32 <= n <= 126 or n > 127:  # printable
                text += chr(n)
                comps = get_completions(text)  # update completions live as you type
                redraw(text, comps)

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

    sys.stdout.write('\n')
    sys.stdout.flush()
    return text.strip(), cancelled


def main():
    cwd = Path(sys.argv[1]).resolve() if len(sys.argv)>1 and Path(sys.argv[1]).is_dir() else Path.home()
    HIST.go(cwd)

    sel       = 0
    scroll    = 0
    hidden    = False
    sort_mode = "name"
    view_mode = "grid"   # "grid" or "list"
    marked    : set = set()
    status    = f"Welcome  OS:{C.BCYAN}{OS.distro}{C.RESET}  pkg:{C.BCYAN}{OS.pkg['name'] if OS.pkg else '?'}{C.RESET}"
    filter_str= ""
    num_buf   = ""        # for multi-digit number jumps

    while True:
        cols, rows = term_size()
        entries = read_dir(cwd, hidden, sort_mode, filter_str)

        if entries:
            sel = max(0, min(sel, len(entries)-1))
        else:
            sel = 0

        # ── DRAW ──
        clear()
        render_header(cwd, cols, CLIP, sort_mode, hidden, view_mode, filter_str)
        if view_mode == "grid":
            scroll = render_grid(entries, sel, cols, rows, marked, scroll)
        else:
            scroll = render_list(entries, sel, cols, rows, marked, scroll)
        render_footer(cols, status)

        current = entries[sel]["path"] if entries else None
        status = ""

        # ── KEY ──
        try:
            k = read_key()
        except (KeyboardInterrupt, EOFError):
            break

        # Number buffer for :N jumps
        if k.isdigit():
            num_buf += k
            status = f"Jump to: {C.BYELLOW}{num_buf}{C.RESET}  (Enter to go, Esc to cancel)"
            continue
        if num_buf:
            if k == "ENTER":
                try:
                    idx = int(num_buf) - 1
                    if 0 <= idx < len(entries): sel = idx
                    else: status = f"{C.BRED}No item #{num_buf}{C.RESET}"
                except: pass
                num_buf = ""; continue
            elif k == "ESC":
                num_buf = ""; status = "Jump cancelled"; continue
            else:
                num_buf = ""  # non-digit/enter clears buffer, fall through

        ku = k.upper()

        # ── NAVIGATION ──
        if k in ("UP","k","K","w","W"):
            sel = max(0, sel-1)

        elif k in ("DOWN","j","J","s","S"):
            sel = min(len(entries)-1, sel+1) if entries else 0

        elif k == "LEFT":
            # Left arrow = go back in history
            cwd = HIST.go_back()
            sel = 0; scroll = 0; filter_str = ""

        elif k == "BACKSPACE":
            # Backspace = go to parent directory
            parent = cwd.parent
            if parent != cwd:
                HIST.go(parent); cwd = parent
            sel = 0; scroll = 0; filter_str = ""

        elif k == "RIGHT":
            cwd = HIST.go_fwd()
            sel = 0; scroll = 0; filter_str = ""

        elif k == "PAGEUP":
            avail_rows = max(5, rows - 11)
            per_row = max(1, (cols-2) // CARD_W) if view_mode=="grid" else 1
            jump = (avail_rows // CARD_H) * per_row if view_mode=="grid" else avail_rows
            sel = max(0, sel - jump)

        elif k == "PAGEDOWN":
            avail_rows = max(5, rows - 11)
            per_row = max(1, (cols-2) // CARD_W) if view_mode=="grid" else 1
            jump = (avail_rows // CARD_H) * per_row if view_mode=="grid" else avail_rows
            sel = min(len(entries)-1, sel+jump) if entries else 0

        elif k == "HOME":
            sel = 0

        elif k == "END":
            sel = len(entries)-1 if entries else 0

        elif k == "ENTER":
            if current:
                if entries[sel]["is_dir"]:
                    HIST.go(current); cwd = current
                    sel = 0; scroll = 0; filter_str = ""
                else:
                    clear(); open_file(current)

        # ── MARKS ──
        elif k == "SPACE":
            if current:
                if current in marked: marked.discard(current)
                else: marked.add(current)
                sel = min(len(entries)-1, sel+1) if entries else 0

        elif ku == "A":
            if len(marked) == len(entries) and entries:
                marked.clear(); status = "Deselected all"
            else:
                marked = {e["path"] for e in entries}; status = f"Marked {len(marked)} items"

        # ── CLIPBOARD ──
        elif ku == "C":
            targets = list(marked) if marked else ([current] if current else [])
            if targets:
                CLIP.set(targets, "copy")
                status = f"Copied {len(targets)} item(s) — navigate and press P to paste"
            else: status = f"{C.BYELLOW}Nothing to copy{C.RESET}"

        elif ku == "X":
            targets = list(marked) if marked else ([current] if current else [])
            if targets:
                CLIP.set(targets, "cut")
                status = f"Cut {len(targets)} item(s) — navigate and press P to paste"
            else: status = f"{C.BYELLOW}Nothing to cut{C.RESET}"

        elif ku == "P":
            if not CLIP.has():
                status = f"{C.BYELLOW}Clipboard empty — use C to copy or X to cut first{C.RESET}"
            else:
                errs = []; ok = 0
                for item in CLIP.items:
                    try:
                        if CLIP.mode == "copy": safe_copy(item, cwd)
                        else:                   safe_move(item, cwd)
                        ok += 1
                    except Exception as e: errs.append(f"{item.name}: {e}")
                if CLIP.mode == "cut": CLIP.clear()
                status = f"Pasted {ok} item(s)" if not errs else f"{C.BRED}{'; '.join(errs)}{C.RESET}"

        # ── DELETE ──
        elif ku == "D":
            targets = list(marked) if marked else ([current] if current else [])
            if not targets: status = "Nothing selected"
            else:
                clear()
                names = ", ".join(t.name for t in targets[:3])
                if len(targets)>3: names += f" +{len(targets)-3}"
                if ask_confirm(f"Permanently delete: {names}?"):
                    errs = []
                    for t in targets:
                        try:
                            if t.is_dir() and not t.is_symlink(): shutil.rmtree(str(t))
                            else: t.unlink()
                        except Exception as e: errs.append(f"{t.name}: {e}")
                    marked -= set(targets)
                    sel = max(0, sel - len(targets))
                    status = f"Deleted {len(targets)-len(errs)} item(s)" if not errs else f"{C.BRED}{'; '.join(errs)}{C.RESET}"
                else: status = "Delete cancelled"

        # ── RENAME ──
        elif ku == "R":
            if current:
                clear()
                nn = ask(f"Rename '{current.name}' to", current.name)
                if nn and nn != current.name:
                    try:
                        current.rename(current.parent / nn)
                        status = f"Renamed → {nn}"
                    except Exception as e: status = f"{C.BRED}{e}{C.RESET}"
                else: status = "Rename cancelled"

        # ── NEW ──
        elif ku == "N":
            clear()
            print(f"\n  {C.BCYAN}Create new:{C.RESET}")
            print(f"  {C.BWHITE}1{C.RESET}. File"); print(f"  {C.BWHITE}2{C.RESET}. Directory")
            ch = ask("Choice [1/2]")
            name = ask("Name")
            if name:
                t = cwd / name
                try:
                    if ch == "1": t.touch(); status = f"Created file: {name}"
                    elif ch == "2": t.mkdir(parents=True, exist_ok=True); status = f"Created dir: {name}"
                    else: status = "Cancelled"
                except Exception as e: status = f"{C.BRED}{e}{C.RESET}"
            else: status = "Cancelled"

        # ── COMPRESS ──
        elif ku == "Z":
            targets = list(marked) if marked else ([current] if current else [])
            if not targets: status = "Nothing selected"
            else:
                clear()
                fmts = [".zip",".tar.gz",".tar.bz2",".tar.xz",".tar",".gz",".bz2",".xz",".7z",".zst"]
                fmt = ask_choice("Compression format", fmts)
                if fmt:
                    default = targets[0].stem if len(targets)==1 else "archive"
                    out = ask("Output name (no extension)", default)
                    if out:
                        dest = cwd / (out + fmt)
                        print(f"  {C.BBLACK}Compressing…{C.RESET}", flush=True)
                        ok, err = do_compress(targets, dest, fmt)
                        status = f"Compressed → {dest.name}" if ok else f"{C.BRED}Failed: {err}{C.RESET}"
                    else: status = "Cancelled"
                else: status = "Cancelled"

        # ── EXTRACT ──
        elif ku == "E":
            if current and current.is_file():
                clear()
                dname = ask("Extract into directory", current.stem)
                dest = cwd / (dname or current.stem)
                dest.mkdir(parents=True, exist_ok=True)
                print(f"  {C.BBLACK}Extracting…{C.RESET}", flush=True)
                ok, err = do_extract(current, dest)
                status = f"Extracted → {dest.name}/" if ok else f"{C.BRED}Failed: {err}{C.RESET}"
            else: status = "Select an archive file to extract"

        # ── PROPERTIES ──
        elif ku == "I":
            if current: show_properties(current, cols)

        # ── HOME ──
        elif ku == "H":
            cwd = Path.home(); HIST.go(cwd)
            sel = 0; scroll = 0; filter_str = ""

        # ── GO PATH (G) — real-time path input with live completion ──
        elif ku == "G":
            gpath, cancelled = realtime_path_input()
            if not cancelled and gpath:
                gpath = gpath.rstrip("/")
                if not gpath: gpath = "/"
                try:
                    exp = Path(os.path.expanduser(gpath)).resolve()
                    if exp.is_dir():
                        HIST.go(exp); cwd = exp; sel = 0; scroll = 0; filter_str = ""
                        status = "Navigated to: " + str(cwd)
                    elif exp.is_file():
                        HIST.go(exp.parent); cwd = exp.parent; filter_str = ""
                        new_e = read_dir(cwd, hidden, sort_mode)
                        sel = next((i for i,e in enumerate(new_e) if e["path"]==exp), 0)
                        status = "File: " + exp.name
                    else:
                        status = "Not found: " + gpath
                except Exception as ex:
                    status = "Error: " + str(ex)
            elif not cancelled:
                status = "Enter a path"
            else:
                status = "Cancelled"

        # ── SEARCH / FILTER ──
        elif k == "/" or ku == "F":
            clear()
            print(f"\n  {C.BCYAN}Search & Filter{C.RESET}")
            print(f"  {C.BWHITE}1{C.RESET}. Filter current directory")
            print(f"  {C.BWHITE}2{C.RESET}. Deep recursive search  {C.BBLACK}(in current dir){C.RESET}")
            print(f"  {C.BWHITE}3{C.RESET}. Jump to path directly")
            print(f"  {C.BWHITE}4{C.RESET}. Clear filter")
            print(f"  {C.BWHITE}5{C.RESET}. Find file/folder        {C.BBLACK}(searches ~/ then system){C.RESET}")
            ch = ask("Choice [1-5]")
            if ch == "1":
                pat = ask("Filter pattern")
                filter_str = pat; sel=0; scroll=0
                status = f"Filter: '{filter_str}'" if filter_str else "Filter cleared"
            elif ch == "2":
                pat = ask("Search pattern")
                if pat:
                    clear()
                    print(f"  {C.BBLACK}Searching in {cwd}…  Ctrl+C to abort{C.RESET}", flush=True)
                    results = do_search(cwd, pat)
                    if results:
                        t = browse_results(results, cols)
                        if t:
                            try:
                                target_dir = t if t.is_dir() else t.parent
                                HIST.go(target_dir); cwd = target_dir; filter_str=""
                                if t.is_file():
                                    new_e = read_dir(cwd, hidden, sort_mode)
                                    sel = next((i for i,e in enumerate(new_e) if e["path"]==t), 0)
                                else: sel=0
                                status = "Navigated to: " + str(cwd)
                            except Exception as ex:
                                status = "Error: " + str(ex)
                    else:
                        status = f"No results for '{pat}'"
            elif ch == "3":
                # Same as G — real-time path input with live completion
                gpath, cancelled = realtime_path_input()
                if not cancelled and gpath:
                    gpath = gpath.rstrip("/")
                    if not gpath: gpath = "/"
                    try:
                        exp = Path(os.path.expanduser(gpath)).resolve()
                        if exp.is_dir():
                            HIST.go(exp); cwd=exp; sel=0; scroll=0; filter_str=""
                            status = "Navigated to: " + str(cwd)
                        elif exp.is_file():
                            HIST.go(exp.parent); cwd=exp.parent; filter_str=""
                            new_e = read_dir(cwd, hidden, sort_mode)
                            sel = next((i for i,e in enumerate(new_e) if e["path"]==exp), 0)
                            status = "File: " + exp.name
                        else:
                            status = "Not found: " + gpath
                    except Exception as ex:
                        status = "Error: " + str(ex)
                else:
                    status = "Cancelled"
            elif ch == "4":
                filter_str=""; status="Filter cleared"
            elif ch == "5":
                pat = ask("Find — enter name to search for")
                if pat:
                    clear()
                    results = []
                    try:
                        results = do_find(pat)
                    except KeyboardInterrupt:
                        pass
                    if results:
                        t = browse_results(results, cols)
                        if t:
                            try:
                                target_dir = t if t.is_dir() else t.parent
                                HIST.go(target_dir); cwd = target_dir; filter_str=""
                                if t.is_file():
                                    new_e = read_dir(cwd, hidden, sort_mode)
                                    sel = next((i for i,e in enumerate(new_e) if e["path"]==t), 0)
                                else: sel=0
                                status = "Navigated to: " + str(cwd)
                            except Exception as ex:
                                status = "Error: " + str(ex)
                    else:
                        status = f"Nothing found for '{pat}'"

        # ── TOGGLE HIDDEN ──
        elif k == ".":
            hidden = not hidden
            status = f"Hidden files: {'shown' if hidden else 'hidden'}"

        # ── TOGGLE VIEW ──
        elif ku == "V":
            view_mode = "list" if view_mode=="grid" else "grid"
            scroll = 0
            status = f"View: {'icon grid' if view_mode=='grid' else 'list'}"

        # ── SORT ──
        elif ku == "T":
            idx = SORT_MODES.index(sort_mode)
            sort_mode = SORT_MODES[(idx+1) % len(SORT_MODES)]
            status = f"Sort: {SORT_LABEL[sort_mode]}"

        # ── CHMOD ──
        elif ku == "L":
            if current:
                clear()
                p = ask("Set permissions (e.g. 755, 644, +x, -x)")
                if p:
                    try:
                        if p.startswith(("+","-")): subprocess.run(["chmod",p,str(current)])
                        else: os.chmod(str(current), int(p,8))
                        status = f"chmod {p} on {current.name}"
                    except Exception as e: status = f"{C.BRED}{e}{C.RESET}"

        # ── OPEN WITH ──
        elif ku == "O":
            if current:
                clear()
                app = ask("Open with command")
                if app:
                    try: subprocess.run([app, str(current)])
                    except Exception as e: status = f"{C.BRED}{e}{C.RESET}"

        # ── SHELL ──
        elif k == "!":
            shell = os.environ.get("SHELL","/bin/bash")
            clear()
            print(f"\n  {C.BBLUE}Shell in: {cwd}{C.RESET}")
            print(f"  {C.BBLACK}(type 'exit' to return){C.RESET}\n")
            subprocess.run([shell], cwd=str(cwd))

        # ── REFRESH ──
        elif k == "F5":
            status = "Refreshed"

        # ── CLEAR MARKS ──
        elif k == "ESC":
            if num_buf: num_buf = ""
            elif marked: marked.clear(); status = "Marks cleared"

        # ── HELP ──
        elif k == "?" or k == "F1":
            show_help(cols)

        # ── QUIT ──
        elif ku == "Q":
            clear()
            print(f"\n  {C.BBLUE}Goodbye.{C.RESET}\n")
            break

# ─── ENTRY ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if sys.version_info < (3, 8):
        print("CLIFM requires Python 3.8+"); sys.exit(1)
    if not sys.stdin.isatty():
        print("CLIFM must run in a terminal."); sys.exit(1)
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n  {C.BBLUE}Interrupted.{C.RESET}\n")