# Nyx — CLI File Manager

> **"Your desktop died. Your files didn't. Nyx keeps you moving."**

A zero-dependency, ASCII-art file manager for the terminal. Built for Linux users who live without a desktop environment — Kali, Arch, servers, chroots, Termux on Android — anywhere a GUI file manager is absent, broken, or simply not needed.

---

## Author

**Kiran Pradeep Malik**
📧 [sysarch.kira@gmail.com](mailto:sysarch.kira@gmail.com)

---

## Features

- **Icon grid and list view** — ASCII art file icons with colors per file type, switchable with one key
- **Full file operations** — copy, cut, paste, delete, rename, new file/dir, chmod, open with
- **Multiselect** — mark multiple files with Space, apply any operation to all marked at once
- **Trash bin** — move to trash instead of permanent delete, with restore and clear options
- **Bookmarks** — save and jump to paths, stored inside nyx.py itself, no external files
- **Bulk rename** — mark multiple files, press R, edit all names in your editor at once
- **Compression** — zip, tar.gz, tar.bz2, tar.xz, tar, gz, bz2, xz, 7z, zst
- **Extraction** — all major archive formats auto-detected
- **Find** — searches ~/ first, then optionally expands to full system scan
- **Deep recursive search** — search inside any directory
- **Filter** — live filter current directory by filename
- **Go to path** — real-time Tab completion path input with live results shown as you type
- **Navigation history** — back and forward like a browser
- **Properties panel** — full file stats, permissions, MIME type, inode
- **Shell escape** — drop to shell in current directory, return to Nyx after
- **30+ distro support** — auto-detects OS and package manager,
- **Termux/Android support** — full support, never uses sudo
- **Zero dependencies** — pure Python 3.8+ stdlib, one file, no pip installs

---

## Requirements

- Python 3.8 or newer
- Any Linux terminal
- No pip packages. No external libraries. Zero installation.

```bash
python3 nyx.py              # start in home directory
python3 nyx.py /etc         # start at a specific path
chmod +x nyx.py && ./nyx.py
```

---

## Supported Operating Systems

| Family | Distros | Package Manager |
|--------|---------|----------------|
| Arch | Arch, Manjaro, EndeavourOS, Artix, Garuda, CachyOS | pacman / yay / paru |
| Debian | Debian, Ubuntu, Kali, Mint, Pop!_OS, Parrot, Raspbian | apt / nala |
| Fedora | Fedora, RHEL, Rocky, AlmaLinux, Nobara | dnf5 / dnf / yum |
| openSUSE | openSUSE Leap, Tumbleweed | zypper |
| Alpine | Alpine, postmarketOS | apk |
| Void | Void Linux | xbps-install |
| Gentoo | Gentoo, Calculate | emerge |
| NixOS | NixOS | nix-env |
| Solus | Solus | eopkg |
| Android | Termux | pkg / apt (no sudo) |

---

## Interface

```
╔══════════════════════════════════════════════════════════════════════╗
║ Nyx v1.0  KALI  [apt]                          [.][Name↑][GRID]    ║
║ ▶ /home/kira/projects                    © main.py, utils.py         ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ┌─────────┐   ┌───────┐   ┌───────┐   ┌──┬──────┐                   ║
║  │         │   │ .___. │   │ .___. │   │▓▓│      │                   ║
║  │  [DIR]  │   │ .PY   │   │ .SH   │   │▓▓│ ZIP  │                   ║
║  │         │   │       │   │       │   │▓▓│      │                   ║
║  └─────────┘   └───────┘   └───────┘   └──┴──────┘                   ║
║    src/           main.py    build.sh    release.zip                 ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║ ↑↓:Nav  Ent:Open  C:Copy  X:Cut  P:Paste  D:Del  B:Trash  R:Rename   ║
║ Z:Zip  E:Extract  I:Info  G:GoPath  /:Search  M:Bookmarks  Q:Quit    ║
║ Ready  OS:kali  family:debian  pkg:apt                               ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## View Modes

### Icon Grid (default)

5-line ASCII art icons in a grid. Each file type has a distinct icon and color.

```
┌─────────┐    ┌───────┐    ┌──┬──────┐    ┌───────┐
│         │    │ .___. │    │▓▓│      │    │ .___. │
│  [DIR]  │    │  .PY  │    │▓▓│ ZIP  │    │  PDF  │
│         │    │       │    │▓▓│      │    │       │
└─────────┘    └───────┘    └──┴──────┘    └───────┘
  projects       main.py     backup.zip    report.pdf
