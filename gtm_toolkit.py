#!/usr/bin/env python3
"""
Nooks GTM Toolkit
Your personal AI-powered go-to-market assistant.

SETUP (one time):
  pip install -r requirements.txt
  Add your API key to ~/.zshrc:
    echo 'export ANTHROPIC_API_KEY=your_key_here' >> ~/.zshrc && source ~/.zshrc

USAGE:
  python3 gtm_toolkit.py
"""

import os
import sys


# ─── Helpers ──────────────────────────────────────────────────────────────────

def check_api_key():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n⚠️  ANTHROPIC_API_KEY not set.")
        print("   Get your key at: https://console.anthropic.com")
        print("   Then run: echo 'export ANTHROPIC_API_KEY=your_key' >> ~/.zshrc && source ~/.zshrc\n")
        sys.exit(1)

def print_header():
    print("\n╔══════════════════════════════════════╗")
    print("║         Nooks GTM Toolkit            ║")
    print("╚══════════════════════════════════════╝")

def print_menu():
    print("\nWhat would you like to do?\n")
    print("  1  →  Pre-Call Research Brief")
    print("  2  →  Personalized Cold Email Writer")
    print("  3  →  Call Notes → CRM Summary")
    print("  4  →  ICP Scorer")
    print()
    print("  q  →  Quit")
    print()


# ─── Tools ────────────────────────────────────────────────────────────────────

def run_brief_generator():
    """Run the pre-call research brief tool."""
    try:
        from brief_generator import generate_brief, save_as_docx
    except ImportError:
        print("\n❌ Could not find brief_generator.py — make sure it's in the same folder as this file.\n")
        return

    print("\n── Pre-Call Research Brief ──────────────────\n")

    company_name  = input("Company name:   ").strip()
    if not company_name:
        print("Company name is required.")
        return

    website_url   = input("Website URL:    ").strip()
    contact_name  = input("Contact name:   ").strip()
    contact_title = input("Contact title:  ").strip()

    print(f"\n⏳ Researching {company_name}...")
    print("   → Generating brief with Claude...\n")

    try:
        brief = generate_brief(company_name, website_url, contact_name, contact_title)
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return

    print("─" * 50)
    print(brief)
    print("─" * 50)

    desktop     = os.path.join(os.path.expanduser("~"), "Desktop")
    safe_name   = company_name.replace("/", "").strip()
    folder_path = os.path.join(desktop, safe_name)
    os.makedirs(folder_path, exist_ok=True)

    filepath = os.path.join(folder_path, "brief.docx")
    save_as_docx(brief, filepath)

    print(f"\n✅ Saved to Desktop → {safe_name} → brief.docx")
    print("   Open it in Word or drag it into Google Docs.\n")


def run_cold_email_writer():
    """Run the cold email writer tool."""
    try:
        from brief_generator import generate_cold_emails, parse_email_variations
    except ImportError:
        print("\n❌ Could not find brief_generator.py — make sure it's in the same folder as this file.\n")
        return

    print("\n── Cold Email Writer ──────────────────────────\n")

    company_name  = input("Company name:   ").strip()
    if not company_name:
        print("Company name is required.")
        return

    website_url   = input("Website URL:    ").strip()
    contact_name  = input("Contact name:   ").strip()
    contact_title = input("Contact title:  ").strip()
    custom_notes  = input("Additional context (optional): ").strip()

    print(f"\n⏳ Writing emails for {company_name}...\n")

    try:
        emails_raw = generate_cold_emails(company_name, website_url, contact_name, contact_title, custom_notes)
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return

    print("─" * 50)
    print(emails_raw)
    print("─" * 50 + "\n")


def run_crm_summary():
    """Run the call notes → CRM summary tool."""
    try:
        from brief_generator import generate_crm_summary
    except ImportError:
        print("\n❌ Could not find brief_generator.py — make sure it's in the same folder as this file.\n")
        return

    print("\n── Call Notes → CRM Summary ──────────────────\n")
    print("Paste your call notes below. Press Enter twice when done.\n")

    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)
    call_notes = "\n".join(lines).strip()

    if not call_notes:
        print("Call notes are required.")
        return

    company_name  = input("Company name:   ").strip()
    contact_name  = input("Contact name:   ").strip()
    contact_title = input("Contact title:  ").strip()
    call_date     = input("Call date:      ").strip()

    print("\n⏳ Generating CRM summary...\n")

    try:
        summary = generate_crm_summary(call_notes, company_name, contact_name, contact_title, call_date)
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return

    print("─" * 50)
    print(summary)
    print("─" * 50 + "\n")


def run_icp_scorer():
    """Run the ICP scorer tool."""
    try:
        from brief_generator import generate_icp_score
    except ImportError:
        print("\n❌ Could not find brief_generator.py — make sure it's in the same folder as this file.\n")
        return

    print("\n── ICP Scorer ─────────────────────────────────\n")

    company_name = input("Company name:   ").strip()
    if not company_name:
        print("Company name is required.")
        return

    website_url = input("Website URL:    ").strip()

    print(f"\n⏳ Researching {company_name}...\n")

    try:
        result = generate_icp_score(company_name, website_url)
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return

    print("─" * 50)
    print(result)
    print("─" * 50 + "\n")


# ─── Main loop ────────────────────────────────────────────────────────────────

def main():
    check_api_key()
    print_header()

    while True:
        print_menu()
        choice = input("Enter a number: ").strip().lower()

        if choice == "1":
            run_brief_generator()
        elif choice == "2":
            run_cold_email_writer()
        elif choice == "3":
            run_crm_summary()
        elif choice == "4":
            run_icp_scorer()
        elif choice in ("q", "quit", "exit"):
            print("\nGo generate some pipeline. 🔮\n")
            break
        else:
            print("\n  Please enter 1, 2, 3, 4, or q.\n")

        input("Press Enter to return to the menu...")
        print_header()


if __name__ == "__main__":
    main()
