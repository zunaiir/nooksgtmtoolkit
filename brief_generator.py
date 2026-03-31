#!/usr/bin/env python3
"""
Pre-Call Research Brief Generator
Powered by Claude AI — Nooks GTM Toolkit

SETUP (one time):
  pip install -r requirements.txt
  export ANTHROPIC_API_KEY=your_key_here   ← get it at console.anthropic.com

USAGE:
  python brief_generator.py
"""

import os
import sys
import re
import anthropic
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Optional: richer news context. Install with: pip install duckduckgo-search
try:
    from duckduckgo_search import DDGS
    HAS_SEARCH = True
except ImportError:
    HAS_SEARCH = False


def fetch_website(url):
    """Pull visible text from a company's homepage."""
    if not url:
        return ""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:4000]
    except Exception as e:
        return f"(Could not fetch website: {e})"


def fetch_news(company_name):
    """Pull recent news headlines about the company (requires duckduckgo-search)."""
    if not HAS_SEARCH:
        return ""
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.news(company_name, max_results=5):
                results.append(f"- {r['title']} ({r.get('date', 'recent')}): {r['body'][:200]}")
        return "\n".join(results) if results else ""
    except Exception:
        return ""


def _ddg_search(query, label, max_results=10):
    """Run a single DuckDuckGo text search and return a formatted findings string."""
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title   = r.get("title", "")
                snippet = r.get("body", "")[:220]
                url     = r.get("href", "")
                results.append(f"  • [{url}]\n    {title}\n    {snippet}")
        if results:
            return f"[{label} — {len(results)} result(s)]\n" + "\n".join(results)
        return f"[{label} — 0 results]"
    except Exception as e:
        return f"[{label} — failed: {e}]"


def _fetch_page_text(url, label, char_limit=3000):
    """Directly fetch a page and return its visible text (best-effort)."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return f"[{label} — HTTP {r.status_code}]"
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)[:char_limit]
        return f"[{label} — fetched successfully]\n{text}" if text else f"[{label} — empty page]"
    except Exception as e:
        return f"[{label} — fetch failed: {e}]"


def fetch_linkedin_sdr_signals(company_name):
    """
    Surface real SDR/BDR team signals using simple targeted searches + direct page fetches.

    Problem with previous approach: long OR-chains and site: restrictions cause DuckDuckGo
    to silently drop queries or return zero results. Fix: one concept per query, short and direct.

    Eight signal sources:
      1–2. Simple SDR/BDR title searches (no boolean complexity)
      3.   SDR leadership titles search
      4.   Hiring signals search
      5.   Alternative title search (ADR, MDR, ISR, inside sales)
      6.   Direct fetch of The Org page (real org chart data)
      7.   Direct fetch of Glassdoor people/reviews page
      8.   LinkedIn company people page (best-effort — often partial)
    """
    if not HAS_SEARCH:
        return ""

    slug = company_name.lower().replace(" ", "-").replace(".", "").replace(",", "")
    findings = []

    # ── Simple DuckDuckGo searches — one concept each ────────────────────────

    # 1. SDR title — bare and direct
    findings.append(_ddg_search(
        f'{company_name} "sales development representative"',
        "Search 1: SDR title"
    ))

    # 2. BDR title — separate query, not an OR chain
    findings.append(_ddg_search(
        f'{company_name} "business development representative"',
        "Search 2: BDR title"
    ))

    # 3. SDR/BDR leadership — short, one phrase at a time
    findings.append(_ddg_search(
        f'{company_name} "head of sales development" OR "VP of sales development" OR "director of sales development"',
        "Search 3: SDR leadership (Head / VP / Director)"
    ))
    findings.append(_ddg_search(
        f'{company_name} "SDR manager" OR "BDR manager" OR "sales development manager"',
        "Search 4: SDR manager titles"
    ))

    # 4. Hiring signals — simple job-board search
    findings.append(_ddg_search(
        f'{company_name} "sales development representative" jobs hiring',
        "Search 5: SDR hiring signals"
    ))

    # 5. Alternative outbound rep titles — one query per title family
    findings.append(_ddg_search(
        f'{company_name} "inside sales representative" OR "inside sales" OR "outbound sales representative"',
        "Search 6: Inside sales / outbound rep titles"
    ))
    findings.append(_ddg_search(
        f'{company_name} "account development representative" OR "market development representative"',
        "Search 7: ADR / MDR titles"
    ))

    # ── Direct page fetches — richer structured data ─────────────────────────

    # 6. The Org — has real org charts with headcounts and team breakdowns
    findings.append(_fetch_page_text(
        f"https://theorg.com/org/{slug}/teams/sales-development",
        "The Org — Sales Development team page"
    ))
    findings.append(_fetch_page_text(
        f"https://theorg.com/org/{slug}",
        "The Org — company overview page"
    ))

    # 7. Glassdoor jobs page for SDR roles at this company
    findings.append(_fetch_page_text(
        f"https://www.glassdoor.com/Jobs/{company_name.replace(' ', '-')}-Sales-Development-Representative-Jobs-E0.htm",
        "Glassdoor — SDR job listings"
    ))

    # 8. LinkedIn company people page (often partial but sometimes surfaces role data)
    findings.append(_fetch_page_text(
        f"https://www.linkedin.com/company/{slug}/people/",
        "LinkedIn — company people page (best-effort)"
    ))

    return "\n\n".join(f for f in findings if f) or "No SDR/BDR signals found."


def generate_brief(company_name, website_url, contact_name, contact_title):
    """Call Claude to generate the pre-call research brief."""
    website_content = fetch_website(website_url)
    news_content    = fetch_news(company_name)

    context_parts = []
    if website_content:
        context_parts.append(f"Website content:\n{website_content}")
    if news_content:
        context_parts.append(f"Recent news:\n{news_content}")
    context = "\n\n".join(context_parts) if context_parts else "No additional context available."

    prompt = f"""You are helping an Account Executive at Nooks prepare for a discovery call.