```

### List View

One item per row with permissions, size, and date. Selected item name turns bold green.

```
  1   [DIR]  projects          rwxr-xr-x    <DIR>  2026-04-10 18:55
  2   [.PY]  main.py           rw-r--r--   12.8 KB  2026-04-10 20:01
  3   [ZIP]  backup.zip        rw-r--r--  892.0 KB  2026-04-08 09:33
```

Press `V` to toggle between both views.

---

## Color Scheme

| Color | Meaning |
|-------|---------|
| **Bold Green** | Currently selected item |
| **Blue** | Directory |
| **Yellow** | Executable file |
| **Green** | Script / code file |
| **Magenta** | Media file |
| **Red** | PDF, ISO, DEB, RPM |
| **Cyan** | Config / env file |
| **Yellow (dim)** | Archive file |
| **White** | Regular file |
| **Dark grey** | Permissions, size, date columns |

---

## Full Keybinding Reference

### Navigation

| Key | Action |
|-----|--------|
| `↑` `K` `W` | Move cursor up |
| `↓` `J` `S` | Move cursor down |
| `←` | Go back in navigation history |
| `→` | Go forward in navigation history |
| `Backspace` | Go to parent directory |
| `Enter` | Open file or enter directory |
| `PageUp` | Jump one page up |
| `PageDown` | Jump one page down |
| `Home` | First item |
| `End` | Last item |
| `H` | Jump to home directory |
| `G` | Go to any path with live Tab completion |
| `1`–`9` + `Enter` | Jump to item by number |

### Multiselect

| Key | Action |
|-----|--------|
| `Space` | Mark or unmark current item |
| `A` | Mark all / unmark all |
| `Esc` | Clear all marks |

Marked items show `★`. All operations work on all marked items when marks are active. When no marks are set, operations apply to the item under the cursor.

### File Operations

| Key | Action |
|-----|--------|
| `C` | Copy marked/current to clipboard |
| `X` | Cut — moves on paste |
| `P` | Paste clipboard here |
| `D` | Delete permanently — asks confirmation |
| `B` | Move to Trash — recoverable |
| `R` | Rename — Bulk rename when multiple marks active |
| `N` | New file or directory |
| `Z` | Compress |
| `E` | Extract archive |
| `L` | chmod — change permissions |
| `O` | Open with a specific command |
| `I` | Properties panel |
| `!` | Open shell in current directory |

### Bookmarks

| Key | Action |
|-----|--------|
| `M` | Open bookmarks manager |
| `M` → `A` | Bookmark current directory |
| `M` → `N` | Bookmark any path with Tab completion |
| `M` → `D` | Delete a bookmark |
| `M` → number | Navigate to that bookmark instantly |

### Search Menu — press `/` or `F`

| Option | What it does |
|--------|-------------|
| `1` | Filter current directory by filename |
| `2` | Deep recursive search from current directory |
| `3` | Jump to path with Tab completion |
| `4` | Clear active filter |
| `5` | Find — searches `~/` first, asks to expand systemwide |
| `6` | Open Trash bin |

Search results show 7 at a time. `↑` / `↓` to page, number + Enter to navigate.

### View and Sort

| Key | Action |
|-----|--------|
| `V` | Toggle icon grid / list view |
| `T` | Cycle sort mode |
| `.` | Toggle hidden files |
| `F5` | Refresh |
| `?` | Help screen |
| `Q` | Quit |

**Sort modes:** Name↑ → Name↓ → Size↑ → Size↓ → Time↑ → Time↓ → Ext

---

## Go to Path — G

Press `G`. Completions appear in real time as you type:

```
  Go to Path  Type path, Tab=complete, Enter=go, Esc=cancel, Ctrl+U=clear

  > ~/pro
    projects/
    programs/
