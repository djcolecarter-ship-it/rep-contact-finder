import re
import json
import requests
import streamlit as st

# ── Helpers ────────────────────────────────────────────────────────────────

def extract_json(text):
    """Safely extract JSON from Claude response"""
    try:
        return json.loads(text)
    except:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    return {"error": "Failed to parse JSON"}

def is_valid_email(email):
    if not email:
        return False
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)

def clean_phone(phone):
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 10:
        return phone
    return None

# ── Enrichment ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400)
def enrich_with_claude(result: dict, api_key: str) -> dict:
    """
    Safer enrichment without web_search.
    Claude uses general knowledge + inference (lower reliability but stable).
    """

    name = result["name"]
    firm = result["firm"]
    loc  = result["location"]
    crd  = result["crd"]

    prompt = f"""
You are a financial sales intelligence assistant.

Given:
Name: {name}
CRD: {crd}
Firm: {firm}
Location: {loc}

Task:
Provide BEST-EFFORT publicly known professional contact details.
DO NOT guess or hallucinate.

Return ONLY valid JSON:

{{
  "phone": "value or null",
  "email": "value or null",
  "linkedin_direct": "full URL or null",
  "title": "value or null",
  "bio_notes": "short summary or null",
  "confidence": "High or Medium or Low",
  "sources_checked": [],
  "caveats": "explain limitations briefly"
}}

Rules:
- If unsure → return null
- Prefer firm-level contact over personal guess
- Confidence:
  High = multiple strong signals
  Medium = partial info
  Low = mostly unknown
"""

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    body = {
        "model": "claude-3-5-sonnet-latest",
        "max_tokens": 400,
        "temperature": 0,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=body,
            timeout=30
        )

        if r.status_code != 200:
            return {"error": f"Claude API error {r.status_code}: {r.text[:200]}"}

        data = r.json()

        text_blocks = [
            b["text"] for b in data.get("content", [])
            if b.get("type") == "text"
        ]

        if not text_blocks:
            return {"error": "No text returned from Claude"}

        raw_text = text_blocks[-1].strip()

        parsed = extract_json(raw_text)

        if "error" in parsed:
            return parsed

        # ── Validation Layer ──
        email = parsed.get("email")
        phone = parsed.get("phone")

        if email and not is_valid_email(email):
            email = None

        phone = clean_phone(phone)

        return {
            "phone": phone,
            "email": email,
            "linkedin_direct": parsed.get("linkedin_direct"),
            "title": parsed.get("title"),
            "bio_notes": parsed.get("bio_notes"),
            "confidence": parsed.get("confidence", "Low"),
            "sources_checked": parsed.get("sources_checked", []),
            "caveats": parsed.get("caveats", "AI-generated; verify before use")
        }

    except Exception as e:
        return {"error": f"Enrichment failed: {str(e)}"}
