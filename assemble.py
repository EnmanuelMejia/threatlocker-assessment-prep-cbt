#!/usr/bin/env python3
"""Assemble source/*.json fragments into content.json for ThreatLocker Assessment Prep.

Assembly model (mirrors full-spectrum-dominance-cbt):
  - Metadata (slug/title/tagline/vendor/disclaimer/accent/simulation/...) comes
    from the fragment whose "slug" == "threatlocker-assessment-prep"
    (source/meta.json). Base pillar files keep their own metadata; only the
    target-slug fragment supplies the header.
  - Array keys (domains, lessons, labs, simulations, consoleSims,
    terminalMissions, media, behavioral, sections) are merged across ALL
    fragments in sorted-filename order, deduplicated by id (first wins).
    This lets new content packs land as additional source/*.json files and
    merge cleanly with the base pillars.
  - "chat_topics" lists merge into chat.topics; "resources" dicts merge.

Then validates the assembled document against the engine's runtime contract
(engine/bootcamp.js ingest(), labs/learn/simulations renderers) and verifies
every referenced SVG exists under assets/diagrams/.

Usage:
  python3 assemble.py            # builds content.json from source/
  python3 assemble.py --check    # validate an existing content.json only
"""
import json, sys, os, glob, re

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "source")
OUT = os.path.join(ROOT, "content.json")

TARGET_SLUG = "threatlocker-assessment-prep"
LIST_KEYS = ["domains", "lessons", "labs", "simulations", "consoleSims",
             "terminalMissions", "media", "behavioral", "sections"]
META_KEYS = ["slug", "title", "tagline", "vendor", "disclaimer", "accent",
             "simulation", "foundations", "math", "chat", "resources"]

errors, warnings = [], []

def fail(msg): errors.append(msg)
def warn(msg): warnings.append(msg)

def fingerprint(it):
    """Stable dedup key for merged list entries. Lessons and behavioral
    prompts in the base pillars carry no id — fingerprint on content."""
    if isinstance(it, dict):
        if it.get("id"):
            return ("id", it["id"])
        if it.get("domain_id") and it.get("title"):
            return ("lesson", it["domain_id"], it["title"])
        if it.get("prompt"):
            return ("behavioral", it["prompt"][:80])
    return ("json", json.dumps(it, sort_keys=True, ensure_ascii=False))

def load_fragments():
    frags = []
    for f in sorted(glob.glob(os.path.join(SRC, "*.json"))):
        name = os.path.basename(f)
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception as e:
            fail(f"{name}: invalid JSON ({e})"); continue
        if not isinstance(d, dict):
            fail(f"{name}: top-level must be an object"); continue
        frags.append((name, d))
    return frags

def merge_fragments(frags):
    metas = [(n, d) for n, d in frags if d.get("slug") == TARGET_SLUG]
    if not metas:
        fail(f"no fragment provides metadata for slug '{TARGET_SLUG}' (source/meta.json)")
        return None
    if len(metas) > 1:
        warn(f"multiple metadata fragments: {[n for n, _ in metas]} — using {metas[0][0]}")
    doc = {k: metas[0][1][k] for k in META_KEYS if k in metas[0][1]}
    # fallback keys: first fragment that carries them (base master), so the
    # metadata-only fragment doesn't drop shared blocks
    for k in ["foundations", "math", "chat"]:
        if k not in doc:
            for n, d in frags:
                if d.get(k):
                    doc[k] = d[k]
                    break

    for k in LIST_KEYS:
        merged, seen = [], set()
        for n, d in frags:
            v = d.get(k)
            if v is None: continue
            if not isinstance(v, list):
                fail(f"{n}: '{k}' must be a list"); continue
            for it in v:
                fp = fingerprint(it)
                if fp[0] == "json":
                    fail(f"{n}: '{k}' entry missing id and not fingerprintable: {str(it)[:80]}"); continue
                if fp in seen:
                    continue  # first occurrence wins
                seen.add(fp); merged.append(it)
        if merged: doc[k] = merged

    topics = []
    for n, d in frags:
        ct = d.get("chat_topics")
        if ct:
            if not isinstance(ct, list): fail(f"{n}: 'chat_topics' must be a list")
            else: topics.extend(ct)
    if topics:
        chat = doc.get("chat") or {}
        existing = chat.get("topics") or []
        seen_t = {t.get("id") for t in existing if isinstance(t, dict)}
        for t in topics:
            tid = t.get("id") if isinstance(t, dict) else None
            if tid and tid in seen_t:
                continue
            if tid: seen_t.add(tid)
            existing.append(t)
        chat["topics"] = existing
        doc["chat"] = chat

    res = {}
    for n, d in frags:
        r = d.get("resources")
        if r:
            if not isinstance(r, dict): fail(f"{n}: 'resources' must be an object")
            else:
                for k, v in r.items():
                    if k in res and isinstance(res[k], list) and isinstance(v, list):
                        res[k] = res[k] + v
                    else:
                        res[k] = v
    if res: doc["resources"] = res
    return doc