```

Tab fills the longest common prefix. One match auto-completes fully. `~` expansion supported.

---

## Trash Bin

Press `B` on any file or folder to move it to `~/.local/share/Trash/files`.

Access trash browser via `/` → `6`:

```
  Trash  /home/kira/.local/share/Trash/files

     1  [FILE]  oldreport.pdf     2.3 KB
     2  [DIR]   backup-folder
     3  [FILE]  config.json       1.1 KB

  [number] + Enter  → Restore that item
  RA               → Restore ALL
  D[number]        → Permanently delete item  e.g. D3
  DA               → Permanently delete ALL trash
  O                → Navigate into trash folder in Nyx
  Q or Enter       → Close
```

When restoring, Nyx asks where to put the files:

```
  Restore to where?
  1. Restored folder  (~/Restored — created if needed)
  2. Type a path       (Tab to complete)
  Q. Cancel
```

Option 1 collects everything into `~/Restored/` — home directory stays clean. Option 2 lets you Tab-complete any destination path.

---

## Bookmarks

Press `M`:

```
  Bookmarks / Shortcuts  (stored inside nyx.py)

     1.  myproject          /home/kira/projects/nyx
     2.  configs            /etc/nginx

  A. Add current directory
  N. Add custom path
  D. Delete a bookmark
  Enter/Q. Cancel
```

Type a number to jump to that path instantly. Bookmarks are written into the `_BOOKMARKS_DATA` line inside `nyx.py` — zero external files, zero config directories, fully self-contained.

---

## Bulk Rename

Mark multiple files with `Space`, press `R`. Your editor opens with one filename per line. Edit names, save, close. Nyx renames every file whose name changed. Unchanged lines are skipped. Conflicts are reported.

---

## Find — Two-Stage Search

Press `/` → `5`:

```
  Find: fonts

  Searching ~/ ...
  Found 3 result(s) in ~/

  Also search the full system?  (finds outside ~/, takes longer)
  Expand to full system? [y/N]:
```

Found in `~/` — shows results and asks to expand. Nothing in `~/` — goes full system automatically. Skips `/proc` `/sys` `/dev` `/run` `/snap`. Ctrl+C aborts cleanly.

---

## Compression

Press `Z` on any file, folder, or selection of marked items:

| Format | Requires |
|--------|---------|
| `.zip` `.tar` `.tar.gz` `.tar.bz2` `.tar.xz` `.gz` `.bz2` `.xz` | Python built-in — always works |
| `.7z` | `7z` binary — Nyx offers to install |
| `.zst` | `zstd` binary — Nyx offers to install |

---

## File Opening

Press `Enter` on any file:

| Type | Tools tried in order |
|------|---------------------|
| Text / code / config | nvim → vim → nano → micro → bat → less → raw output |


---

## Edge Cases Handled

- Directory deleted while inside it — walks up to nearest existing parent automatically
- File deleted between listing and opening — reports it, does not crash
- Permission denied on directory — shows empty, does not crash
- Broken symlinks — shown correctly, does not crash
- Cursor out of range after delete — clamped to last valid item
- Marks pointing to deleted files — removed before each operation
- Clipboard items deleted before paste — reports missing, pastes the rest
- Rename to existing name — reports conflict, no overwrite
- Archive extraction failure — reports error, does not crash
- Search on huge directories — Ctrl+C aborts cleanly at any point

---

## Termux / Android

Detected automatically. Never uses sudo. Uses `pkg install` or `apt install` directly. All operations work identically.

---

## Technical Notes

- Pure Python stdlib — no pip, one file
- `os.read(fd, 1)` directly on the kernel fd — bypasses all Python buffering layers
- `termios` / `tty` / `select()` for reliable raw single-keypress input
- Bookmarks written into `_BOOKMARKS_DATA` line inside `nyx.py` on save
- Navigation history — 50-entry deque, back and forward
- Clipboard survives directory changes
- Trash follows XDG spec — `~/.local/share/Trash/files`
- Marks cleaned automatically before every operation

---

## Changelog

| Version | Changes |
|---------|---------|
| v4.0 | Trash with smart restore, self-contained bookmarks, bulk rename, two-stage find, scrollable results browser, multiselect on all ops, 30+ distro support, Termux support, real-time path completion |
| v3.0 | Icon grid view, list view, systemwide find |
| v2.0 | Compression, extraction, properties, search, filter, navigation history |
| v1.0 | Navigation, copy, cut, paste, delete, rename |

---

## License

MIT — use it, modify it, distribute it.

---

*Built for the terminal. Runs everywhere. Needs nothing.*