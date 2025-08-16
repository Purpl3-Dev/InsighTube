#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
InsighTube - OSINT YouTube Console

Commands:
  help
  show options
  show modules
  set api <APIKEY>
  set target <CHANNEL_ID>
  set module <NAME|all>
  set save true|false
  set verbose true|false
  set max <1-500>
  run
  exit
"""

import os
import sys
import json
import csv
from typing import Dict, Any, List, Optional

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except Exception as e:
    print("[-] Missing: google-api-python-client\n    pip install google-api-python-client")
    raise

# =========================
# Config & Global status
# =========================

OUTPUT_DIR = "output"
STATE: Dict[str, Any] = {
    "api_key": None,
    "target": None,           # Channel ID (UCxxxx)
    "modules": [],            # [] => ALL
    "max_results": 50,        # 1..500 (Default API = 50)
    "verbose": False,
    "save": False,            # Output disabled
    "all_data": {},           # FULL.json output
    "uploads_id": None
}

# =========================
# Colors ANSI & Emojis
# =========================

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
MAG    = "\033[95m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

EMO = {
    "profile": "📺",
    "video": "📼",
    "playlist": "🎶",
    "comment": "💬",
    "activity": "🧩",
    "thumb": "🖼",
    "ok": "🟢",
    "warn": "🟡",
    "err": "🔴",
    "run": "⚡",
}

# =========================
# Visual utils
# =========================

def banner():
    print(f"""{MAG}{BOLD}                                                               ᑭᑌᖇᑭᒪ3ᗪEᐯ
