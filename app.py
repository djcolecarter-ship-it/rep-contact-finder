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
st.caption("Real IAPD lookup + Claude AI web enrichment")

# ── Check for API key ───────────────────────────────────────────────────────
if "ANTHROPIC_API_KEY" not in st.secrets:
    st.warning("⚠️ Anthropic API key not found. Add it in Streamlit → Settings → Secrets as ANTHROPIC_API_KEY")
    api_key = None
else:
    api_key = st.secrets["ANTHROPIC_API_KEY"]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get_raw(crd):
    params = {"query": crd, "includePrevious": "true", "hl": "true", "nrows": "12", "start": "0", "r": "25", "sort": "score+desc", "wt": "json"}
    try:
        r = requests.get("https://api.adviserinfo.sec.gov/search/individual", params=params, headers=HEADERS, timeout=12)
        if r.status_code == 200:
            hits = r.json().get("hits", {}).get("hits", [])
            for hit in hits:
                src = hit.get("_source", {})
                if str(src.get("ind_source_id", "")) == str(crd):
                    return src
            if hits:
                return hits[0].get("_source", {})
    except:
        pass
    return None

def safe_list(val):
    return val if isinstance(val, list) else []

def build_card(src, crd):
    first = src.get("ind_firstname", "")
    middle = src.get("ind_middlename", "").strip()
    last = src.get("ind_lastname", "")
    name = " ".join(x for x in [first, middle, last] if x) or "Not found"

    firms = safe_list(src.get("ind_bc_current_employments")) or safe_list(src.get("ind_ia_current_employments"))
    current_firm = firms[0].get("firm_name", "N/A") if firms and isinstance(firms[0], dict) else "N/A"
    location = f"{firms[0].get('branch_city','')}, {firms[0].get('branch_state','')}" if firms and isinstance(firms[0], dict) else "N/A"

    # ←←← RESTORED REGISTRATION STATUS ←←←
    bc_scope = src.get("ind_bc_scope", "")
    ia_scope = src.get("ind_ia_scope", "")
    status = "✅ Active" if bc_scope == "Active" or ia_scope == "Active" else "⚠️ Not Active / Check BrokerCheck"

    bc_link = f"https://brokercheck.finra.org/individual/summary/{crd}"
    iapd_link = f"https://adviserinfo.sec.gov/individual/{crd}"
    linkedin_search = f"https://www.linkedin.com/search/results/people/?keywords={requests.utils.quote(name + ' ' + current_firm)}"

    return {
        "name": name, "crd": crd, "firm": current_firm, "location": location,
        "status": status,
        "bc_link": bc_link, "iapd_link": iapd_link, "linkedin_search": linkedin_search
    }

# ── Claude Enrichment (unchanged) ───────────────────────────────────────────
@st.cache_data(ttl=86400)
def enrich_with_claude(name, crd, firm, loc, api_key):
    if not api_key:
        return {"error": "No API key configured"}

    prompt = f"""You are a financial industry contact researcher. Search the web for this advisor:

Name: {name}
CRD: {crd}
Current Firm: {firm}
Location: {loc}

Find:
- Direct business phone
- Business email
- Direct LinkedIn profile URL
- Firm website URL
- Current title/role at the firm
- Any useful bio notes

Return ONLY valid JSON:
{{
  "phone": "value or null",
  "email": "value or null",
  "linkedin_direct": "full profile URL or null",
  "firm_website": "full firm website URL or null",
  "title": "value or null",
  "bio_notes": "1-2 sentence summary or null",
  "confidence": "High/Medium/Low",
  "sources_checked": ["list of domains"],
  "caveats": "brief note or null"
}}"""

    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    body = {"model": "claude-3-haiku-20240307", "max_tokens": 1024, "tools": [{"type": "web_search_20250305", "name": "web_search"}], "messages": [{"role": "user", "content": prompt}]}

    try:
        r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=60)
        if r.status_code != 200:
            return {"error": f"Claude API error {r.status_code}"}
        data = r.json()
        text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        if not text_blocks:
            return {"error": "No response from Claude"}
        parsed = json.loads(text_blocks[-1].strip()) if text_blocks[-1].strip().startswith("{") else json.loads(re.search(r'\{.*\}', text_blocks[-1], re.DOTALL).group())
        return parsed
    except Exception as e:
        return {"error": str(e)}

