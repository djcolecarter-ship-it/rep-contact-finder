import streamlit as st
import requests
import json
import re

st.set_page_config(page_title="Rep Contact Finder", page_icon="🎯", layout="centered")

st.markdown("""
    <style>
    .card { background: #1e2a3a; border-radius: 12px; padding: 24px; margin-top: 16px; }
    .field-label { color: #7eb3d8; font-size: 13px; font-weight: 600; text-transform: uppercase; margin-bottom: 2px; }
    .field-value { color: #ffffff; font-size: 16px; margin-bottom: 14px; }
    .enrich-card { background: #1a2e1a; border: 1px solid #2d5a2d; border-radius: 12px; padding: 24px; margin-top: 16px; }
    .enrich-label { color: #7ed87e; font-size: 13px; font-weight: 600; text-transform: uppercase; margin-bottom: 2px; }
    .enrich-value { color: #ffffff; font-size: 15px; margin-bottom: 14px; }
    .confidence-high { color: #4caf50; font-weight: 600; }
    .confidence-medium { color: #ff9800; font-weight: 600; }
    .confidence-low { color: #f44336; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Rep Contact Finder")
st.caption("Type a CRD and press Enter or click Look Up. Optionally enrich with AI to find phone, email, and web notes.")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
}

# ── SEC IAPD ─────────────────────────────────────────────────────────────────

def get_raw(crd):
    params = {
        "query": crd,
        "includePrevious": "true",
        "hl": "true",
        "nrows": "12",
        "start": "0",
        "r": "25",
        "sort": "score+desc",
        "wt": "json",
    }
    try:
        r = requests.get(
            "https://api.adviserinfo.sec.gov/search/individual",
            params=params,
            headers=HEADERS,
            timeout=12
        )
        if r.status_code == 200:
            hits = r.json().get("hits", {}).get("hits", [])
            for hit in hits:
                src = hit.get("_source", {})
                if str(src.get("ind_source_id", "")) == str(crd):
                    return src
            if hits:
                return hits[0].get("_source", {})
    except Exception as e:
        st.error(f"Request error: {e}")
    return None

def safe_list(val):
    return val if isinstance(val, list) else []

def build_card(src, crd):
    first  = src.get("ind_firstname", "")
    middle = src.get("ind_middlename", "").strip()
    last   = src.get("ind_lastname", "")
    name   = " ".join(x for x in [first, middle, last] if x) or "Not found"

    firms = safe_list(src.get("ind_bc_current_employments"))
    if not firms:
        firms = safe_list(src.get("ind_ia_current_employments"))
    if not firms:
        firms = safe_list(src.get("ind_bc_scope"))

    current_firm = "N/A"
    firm_crd     = "N/A"
    city         = ""
    state_loc    = ""

    if firms and isinstance(firms[0], dict):
        f = firms[0]
        current_firm = f.get("firm_name", "N/A")
        firm_crd     = str(f.get("firm_id", "N/A"))
        city         = f.get("branch_city", f.get("firm_bc_city", f.get("firm_ia_city", "")))
        state_loc    = f.get("branch_state", f.get("firm_bc_state", f.get("firm_ia_state", "")))
    elif firms and isinstance(firms[0], str):
        current_firm = firms[0]

    location = ", ".join(x for x in [city, state_loc] if x) or "N/A"

    exams = safe_list(src.get("ind_approved_finra_registration_list"))
    lic_names = []
    for e in exams:
        n = e.get("examName", e.get("regDesc", ""))
        if n and n not in lic_names:
            lic_names.append(n)
    reg_count = src.get("ind_approved_finra_registration_count", 0)
    licenses_str = ", ".join(lic_names[:6]) if lic_names else (f"{reg_count} active registration(s)" if reg_count else "See BrokerCheck")

    regs = safe_list(src.get("ind_state_registration_list"))
    state_names = []
    for r in regs:
        s = r.get("state", r.get("stateCode", ""))
        if s and s not in state_names:
            state_names.append(s)
    states_str = ", ".join(sorted(state_names)[:8]) if state_names else "N/A"

    disc_bc = src.get("ind_bc_disclosure_fl", "N")
    disc_ia = src.get("ind_ia_disclosure_fl", "N")
    disc    = "Y" if "Y" in [disc_bc, disc_ia] else "N"
    disclosures = "⚠️ YES — review on BrokerCheck" if disc == "Y" else "✅ None reported"

    start_date = src.get("ind_industry_cal_date_iapd", src.get("ind_industry_cal_date", ""))
    years_str  = f"Since {start_date[:4]}" if start_date else "N/A"

    emp_count = src.get("ind_employments_count", "N/A")

    bc_scope = src.get("ind_bc_scope", "")
    ia_scope = src.get("ind_ia_scope", "")
    status = "✅ Active" if bc_scope == "Active" or ia_scope == "Active" else "⚠️ Not Active / Check BrokerCheck"

    bc_link       = f"https://brokercheck.finra.org/individual/summary/{crd}"
    iapd_link     = f"https://adviserinfo.sec.gov/individual/{crd}"
    li_query      = requests.utils.quote(name + " " + current_firm)
    linkedin_link = f"https://www.linkedin.com/search/results/people/?keywords={li_query}"

    return {
        "name": name, "crd": crd, "firm": current_firm, "firm_crd": firm_crd,
        "location": location, "licenses": licenses_str, "states": states_str,
        "disclosures": disclosures, "years": years_str, "emp_count": str(emp_count),
        "status": status,
        "bc_link": bc_link, "iapd_link": iapd_link, "linkedin_link": linkedin_link,
    }

# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_json(text):
    try:
        return json.loads(text)
    except:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    return {"error": "Failed to parse JSON from Claude response"}

def is_valid_email(email):
    if not email:
        return False
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))

def clean_phone(phone):
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    return phone if len(digits) >= 10 else None

# ── Claude Enrichment (with live web search) ──────────────────────────────────

@st.cache_data(ttl=86400)
def enrich_with_claude(name, crd, firm, loc, api_key):
    """
    Calls claude-sonnet-4-6 with web_search tool enabled.
    Searches live web for phone, email, title, bio notes, LinkedIn.
    Results cached 24hrs per CRD to save API cost.
    """

    prompt = f"""You are a financial industry contact researcher. Search the web to find current contact details for this registered financial advisor.

Name: {name}
CRD: {crd}
Current Firm: {firm}
Location: {loc}

Search for:
1. Their direct business phone number
2. Their business email address
3. Their direct LinkedIn profile URL (the actual profile, not a search)
4. Their title/role at the current firm
5. Any useful notes from their firm bio page (AUM, specialties, team name, client type)

Try these searches:
- "{name}" "{firm}" contact phone
- "{name}" "{firm}" email
- "{name}" financial advisor {loc}
- "{name}" site:[firm's likely website domain]

Return ONLY a valid JSON object with no extra text or markdown fences:

{{
  "phone": "value or null",
  "email": "value or null",
  "linkedin_direct": "full profile URL or null",
  "title": "value or null",
  "bio_notes": "1-2 sentence summary from bio or null",
  "confidence": "High or Medium or Low",
  "sources_checked": ["list of domains where you found info"],
  "caveats": "brief note on data quality or null"
}}

Rules:
- Never invent or guess contact info. Only return what you actually found on the web.
- confidence = High if phone+email both confirmed, Medium if one found, Low if neither found.
- If you find conflicting info across sources, use the most recent and note it in caveats."""

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    body = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1024,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=body,
            timeout=60,
        )

        if r.status_code != 200:
            return {"error": f"Claude API error {r.status_code}: {r.text[:300]}"}

        data = r.json()

        # Get the last text block (after any tool use rounds)
        text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        if not text_blocks:
            return {"error": "No text response returned from Claude."}

        parsed = extract_json(text_blocks[-1].strip())

        if "error" in parsed:
            return parsed

        # Validate fields
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
            "caveats": parsed.get("caveats", "Verify before use"),
        }

    except Exception as e:
        return {"error": f"Enrichment failed: {str(e)}"}

# ── UI ────────────────────────────────────────────────────────────────────────

api_key = st.secrets["ANTHROPIC_API_KEY"]

with st.form("crd_form"):
    crd_input = st.text_input("CRD Number", placeholder="e.g. 2697880")
    col_a, col_b = st.columns(2)
    with col_a:
        submitted = st.form_submit_button("🔍 Look Up Contact", use_container_width=True, type="primary")
    with col_b:
        enrich = st.form_submit_button("🤖 Look Up + AI Enrich", use_container_width=True)

if submitted or enrich:
    crd_clean = crd_input.strip()
    if not crd_clean.isdigit() or len(crd_clean) < 4:
        st.error("❌ Please enter a valid CRD number (digits only, at least 4 digits).")
    else:
        with st.spinner("🔄 Searching SEC IAPD..."):
            src = get_raw(crd_clean)

        if not src:
            st.warning("⚠️ No data found. Try manually:")
            col1, col2 = st.columns(2)
            with col1:
                st.link_button("📋 BrokerCheck", f"https://brokercheck.finra.org/individual/summary/{crd_clean}", use_container_width=True)
            with col2:
                st.link_button("🏛️ SEC IAPD", f"https://adviserinfo.sec.gov/individual/{crd_clean}", use_container_width=True)
        else:
            result = build_card(src, crd_clean)
            st.success(f"✅ Found: **{result['name']}**")

            st.markdown(f"""
            <div class='card'>
                <div class='field-label'>Full Name</div>
                <div class='field-value'>👤 {result['name']}</div>
                <div class='field-label'>CRD Number</div>
                <div class='field-value'>🔢 {result['crd']}</div>
                <div class='field-label'>Status</div>
                <div class='field-value'>{result['status']}</div>
                <div class='field-label'>Current Firm</div>
                <div class='field-value'>🏢 {result['firm']} <span style='color:#aaa;font-size:13px'>(Firm CRD: {result['firm_crd']})</span></div>
                <div class='field-label'>Office Location</div>
                <div class='field-value'>📍 {result['location']}</div>
                <div class='field-label'>Licenses / Registrations</div>
                <div class='field-value'>📜 {result['licenses']}</div>
                <div class='field-label'>Registered States</div>
                <div class='field-value'>🗺️ {result['states']}</div>
                <div class='field-label'>Industry Start Year</div>
                <div class='field-value'>📅 {result['years']}</div>
                <div class='field-label'>Total Firms (Career)</div>
                <div class='field-value'>🏦 {result['emp_count']}</div>
                <div class='field-label'>Disclosures</div>
                <div class='field-value'>{result['disclosures']}</div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.link_button("📋 BrokerCheck", result["bc_link"], use_container_width=True)
            with col2:
                st.link_button("🏛️ SEC IAPD", result["iapd_link"], use_container_width=True)
            with col3:
                st.link_button("🔗 LinkedIn Search", result["linkedin_link"], use_container_width=True)

            # ── AI Enrichment ──
            if enrich:
                with st.spinner("🤖 Claude is searching the web for phone, email, and bio notes... (15–40 sec)"):
                    enriched = enrich_with_claude(
                        result["name"], result["crd"],
                        result["firm"], result["location"],
                        api_key
                    )

                if "error" in enriched:
                    st.error(f"Enrichment error: {enriched['error']}")
                else:
                    conf = enriched.get("confidence", "Low")
                    conf_class = {"High": "confidence-high", "Medium": "confidence-medium"}.get(conf, "confidence-low")

                    phone      = enriched.get("phone") or "Not found"
                    email      = enriched.get("email") or "Not found"
                    title      = enriched.get("title") or "Not found"
                    bio_notes  = enriched.get("bio_notes") or "None found"
                    sources    = ", ".join(enriched.get("sources_checked", [])) or "None"
                    caveats    = enriched.get("caveats") or "None"

                    st.markdown(f"""
                    <div class='enrich-card'>
                        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;'>
                            <span style='color:#7ed87e;font-size:15px;font-weight:700;'>🤖 AI Enrichment Results</span>
                            <span class='{conf_class}'>Confidence: {conf}</span>
                        </div>
                        <div class='enrich-label'>Direct Phone</div>
                        <div class='enrich-value'>📞 {phone}</div>
                        <div class='enrich-label'>Business Email</div>
                        <div class='enrich-value'>📧 {email}</div>
                        <div class='enrich-label'>Title at Current Firm</div>
                        <div class='enrich-value'>💼 {title}</div>
                        <div class='enrich-label'>Bio / Notes</div>
                        <div class='enrich-value'>📝 {bio_notes}</div>
                        <div class='enrich-label'>Sources Checked</div>
                        <div class='enrich-value' style='font-size:13px;color:#aaa;'>🔗 {sources}</div>
                        <div class='enrich-label'>Caveats</div>
                        <div class='enrich-value' style='font-size:13px;color:#ffcc80;'>⚠️ {caveats}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    if enriched.get("linkedin_direct"):
                        st.link_button("🔗 Direct LinkedIn Profile", enriched["linkedin_direct"], use_container_width=True)

st.divider()
st.caption("Data sourced from SEC IAPD · AI enrichment via Anthropic Claude with web search · Built for Thrivent wholesalers · Use contact data in accordance with your firm's policies and FINRA/CAN-SPAM requirements.")
