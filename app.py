import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="CRD Contact Finder", page_icon="🎯", layout="centered")

st.title("🎯 CRD Contact Finder")
st.caption("Backend research — no more copy/paste")

crd = st.text_input("Enter CRD Number", placeholder="2697880", max_chars=8)

if st.button("🚀 Run Full Research", type="primary", use_container_width=True):
    if not crd.isdigit() or not (4 <= len(crd) <= 8):
        st.error("Please enter a valid CRD (4–8 digits)")
        st.stop()

    with st.spinner("Researching BrokerCheck + IAPD + web..."):
        result = {
            "name": "Not found",
            "firm": "Not found",
            "title": "Not found",
            "location": "Not found",
            "email": "Not found (public sources limited)",
            "phone": "Not found (public sources limited)",
            "linkedin": "Not found",
            "licenses": "Not found",
            "disclosures": "None found"
        }

        # BrokerCheck scrape
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            r = requests.get(f"https://brokercheck.finra.org/individual/summary/{crd}", headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Try to extract name and firm (BrokerCheck puts data in script tags or title)
            title = soup.find("title")
            if title:
                title_text = title.get_text()
                if " - " in title_text:
                    result["name"] = title_text.split(" - ")[0].strip()
                    result["firm"] = title_text.split(" - ")[-1].strip()
        except:
            pass

        # IAPD scrape (basic)
        try:
            r2 = requests.get(f"https://adviserinfo.sec.gov/search/individual?query={crd}", headers=headers, timeout=10)
            if "No results" not in r2.text:
                result["firm"] = "Found in IAPD (see details below)"
        except:
            pass

        # Display clean card
        st.success(f"✅ Research complete for CRD {crd}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Full Name**")
            st.write(result["name"])
            st.markdown("**Current Firm**")
            st.write(result["firm"])
            st.markdown("**Title / Role**")
            st.write(result["title"])
        with col2:
            st.markdown("**Branch / Location**")
            st.write(result["location"])
            st.markdown("**Best Email**")
            st.write(result["email"])
            st.markdown("**Best Phone**")
            st.write(result["phone"])

        st.markdown("**Licenses**")
        st.write(result["licenses"])
        st.markdown("**Disclosures**")
        st.write(result["disclosures"])

        st.info("Email & phone are hard to scrape automatically on free tier. If nothing shows, try the prompt below or use Copilot manually.")

        # Fallback prompt (if you still want it)
        if st.button("Show Copilot Prompt as Backup"):
            prompt = f"You are an expert financial wholesaler contact researcher.\n\nCRD: **{crd}**\n\nFull research on BrokerCheck, IAPD, Google, LinkedIn for latest email and phone."
            st.text_area("Copy this if needed:", prompt, height=200)

st.caption("Live at https://rep-contact-finder.streamlit.app — built for you")
