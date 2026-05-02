# CLIFM — CLI File Manager

> **"Your desktop died. Your files didn't. CLIFM keeps you moving."**

A fast, zero-dependency, ASCII-art file manager for the terminal. Built for Linux users who live without a desktop environment — Kali, Arch, servers, chroots, Termux on Android — anywhere a GUI file manager is absent, broken, or just too slow to matter.

CLIFM starts in under a second, runs on any terminal width, and never touches the mouse. Every operation is one or two keystrokes.

---

## Author

**Kiran Pradeep Malik**
📧 [sysarch.kira@gmail.com](mailto:sysarch.kira@gmail.com)

---

## Why CLIFM Exists

When you boot into a minimal Arch install, a Kali live USB, an Android phone running Termux, or SSH into a headless server — there is no Nautilus, no Dolphin, no Thunar. You are left with raw `ls`, `cp`, `mv`, `rm` commands chained together, trying to remember paths, making typos, and losing track of where you are.

CLIFM solves this. It gives you a real file manager — with icons, two view modes, clipboard, search, compression, extraction, properties, and a shell escape — entirely inside the terminal, requiring nothing beyond Python 3.8 and the standard library.

---

## Requirements

- Python 3.8 or newer
- Any Linux terminal (xterm, alacritty, kitty, gnome-terminal, termux, tmux, etc.)
- No pip packages. No external libraries. Zero installation beyond copying one file.

```bash
python3 clifm.py              # start in home directory
python3 clifm.py /etc         # start in a specific directory
chmod +x clifm.py && ./clifm  # run directly if executable
```

---

## Supported Operating Systems

CLIFM auto-detects your OS at startup and adapts accordingly.

| OS / Distro Family | Package Manager Used | Notes |
|--------------------|---------------------|-------|
| Arch, Manjaro, EndeavourOS, Artix, Garuda, CachyOS | pacman / yay / paru | AUR helpers preferred if present |
| Debian, Ubuntu, Kali, Mint, Pop!_OS, Parrot, Raspbian | apt / nala | nala preferred if installed |
| Fedora, RHEL, Rocky, AlmaLinux, Nobara | dnf5 / dnf / yum | dnf5 preferred on Fedora 41+ |
| openSUSE Leap / Tumbleweed, SLES | zypper | |
| Alpine, postmarketOS | apk | |
| Void Linux | xbps-install | |
| Gentoo, Calculate | emerge | |
| NixOS | nix-env | |
| Solus | eopkg | |
| Clear Linux | swupd | |
| Slackware | slackpkg | |
| Android / Termux | pkg / apt | Never uses sudo |
| macOS (Homebrew) | brew | |

When a required external tool (like `7z`, `unrar`, `mpv`, `chafa`) is missing, CLIFM shows the exact install command for your distro and offers to run it for you.

---

## Interface Overview

```
╔══════════════════════════════════════════════════════════════════════╗
║ CLIFM v4.0  ARCH LINUX  [pacman]              [.][Name↑][GRID]      ║
║ ▶ /home/ghost/projects                  © main.py, utils.py         ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ┌─────────┐   ┌───────┐   ┌───────┐   ┌──┬──────┐                 ║
║  │         │   │ .___. │   │ .___. │   │▓▓│      │                 ║
║  │  [DIR]  │   │ .PY   │   │ .SH   │   │▓▓│ ZIP  │                 ║
║  │         │   │       │   │       │   │▓▓│      │                 ║
║  └─────────┘   └───────┘   └───────┘   └──┴──────┘                 ║
║    src            main.py    build.sh    release.zip                 ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║ ↑↓:Nav  Ent:Open  C:Copy  X:Cut  P:Paste  D:Del  R:Rename  N:New   ║
║ Z:Zip  E:Extract  I:Info  G:GoPath  /:Search  V:View  T:Sort  Q:Quit║
║ Ready  OS:arch  family:arch  pkg:pacman                              ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Header** — shows current path, active clipboard contents, filter status, sort mode, view mode, hidden file toggle.

**Content area** — either icon grid (big ASCII art icons, multiple per row) or list view (one item per row with permissions, size, date).

**Footer** — all keybindings always visible. Status bar shows last action result.

---

## View Modes

### Icon Grid View (default)

Big 5-line ASCII art icons arranged in a grid. Each file type has a unique icon shape and color. Directories get a box-style folder icon. Archive files get a striped side. Selected item highlights in green.

```
┌─────────┐    ┌───────┐    ┌──┬──────┐    ┌───────┐
│         │    │ .___. │    │▓▓│      │    │ .___. │
│  [DIR]  │    │  .PY  │    │▓▓│ ZIP  │    │  PDF  │
│         │    │       │    │▓▓│      │    │       │
└─────────┘    └───────┘    └──┴──────┘    └───────┘
  projects       main.py      backup.zip    report.pdf
