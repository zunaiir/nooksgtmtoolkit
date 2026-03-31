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


def fetch_linkedin_sdr_signals(company_name):
    """
    Search LinkedIn via DuckDuckGo to surface real SDR/BDR team signals.
    Runs three targeted searches:
      1. LinkedIn profiles of current SDRs/BDRs at the company
      2. LinkedIn profiles of Sales Development leaders
      3. Open SDR/BDR job postings on LinkedIn
    Returns a structured summary of what was found.
    """
    if not HAS_SEARCH:
        return ""

    findings = []

    queries = [
        # Individual SDR/BDR profiles
        (
            f'site:linkedin.com/in "{company_name}" '
            f'"Sales Development Representative" OR "Business Development Representative" OR "SDR" OR "BDR"',
            "SDR/BDR profiles"
        ),
        # Sales Development leadership
        (
            f'site:linkedin.com/in "{company_name}" '
            f'"Head of Sales Development" OR "VP of Sales Development" OR "Director of Sales Development" '
            f'OR "Manager of Sales Development" OR "SDR Manager" OR "BDR Manager"',
            "SDR/BDR leadership"
        ),
        # Open job postings for SDRs/BDRs
        (
            f'site:linkedin.com/jobs "{company_name}" '
            f'"Sales Development Representative" OR "Business Development Representative" OR "SDR" OR "BDR"',
            "SDR/BDR job postings"
        ),
    ]

    for query, label in queries:
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=8):
                    title = r.get("title", "")
                    snippet = r.get("body", "")[:180]
                    url = r.get("href", "")
                    results.append(f"  • {title} — {snippet}")
            if results:
                findings.append(f"[{label} — {len(results)} result(s) found]\n" + "\n".join(results))
            else:
                findings.append(f"[{label} — 0 results found]")
        except Exception as e:
            findings.append(f"[{label} — search failed: {e}]")

    return "\n\n".join(findings) if findings else ""


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
HOW TO INTERPRET LINKEDIN SDR/BDR SIGNALS:
The LinkedIn data above was gathered by searching LinkedIn profiles and job postings via DuckDuckGo.
Use it as your primary source of truth for SDR/BDR team size — it is more reliable than website copy.

- Count how many distinct SDR/BDR profile results appear. Each result typically represents one real employee.
  Use this to estimate team size: 1–3 results = very small team; 4–8 = small team; 9–20 = mid-size; 20+ = large team.
- Job posting results indicate active hiring and growth intent — weight this positively.
- Leadership results (Head/VP/Director/Manager of Sales Dev) confirm a structured outbound org — weight this strongly.
- If LinkedIn searches returned 0 results for profiles AND 0 for job postings, treat SDR/BDR team presence as Unknown or Weak.
- Do NOT let the website or news content override clear LinkedIn evidence of a large or small SDR team.

---
Research this company and produce an ICP scorecard. Format it exactly like this:

### ICP Score: [1, 2, 3, or 4] / 4

**[One-line verdict — e.g. "Strong fit — pursue now" or "Poor fit — deprioritize"]**

---

### Why This Score

[2–3 sentences explaining the reasoning. Be specific about signals found — especially what the LinkedIn data showed about their SDR/BDR team.]

---

### SDR / BDR Team Intelligence

- **Estimated SDR/BDR headcount:** [Your best estimate based on LinkedIn profile results — e.g. "~12 profiles found" or "0 profiles found"]
- **Leadership present:** [Yes / No / Unknown — name any SDR/BDR leaders found]
- **Active hiring:** [Yes / No — based on job postings found]
- **LinkedIn confidence:** [High / Medium / Low — based on how many results were returned]

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
