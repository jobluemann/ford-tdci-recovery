# Architecture — ford-tdci-recovery v0.2

## The idea

Owners pay dealer diagnostic fees to rediscover faults that are already
documented as standard problems on their model. This project inverts that:
a **Bluetooth-first open-source diagnostic suite** where the first answer to
"what's wrong?" is "here are the known issues for your car, ranked against
your actual fault codes and symptoms — with sources."

## The dividing line (important)

- **Reading is open.** Fault codes, live data, module presence and identity
  need no security access. This suite covers all of it over a cheap ELM327
  (USB or Bluetooth serial).
- **Writing is locked.** Reflashing or security-protected service functions
  need Ford's seed/key. `pcm_flasher.py` is the framework only — you supply
  your own key implementation and firmware. Flashing over Bluetooth is
  refused by default; see docs/DIY_REFLASH_NOTES.md.

## Components

```
ford_recovery.py     menu: backup, DTCs, live DPF, module scan, KB lookup,
                     forum search, AI chat, community sharing
pcm_flasher.py       expert UDS reflash (bring your own seed/key + firmware)
ftr/                 transport, decoders, UDS, VBF, flasher, modules,
                     known_issues, feeds, aichat, share
data/                known_issues_kuga_mk2.json  <- curated, sourced KB
                     feeds.json (user-added forum RSS feeds)
site/                collect.php + index.html   <- community data platform
docs/                procedures, guides, reflash notes
```

## Knowledge base contract

Every issue in the KB carries: `known_issue: yes/no`, a confidence level,
symptoms, DTCs, ranked likely causes, checks, fixes, and **source links**.
Entries without a live source are marked `community-reported`. Contributions
arrive as pull requests adding sourced entries — the KB is the project's
long-term value, so sourcing discipline matters more than volume.

## Community data platform (no Node.js)

The `site/` folder drops onto any PHP shared host:

- `collect.php` accepts anonymized POST reports (`ftr-report/1` schema),
  refuses anything containing a VIN field, appends to `data/reports.jsonl`,
  and serves them read-only via `GET ?list=1`.
- `index.html` renders the collected reports as a plain table. Static, no
  build step, no framework.

Clients opt in per-report from menu option 11; the VIN is stripped and
replaced by a truncated SHA-256 reference before anything leaves the laptop.

## AI assistant

Optional, env-configured against any OpenAI-compatible endpoint
(`AI_BASE_URL` / `AI_API_KEY` / `AI_MODEL`). The system prompt pins it to
the KB and a VIN-stripped snapshot and forbids emissions-bypass advice.
Without configuration the assistant says so and the offline KB lookup
remains fully functional.

## Roadmap

- [ ] More vehicle KBs (Focus Mk3, Mondeo, EcoSport) via the same schema
- [ ] MS-CAN auto-switching support notes per adapter type
- [ ] Freeze-frame capture on module scan
- [ ] Community platform: aggregate stats (most-common codes per ECU)
- [ ] Android wrapper (Termux/tkinter-free UI) — help wanted