```

Press `V` to switch to list view.

### List View

One item per row. Shows: item number, mark indicator, file type icon, filename, permissions, size, last modified date.

```
  1   [DIR]  projects          rwxr-xr-x    <DIR>  2026-04-10 18:55
  2   [.PY]  main.py           rw-r--r--   12.8 KB  2026-04-10 20:01
  3   [ZIP]  backup.zip        rw-r--r--  892.0 KB  2026-04-08 09:33
```

Selected item name turns **bold green** so you always know exactly where your cursor is. Executables show in **yellow**, directories in **blue**, regular files in **white**, symlinks in **cyan**.

Press `V` to switch back to grid view.

---

## File Type Colors

| Color | Meaning |
|-------|---------|
| **Blue** | Directory |
| **Bold Green** | Currently selected item |
| **Yellow** | Executable file |
| **Green** | Script files (.py .sh .go .rs etc) |
| **Magenta** | Media files (.mp3 .mp4 .mkv etc) |
| **Red** | PDF, ISO, DEB, RPM |
| **Cyan** | Config files (.conf .ini .env .toml) |
| **Yellow (dim)** | Archive files (.zip .tar .gz .7z etc) |
| **White** | Regular text and document files |
| **Dark grey** | Permissions, size, date columns |

---

## Full Keybinding Reference

### Navigation

| Key | Action |
|-----|--------|
| `↑` or `K` or `W` | Move cursor up |
| `↓` or `J` or `S` | Move cursor down |
| `←` (left arrow) | Go back in navigation history |
| `→` (right arrow) | Go forward in navigation history |
| `Backspace` | Go to parent directory |
| `Enter` | Open file or enter directory |
| `PageUp` | Jump one full page up |
| `PageDown` | Jump one full page down |
| `Home` | Jump to first item |
| `End` | Jump to last item |
| `H` | Jump to home directory (~/) |
| `G` | Go to any path (with live Tab completion) |
| `1`–`9` then `Enter` | Jump to item by number (multi-digit supported) |

### Selection and Marks

| Key | Action |
|-----|--------|
| `Space` | Mark or unmark current item, cursor advances |
| `A` | Mark all items / unmark all if all are marked |
| `Esc` | Clear all marks |

Marked items show a `★` symbol next to them. All file operations (copy, cut, delete, compress) work on marked items when marks are active, or on the current cursor item when no marks are set.

### Clipboard

| Key | Action |
|-----|--------|
| `C` | Copy marked/current item(s) to clipboard |
| `X` | Cut marked/current item(s) — moves on paste |
| `P` | Paste clipboard contents into current directory |

The clipboard persists as you navigate between directories. The header shows what is in the clipboard at all times. If you cut items and they no longer exist by the time you paste, CLIFM handles this gracefully and reports which items were missing.

Name collision on paste is handled automatically — if a file with the same name exists, the pasted file is renamed to `filename_copy1`, `filename_copy2`, etc.

### File Operations

| Key | Action |
|-----|--------|
| `D` | Delete marked/current item(s) — asks confirmation |
| `R` | Rename current item |
| `N` | Create new file or directory |
| `Z` | Compress marked/current item(s) |
| `E` | Extract archive file |
| `L` | Change permissions (chmod) |
| `O` | Open file with a specific command |
| `I` | Show detailed properties panel |
| `!` | Open a shell in the current directory |

### Search and Navigation

| Key | Action |
|-----|--------|
| `G` | Go to path with live completion |
| `/` or `F` | Open search and filter menu |

**Search menu options:**

| Option | What it does |
|--------|-------------|
| `1` Filter | Hides all files in current dir that don't match your pattern. Fast, instant. Clears on dir change. |
| `2` Deep search | Recursively searches all subdirectories from current location. Shows results 7 at a time. |
| `3` Jump to path | Same as G — live Tab completion path input. |
| `4` Clear filter | Removes any active filter. |
| `5` Find | Searches `~/` first, then the full system if nothing found. Skips `/proc` `/sys` `/dev`. Ctrl+C to abort. |

Results from options 2 and 5 are shown in a scrollable browser — 7 results at a time. Use `↑`/`↓` arrows to page through. Type a number and press Enter to navigate to that result.

### View and Sort

| Key | Action |
|-----|--------|
| `V` | Toggle between icon grid and list view |
| `T` | Cycle through sort modes |
| `.` | Toggle hidden files (dotfiles) on/off |
| `F5` | Refresh current directory |

**Sort modes** (cycles with `T`):

`Name↑` → `Name↓` → `Size↑` → `Size↓` → `Time↑` → `Time↓` → `Ext` → back to `Name↑`

### Other

| Key | Action |
|-----|--------|
| `?` or `F1` | Show help screen with all keybindings |
| `Q` | Quit |

---

## Go to Path — G key

Press `G` from anywhere. The screen clears and shows a live path input:

```
  Go to Path  Type path, Tab=complete, Enter=go, Esc=cancel, Ctrl+U=clear

  > ~/Do
    Documents/
    Downloads/
    dotfiles/