Nooks is an AI-powered sales assistant platform that helps B2B sales teams generate more pipeline from
outbound. It combines an AI parallel dialer, AI coaching assistant, and AI prospecting assistant into one
platform — helping SDR and BDR teams have more quality conversations, ramp faster, and hit quota.
Nooks customers typically see 2–3x pipeline per rep within days of adopting the platform.

Nooks sells to companies with dedicated SDR/BDR teams running high-volume outbound. The primary buyers
are VP of Sales, Head of Sales Development, CRO, and Revenue Operations leaders at B2B SaaS companies.

---
PROSPECT INFO:
Company:       {company_name}
Contact:       {contact_name or "Unknown"} — {contact_title or "Unknown title"}
---
CONTEXT:
{context}

---
Generate a tight, scannable pre-call research brief. Format it exactly like this:

## {company_name} — Pre-Call Brief

### What They Do
[2–3 sentences on the company's core business, go-to-market motion, and scale]

### Sales Team Signals
[Based on available signals, what does their outbound sales motion look like? Team size, SDR/BDR presence, tools they likely use (Outreach, Salesloft, Gong, ZoomInfo, etc.), hiring signals]

### Outbound Pain Points
[What pipeline generation and outbound challenges might a company like this face? Think: connect rates, rep ramp time, coaching at scale, tool sprawl, pipeline predictability]

### Nooks Fit
[How could Nooks specifically solve their problems — be concrete about the dialer, coaching, or prospecting angle]

### Tailored Discovery Questions
1. [Question]
2. [Question]
3. [Question]
4. [Question]
5. [Question]

### One-Line Opener
[A compelling, personalized opening line for the first 30 seconds of the call — sounds human, not scripted]

Keep the whole brief under 450 words. Make it something the AE can read in 90 seconds right before the call."""

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def generate_cold_emails(company_name, website_url, contact_name, contact_title, custom_notes):
    """Generate 3 cold email variations for a Nooks prospect."""
    website_content = fetch_website(website_url)
    news_content    = fetch_news(company_name)

    context_parts = []
    if website_content:
        context_parts.append(f"Website content:\n{website_content}")
    if news_content:
        context_parts.append(f"Recent news:\n{news_content}")
    if custom_notes:
        context_parts.append(f"Additional context from the rep:\n{custom_notes}")
    context = "\n\n".join(context_parts) if context_parts else "No additional context available."

    prompt = f"""You are helping an Account Executive at Nooks write cold outbound emails.

Nooks is an AI sales assistant platform that helps SDR and BDR teams generate more pipeline. It includes
an AI parallel dialer (2–3x more conversations per rep), an AI coaching assistant (faster ramp, better
conversion), and an AI prospecting assistant (less research time, higher intent outreach). Companies
switch to Nooks from fragmented stacks of dialers, sequencers, and coaching tools.

---
PROSPECT INFO:
Company:       {company_name}
Contact:       {contact_name or "Unknown"} — {contact_title or "Unknown title"}
---
CONTEXT:
{context}

---
Write 3 cold email variations. Each needs a subject line and a short body.

Format exactly like this:

---
**Variation 1: Direct**
**Subject:** [subject line]

[Body]

---
**Variation 2: Insight-Led**
**Subject:** [subject line]

[Body]

---
**Variation 3: Question-Based**
**Subject:** [subject line]

[Body]

---
Rules — follow every one of these:
- Each email must be under 100 words
- Use short paragraphs of 1 to 2 lines each
- Each email follows one simple structure: one observation about their sales team, one specific pain (low connect rates, rep ramp time, coaching at scale, pipeline unpredictability, or tool sprawl), one outcome Nooks delivers, one ask
- Never stack multiple features or products in the same email
- Use concrete, specific language. No "purpose-built", "robust", "seamlessly", or generic sales phrases
- Write like a peer who has seen this problem before at their scale, not like a salesperson pitching software
- No dashes used as punctuation. No overly polished transitions
- Sign off with: [Your name] at Nooks
- One CTA per email, kept light: "curious if you've run into this?" or "worth a quick call?" — never "book a demo"
- The tone should feel like it was written in 30 seconds, not edited for 30 minutes
"""

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def generate_crm_summary(call_notes, company_name, contact_name, contact_title, call_date):
    """Generate a CRM-ready call summary with standard fields and MEDDPICC scoring."""

    prompt = f"""You are helping an Account Executive at Nooks log a sales call in their CRM.

Nooks is an AI-powered sales assistant platform — AI parallel dialer, AI coaching assistant, and AI
prospecting assistant — for SDR and BDR teams at B2B SaaS companies.

---
CALL INFO:
Company:      {company_name or "Unknown"}
Contact:      {contact_name or "Unknown"} — {contact_title or "Unknown title"}
Date:         {call_date or "Unknown"}
---
CALL NOTES:
{call_notes}

---
Generate a structured CRM summary in two parts.

PART 1 — CALL SUMMARY (for the CRM notes field):

### Overview
[2–3 sentences capturing what was discussed and the outcome of the call]

### Pain Points
[Bullet list of specific pains the prospect mentioned — connect rates, ramp time, coaching gaps, tool sprawl, pipeline shortfalls, etc.]

### Objections
[Bullet list of objections raised, or "None raised" if none]

### Stakeholders Mentioned
[Name — Title — Role in deal, one per line. "None mentioned" if none]

### Next Steps
[Numbered list of agreed next steps with owners]

### Deal Stage
[Recommended CRM stage and one sentence of reasoning]

---

PART 2 — MEDDPICC SCORECARD:

**Metrics:** [What quantifiable outcomes did they mention? Pipeline per rep, connect rates, ramp time, quota attainment, number of conversations per day?]
**Economic Buyer:** [Who controls the budget? VP Sales, CRO, Head of SDR? Identified or unknown?]
**Decision Criteria:** [What will they use to evaluate solutions? Ease of use, dialer quality, AI accuracy, integration with their CRM/sequencer?]
**Decision Process:** [How will they decide? Timeline? Who else is involved? Is there a formal evaluation?]
**Paper Process:** [Any legal, procurement, or security review steps mentioned?]
**Identify Pain:** [What is the core business pain driving this evaluation? Low pipeline, poor rep productivity, high ramp time?]
**Champion:** [Is there an internal advocate pushing for this? Who?]
**Competition:** [Are they evaluating other tools? Outreach, Salesloft, Orum, Koncert, or other dialers mentioned?]

---
Rules:
- Be specific, not generic. Use exact words or numbers from the call notes where possible.
- If something wasn't mentioned, write "Not discussed" rather than guessing.
- Keep the tone professional and factual — this is going into a CRM, not a pitch deck.
- Total length should be under 450 words.
"""

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def generate_icp_score(company_name, website_url):
    """Research a company and score it against Nooks' ICP (1-4)."""
    website_content   = fetch_website(website_url)
    news_content      = fetch_news(company_name)
    linkedin_signals  = fetch_linkedin_sdr_signals(company_name)

    context_parts = []
    if website_content:
        context_parts.append(f"WEBSITE CONTENT:\n{website_content}")
    if news_content:
        context_parts.append(f"RECENT NEWS:\n{news_content}")
    if linkedin_signals:
        context_parts.append(f"LINKEDIN SDR/BDR SIGNALS (searched LinkedIn via DuckDuckGo):\n{linkedin_signals}")
    context = "\n\n".join(context_parts) if context_parts else "No additional context available."

    prompt = f"""You are a sales researcher helping Nooks' GTM team decide whether to pursue a prospect.

Nooks' Ideal Customer Profile (ICP):
- B2B companies with a dedicated SDR or BDR team running high-volume outbound
- Industries: B2B SaaS, fintech, cybersecurity, HR tech, MarTech, sales tech, healthcare tech, logistics tech
- Company stage: Series B and beyond, or established companies scaling their outbound sales motion
- Team signals: 5+ SDRs/BDRs, active hiring for SDR/BDR roles, SDR leader (Head of Sales Dev / VP Sales Dev) present
- Pain signals: low connect rates on outbound calls, long rep ramp times (90+ days), inconsistent coaching, relying on manual research, scattered tool stack (separate dialer + sequencer + coaching tool)
- Decision makers: VP of Sales, Head of Sales Development, CRO, Revenue Operations

NOT a good fit:
- Companies with no outbound motion (inbound-only or PLG-only)
- Very early-stage startups with no dedicated SDR team yet
- Companies without a phone-heavy sales motion (purely email or social)
- Non-B2B companies (B2C, consumer, retail)
- Very small teams (fewer than 3 SDRs) with no growth plans

---
COMPANY: {company_name}
WEBSITE: {website_url or "Not provided"}
---
CONTEXT:
{context}

---
HOW TO INTERPRET THE SDR/BDR SIGNALS:
Five searches were run — LinkedIn broad search, open-web mentions, leadership search, hiring signals,
and alternative title sweep (ADR, MDR, ISR, inside sales). Use these as your primary source of truth
for SDR/BDR team presence and size — they are more reliable than website copy.

Interpreting results:
- Each distinct profile or person mention typically represents one real team member.
  Estimate team size: 1–3 results = very small; 4–8 = small; 9–20 = mid-size; 20+ = large team.
- Mentions on Glassdoor, The Org, Crunchbase, or news articles confirm the team is real and visible.
- Any active job posting for an SDR/BDR/ADR/MDR role = strong growth signal, weight positively.
- Leadership results (VP/Director/Head/Manager of Sales Dev) = structured outbound org, weight strongly.
- Alternative titles (ADR, MDR, ISR, inside sales rep) count equally — they are the same role.
- If ALL five searches returned 0 results, treat SDR/BDR presence as Unknown or Weak.
- Do NOT let website copy override clear evidence from search results about team size or presence.

---
Research this company and produce an ICP scorecard. Format it exactly like this:

### ICP Score: [1, 2, 3, or 4] / 4

**[One-line verdict — e.g. "Strong fit — pursue now" or "Poor fit — deprioritize"]**

---

### Why This Score

[2–3 sentences explaining the reasoning. Be specific about signals found — especially what the LinkedIn data showed about their SDR/BDR team.]

---

### SDR / BDR Team Intelligence

- **Estimated SDR/BDR headcount:** [Best estimate from all search results — e.g. "~15 reps found across LinkedIn + Glassdoor" or "No individual reps found"]
- **Title variants found:** [List any non-standard titles surfaced — ADR, MDR, ISR, inside sales, etc.]
- **Leadership present:** [Yes / No / Unknown — name specific leaders found and their titles]
- **Active hiring:** [Yes / No — cite any specific job postings found]
- **Signal confidence:** [High / Medium / Low — based on how many of the 5 searches returned results]

---

### ICP Signal Breakdown

- **Outbound Sales Motion:** [Strong / Moderate / Weak / Unknown] — [one line explanation]
- **SDR / BDR Team Size:** [Strong / Moderate / Weak / Unknown] — [one line with the actual LinkedIn-derived estimate]
- **Industry Fit:** [Strong / Moderate / Weak / Unknown] — [one line explanation]
- **Company Stage & Growth:** [Strong / Moderate / Weak / Unknown] — [one line explanation]
- **Pain Signal Presence:** [Strong / Moderate / Weak / Unknown] — [one line explanation]

---

### Recommended Action

[One of these four, based on the score:]
- **Score 4:** Prioritize immediately. Add to active pipeline and reach out this week.
- **Score 3:** Worth pursuing. Research further and add to outbound sequence.
- **Score 2:** Possible fit. Monitor and revisit when you have more information.
- **Score 1:** Deprioritize. Move on — better opportunities exist.

---

Scoring guide:
- 4 = 4–5 strong ICP signals — clear fit, high priority
- 3 = 3 strong signals or 4–5 moderate ones — good fit, worth pursuing
- 2 = 1–2 strong signals or mixed signals — possible fit, needs qualification
- 1 = Few or no ICP signals — poor fit, not worth time right now

Be honest and precise. The LinkedIn data is ground truth for SDR team size — use it.
A bad lead wastes more time than no lead.
"""

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def parse_email_variations(emails_text):
    """Parse AI email output into a list of (title, subject, body) tuples."""
    variations = []
    chunks = re.split(r'\n?---\n?', emails_text)

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        lines = chunk.split('\n')
        title, subject, body_lines, found_subject = "", "", [], False

        for line in lines:
            clean = line.strip()
            if re.match(r'\*\*Variation \d+', clean):
                title = re.sub(r'\*\*', '', clean).strip()
            elif clean.startswith('**Subject:**'):
                subject = clean.replace('**Subject:**', '').strip()
                found_subject = True
            elif found_subject:
                body_lines.append(line)

        if title and subject:
            body = '\n'.join(body_lines).strip()
            body = re.sub(r'\n{3,}', '\n\n', body)
            variations.append((title, subject, body))

    return variations


def save_as_docx(brief_text, filepath):
    """Convert the markdown-style brief into a formatted Word document."""
    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    for line in brief_text.splitlines():
        line = line.strip()

        if line.startswith("## "):
            p = doc.add_heading(line[3:], level=1)
            p.runs[0].font.color.rgb = RGBColor(0x7C, 0x3A, 0xED)  # Nooks purple

        elif line.startswith("### "):
            doc.add_heading(line[4:], level=2)

        elif re.match(r"^\*(.+)\*$", line):
            p = doc.add_paragraph()
            run = p.add_run(re.match(r"^\*(.+)\*$", line).group(1))
            run.italic = True
            run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

        elif re.match(r"^\d+\.", line):
            p = doc.add_paragraph(style="List Bullet")
            p.style = doc.styles["Normal"]
            p.add_run(line)

        elif line == "" or line == "---":
            doc.add_paragraph("")

        else:
            doc.add_paragraph(line)

    doc.save(filepath)


def main():
    print("\n╔══════════════════════════════════════╗")
    print("║   Pre-Call Research Brief Generator  ║")
    print("╚══════════════════════════════════════╝\n")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY not set.")
        print("   Get your key at: https://console.anthropic.com")
        print("   Then run:  export ANTHROPIC_API_KEY=your_key_here\n")
        sys.exit(1)

    company_name  = input("Company name:   ").strip()
    if not company_name:
        print("Company name is required.")
        sys.exit(1)

    website_url   = input("Website URL:    ").strip()
    contact_name  = input("Contact name:   ").strip()
    contact_title = input("Contact title:  ").strip()

    print(f"\n⏳ Researching {company_name}...")
    if HAS_SEARCH:
        print("   → Fetching website & recent news...")
    else:
        print("   → Fetching website content...")
    print("   → Generating brief with Claude...\n")

    try:
        brief = generate_brief(company_name, website_url, contact_name, contact_title)
    except anthropic.AuthenticationError:
        print("❌ Invalid API key. Double-check your ANTHROPIC_API_KEY.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

    print("─" * 50)
    print(brief)
    print("─" * 50)

    desktop     = os.path.join(os.path.expanduser("~"), "Desktop")
    safe_name   = company_name.replace("/", "").strip()
    folder_path = os.path.join(desktop, safe_name)
    os.makedirs(folder_path, exist_ok=True)

    filename = os.path.join(folder_path, "brief.docx")
    save_as_docx(brief, filename)

    print(f"\n✅ Saved to Desktop → {safe_name} → brief.docx")
    print("   Open it in Word or drag it into Google Docs.\n")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