██╗███╗   ██╗███████╗██╗ ██████╗ ██╗  ██╗████████╗██╗   ██╗██████╗ ███████╗
██║████╗  ██║██╔════╝██║██╔════╝ ██║  ██║╚══██╔══╝██║   ██║██╔══██╗██╔════╝
██║██╔██╗ ██║███████╗██║██║  ███╗███████║   ██║   ██║   ██║██████╔╝█████╗  
██║██║╚██╗██║╚════██║██║██║   ██║██╔══██║   ██║   ██║   ██║██╔══██╗██╔══╝  
██║██║ ╚████║███████║██║╚██████╔╝██║  ██║   ██║   ╚██████╔╝██████╔╝███████╗
╚═╝╚═╝  ╚═══╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═════╝ ╚══════╝EN.
{RESET}{CYAN}OSINT YouTube Console — v4 PRO{RESET}
""")

def header(title: str, color: str = CYAN, icon: Optional[str]=None):
    sym = icon + " " if icon else ""
    print(f"{color}{'='*35}\n{sym}{title}\n{'='*35}{RESET}")

def print_kv(label: str, value: Any, color_label: str = GREEN):
    print(f"{EMO['ok']} {color_label}{label:<10}{RESET} {value if value not in [None, ''] else 'N/A'}")

def print_note(text: str):
    print(f"{YELLOW}{EMO['warn']} {text}{RESET}")

def print_err(text: str):
    print(f"{RED}{EMO['err']} {text}{RESET}")

def print_sep(color: str = CYAN):
    print(f"{color}{'-'*35}{RESET}")

def card(title: str, items: List[Dict[str, Any]], fields: List[str], icon: str, color: str = CYAN, limit: int = 10):
    if not items:
        print_note(f"No results {title}")
        return
    for i, it in enumerate(items[:limit], 1):
        header(f"{title} #{i}", color, icon)
        for f in fields:
            lbl = f.replace("_", " ").title()
            print_kv(f"{lbl}:", it.get(f))
        print_sep()

# =========================
# API helpers
# =========================

def yt(youtube, resource: str, **kwargs) -> Dict[str, Any]:
    """API request wrapper with error handling and verbose."""
    if STATE["verbose"]:
        print(f"{DIM}[DEBUG] {resource}.list({kwargs}){RESET}")
    try:
        return getattr(youtube, resource)().list(**kwargs).execute()
    except HttpError as e:
        # common errors: 404 playlistNotFound, disabled, etc.
        status = getattr(e.resp, "status", None)
        if status == 404:
            print_note(f"Not found {resource} (404)")
            return {}
        print_err(f"Error {resource}: {e}")
        return {}
    except Exception as e:
        print_err(f"Exception {resource}: {e}")
        return {}

def get_service():
    return build("youtube", "v3", developerKey=STATE["api_key"])

def ensure_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

# =========================
# Save
# =========================

def save_rows(rows: Any, module: str):
    if not STATE["save"]:
        # We still accumulate in all_data for FULL.json if you then activate it
        STATE["all_data"][module] = rows
        return
    ensure_dir()
    chan = STATE["target"] or "unknown"
    json_path = os.path.join(OUTPUT_DIR, f"{chan}_{module}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    if isinstance(rows, list) and rows:
        # CSV 
        keys = set().union(*(r.keys() for r in rows))
        csv_path = os.path.join(OUTPUT_DIR, f"{chan}_{module}.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(keys))
            w.writeheader()
            w.writerows(rows)
    print_kv("Saved:", f"{OUTPUT_DIR}/ ({module})")

    STATE["all_data"][module] = rows

def save_full_json():
    if not STATE["save"]:
        return
    ensure_dir()
    chan = STATE["target"] or "unknown"
    path = os.path.join(OUTPUT_DIR, f"{chan}_FULL.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(STATE["all_data"], f, indent=2, ensure_ascii=False)
    print_kv("FULL JSON:", path)

# =========================
# Norm
# =========================

def norm_channel(item: Dict[str, Any]) -> Dict[str, Any]:
    sn = item.get("snippet", {})
    st = item.get("statistics", {})
    cd = item.get("contentDetails", {})
    uploads = cd.get("relatedPlaylists", {}).get("uploads")
    STATE["uploads_id"] = uploads
    return {

        "id": item.get("id"),
        "title": sn.get("title"),
        "description": sn.get("description"),
        "handler": sn.get("customUrl"),
        "publishedAt": sn.get("publishedAt"),
        "subs": st.get("subscriberCount"),
        "views": st.get("viewCount"),
        "videos": st.get("videoCount"),
        "uploads": uploads,
    }

def norm_playlist(item: Dict[str, Any]) -> Dict[str, Any]:
    sn = item.get("snippet", {})
    cd = item.get("contentDetails", {})
    return {

        "playlistId": item.get("id"),
        "title": sn.get("title"),
        "publishedAt": sn.get("publishedAt"),
        "videoCount": cd.get("itemCount"),
    }

def norm_playlist_item(item: Dict[str, Any]) -> Dict[str, Any]:
    sn = item.get("snippet", {})
    cd = item.get("contentDetails", {})
    return {

        "videoId": cd.get("videoId"),
        "title": sn.get("title"),
        "publishedAt": cd.get("videoPublishedAt") or sn.get("publishedAt"),
        "playlistId": sn.get("playlistId"),
        "position": sn.get("position"),
    }

def norm_comment_thread(item: Dict[str, Any]) -> Dict[str, Any]:
    try:
        top = item["snippet"]["topLevelComment"]["snippet"]
    except Exception:
        top = {}
    return {

        "author": top.get("authorDisplayName"),
        "authorChannelId": (top.get("authorChannelId") or {}).get("value"),
        "text": top.get("textOriginal") or top.get("textDisplay"),
        "publishedAt": top.get("publishedAt"),
        "likeCount": top.get("likeCount"),
        "videoId": (item.get("snippet") or {}).get("videoId"),
        "totalReplyCount": item.get("snippet", {}).get("totalReplyCount"),
    }

def norm_activity(item: Dict[str, Any]) -> Dict[str, Any]:
    sn = item.get("snippet", {})
    return {

        "type": sn.get("type"),
        "title": sn.get("title"),
        "publishedAt": sn.get("publishedAt"),
        "channelId": sn.get("channelId"),
    }

def norm_thumbs(snippet: Dict[str, Any]) -> List[Dict[str, Any]]:
    thumbs = snippet.get("thumbnails", {}) if snippet else {}
    out = []
    for size, data in thumbs.items():
        out.append({"size": size, "url": data.get("url")})
    return out

# =========================
# Paginate
# =========================
def paginate(youtube, resource: str, part: str, max_results: int = 50, **kwargs) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    token = None
    remaining = max(1, min(max_results, STATE["max_results"]))
    while True:
        batch = min(50, remaining)
        res = yt(youtube, resource, part=part, maxResults=batch, pageToken=token, **kwargs)
        items = res.get("items", [])
        rows.extend(items)
        remaining -= len(items)
        token = res.get("nextPageToken")
        if not token or remaining <= 0:
            break
    return rows

# =========================
# Modules
# =========================

def mod_metadata(youtube):
    header("CHANNEL PROFILE", CYAN, EMO["profile"])
    res = yt(youtube, "channels",
             part="snippet,statistics,contentDetails,brandingSettings",
             id=STATE["target"])
    rows = [norm_channel(it) for it in res.get("items", [])]
    if not rows:
        print_note("Channel not found or no data")
    else:
        r = rows[0]
        print_kv("Handler:", r.get("handler"))
        print_kv("Title:", r.get("title"))
        print_kv("ID:", r.get("id"))
        print_kv("Created:", r.get("publishedAt"))
        print_kv("Subs:", r.get("subs"))
        print_kv("Videos:", r.get("videos"))
        print_kv("Views:", r.get("views"))
        print_kv("UploadsID:", r.get("uploads"))
        print_sep()
    save_rows(rows, "metadata")
    return rows

def mod_uploads(youtube):
    header("UPLOADS (Playlist upload)", CYAN, EMO["video"])
    up = STATE.get("uploads_id")
    if not up:
        print_note("This channel does not display playlist uploads.")
        save_rows([], "uploads")
        return []
    items = paginate(youtube, "playlistItems",
                     part="snippet,contentDetails",
                     playlistId=up,
                     max_results=STATE["max_results"])
    rows = [norm_playlist_item(it) for it in items]
    if rows:
        card("VIDEO", rows, ["title", "videoId", "publishedAt"], EMO["video"], CYAN, limit=10)
        print_kv("Total videos:", len(rows))
    else:
        print_note("There are no videos in uploads.")
    save_rows(rows, "uploads")
    return rows

def mod_playlists(youtube):
    header("PLAYLISTS", CYAN, EMO["playlist"])
    items = paginate(youtube, "playlists",
                     part="snippet,contentDetails",
                     channelId=STATE["target"],
                     max_results=STATE["max_results"])
    rows = [norm_playlist(it) for it in items]
    if rows:
        card("PLAYLIST", rows, ["title", "playlistId", "publishedAt", "videoCount"], EMO["playlist"], CYAN, limit=10)
        print_kv("Total playlists:", len(rows))
    else:
        print_note("No public playlists.")
    save_rows(rows, "playlists")
    return rows

def mod_videos_from_playlists(youtube):
    header("VIDEOS FROM PLAYLISTS", CYAN, EMO["video"])
    # Reuse mod_playlists but without duplicate printing
    items = paginate(youtube, "playlists",
                     part="snippet,contentDetails",
                     channelId=STATE["target"],
                     max_results=STATE["max_results"])
    pls = [norm_playlist(it) for it in items]
    all_vids: List[Dict[str, Any]] = []
    for pl in pls:
        pid = pl["playlistId"]
        pitems = paginate(youtube, "playlistItems",
                          part="snippet,contentDetails",
                          playlistId=pid,
                          max_results=STATE["max_results"])
        vids = [norm_playlist_item(x) for x in pitems]
        for v in vids:
            v["fromPlaylistId"] = pid
            v["fromPlaylistTitle"] = pl["title"]
        all_vids.extend(vids)
    if all_vids:
        card("VIDEO", all_vids, ["title", "videoId", "publishedAt", "fromPlaylistTitle"], EMO["video"], CYAN, limit=10)
        print_kv("Total vídeos:", len(all_vids))
    else:
        print_note("Sin vídeos en playlists.")
    save_rows(all_vids, "playlists_videos")
    return all_vids

def mod_comments(youtube):
    header("COMMENTS (threads top-level)", YELLOW, EMO["comment"])
    # Best public option: allThreadsRelatedToChannelId (comments on channel videos)
    items = paginate(youtube, "commentThreads",
                     part="snippet",
                     allThreadsRelatedToChannelId=STATE["target"],
                     max_results=STATE["max_results"])
    rows = [norm_comment_thread(it) for it in items]
    if rows:
        card("COMMENT", rows, ["author", "authorChannelId", "publishedAt", "likeCount", "videoId", "text"], EMO["comment"], YELLOW, limit=10)
        print_kv("Total comments:", len(rows))
    else:
        print_note("No public comments associated with the channel.")
    save_rows(rows, "comments")
    return rows

def mod_activities(youtube):
    header("ACTIVITIES", MAG, EMO["activity"])
    items = paginate(youtube, "activities",
                     part="snippet,contentDetails",
                     channelId=STATE["target"],
                     max_results=STATE["max_results"])
    rows = [norm_activity(it) for it in items]
    if rows:
        card("ACTIVITY", rows, ["type", "title", "publishedAt"], EMO["activity"], MAG, limit=10)
        print_kv("Total activities:", len(rows))
    else:
        print_note("No public activities.")
    save_rows(rows, "activities")
    return rows

def mod_thumbnails(youtube):
    header("THUMBNAILS", CYAN, EMO["thumb"])
    res = yt(youtube, "channels", part="snippet", id=STATE["target"])
    rows: List[Dict[str, Any]] = []
    for it in res.get("items", []):
        sn = it.get("snippet", {})
        rows.extend(norm_thumbs(sn))
    if rows:
        card("THUMB", rows, ["size", "url"], EMO["thumb"], CYAN, limit=10)
        print_kv("Total thumbs:", len(rows))
    else:
        print_note("Sin thumbnails.")
    save_rows(rows, "thumbnails")

    return rows

# Dispatch
DISPATCH = {

    "Metadata": mod_metadata,
    "Uploads": mod_uploads,
    "Playlists": mod_playlists,
    "VideosFromPlaylists": mod_videos_from_playlists,
    "Comments": mod_comments,
    "Activities": mod_activities,
    "Thumbnails": mod_thumbnails,
}

# =========================
# Console
# =========================

def show_options():
    header("OPTIONS", CYAN, "🛠")
    print_kv("API:", obfuscate(STATE["api_key"]))
    print_kv("Target:", STATE["target"])
    print_kv("Modules:", STATE["modules"] or "ALL")
    print_kv("Verbose:", STATE["verbose"])
    print_kv("Save:", STATE["save"])
    print_kv("Max:", STATE["max_results"])
    print_sep()

def show_modules():
    header("MODULES", CYAN, "📦")
    for name in DISPATCH.keys():
        print(f"{EMO['ok']} {name}")
    print_sep()

def show_help():
    header("HELP", CYAN, "❓")
    print(f"""Commands:

  {BOLD}show options{RESET}          -> Show current settings
  {BOLD}show modules{RESET}          -> List available modules
  {BOLD}set api <APIKEY>{RESET}      -> Configure API key
  {BOLD}set target <ID>{RESET}       -> Configure target_ID (UCxxxx)
  {BOLD}set module <NAME|all>{RESET} -> Select module or 'all' for all
  {BOLD}set save true|false{RESET}   -> Enable/Disable saving to files
  {BOLD}set verbose true|false{RESET}-> Enable debug logs
  {BOLD}set max <1-500>{RESET}       -> Limit results by module
  {BOLD}run{RESET}                   -> Run selected modules
  {BOLD}exit{RESET}                  -> Exit
