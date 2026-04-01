#!/usr/bin/env python3
"""
upload_eventlogs_to_elk.py  –  Upload Skadi EventLogs to Elasticsearch

loki_EventLogs.json has an unusual nested structure that Logstash cannot
handle efficiently (it is one large pretty-printed JSON object, not JSON Lines):

    {
      "C:\\...\\Application.evtx": [ <event>, <event>, ... ],
      "C:\\...\\Security.evtx":    [ <event>, ... ],
      ...
    }

This script flattens that structure and bulk-uploads to ES.

Usage:
    python upload_eventlogs_to_elk.py [--host URL] [--user USER] [--pass PASS]
                                      [--file PATH] [--index INDEX]
                                      [--case CASE_NAME]

Defaults come from the skadi.env values:
    ES host:  http://localhost:9200
    Creds:    elastic / Y2K_passwd
    File:     C:\\client_data\\local\\parsed_skadi\\loki_skadi\\EventLogs\\loki_EventLogs.json
    Index:    skadi-eventlogs
    Case:     loki_skadi

Requirements:
    pip install elasticsearch
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults (override via CLI or environment variables)
# ---------------------------------------------------------------------------
DEFAULT_ES_HOST  = os.environ.get("ES_HOST",  "https://localhost:9200")
DEFAULT_ES_USER  = os.environ.get("ES_USER",  "elastic")
DEFAULT_ES_PASS  = os.environ.get("ES_PASS",  os.environ.get("ELASTIC_PASSWORD", ""))
DEFAULT_INDEX    = "dfir-loki"
DEFAULT_CASE     = "loki_skadi"
DEFAULT_FILE     = r"C:\client_data\local\parsed_skadi\loki_skadi\EventLogs\loki_EventLogs.json"

BATCH_SIZE = 500   # documents per bulk request


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host",  default=DEFAULT_ES_HOST,  help="Elasticsearch URL  (default: %(default)s)")
    p.add_argument("--user",  default=DEFAULT_ES_USER,  help="ES username         (default: %(default)s)")
    p.add_argument("--pass",  dest="password",
                              default=DEFAULT_ES_PASS,  help="ES password          (default: %(default)s)")
    p.add_argument("--file",  default=DEFAULT_FILE,     help="Path to loki_EventLogs.json")
    p.add_argument("--index", default=DEFAULT_INDEX,    help="Target ES index      (default: %(default)s)")
    p.add_argument("--case",  default=DEFAULT_CASE,     help="Case/triage name     (default: %(default)s)")
    p.add_argument("--dry-run", action="store_true",    help="Parse only, do not upload")
    return p.parse_args()


def iter_actions(data: dict, index: str, case_name: str):
    """Yield ES bulk action dicts from the nested EventLogs structure."""
    for evtx_path, events in data.items():
        if not isinstance(events, list) or not events:
            continue
        # Derive a short name for use as a filter in Kibana
        evtx_name = Path(evtx_path.replace("\\", "/")).name

        for evt in events:
            if not isinstance(evt, dict):
                continue
            doc = dict(evt)
            doc["evtx_source_path"] = evtx_path
            doc["evtx_source_name"] = evtx_name
            doc["artifact_type"]    = "eventlogs"
            doc["tags"]             = ["eventlogs"]
            doc["case_name"]        = case_name
            yield {"_index": index, "_source": doc}


def bulk_upload(es, actions, batch_size: int = BATCH_SIZE) -> tuple[int, int]:
    """Upload in batches; return (success_count, fail_count)."""
    from elasticsearch.helpers import streaming_bulk

    ok_total = fail_total = 0
    for ok, info in streaming_bulk(es, actions, chunk_size=batch_size,
                                   raise_on_error=False, raise_on_exception=False):
        if ok:
            ok_total += 1
        else:
            fail_total += 1
            action_result = info.get("index") or info.get("create") or {}
            err = action_result.get("error", {})
            print(f"  [!] Failed doc: {err.get('type')}: {err.get('reason')}", file=sys.stderr)
    return ok_total, fail_total


def main() -> int:
    args = parse_args()

    # ── Load JSON ──────────────────────────────────────────
    fpath = Path(args.file)
    if not fpath.exists():
        print(f"[-] File not found: {fpath}", file=sys.stderr)
        return 1

    print(f"[*] Loading  {fpath}")
    with fpath.open(encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        print("[-] Unexpected JSON structure — expected a top-level object.", file=sys.stderr)
        return 1

    total_events = sum(len(v) for v in data.values() if isinstance(v, list))
    total_evtx   = len(data)
    print(f"[*] Found    {total_events:,} events across {total_evtx} EVTX sources")

    if args.dry_run:
        print("[*] Dry-run mode — skipping upload")
        for src, evts in data.items():
            n = len(evts) if isinstance(evts, list) else 0
            if n:
                print(f"    {n:>5}  {Path(src.replace(chr(92), '/')).name}")
        return 0

    # ── Connect to Elasticsearch ───────────────────────────
    try:
        from elasticsearch import Elasticsearch
    except ImportError:
        print("[-] elasticsearch package not installed.\n    Run: pip install elasticsearch", file=sys.stderr)
        return 1

    print(f"[*] Connecting {args.host}  (user={args.user})")
    es = Elasticsearch(args.host, basic_auth=(args.user, args.password),
                       verify_certs=False, ssl_show_warn=False)
    if not es.ping():
        print("[-] Cannot reach Elasticsearch — check host/credentials and that the stack is running.", file=sys.stderr)
        return 1
    print("[+] Connected")

    # ── Upload ─────────────────────────────────────────────
    print(f"[*] Uploading to index '{args.index}' ...")
    actions = iter_actions(data, args.index, args.case)
    ok, fail = bulk_upload(es, actions)

    print(f"[+] Done — uploaded: {ok:,}  failed: {fail:,}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
