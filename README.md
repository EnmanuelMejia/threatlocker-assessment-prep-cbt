# ThreatLocker Assessment Prep — Interactive CBT

An interactive, adaptive computer-based training course preparing a
cybersecurity candidate for assessment-style evaluation: Zero Trust endpoint
defense, security graphs ("think like an attacker"), and AI-aided SOC work —
scored scenario drills with weakest-domain targeting, structured lessons,
guided hands-on labs, simulated terminal/console/mission sandboxes, a timed
180-minute simulation, behavioral prep, and a chat companion.

**Live:** https://interstitiumlabs.dev/bootcamps/threatlocker-assessment-prep/
Also deployed on https://learn.interstitiumlabs.dev and https://enmanueldmejia.com

## How it works

- **Interactive** — scenarios are hands-on scored decisions, not reading material.
- **Adaptive** — the drill queue targets weakest domains first; per-domain mastery is tracked locally in your browser (localStorage, nothing leaves your device).
- **Independent** — study companion by Interstitium Labs. Not affiliated with ThreatLocker, ELVTR, or Microsoft. Confers no certificate. All scenarios are original practice content; no vendor or course material is reproduced.

## Run it

Open `index.html` in any browser — self-contained, zero dependencies. `chat/index.html` is the conversational practice companion.

Source content lives in `source/`:
- `tl.json`, `ai.json`, `graphs.json` — base pillar fragments (from full-spectrum-dominance-cbt)
- `full-spectrum-dominance.json` — base master assembly (same source)
- `meta.json` — this bootcamp's header metadata (slug/title/tagline/disclaimer/accent/simulation)

`content.json` is the deployed payload, produced by `python3 assemble.py`
(merges all fragments, dedups by id, validates schema + SVG references).
`engine/` is the shared bootcamp runtime (lessons, labs, terminal, console,
missions, chat, simulations) — identical architecture to
`../full-spectrum-dominance-cbt/`.

## Deploy

```bash
# refresh the staged asset tree, then deploy the worker + routes
python3 deploy/stage.py
~/workspace/skills/cloudflare/bin/deploy-worker-assets deploy/worker-config.json
python3 deploy/create-routes.py   # idempotent; skips existing routes
```

Worker: `threatlocker-assessment-prep-cbt`. Routes (all three domains):
`*/bootcamps/threatlocker-assessment-prep/*` — more specific than the existing
`*/bootcamps/*` → cert-bootcamps, so it takes precedence.

Built by [Interstitium Labs](https://interstitiumlabs.dev) — Enmanuel D. Mejia, Founder.