""")
    print_sep()

def obfuscate(s: Optional[str]) -> str:
    if not s:
        return "N/A"
    if len(s) <= 6:
        return "***"
    return s[:3] + "*"*(len(s)-6) + s[-3:]

def run_cmd():
    if not STATE["api_key"] or not STATE["target"]:
        print_err("You must set 'api' and 'target' before running (set api / set target).")
        return
    try:
        youtube = get_service()
    except Exception as e:
        print_err(f"Failed to initialize YouTube service: {e}")
        return

    modules = STATE["modules"] or list(DISPATCH.keys())

    header("RUN", CYAN, EMO["run"])
    for m in modules:
        print(f"{BOLD}{CYAN} -> {m}{RESET}")
        try:
            DISPATCH[m](youtube)
        except Exception as e:
            print_err(f"Error in module {m}: {e}")

    save_full_json()

def main():
    banner()
    while True:
        try:
            cmdline = input(f"{BOLD}{CYAN}INSIGHTUBE >> {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break
        if not cmdline:
            continue
        parts = cmdline.split()
        cmd = parts[0].lower()

        if cmd == "exit":
            print("QUITTING...")
            break
        elif cmd == "help":
            show_help()
        elif cmd == "show":
            if len(parts) > 1 and parts[1].lower() == "options":
                show_options()
            elif len(parts) > 1 and parts[1].lower() == "modules":
                show_modules()
            else:
                print_note("Use: show options | show modules")
        elif cmd == "set":
            if len(parts) < 3:
                print_note("Use: set <api|target|module|save|verbose|max> <valor>")
                continue
            key = parts[1].lower()
            val = " ".join(parts[2:]).strip()
            if key == "api":
                STATE["api_key"] = val
                print_kv("API set:", obfuscate(val))
            elif key == "target":
                STATE["target"] = val
                print_kv("Target set:", val)
            elif key == "module":
                if val.lower() == "all":
                    STATE["modules"] = []
                    print_kv("Modules:", "ALL")
                else:
                    if val not in DISPATCH:
                        print_note(f"Unknown module. Use 'show modules'.")
                    else:
                        STATE["modules"] = [val]
                        print_kv("Module:", val)
            elif key == "save":
                STATE["save"] = val.lower() == "true"
                print_kv("Save:", STATE["save"])
            elif key == "verbose":
                STATE["verbose"] = val.lower() == "true"
                print_kv("Verbose:", STATE["verbose"])
            elif key == "max":
                try:
                    n = int(val)
                    if n < 1: n = 1
                    if n > 500: n = 500
                    STATE["max_results"] = n
                    print_kv("Max:", n)
                except:
                    print_note("Invalid value for max. Use a number 1..500.")
            else:
                print_note("Unknown key. Use: api|target|module|save|verbose|max")
        elif cmd == "run":
            run_cmd()
        else:
            print_note("Unknown command. Use 'help' for options.")

if __name__ == "__main__":
    main()
