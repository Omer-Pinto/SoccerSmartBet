# Team News Vertical

**Purpose:** Gather team morale, coach stability, preparation quality, and other betting-relevant news

---

## Requirements

- Match previews and team news articles
- Coach statements on rotation/lineup
- Morale indicators (controversies, protests, ownership issues)
- Training reports and press conferences
- Transfers and squad changes

---

## Problem: No Free Structured APIs

**Status:** 🔴 Disabled

### Paid API: Sportmonks Pre-Match News
- **Cost:** Paid subscription only
- **Features:** Scout-analyzed match previews 48h before kickoff
- **Coverage:** Premier League, Champions League, La Liga, Serie A, Bundesliga, Ligue 1
- **Decision:** **Not using** - violates "no paid services" constraint

---

## Alternative: Web Scraping (NOT RECOMMENDED)

### Free News Sources
| Source | URL | Coverage | Difficulty |
|--------|-----|----------|------------|
| BBC Sport | bbc.com/sport/football | Premier League | Medium |
| Sky Sports | skysports.com | Multi-league | Medium |
| ESPN FC | espn.com/soccer | Global | Easy |
| The Athletic | theathletic.com | Premium (paywall) | Hard |

### Why Disabled?
1. **Fragility:** Site layout changes break scrapers constantly
2. **Legal:** ToS violations, potential IP blocks
3. **Data Quality:** Unstructured text, hard to extract signals
4. **Maintenance:** High effort to maintain multiple scrapers
5. **Not Critical:** Injuries/suspensions provide core team strength data

---

## Decision: Disable Team News Vertical

**Rationale:**
- **MVP Focus:** Injuries/suspensions/H2H/weather provide sufficient data
- **AI Can Still Bet:** System can make informed bets without news articles
- **Revisit Later:** If MCP news tools mature (reliable football news MCPs), re-enable

**Impact:**
- Team Intelligence Agent won't have `relevant_news` field
- Still has: form trend, injury impact, rotation risk (inferred from fixtures), key players status

---

## Future Consideration: MCP News Servers

If reliable football news MCP servers emerge:
- **mcp-sports-news** (hypothetical): Aggregates BBC/ESPN/Sky with ToS compliance
- **Integration:** Use as external MCP tool, not custom development
- **Criteria:** Must be free, maintained, cover major leagues

---

## See Also
- [Team Intelligence Agent](../../../../status/pre_gambling_flow/PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md#52-team-intelligence-agent-node) - operates without news data for MVP
- [Disabled Verticals](../executive_summary.md#-key-concerns) - list of scraping-based features
