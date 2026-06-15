# CRM SCHEMA — ABUZ8 Mission Control
**Version:** 1.0
**Type:** Markdown-based (no database needed at this stage)

---

## FILE STRUCTURE

```
.\LIVE_CRM\
├── MISSION_CONTROL.md      — Master dashboard (all metrics)
├── PIPELINE_BOARD.md       — Sales pipeline (prospect → closed)
├── AGENT_TASK_BOARD.md     — Agent assignments and status
├── PRODUCT_BOARD.md        — Product inventory and status
├── CONTENT_BOARD.md        — Content queue and publishing
├── OUTREACH_BOARD.md       — Email campaigns and metrics
├── DAILY_SCOREBOARD.md     — Today's metrics and must-do
├── BLOCKERS.md             — What's stuck and why
├── CRM_SCHEMA.md           — This file (structure docs)
├── OUTREACH_INSTRUCTIONS.md — Pipeline execution guide
├── READY_TO_POST.md        — Approved content queue
└── prospects_batch_001.md  — Lead list (batch 1)
```

## LEAD SCHEMA
| Field | Type | Required | Source |
|-------|------|----------|--------|
| business_name | string | ✅ | Google Maps |
| niche | string | ✅ | Pipeline config |
| city | string | ✅ | Pipeline config |
| website | URL | — | Google Maps |
| phone | string | — | Google Maps |
| owner_name | string | — | Enrichment |
| email | string | — | Enrichment |
| review_count | int | — | Google Maps |
| star_rating | float | — | Google Maps |
| site_score | 1-10 | — | Diagnosis |
| status | enum | ✅ | Pipeline stage |
| last_action | string | — | Activity log |
| next_action | string | ✅ | Pipeline rules |

## PIPELINE STAGES
1. PROSPECT → just found, no enrichment
2. ENRICHED → site audited, contact found, scored
3. OUTREACH_SENT → email sent
4. REPLIED → got a response (positive or negative)
5. CALL_BOOKED → meeting scheduled
6. PROPOSAL_SENT → quote/proposal delivered
7. CLOSED_WON → deal done, payment received
8. CLOSED_LOST → declined (retry in 30 days)

## UPDATE RULES
- Update boards in real-time as actions happen
- DAILY_SCOREBOARD.md resets each day
- MISSION_CONTROL.md is the master truth
- Never delete entries — move to appropriate stage
- Log all activity with timestamps
