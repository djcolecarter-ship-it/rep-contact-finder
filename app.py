import streamlit as st

st.set_page_config(page_title="CRD Contact Finder", page_icon="🎯", layout="centered")

st.title("🎯 CRD Contact Finder")
st.markdown("**Instant research prompt for Microsoft Copilot** — just for ETF & Fund wholesalers")

crd = st.text_input("Enter CRD Number", placeholder="2697880", max_chars=8)

if st.button("🚀 Generate Research Prompt", type="primary", use_container_width=True):
    if not crd.isdigit() or not (4 <= len(crd) <= 8):
        st.error("Please enter a valid CRD (4–8 digits only)")
    else:
        prompt = f"""You are an expert financial wholesaler contact researcher.

CRD: **{crd}**

1. Check BrokerCheck summary page for exact Full Name and Current Firm
2. Check SEC IAPD for title, branch, licenses
3. Search the open web for the most recent business email and phone

Return ONLY this format:

Full Name: 
CRD: {crd}
Current Firm: 
Title/Role: 
Branch/Office Location: 
Best Business Email: 
Email Confidence: XX% (brief reason)
Best Phone: 
Phone Confidence: XX% (brief reason)
LinkedIn URL: 
Licenses: 
Disclosures/Flags: (Yes/No + note)
Best Contact Method: (email / phone / LinkedIn)
Overall Confidence: High / Medium / Low
Sources: 
Notes / Caveats: 

Never invent info. If nothing found, say so clearly."""

        st.success(f"✅ Prompt ready for CRD {crd}")
        
        st.text_area("Copy this prompt into Microsoft Copilot:", prompt, height=400)
        
        st.code(prompt, language=None)
        
        if st.button("📋 Copy Prompt to Clipboard"):
            st.session_state.copied = prompt
            st.toast("✅ Copied to clipboard!", icon="📋")

st.caption("Built for work computer — open this link anywhere, no Python needed.")
