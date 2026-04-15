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
st.caption("Type a CRD and press Enter or click Look Up.")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
}

def get_raw(crd):
    """
    Correct working endpoint confirmed via SEC IAPD / Stack Overflow.
    Searches by CRD number using ind_source_id match.
    """
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
            # Match exactly by CRD (ind_source_id)
            for hit in hits:
                src = hit.get("_source", {})
                if str(src.get("ind_source_id", "")) == str(crd):
                    return src
            # If no exact match, return first result
            if hits:
                return hits[0].get("_source", {})
    except Exception as e:
        st.error(f"Request error: {e}")
    return None

def safe_list(val):
    return val if isinstance(val, list) else []

def build_card(src, crd):
    # Name
    first  = src.get("ind_firstname", "")
    middle = src.get("ind_middlename", "").strip()
    last   = src.get("ind_lastname", "")
    name   = " ".join(x for x in [first, middle, last] if x) or "Not found"

    # Firm — try broker-dealer scope first, then IA scope
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

    # Licenses
    exams = safe_list(src.get("ind_approved_finra_registration_list"))
    lic_names = []
    for e in exams:
        n = e.get("examName", e.get("regDesc", ""))
        if n and n not in lic_names:
            lic_names.append(n)
    # Also check registration count as fallback info
    reg_count = src.get("ind_approved_finra_registration_count", 0)
    licenses_str = ", ".join(lic_names[:6]) if lic_names else (f"{reg_count} active registration(s) — see BrokerCheck" if reg_count else "See BrokerCheck")

    # Registered States
    regs = safe_list(src.get("ind_state_registration_list"))
    state_names = []
    for r in regs:
        s = r.get("state", r.get("stateCode", ""))
        if s and s not in state_names:
            state_names.append(s)
    states_str = ", ".join(sorted(state_names)[:8]) if state_names else "N/A"

    # Disclosures
    disc_bc = src.get("ind_bc_disclosure_fl", "N")
    disc_ia = src.get("ind_ia_disclosure_fl", "N")
    disc    = "Y" if "Y" in [disc_bc, disc_ia] else "N"
    disclosures = "⚠️ YES — review on BrokerCheck" if disc == "Y" else "✅ None reported"

    # Years / Start date
    start_date = src.get("ind_industry_cal_date_iapd", src.get("ind_industry_cal_date", ""))
    years_str  = f"Since {start_date[:4]}" if start_date else "N/A"

    # Employment count
    emp_count = src.get("ind_employments_count", "N/A")

    # Status
    bc_scope = src.get("ind_bc_scope", "")
    ia_scope = src.get("ind_ia_scope", "")
    if bc_scope == "Active" or ia_scope == "Active":
        status = "✅ Active"
    else:
        status = "⚠️ Not Active / Check BrokerCheck"

    # Links
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

# ── UI ──────────────────────────────────────────────────────────────────────

with st.form("crd_form"):
    crd_input = st.text_input("CRD Number", placeholder="e.g. 2697880")
    submitted = st.form_submit_button("🔍 Look Up Contact", use_container_width=True, type="primary")

if submitted:
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
                st.link_button("🔗 LinkedIn", result["linkedin_link"], use_container_width=True)

st.divider()
st.caption("Data sourced from SEC IAPD · Built for Thrivent wholesalers")
