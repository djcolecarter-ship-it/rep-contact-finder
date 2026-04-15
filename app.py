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
    urls = [
        f"https://api.adviserinfo.sec.gov/api/individual/individual?crd={crd}",
        f"https://api.adviserinfo.sec.gov/api/individual/search?query={crd}&hl=true",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=12)
            if r.status_code == 200:
                hits = r.json().get("hits", {}).get("hits", [])
                if hits:
                    return hits[0].get("_source", {})
        except Exception:
            continue
    return None

def safe_list(val):
    if isinstance(val, list):
        return val
    return []

def build_card(src, crd):
    first  = src.get("ind_firstname",  src.get("firstName",  ""))
    middle = src.get("ind_middlename", src.get("middleName", "")).strip()
    last   = src.get("ind_lastname",   src.get("lastName",   ""))
    name   = " ".join(x for x in [first, middle, last] if x) or "Not found"

    firms = safe_list(src.get("ind_bc_scope")) or safe_list(src.get("ind_ia_scope")) or safe_list(src.get("currentEmployments"))
    current_firm = "N/A"
    firm_crd     = "N/A"
    city         = ""
    state_loc    = ""
    if firms:
        f            = firms[0]
        current_firm = f.get("firm_name", f.get("firmName", "N/A"))
        firm_crd     = str(f.get("firm_id", f.get("firmCrdNumber", "N/A")))
        city         = f.get("firm_bc_city", f.get("firm_ia_city", f.get("city", "")))
        state_loc    = f.get("firm_bc_state", f.get("firm_ia_state", f.get("state", "")))

    location = ", ".join(x for x in [city, state_loc] if x) or "N/A"

    exams = safe_list(src.get("ind_approved_finra_registration_list")) or safe_list(src.get("currentIaRegistrations"))
    lic_names = []
    for e in exams:
        n = e.get("examName", e.get("regDesc", ""))
        if n and n not in lic_names:
            lic_names.append(n)
    licenses_str = ", ".join(lic_names[:6]) if lic_names else "See BrokerCheck"

    regs = safe_list(src.get("ind_state_registration_list")) or safe_list(src.get("stateRegistrations"))
    state_names = []
    for r in regs:
        s = r.get("state", r.get("stateCode", ""))
        if s and s not in state_names:
            state_names.append(s)
    states_str = ", ".join(sorted(state_names)[:8]) if state_names else "N/A"

    disc = src.get("ind_bc_disclosure_fl", src.get("hasDisclosures", "N"))
    disclosures = "⚠️ YES — review on BrokerCheck" if disc in ["Y", True] else "✅ None reported"

    years = str(src.get("ind_years_in_industry", src.get("yearsInIndustry", "N/A")))

    bc_link       = f"https://brokercheck.finra.org/individual/summary/{crd}"
    iapd_link     = f"https://adviserinfo.sec.gov/individual/{crd}"
    li_query      = requests.utils.quote(name + " " + current_firm)
    linkedin_link = f"https://www.linkedin.com/search/results/people/?keywords={li_query}"

    return {
        "name": name, "crd": crd, "firm": current_firm, "firm_crd": firm_crd,
        "location": location, "licenses": licenses_str, "states": states_str,
        "disclosures": disclosures, "years": years,
        "bc_link": bc_link, "iapd_link": iapd_link, "linkedin_link": linkedin_link,
    }

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
            st.warning("⚠️ No data found for this CRD. Try the links below:")
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
                <div class='field-label'>Current Firm</div>
                <div class='field-value'>🏢 {result['firm']} <span style='color:#aaa;font-size:13px'>(Firm CRD: {result['firm_crd']})</span></div>
                <div class='field-label'>Office Location</div>
                <div class='field-value'>📍 {result['location']}</div>
                <div class='field-label'>Licenses / Registrations</div>
                <div class='field-value'>📜 {result['licenses']}</div>
                <div class='field-label'>Registered States</div>
                <div class='field-value'>🗺️ {result['states']}</div>
                <div class='field-label'>Years in Industry</div>
                <div class='field-value'>📅 {result['years']} years</div>
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
st.caption("Data sourced from SEC IAPD + FINRA BrokerCheck · Built for Thrivent wholesalers")
