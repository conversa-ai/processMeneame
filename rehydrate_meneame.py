#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Menéame rehydration (direct API; NO cache).

Input: dehydrated IDs-only JSON (dialogue chains of turn IDs).
Fetch: https://www.meneame.net/api/list.php?id=<article_id>

IMPORTANT:
- Your dialogue chain IDs correspond to objects[*].order (NOT objects[*].id).

Output: local rehydrated JSON with dialogue texts (NOT FOR REDISTRIBUTION),
where each turn is represented as a JSON-compatible 2-tuple:
  [ "<SPEAKER_LETTER>", "<TURN_TEXT>" ]
Missing turns are represented as null.

Assumptions:
- article_id is the dehydrated file stem OR present in input fields link_id/thread_id/article_id.
- Each dialogue chain contains integers matching objects[*].order in the API response.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import re
import sys
import time
from typing import Dict, List, Optional, Tuple

import requests


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_USER_MENTION_RE = re.compile(r"@\w+|u/\w+", re.IGNORECASE)


def _clean_text(text: str) -> str:
    if text is None:
        return ""
    t = html.unescape(str(text))
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = _TAG_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    return t


def _index_to_letters(i: int) -> str:
    # 0->A, 25->Z, 26->AA, ...
    if i < 0:
        raise ValueError("Index must be non-negative")
    letters: List[str] = []
    while True:
        i, rem = divmod(i, 26)
        letters.append(chr(ord("A") + rem))
        if i == 0:
            break
        i -= 1
    return "".join(reversed(letters))


def _assign_speaker(raw_user: str, mapping: Dict[str, str]) -> str:
    u = (raw_user or "").strip()
    if not u:
        u = "__unknown__"
    if u in mapping:
        return mapping[u]
    label = _index_to_letters(len(mapping))
    mapping[u] = label
    return label


def _replace_user_handle_occurrences(text: str, raw_user: str, label: str) -> str:
    """
    Conservative replacement of exact username tokens with speaker label.
    This prevents leaking handles in the rehydrated output.
    """
    if not raw_user:
        return text
    esc = re.escape(raw_user)
    return re.sub(rf"(?i)\b{esc}\b", label, text)


def _extract_article_id(obj: dict, input_path_stem: str) -> str:
    for k in ("article_id", "link_id", "thread_id"):
        v = obj.get(k)
        if isinstance(v, int):
            return str(v)
        if isinstance(v, str) and v.strip():
            m = re.search(r"(\d+)", v)
            return m.group(1) if m else v.strip()

    m = re.search(r"(\d+)", input_path_stem)
    return m.group(1) if m else input_path_stem


def _fetch_meneame(article_id: str, user_agent: str, timeout_s: float, retries: int, sleep_s: float, debug: bool) -> dict:
    url = f"https://www.meneame.net/api/list.php?id={article_id}"
    headers = {"User-Agent": user_agent}

    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            if debug:
                print(f"[debug] GET {url} (attempt {attempt}/{retries})", file=sys.stderr)
            r = requests.get(url, headers=headers, timeout=timeout_s)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(sleep_s)
    raise RuntimeError(f"Failed to fetch Menéame api/list.php for id={article_id}: {last_err}")


def _build_turn_map_keyed_by_order(api_json: dict, debug: bool) -> Tuple[str, Dict[int, Tuple[str, str]]]:
    """
    Returns:
      thread_url, tmap where tmap[order] = (user, content)
    """
    thread_url = str(api_json.get("url") or "")
    objs = api_json.get("objects") or []
    if not isinstance(objs, list):
        objs = []

    tmap: Dict[int, Tuple[str, str]] = {}
    n_missing_order = 0

    for o in objs:
        if not isinstance(o, dict):
            continue
        try:
            order_int = int(o.get("order"))
        except Exception:
            n_missing_order += 1
            continue
        user = str(o.get("user") or "")
        content = str(o.get("content") or "")
        tmap[order_int] = (user, content)

    if debug:
        if n_missing_order:
            print(f"[debug] objects missing usable 'order': {n_missing_order}", file=sys.stderr)
        print(f"[debug] turns indexed by order: {len(tmap)}", file=sys.stderr)

    return thread_url, tmap


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Dehydrated Menéame IDs-only JSON (dialogue chains keyed by order).")
    ap.add_argument("--output", required=True, help="Rehydrated JSON (contains text; local use only).")
    ap.add_argument("--user-agent", required=True, help="User-Agent string for HTTP requests.")

    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--sleep", type=float, default=1.0)

    ap.add_argument("--replace-mentions", action="store_true", help="Replace generic @mentions/u/mentions with @USER")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        dehydrated = json.load(f)

    dialogues = dehydrated.get("dialogues")
    if not isinstance(dialogues, dict):
        raise SystemExit("Input dehydrated file must contain a 'dialogues' dict.")

    input_stem = re.sub(r"\.json$", "", args.input.split("/")[-1])
    article_id = _extract_article_id(dehydrated, input_stem)

    api_json = _fetch_meneame(
        article_id=article_id,
        user_agent=args.user_agent,
        timeout_s=args.timeout,
        retries=args.retries,
        sleep_s=args.sleep,
        debug=args.debug,
    )

    thread_url, tmap = _build_turn_map_keyed_by_order(api_json, debug=args.debug)

    # Speaker mapping is per thread (file)
    speaker_map: Dict[str, str] = {}

    dialogues_out: Dict[str, List[Optional[List[str]]]] = {}
    missing: Dict[str, Dict[str, int]] = {}

    for did, chain in dialogues.items():
        if not isinstance(chain, list):
            continue

        turns: List[Optional[List[str]]] = []
        n_missing = 0

        for x in chain:
            try:
                order_id = int(x)
            except Exception:
                turns.append(None)
                n_missing += 1
                continue

            if order_id not in tmap:
                turns.append(None)
                n_missing += 1
                continue

            raw_user, raw_content = tmap[order_id]
            speaker = _assign_speaker(raw_user, speaker_map)

            txt = _clean_text(raw_content)
            txt = _replace_user_handle_occurrences(txt, raw_user, speaker)
            if args.replace_mentions:
                txt = _USER_MENTION_RE.sub("@USER", txt)

            if not txt:
                turns.append(None)
                n_missing += 1
                continue

            # JSON-friendly tuple representation: [speaker, text]
            turns.append([speaker, txt])

        dialogues_out[str(did)] = turns
        missing[str(did)] = {"n_turns": len(chain), "n_missing": n_missing}

    out = {
        "format": "meneame_dialogue_text_v4_order_keyed_tuples",
        "source": "meneame",
        "thread_id": str(dehydrated.get("thread_id") or input_stem),
        "article_id": article_id,
        "thread_url": thread_url or f"https://www.meneame.net/story/{article_id}",
        "snapshot_date": dehydrated.get("snapshot_date") or _dt.date.today().isoformat(),
        "rehydrated_at": _dt.date.today().isoformat(),
        "key_used": "objects.order",
        "turn_representation": "[speaker_letter, text] (null if missing)",
        "dialogues": dialogues_out,
        "missing": missing,
        "notice": "This file contains user-generated content retrieved at runtime from Menéame. Do not redistribute.",
    }

    out_dir = "/".join(args.output.split("/")[:-1])
    if out_dir:
        import os
        os.makedirs(out_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    if args.debug:
        print(f"[ok] wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