def validate(doc):
    if doc.get("slug") != TARGET_SLUG:
        fail(f"slug must be '{TARGET_SLUG}', got {doc.get('slug')!r}")
    for k in ["title", "tagline", "disclaimer"]:
        if not doc.get(k): fail(f"missing required metadata: {k}")
    disc = str(doc.get("disclaimer", ""))
    for name in ["ThreatLocker", "ELVTR", "Microsoft"]:
        if name not in disc: fail(f"disclaimer must name {name}")
    if "no certificate" not in disc.lower():
        fail("disclaimer must state it confers no certificate")

    domains = doc.get("domains") or []
    if not domains: fail("domains is empty")
    domain_ids, total_scen = set(), 0
    for d in domains:
        domain_ids.add(d.get("id"))
        if not d.get("name"): fail(f"domain {d.get('id')}: missing name")
        scens = d.get("scenarios") or []
        if not scens: warn(f"domain {d.get('id')}: has no scenarios")
        for s in scens:
            total_scen += 1
            for k in ["title", "situation", "prompt", "choices", "answer", "why"]:
                if s.get(k) in (None, ""):
                    fail(f"scenario {d.get('id')}:{s.get('id')}: missing '{k}'")
            ch, a = s.get("choices") or [], s.get("answer")
            if not isinstance(ch, list) or len(ch) < 2:
                fail(f"scenario {d.get('id')}:{s.get('id')}: need >=2 choices")
            elif not isinstance(a, int) or not (0 <= a < len(ch)):
                fail(f"scenario {d.get('id')}:{s.get('id')}: answer index out of range")
            for ev in (s.get("evidence") or []):
                if not (isinstance(ev, (list, tuple)) and len(ev) == 2):
                    fail(f"scenario {d.get('id')}:{s.get('id')}: evidence must be [label, text] pairs")
    print(f"  domains={len(domains)} scenarios={total_scen}")

    for l in (doc.get("lessons") or []):
        for k in ["domain_id", "title", "concepts"]:
            if not l.get(k): fail(f"lesson {l.get('title', '?')}: missing '{k}'")
        if l.get("domain_id") not in domain_ids:
            fail(f"lesson {l.get('title')}: unknown domain_id {l.get('domain_id')!r}")

    lab_ids = set()
    for lb in (doc.get("labs") or []):
        for k in ["id", "title", "objective", "steps", "checks", "success_message"]:
            if not lb.get(k): fail(f"lab {lb.get('id', '?')}: missing '{k}'")
        lab_ids.add(lb.get("id"))
        for c in (lb.get("checks") or []):
            for k in ["command_pattern", "expect_contains"]:
                if k not in c: fail(f"lab {lb.get('id')}: check missing '{k}'")
            try: re.compile(c["command_pattern"])
            except Exception as e: fail(f"lab {lb.get('id')}: bad command_pattern regex ({e})")

    for sm in (doc.get("simulations") or []):
        for k in ["id", "title", "domain_id", "brief", "steps", "debrief"]:
            if not sm.get(k): fail(f"simulation {sm.get('id', '?')}: missing '{k}'")
        if sm.get("domain_id") not in domain_ids:
            fail(f"simulation {sm.get('id')}: unknown domain_id")

    for m in (doc.get("media") or []):
        svg = m.get("svg")
        if svg:
            if not os.path.isfile(os.path.join(ROOT, svg)):
                fail(f"media {m.get('id')}: missing svg file {svg}")
        else:
            warn(f"media {m.get('id')}: no svg path")

    for sec in (doc.get("sections") or []):
        for lid in (sec.get("lab_ids") or []):
            if lid not in lab_ids: fail(f"section {sec.get('id')}: unknown lab_id {lid!r}")
        for did in (sec.get("drill_domain_ids") or []):
            if did not in domain_ids: fail(f"section {sec.get('id')}: unknown drill_domain_id {did!r}")

    try:
        with open(os.path.join(ROOT, "engine", "foundations.json"), encoding="utf-8") as fh:
            ftracks = {t["id"] for t in json.load(fh)["tracks"]}
        with open(os.path.join(ROOT, "engine", "math.json"), encoding="utf-8") as fh:
            mmods = {x["id"] for x in json.load(fh)["modules"]}
    except Exception as e:
        fail(f"could not load engine foundations/math: {e}"); ftracks, mmods = set(), set()
    for f in (doc.get("foundations") or []):
        t = f.get("track") if isinstance(f, dict) else f
        if t not in ftracks: fail(f"foundations: unknown track {t!r}")
    for m in (doc.get("math") or []):
        if m not in mmods: fail(f"math: unknown module {m!r}")

    chat = doc.get("chat") or {}
    if chat and not chat.get("topics"): warn("chat block has no topics")
    if (doc.get("simulation") or {}) and not doc["simulation"].get("minutes"):
        warn("simulation block missing minutes")

def main():
    doc = None
    if "--check" in sys.argv:
        try:
            with open(OUT, encoding="utf-8") as fh: doc = json.load(fh)
        except Exception as e:
            print(f"ERROR: cannot read content.json: {e}"); sys.exit(2)
        validate(doc)
    else:
        frags = load_fragments()
        if not errors:
            if not frags: fail("no source/*.json fragments found")
            else:
                doc = merge_fragments(frags)
                if doc is not None: validate(doc)
        if not errors and doc is not None:
            with open(OUT, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, ensure_ascii=False, indent=1); fh.write("\n")
            print(f"wrote {OUT}")
    for w in warnings: print(f"WARNING: {w}")
    for e in errors: print(f"ERROR: {e}")
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
