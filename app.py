import streamlit as st
import requests

st.set_page_config(page_title="Rep Contact Finder", page_icon="🎯", layout="centered")

st.markdown("""
    <style>
    .card { background: #1e2a3a; border-radius: 12px; padding: 24px; margin-top: 16px; }
    .field-label { color: #7eb3d8; font-size: 13px; font-weight: 600; text-transform: uppercase; margin-bottom: 2px; }
    .field-value { color: #ffffff; font-size: 16px; margin-bottom: 14px; }
    .badge-green { background: #1a7a4a; color: white; padding: 2px 10px; border-radius: 20px; font-size: 12px; }
    .badge-red   { background: #8b1a1a; color: white; padding: 2px 10px; border-radius: 20px; font-size: 12px; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Rep Contact Finder")
st.caption("Type a CRD → get the full contact card instantly. No copy-paste. No Copilot needed.")

crd = st.text_input("CRD Number", placeholder="e.g. 2697880", max_chars=8)

def lookup_brokercheck(crd):
    """Hit the BrokerCheck public endpoint directly."""
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://brokercheck.finra.org/"
    }
    # Step 1: Get individual summary
    summary_url = f"https://api.brokercheck.finra.org/search/individual?query={crd}&hl=true&includePrevious=true&warnBcOnly=false&county=false&firm=false&co=false&nr=false&bd=false&ia=false&iap=false&iard=false&ria=false&riap=false&riard=false&sa=false&ft=false"
    r = requests.get(summary_url, headers=headers, timeout=10)
    r.raise_for_status()
    hits = r.json().get("hits", {}).get("hits", [])
    
    if not hits:
        return None

    src = hits[0].get("_source", {})

    # Step 2: Get detailed individual report
    ind_crd = src.get("ind_source_id", crd)
    detail_url = f"https://api.brokercheck.finra.org/individual/{ind_crd}?hl=true"
    r2 = requests.get(detail_url, headers=headers, timeout=10)
    detail = {}
    if r2.status_code == 200:
        detail = r2.json().get("hits", {}).get("hits", [{}])[0].get("_source", {})

    # Parse the data
    name = src.get("ind_firstname", "") + " " + src.get("ind_middlename", "").strip() + " " + src.get("ind_lastname", "")
    name = " ".join(name.split())

    firm = src.get("ind_bc_scope", [{}])
    current_firm = firm[0].get("firm_name", "N/A") if firm else "N/A"
    firm_crd = firm[0].get("firm_id", "N/A") if firm else "N/A"

    # Licenses
    exams = detail.get("examsInfo", {}).get("examsList", [])
    licenses = [e.get("examName", "") for e in exams if e.get("examCategory") in ["S", "PE"]]
    licenses_str = ", ".join(licenses[:5]) if licenses else "Not found"

    # Registrations / States
    regs = detail.get("registrationInfo", {}).get("stateRegistrations", [])
    states = list(set([r.get("state", "") for r in regs]))[:6]
    states_str = ", ".join(sorted(states)) if states else "N/A"

    # Disclosures
    disc_count = src.get("ind_bc_disclosure_fl", "N")
    disclosures = "⚠️ YES — check BrokerCheck" if disc_count == "Y" else "✅ None"

    # Years in industry
    years = src.get("ind_years_in_industry", "N/A")

    # Office address
    office_info = firm[0] if firm else {}
    city = office_info.get("firm_ia_city", office_info.get("firm_bc_city", ""))
    state_loc = office_info.get("firm_ia_state", office_info.get("firm_bc_state", ""))
    location = f"{city}, {state_loc}".strip(", ") or "N/A"

    # BrokerCheck link
    bc_link = f"https://brokercheck.finra.org/individual/summary/{ind_crd}"

    # LinkedIn search link
    linkedin_link = f"https://www.linkedin.com/search/results/people/?keywords={requests.utils.quote(name + ' ' + current_firm)}"

    return {
        "name": name,
        "crd": ind_crd,
        "firm": current_firm,
        "firm_crd": firm_crd,
        "location": location,
        "licenses": licenses_str,
        "states": states_str,
        "disclosures": disclosures,
        "years": years,
        "bc_link": bc_link,
        "linkedin_link": linkedin_link,
    }

if st.button("🔍 Look Up Contact", type="primary", use_container_width=True):
    if not crd or not crd.isdigit():
        st.error("Please enter a valid numeric CRD number.")
    else:
        with st.spinner("Pulling data from BrokerCheck..."):
            try:
                data = lookup_brokercheck(crd)
                if not data:
                    st.warning("No results found for that CRD. Double-check the number.")
                else:
                    st.success(f"✅ Found: {data['name']}")
                    st.markdown(f"""
                    <div class='card'>
                        <div class='field-label'>Full Name</div>
                        <div class='field-value'>👤 {data['name']}</div>

                        <div class='field-label'>CRD Number</div>
                        <div class='field-value'>🔢 {data['crd']}</div>

                        <div class='field-label'>Current Firm</div>
                        <div class='field-value'>🏢 {data['firm']} &nbsp;<span style='color:#888; font-size:13px'>(Firm CRD: {data['firm_crd']})</span></div>

                        <div class='field-label'>Office Location</div>
                        <div class='field-value'>📍 {data['location']}</div>

                        <div class='field-label'>Licenses</div>
                        <div class='field-value'>📜 {data['licenses']}</div>

                        <div class='field-label'>Registered States</div>
                        <div class='field-value'>🗺️ {data['states']}</div>

                        <div class='field-label'>Years in Industry</div>
                        <div class='field-value'>📅 {data['years']} years</div>

                        <div class='field-label'>Disclosures</div>
                        <div class='field-value'>{data['disclosures']}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.link_button("📋 Full BrokerCheck Report", data['bc_link'], use_container_width=True)
                    with col2:
                        st.link_button("🔗 Search on LinkedIn", data['linkedin_link'], use_container_width=True)

            except requests.exceptions.RequestException as e:
                st.error(f"Network error: {e}")
            except Exception as e:
                st.error(f"Something went wrong: {e}")

st.divider()
st.caption("Data pulled live from FINRA BrokerCheck public API · Built for Thrivent wholesalers")