# ── UI ────────────────────────────────────────────────────────────────────────
with st.form("crd_form"):
    crd_input = st.text_input("CRD Number", placeholder="e.g. 2697880")
    col_a, col_b = st.columns(2)
    with col_a:
        submitted = st.form_submit_button("🔍 Look Up Contact", use_container_width=True, type="primary")
    with col_b:
        enrich = st.form_submit_button("🤖 Look Up + AI Enrich (find email/phone/website)", use_container_width=True)

if submitted or enrich:
    crd_clean = crd_input.strip()
    if not crd_clean.isdigit() or len(crd_clean) < 4:
        st.error("❌ Please enter a valid CRD number")
    else:
        with st.spinner("Searching SEC IAPD..."):
            src = get_raw(crd_clean)

        if not src:
            st.warning("No data found")
        else:
            result = build_card(src, crd_clean)
            st.success(f"✅ Found: **{result['name']}**")

            # Clean card with Active status restored
            st.markdown(f"""
            <div class='card'>
                <div class='field-label'>Full Name</div>
                <div class='field-value'>👤 {result['name']}</div>
                <div class='field-label'>CRD Number</div>
                <div class='field-value'>🔢 {result['crd']}</div>
                <div class='field-label'>Status</div>
                <div class='field-value'>{result['status']}</div>
                <div class='field-label'>Current Firm</div>
                <div class='field-value'>🏢 {result['firm']}</div>
                <div class='field-label'>Office Location</div>
                <div class='field-value'>📍 {result['location']}</div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.link_button("📋 BrokerCheck", result["bc_link"], use_container_width=True)
            with col2:
                st.link_button("🏛️ SEC IAPD", result["iapd_link"], use_container_width=True)
            with col3:
                st.link_button("🔗 LinkedIn Search", result["linkedin_search"], use_container_width=True)

            # AI Enrichment section (unchanged)
            if enrich:
                with st.spinner("🤖 Claude is searching the web for email, phone, firm website, and LinkedIn..."):
                    enriched = enrich_with_claude(result["name"], result["crd"], result["firm"], result["location"], api_key)

                if "error" in enriched:
                    st.error(f"Enrichment error: {enriched['error']}")
                else:
                    conf = enriched.get("confidence", "Low")
                    conf_class = {"High": "confidence-high", "Medium": "confidence-medium"}.get(conf, "confidence-low")

                    st.markdown(f"""
                    <div class='enrich-card'>
                        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;'>
                            <span style='color:#7ed87e;font-size:15px;font-weight:700;'>🤖 AI Enrichment Results</span>
                            <span class='{conf_class}'>Confidence: {conf}</span>
                        </div>
                        <div class='enrich-label'>Direct Phone</div>
                        <div class='enrich-value'>📞 {enriched.get('phone') or 'Not found'}</div>
                        <div class='enrich-label'>Business Email</div>
                        <div class='enrich-value'>📧 {enriched.get('email') or 'Not found'}</div>
                        <div class='enrich-label'>Title at Firm</div>
                        <div class='enrich-value'>💼 {enriched.get('title') or 'Not found'}</div>
                        <div class='enrich-label'>Firm Website</div>
                        <div class='enrich-value'>🌐 {enriched.get('firm_website') or 'Not found'}</div>
                        <div class='enrich-label'>Direct LinkedIn</div>
                        <div class='enrich-value'>🔗 {enriched.get('linkedin_direct') or 'Not found'}</div>
                        <div class='enrich-label'>Bio / Notes</div>
                        <div class='enrich-value'>📝 {enriched.get('bio_notes') or 'None found'}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    if enriched.get("firm_website"):
                        st.link_button("🌐 Visit Firm Website", enriched["firm_website"], use_container_width=True)
                    if enriched.get("linkedin_direct"):
                        st.link_button("🔗 Open Direct LinkedIn Profile", enriched["linkedin_direct"], use_container_width=True)

st.caption("Built for Thrivent wholesalers • Use responsibly per FINRA/CAN-SPAM rules")