```

As you type, matching completions appear below the prompt in real time. Tab key completes the longest common prefix. If only one match exists, it is filled in automatically. Press `Enter` to navigate. Press `Esc` to cancel. Press `Ctrl+U` to clear the whole line.

Works with `~` expansion. Works for both directories (navigates into them) and files (navigates to the parent directory and places the cursor on the file).

---

## Compression and Extraction

### Compress (`Z`)

Select items with `Space` or just be on a file, press `Z`. Choose format:

| Format | Tool required | Notes |
|--------|-------------|-------|
| `.zip` | Python built-in | Always works |
| `.tar.gz` | Python built-in | Always works |
| `.tar.bz2` | Python built-in | Always works |
| `.tar.xz` | Python built-in | Always works |
| `.tar` | Python built-in | Always works |
| `.gz` | Python built-in | Single file only |
| `.bz2` | Python built-in | Single file only |
| `.xz` | Python built-in | Single file only |
| `.7z` | `7z` binary | CLIFM offers to install if missing |
| `.zst` | `zstd` binary | CLIFM offers to install if missing |

If output file already exists, CLIFM asks before overwriting.

### Extract (`E`)

Place cursor on any archive file, press `E`. CLIFM detects the format from the extension and extracts it. Supports: `.zip` `.tar` `.tar.gz` `.tgz` `.tar.bz2` `.tar.xz` `.tar.zst` `.gz` `.bz2` `.xz` `.7z` `.rar` `.zst`.

For `.7z` and `.rar`, CLIFM checks if the required binary is installed and offers to install it using your distro's package manager if not.

---

## File Opening

Press `Enter` on a file. CLIFM detects the file type and opens it with the best available tool:

| File type | Tools tried in order |
|-----------|---------------------|
| Text, code, config, scripts | nvim → vim → nano → micro → helix → bat → less → more → raw output |
| Images | chafa → feh → sxiv → nsxiv → imv |
| Video/Audio | mpv → vlc → mplayer |
| PDF | zathura → mupdf → evince → okular |
| Everything else | xdg-open → less → more |

`chafa` is especially useful — it renders images as colored ASCII art directly in the terminal, no GUI needed.

If no viewer is found, CLIFM shows the exact install command for your distro.

---

## Properties Panel (`I`)

Press `I` on any file or directory to see:

```
╔═══════════════════════════════════════╗
║ Properties: main.py                   ║
╠═══════════════════════════════════════╣
║  Name:               main.py          ║
║  Path:               /home/ghost/...  ║
║  Type:               File             ║
║  Size:               12.8 KB (13107)  ║
║  Permissions:        rw-r--r-- (0644) ║
║  Owner UID:          1000             ║
║  Group GID:          1000             ║
║  Modified:           2026-04-10 20:01 ║
║  Accessed:           2026-04-10 20:05 ║
║  Changed:            2026-04-10 20:01 ║
║  Extension:          .py              ║
║  Executable:         No               ║
║  MIME:               Python script    ║
║  Inode:              2883622          ║
║  Links:              1                ║
╚═══════════════════════════════════════╝
```

For directories, shows direct children count (files and subdirectories).

---

## Shell Escape (`!`)

Press `!` to drop into a shell inside the current directory. Your `$SHELL` environment variable is used (bash, zsh, fish, etc.). Type `exit` to return to CLIFM exactly where you left off.

---

## Edge Case Handling

CLIFM is built to never crash, no matter what the filesystem throws at it.

- **Directory deleted while inside it** — CLIFM walks up to the nearest existing parent automatically on the next render cycle, shows a warning in the status bar.
- **File deleted between listing and opening** — Reports "file no longer exists" instead of crashing.
- **Permission denied on directory** — Shows empty directory instead of crashing.
- **Broken symlinks** — Shows the symlink and its target path, does not crash on `stat()`.
- **Cursor out of range after delete** — Automatically clamped to the last valid item.
- **Marks pointing to deleted files** — Silently removed from mark set before each operation.
- **Clipboard items deleted before paste** — Reports how many items were missing, pastes the rest.
- **Rename to existing filename** — Reports conflict, does not overwrite.
- **New file/dir with `/` in name** — Rejected with error message.
- **Archive extraction destination fails to create** — Reports the error, does not crash.
- **Terminal too small** — Gracefully degrades, minimum dimensions enforced.
- **Search on huge directories** — Ctrl+C aborts cleanly at any point.

---

## Termux / Android Notes

CLIFM fully supports Android via Termux. Detection is automatic.

- Never uses `sudo` — Termux does not have it
- Uses `pkg install` or `apt install` directly
- Home directory is correctly detected via `$HOME` which Termux sets to `/data/data/com.termux/files/home`
- All Python stdlib operations work identically on Termux
- External tools like `nvim`, `mpv`, `chafa` are available via `pkg install`

---

## Technical Notes

- **Pure Python stdlib** — `os`, `sys`, `shutil`, `stat`, `tarfile`, `zipfile`, `gzip`, `bz2`, `lzma`, `termios`, `tty`, `select`, `fnmatch`, `readline`, `subprocess`, `platform`, `pathlib`
- **Zero pip dependencies** — copy one `.py` file, run it
- **Raw terminal input** — uses `os.read(fd, 1)` directly on the kernel file descriptor, bypassing Python's `BufferedReader` and `TextIOWrapper` entirely — this is why keypresses are always reliable
- **Non-blocking escape sequence detection** — uses `select()` with 80ms timeout to distinguish a bare `Esc` keypress from arrow key sequences like `\x1b[A`
- **Navigation history** — 50-entry deque, back and forward like a browser
- **Clipboard survives directory changes** — copy in `/etc`, navigate to `/home`, paste
- **Sort is stable** — directories always listed before files regardless of sort mode

---

## Changelog

| Version | Changes |
|---------|---------|
| v4.0 | os.read() kernel-level input, full distro support, Termux support, realtime path completion, scrollable search results, EXE/selected color distinction |
| v3.0 | Icon grid view, list view, browse_results pager, do_find systemwide search |
| v2.0 | Compression/extraction, properties panel, search, filter, navigation history |
| v1.0 | Initial release — navigation, copy, cut, paste, delete, rename |

---

## License

MIT License. Use it, modify it, distribute it. Credit appreciated but not required.

---

*Built for the terminal. Runs everywhere. Needs nothing.*
