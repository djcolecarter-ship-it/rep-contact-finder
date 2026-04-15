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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
}

def lookup_iapd(crd):
    """
    Primary: SEC IAPD individual lookup — works server-side, no auth required.
    """
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{crd}%22&dateRange=custom&startdt=2000-01-01&enddt=2099-01-01&forms=ADV"

    # Direct IAPD individual endpoint
    iapd_url = f"https://api.adviserinfo.sec.gov/api/individual/individual?crd={crd}"
    r = requests.get(iapd_url, headers=HEADERS, timeout=15)

    if r.status_code == 200:
        data = r.json()
        hits = data.get("hits", {}).get("hits", [])
        if hits:
            return parse_iapd(hits[0].get("_source", {}), crd)

    # Fallback: IAPD search endpoint
    search_url = f"https://api.adviserinfo.sec.gov/api/individual/search?query={crd}&hl=true"
    r2 = requests.get(search_url, headers=HEADERS, timeout=15)

    if r2.status_code == 200:
        data2 = r2.json()
        hits2 = data2.get("hits", {}).get("hits", [])
        if hits2:
            return parse_iapd(hits2[0].get("_source", {}), crd)

    return None, f"No results found via SEC IAPD for CRD {crd}"


def parse_iapd(src, crd):
    """Parse the SEC IAPD response into a clean contact card."""

    # Name
    first = src.get("ind_firstname", src.get("firstName", ""))
    middle = src.get("ind_middlename", src.get("middleName", "")).strip()
    last = src.get("ind_lastname", src.get("lastName", ""))
    name = " ".join(filter(None, [first, middle, last])) or "Not found"

    # Current firm
    firms = src.get("ind_ia_scope", src.get("currentEmployments", []))
    if isinstance(firms, list) and firms:
        current_firm = firms[0].get("firm_name", firms[0].get("firmName", "N/A"))
        firm_crd = firms[0].get("firm_id", firms[0].get("firmCrdNumber", "N/A"))
        city = firms[0].get("firm_ia_city", firms[0].get("city", ""))
        state_loc = firms[0].get("firm_ia_state", firms[0].get("state", ""))
    else:
        current_firm = "N/A"
        firm_crd = "N/A"
        city = ""
        state_loc = ""

