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
st.caption("Type a CRD → get the full contact card instantly.")

# ── Input form (Enter key triggers search too) ─────────────────────────────
with st.form("crd_form"):
    crd = st.text_input("CRD Number", placeholder="e.g. 2697880")
    submitted = st.form_submit_button("🔍 Look Up Contact", use_container_width=True, type="primary")

# ── Lookup Functions ────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
}

def try_iapd(crd):
    endpoints = [
        f"https://api.adviserinfo.sec.gov/api/individual/individual?crd={crd}",
        f"https://api.adviserinfo.sec.gov/api/individual/search?query={crd}&hl=true",
    ]
    for url in endpoints:
        try:
            r = requests.get(url, headers=HEADERS, timeout=12)
            if r.status_code == 200:
                hits = r.json().get("hits", {}).get("hits", [])
                if hits:
                    return hits[0].get("_source", {}), "iapd"
        except:
            continue
    return None, None

def try_finra(crd):
    """Try FINRA with full browser session simulation."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://brokercheck.finra.org",
        "Referer": "https://brokercheck.finra.org/",
    })
    try:
        session.get("https://brokercheck.finra.org/", timeout=8)
        r = session.get(
            f"https://api.brokercheck.finra.org/individual/{crd}",
            params={"hl": "true", "includePrevious": "true"},
            timeout=12
        )
        if r.status_code == 200:
            hits = r.json().get("hits", {}).get("hits", [])
            if hits:
                return hits[0].get("_source", {}), "finra"
    except:
        pass
    return None, None

def build_card(src, crd, source):
    """Parse whichever source returned data."""

    # Name
    first  = src.get("ind_firstname",  src.get("firstName",  ""))
    middle = src.get("ind_middlename", src.get("middleName", "")).strip()
    last   = src.get("ind_lastname",   src.get("lastName",   ""))
    name   = " ".join(filter(None, [first, middle, last])) or "Not found"

    # Firm
    for key in ["ind_bc_scope", "ind_ia_scope", "currentEmployments"]:
        firms = src.get(key, [])
        if firms:
            break
    current_firm = "N/A"
    firm_crd     = "N/A"
    city = state_loc = ""
    if firms:
        f = firms[0]
        current_firm = f.get("firm_name", f.get("firmName", "N/A"))
        firm_crd     = str(f.get("firm_id", f.get("firmCrdNumber", "N/A")))
        city         = f.get("firm_bc_city", f.get("firm_ia_city", f.get("city", "")))
        state_loc    = f.get("firm_bc_state", f.get("firm_ia_state", f.get("state", "")))

    location = ", ".join(filter(None, [city, state_loc])) or "N/A"

    # Licenses
    for key in ["ind_approved_finra_registration_list", "currentIaRegistrations"]:
        exams = src.get(key, [])
        if exams:
            break
    licenses = list(set([
        e.get("examName", e.get("regDesc", ""))
        for e in (exams or [])
        if e.get("examName", e.get("regDesc", ""))
    ]))[:6]
    licenses_str = ", ".join(licenses) if licenses else "See BrokerCheck"

    # States
    for key in ["ind_state_registration_list", "stateRegistrations"]:
        regs = src.get(key, [])
        if regs:
            break
    states = list(set([
        r.get("state", r.get("stateCode", ""))
        for r in (regs or [])
        if r.get("state", r.get("stateCode", ""))
