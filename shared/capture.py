#!/usr/bin/env python3
"""capture.py — save connector results to input files WITHOUT re-typing them.

Every tool result in this session is already on disk: in the session transcript
(~/.claude/projects/<project>/<session>.jsonl) and, for large results, in the
tool-results/ file the transcript points to. This script finds the result of a
connector call and writes it byte-for-byte to an input file, so a long JSON
report never has to be copied by hand (copying is where truncation errors creep in).

  python3 capture.py --tool qbo_accounting_get_balance_sheet --match start_date=2026-10-19 --out W/inputs/qbo_bs_2026-10-19.json
  python3 capture.py --tool ramp_list_bills --merge bills --out W/inputs/ramp_bills.json
  python3 capture.py --tool ramp_get_bill_details --map-by bill_id --out W/inputs/ramp_bill_details.json
  python3 capture.py --tool read_resource --match-contains uri=01ABC --text --out W/state/state.json
  python3 capture.py --list            # show the connector calls this session has made

--tool      suffix of the tool name (e.g. ramp_list_bills matches mcp__Ramp__ramp_list_bills)
--match     k=v   input argument must equal v (repeatable)
--match-contains k=v   input argument must contain v (repeatable)
--merge K   merge the list K across every matching call (pages), de-duplicated by "id"
--map-by K  write {input[K]: result_json} for every matching call
--text      write the result text as-is (default: must parse as JSON; it is re-serialised exactly as parsed)
--last      (default) use the most recent matching call
--session   path to a transcript (default: the most recently modified one)
Exit 3 when nothing matches or the result is an error.
"""
import sys, os, re, json, glob, argparse

def transcripts():
    pats = [os.path.expanduser("~/.claude/projects/*/*.jsonl")]
    if os.environ.get("CLAUDE_CONFIG_DIR"): pats.append(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "projects/*/*.jsonl"))
    files = [f for p in pats for f in glob.glob(p)]
    return sorted(set(files), key=os.path.getmtime, reverse=True)

def result_text(content):
    if isinstance(content, str): return content
    if isinstance(content, list):
        return "".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
    return ""

SAVED = re.compile(r"Output has been saved to (\S+?\.txt)")

def resolve(text):
    """large results are spilled to a file; follow the pointer"""
    if text.startswith("Error: result") and "saved to" in text:
        m = SAVED.search(text)
        if m and os.path.exists(m.group(1)): return open(m.group(1), encoding="utf-8").read()
        raise SystemExit(f"result was spilled to a file that is not readable: {m.group(1) if m else '?'}")
    return text

def calls(path):
    uses, out = {}, []
    for line in open(path, encoding="utf-8"):
        try: o = json.loads(line)
        except Exception: continue
        m = o.get("message")
        if not isinstance(m, dict) or not isinstance(m.get("content"), list): continue
        for c in m["content"]:
            if not isinstance(c, dict): continue
            if c.get("type") == "tool_use": uses[c["id"]] = (c["name"], c.get("input") or {})
            elif c.get("type") == "tool_result" and c.get("tool_use_id") in uses:
                name, inp = uses[c["tool_use_id"]]
                out.append({"name": name, "input": inp, "text": result_text(c.get("content")), "is_error": bool(c.get("is_error"))})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool"); ap.add_argument("--out"); ap.add_argument("--session")
    ap.add_argument("--match", action="append", default=[]); ap.add_argument("--match-contains", action="append", default=[])
    ap.add_argument("--merge"); ap.add_argument("--map-by"); ap.add_argument("--text", action="store_true"); ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    sess = a.session or (transcripts() or [None])[0]
    if not sess: print("no session transcript found"); sys.exit(3)
    cs = [c for c in calls(sess) if c["name"].startswith("mcp__")]
    if a.list:
        for c in cs: print(c["name"], json.dumps(c["input"])[:160], len(c["text"]))
        return
    def ok(c):
        if not c["name"].endswith(a.tool): return False
        for kv in a.match:
            k, v = kv.split("=", 1)
            if str(c["input"].get(k)) != v: return False
        for kv in a.match_contains:
            k, v = kv.split("=", 1)
            if v not in str(c["input"].get(k, "")): return False
        return True
    hits = [c for c in cs if ok(c)]
    if not hits: print(f"no {a.tool} call matching {a.match + a.match_contains} in {sess}"); sys.exit(3)
    for c in hits:
        if c["is_error"] or (c["text"].startswith(("Error:", "MCP error")) and "saved to" not in c["text"]):
            print(f"{a.tool} returned an error — re-run the call: {c['text'][:300]}"); sys.exit(3)
    if a.merge:
        merged, seen, last = [], set(), None
        for c in hits:
            js = json.loads(resolve(c["text"])); last = js
            for r in js.get(a.merge, []):
                k = r.get("id") or json.dumps(r, sort_keys=True)
                if k in seen: continue
                seen.add(k); merged.append(r)
        body = dict(last); body[a.merge] = merged; body["pages_merged"] = len(hits)
        data = json.dumps(body)
    elif a.map_by:
        body = {}
        for c in hits:
            body[str(c["input"].get(a.map_by))] = json.loads(resolve(c["text"]))
        data = json.dumps(body)
    else:
        t = resolve(hits[-1]["text"])
        if a.text: data = t
        else:
            json.loads(t)          # must be valid JSON
            data = t               # keep the connector's exact bytes
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(data)
    print(json.dumps({"out": a.out, "bytes": len(data.encode("utf-8")), "calls": len(hits), "session": os.path.basename(sess)}))

if __name__ == "__main__":
    main()
