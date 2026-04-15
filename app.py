import streamlit as st
import requests

st.set_page_config(page_title="Rep Contact Finder", page_icon="🎯", layout="centered")

st.markdown("""
    <style>
    .card { background: #1e2a3a; border-radius: 12px; padding: 24px; margin-top: 16px; }
    .field-label { color: #7eb3d8; font-size: 13px; font-weight: 600; text-transform: uppercase; margin-bottom: 2px; }
    .field-value { color: #ffffff; font-size: 16px; margin-bottom: 14px; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Rep Contact Finder")
st.caption("Type a CRD → get the full contact card instantly. No copy-paste. No Copilot needed.")

crd = st.text_input("CRD Number", placeholder="e.g. 2697880", max_chars=8)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://brokercheck.finra.org",
    "Referer": "https://brokercheck.finra.org/",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
}

def lookup_by_crd(crd):
    """Direct CRD lookup using the correct BrokerCheck endpoint."""
    
    # Use a session to maintain cookies like a real browser
    session = requests.Session()
    
    # First, hit the main page to get cookies
    session.get("https://brokercheck.finra.org/", headers=HEADERS, timeout=10)
    
    # Now hit the correct individual detail endpoint directly by CRD
    url = f"https://api.brokercheck.finra.org/individual/{crd}"
    params = {
        "hl": "true",
        "includePrevious": "true",
        "nrows": "12",
        "start": "0",
        "r": "25",
        "warnBcOnly": "false"
    }
    
    r = session.get(url, headers=HEADERS, params=params, timeout=15)
    
    if r.status_code != 200:
        return None, f"HTTP {r.status_code} from BrokerCheck API"
    
    data = r.json()
    hits = data.get("hits", {}).get("hits", [])
    
    if not hits:
        return None, "No record found for this CRD"
    
    src = hits[0].get("_source", {})
    
    # --- Parse Name ---
    first = src.get("ind_firstname", "")
    middle = src.get("ind_middlename", "").strip()
    last = src.get("ind_lastname", "")
    name = " ".join(filter(None, [first, middle, last]))

    # --- Current Firm ---
    bc_scope = src.get("ind_bc_scope", [])
    ia_scope = src.get("ind_ia_scope", [])
    all_firms = bc_scope + ia_scope
    current_firm = all_firms[0].get("firm_name", "N/A") if all_firms else "N/A"
    firm_crd = all_firms[0].get("firm_id", "N/A") if all_firms else "N/A"

    # --- Location ---
    city = all_firms[0].get("firm_bc_city", all_firms[0].get("firm_ia_city", "")) if all_firms else ""
    state_loc = all_firms[0].get("firm_bc_state", all_firms[0].get("firm_ia_state", "")) if all_firms else ""
    location = ", ".join(filter(None, [city, state_loc])) or "N/A"

    # --- Licenses ---
    exams = src.get("ind_approved_finra_registration_list", [])
    licenses = list(set([e.get("examName", "") for e in exams if e.get("examName")])) if exams else []
    
    # Also check examsInfo
    exams2 = src.get("examsInfo", {}).get("examsList", []) if isinstance(src.get("examsInfo"), dict) else []
    licenses += [e.get("examName", "") for e in exams2 if e.get("examName")]
    licenses = list(set(filter(None, licenses)))[:6]
    licenses_str = ", ".join(licenses) if licenses else "Not found in summary"

    # --- Registered States ---
    regs = src.get("ind_state_registration_list", [])
    states = list(set([r.get("state", "") for r in regs if r.get("state")]))
    states_str = ", ".join(sorted(states)[:8]) if states else "N/A"

    # --- Disclosures ---
    disc_flag = src.get("ind_bc_disclosure_fl", "N")
    disclosures = "⚠️ YES — review on BrokerCheck" if disc_flag == "Y" else "✅ None reported"

    # --- Years ---
    years = src.get("ind_years_in_industry", "N/A")

    # --- Links ---
    bc_link = f"https://brokercheck.finra.org/individual/summary/{crd}"
    linkedin_search = f"https://www.linkedin.com/search/results/people/?keywords={requests.utils.quote(name + ' ' + current_firm)}"

    return {
        "name": name or "Not found",
        "crd": crd,
        "firm": current_firm,
        "firm_crd": firm_crd,
        "location": location,
        "licenses": licenses_str,
        "states": states_str,
        "disclosures": disclosures,
        "years": str(years),
        "bc_link": bc_link,
        "linkedin_link": linkedin_search,
    }, None


if st.button("🔍 Look Up Contact", type="primary", use_container_width=True):
    if not crd or not crd.strip().isdigit():
        st.error("Please enter a valid numeric CRD number.")
    else:
        with st.spinner("🔄 Pulling live data from FINRA BrokerCheck..."):
            try:
                result, error = lookup_by_crd(crd.strip())
                
                if error:
                    st.warning(f"⚠️ {error}")
                    st.info(f"👉 [Open BrokerCheck manually](https://brokercheck.finra.org/individual/summary/{crd})")
                elif result:
                    st.success(f"✅ Found: **{result['name']}**")
                    
                    st.markdown(f"""
                    <div class='card'>
                        <div class='field-label'>Full Name</div>
                        <div class='field-value'>👤 {result['name']}</div>

                        <div class='field-label'>CRD Number</div>
                        <div class='field-value'>🔢 {result['crd']}</div>

                        <div class='field-label'>Current Firm</div>
                        <div class='field-value'>🏢 {result['firm']} &nbsp;<span style='color:#aaa; font-size:13px'>(Firm CRD: {result['firm_crd']})</span></div>

                        <div class='field-label'>Office Location</div>
                        <div class='field-value'>📍 {result['location']}</div>

                        <div class='field-label'>Licenses</div>
                        <div class='field-value'>📜 {result['licenses']}</div>

                        <div class='field-label'>Registered States</div>
                        <div class='field-value'>🗺️ {result['states']}</div>

                        <div class='field-label'>Years in Industry</div>
                        <div class='field-value'>📅 {result['years']} years</div>

                        <div class='field-label'>Disclosures</div>
                        <div class='field-value'>{result['disclosures']}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.link_button("📋 Full BrokerCheck Report", result['bc_link'], use_container_width=True)
                    with col2:
                        st.link_button("🔗 Search LinkedIn", result['linkedin_link'], use_container_width=True)

            except requests.exceptions.Timeout:
                st.error("⏱️ Request timed out. BrokerCheck may be slow — try again.")
            except requests.exceptions.RequestException as e:
                st.error(f"🌐 Network error: {e}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {e}")
                st.code(str(e))

st.divider()
st.caption("Data pulled live from FINRA BrokerCheck · Built for Thrivent wholesalers")
