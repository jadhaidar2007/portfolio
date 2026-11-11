# Jad Haidar — AI automation & data projects

Industrial Engineering & Management student (Data Science minor) at Constructor
University Bremen. I build working tools with LLMs, automation and data, from
the first prototype to something people use every day.

## Projects in this repo

### [`llm-wiki/`](llm-wiki) — AI-native knowledge base
An LLM wiki with an **ask agent** that only answers from pages the user may see and
cites every claim, a **curator agent** that drafts new pages from source documents,
a **human review gate** before anything becomes authoritative, a **linter** for stale
pages and contradictions, and a **retrieval eval** that also tests for permission leaks.
Runs offline; uses Claude when an API key is set.

### [`fixture-intel/`](fixture-intel) — tanker fixture intelligence (internship, rebuilt)
Clean-room rebuild, on synthetic data, of the system I built for the oil trading desk at
Enervest / 1ENERGIN DMCC in Dubai: broker emails via **Microsoft Graph** → per-broker
parsers → deduplicated SQLite → Flask dashboard + a morning briefing email with inline
SVG sparklines.

## Jadworks — AI automation agency (2025 – present)

I run a small web and AI automation agency for small businesses. I own the full cycle:
finding clients, pitching, building, delivering and supporting. Client work is not in
this repo, but here is what I build:

- **WhatsApp lead-capture bots.** Incoming WhatsApp messages (Twilio) are answered by an
  LLM (GPT-4o-mini) that collects the lead's details and logs them to Google Sheets,
  built as n8n workflows.
- **Real estate lead bots.** Bots for property businesses that respond to enquiries
  straight away, qualify the lead, and pass it on to the agent.
- **Class-booking web app for CrossFit 961 (Lebanon).** Built end to end, from
  requirements to delivery, as a replacement for their booking software.
- **Model selection for client automations.** Compared commercial and open-source
  LLMs (Claude vs. Qwen) on cost and output quality before putting them into
  client workflows.

## Elsewhere

- [`jadhaidar2007/jad`](https://github.com/jadhaidar2007/jad): a video clipping pipeline
  (download → Whisper transcription → LLM clip selection → captioned edits → scheduled
  uploads).

## Contact

jadhaidar76@gmail.com · [getjadworks.com](https://getjadworks.com) · Bremen, Germany
