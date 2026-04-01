#!/usr/bin/env python3
"""
Extract structured agenda/topic data from cabinet meeting briefing HTML files.
"""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

# Input and output paths
BRIEFING_DIR = Path("/sessions/stoic-cool-dirac/cabinet-deploy")
BRIEFING_FILES = [
    "cabinet_meeting_4_briefing.html",
    "cabinet_meeting_5_briefing.html",
    "cabinet_meeting_6_briefing.html",
    "cabinet_meeting_8_briefing.html",
    "cabinet_meeting_9_briefing.html",
    "cabinet_meeting_10_briefing.html",
    "cabinet_meeting_11_briefing.html",
    "cabinet_meeting_13_briefing.html",
]
OUTPUT_DIR = BRIEFING_DIR / "data"
OUTPUT_FILE = OUTPUT_DIR / "briefings.json"

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)


def extract_meeting_metadata(soup):
    """Extract meeting number and date from title tag."""
    title = soup.find("title")
    if not title:
        return None, None

    title_text = title.string
    # Format: "제5회 국무회의 브리핑 (2026-02-10)"
    match = re.search(r"제(\d+)회.*?\((\d{4}-\d{2}-\d{2})\)", title_text)
    if match:
        meeting_num = int(match.group(1))
        date = match.group(2)
        return meeting_num, date
    return None, None


def extract_summary_bullets(summary_div):
    """Extract bullet points from summary div."""
    if not summary_div:
        return []

    bullets = []
    ul = summary_div.find("ul")
    if ul:
        for li in ul.find_all("li"):
            text = li.get_text(strip=True)
            if text:
                bullets.append(text)
    else:
        # If no ul, get text content directly
        text = summary_div.get_text(strip=True)
        if text:
            bullets.append(text)

    return bullets


def extract_exchanges(topic_div):
    """Extract president and response exchanges."""
    exchanges = []
    exchanges_div = topic_div.find("div", class_="exchanges")
    if not exchanges_div:
        return exchanges

    # Find all exchange pairs (president + response)
    current_pres = None
    ex_divs = exchanges_div.find_all("div", class_="exchange")

    for ex_div in ex_divs:
        ex_pres = ex_div.find("div", class_="ex-pres")
        ex_resp = ex_div.find("div", class_="ex-resp")

        if ex_pres:
            # President statement
            text = ex_pres.get_text(strip=True)
            # Remove role label if present
            text = re.sub(r"대통령|국무총리|장관|청장", "", text, count=1).strip()
            current_pres = text

        if ex_resp and current_pres:
            # Response statement
            resp_text = ex_resp.get_text(strip=True)
            # Extract department from role tag
            role = ex_resp.find("span", class_="role")
            dept = role.get_text(strip=True) if role else "미기재"

            exchanges.append({
                "president": current_pres,
                "dept": dept,
                "response": resp_text
            })
            current_pres = None
        elif ex_resp and not current_pres:
            # Standalone response (no matching president statement yet)
            resp_text = ex_resp.get_text(strip=True)
            role = ex_resp.find("span", class_="role")
            dept = role.get_text(strip=True) if role else "미기재"

            exchanges.append({
                "president": "",
                "dept": dept,
                "response": resp_text
            })

    return exchanges


def extract_actions(topic_div):
    """Extract action items with department names."""
    actions = []
    actions_div = topic_div.find("div", class_="actions")
    if not actions_div:
        return actions

    ul = actions_div.find("ul")
    if ul:
        for li in ul.find_all("li"):
            # Extract department (in strong tag) and description
            strong = li.find("strong")
            if strong:
                dept = strong.get_text(strip=True)
                # Get remaining text after strong tag
                remaining = li.get_text(strip=True)
                remaining = remaining.replace(dept, "", 1).strip()
                actions.append({
                    "dept": dept,
                    "desc": remaining
                })
            else:
                # No strong tag, treat whole text as description
                text = li.get_text(strip=True)
                if text:
                    actions.append({
                        "dept": "미기재",
                        "desc": text
                    })

    return actions


def extract_topics(soup):
    """Extract all topics from a briefing HTML."""
    topics = []
    topic_divs = soup.find_all("div", class_="topic")

    for topic_div in topic_divs:
        # Extract ID
        topic_id = topic_div.get("id", "")

        # Extract title
        h3 = topic_div.find("h3")
        title = h3.get_text(strip=True) if h3 else ""

        # Extract summary
        summary_div = topic_div.find("div", class_="summary")
        summary = extract_summary_bullets(summary_div)

        # Extract exchanges
        exchanges = extract_exchanges(topic_div)

        # Extract actions
        actions = extract_actions(topic_div)

        topics.append({
            "id": topic_id,
            "title": title,
            "summary": summary,
            "exchanges": exchanges,
            "actions": actions
        })

    return topics


def process_file(file_path):
    """Process a single HTML briefing file."""
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    meeting_num, date = extract_meeting_metadata(soup)
    if not meeting_num or not date:
        print(f"Warning: Could not extract metadata from {file_path.name}")
        return None

    topics = extract_topics(soup)

    # Create meeting record
    meeting_record = {
        "meeting": meeting_num,
        "date": date,
        "topics": topics
    }

    return meeting_record


def main():
    """Main extraction function."""
    all_briefings = []

    # Process each briefing file
    for filename in BRIEFING_FILES:
        file_path = BRIEFING_DIR / filename
        if not file_path.exists():
            print(f"Warning: {filename} not found")
            continue

        print(f"Processing {filename}...")
        record = process_file(file_path)
        if record:
            all_briefings.append(record)

    # Sort by meeting number
    all_briefings.sort(key=lambda x: x["meeting"])

    # Flatten structure: merge topics with meeting metadata
    flattened = []
    for meeting in all_briefings:
        for topic in meeting["topics"]:
            flattened.append({
                "meeting": meeting["meeting"],
                "date": meeting["date"],
                "id": topic["id"],
                "title": topic["title"],
                "summary": topic["summary"],
                "exchanges": topic["exchanges"],
                "actions": topic["actions"]
            })

    # Write output JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(flattened, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Extraction complete!")
    print(f"✓ Output written to: {OUTPUT_FILE}")

    # Print summary
    print(f"\n=== SUMMARY ===")
    print(f"Total meetings: {len(all_briefings)}")
    for meeting in all_briefings:
        topic_count = len(meeting["topics"])
        print(f"  Meeting {meeting['meeting']} ({meeting['date']}): {topic_count} topics")
    print(f"Total topics extracted: {len(flattened)}")


if __name__ == "__main__":
    main()
