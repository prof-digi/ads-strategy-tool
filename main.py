import streamlit as st
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# --- CONFIGURATION (Load from Streamlit Secrets or Environment Variables) ---
# In Streamlit Cloud, you set these in the Dashboard settings.
# Locally, you can set them in a .streamlit/secrets.toml file.
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]      # Your HostGator/Business Email
    EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]    # Your Email Password
    SMTP_SERVER = st.secrets["SMTP_SERVER"]          # e.g., mail.yourdomain.com
    SMTP_PORT = st.secrets.get("SMTP_PORT", 465)     # Usually 465 for SSL or 587 for TLS
    YOUR_ADMIN_EMAIL = "you@youragency.com"          # Where you receive the leads
except FileNotFoundError:
    st.error("Secrets not found. Please set up your .streamlit/secrets.toml file.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# --- FUNCTION 1: GENERATE STRATEGY WITH GEMINI ---
def generate_ppc_strategy(company_name, industry, goal, budget, competitor_url, problems):
    # You can keep your preferred model here
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    prompt = f"""
    Act as a Senior Google Ads Strategist.
    Create a tactical proposal for a UK-based client.
    
    ### CLIENT PROFILE
    - **Company:** {company_name}
    - **Industry:** {industry}
    - **Goal:** {goal}
    - **Budget:** £{budget}/month
    - **Current Pain Points:** {problems}
    - **Competitor:** {competitor_url}

    ### REQUIRED OUTPUT (Markdown):
    1. **Executive Summary**: 2 sentences on potential ROI given their budget of £{budget}.
    2. **Pain Point Analysis**: 
       - Address their specific problem ("{problems}") and explain exactly how to fix it.
    3. **Competitor Reconnaissance**: 
       - Analyze {competitor_url}. Identify 2 specific weaknesses.
    4. **Budget Split Table**: 
       - Exact breakdown of the £{budget} (e.g., Search vs. Retargeting). Use £ symbols.
    5. **Keyword Strategy**:
       - 10 High-Intent Keywords (relevant to the UK market).
       - 5 Negative Keywords to block.
    6. **Ad Copy Blueprint**:
       - 1 Responsive Search Ad (3 Headlines, 2 Descriptions).
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating strategy: {e}"
           
# --- FUNCTION 2: SEND EMAIL (Updated for HostGator TLS) ---
def send_email_report(user_email, strategy_text, company_name):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = user_email
    msg['Subject'] = f"🚀 Your Google Ads Strategy for {company_name}"

    # Email Body (HTML)
    body = f"""
    <h2>Your Custom Google Ads Roadmap is Ready</h2>
    <p>Hi there,</p>
    <p>Here is the strategy report we generated for <b>{company_name}</b>.</p>
    <hr>
    {strategy_text.replace(chr(10), '<br>')} 
    <hr>
    <p>Ready to implement this? Reply to this email to book a free 15-minute consultation.</p>
    """
    msg.attach(MIMEText(body, 'html'))

    try:
        # 1. Connect using Port 587 (Standard TLS)
        # Note: We use SMTP, not SMTP_SSL
        server = smtplib.SMTP(SMTP_SERVER, 587)
        
        # 2. Secure the connection
        server.starttls() 
        
        # 3. Login
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        
        # 4. Send to User
        server.sendmail(EMAIL_ADDRESS, user_email, msg.as_string())
        
        # 5. Send Copy to YOU
        admin_msg = MIMEMultipart()
        admin_msg['From'] = EMAIL_ADDRESS
        admin_msg['To'] = YOUR_ADMIN_EMAIL
        admin_msg['Subject'] = f"🔔 NEW LEAD: {company_name}"
        
        admin_body = f"New lead generated!\n\nEmail: {user_email}\nCompany: {company_name}\n\nReport:\n{strategy_text}"
        admin_msg.attach(MIMEText(admin_body, 'plain'))
        
        server.sendmail(EMAIL_ADDRESS, YOUR_ADMIN_EMAIL, admin_msg.as_string())
        
        server.quit()
        return True
        
    except Exception as e:
        # This will print the exact error to your app screen so we can see it
        st.error(f"❌ Email Failed. Error details: {e}")
        return False
        
# --- MAIN STREAMLIT UI ---
def main():
    st.set_page_config(page_title="Free Google Ads Strategy Generator", page_icon="🚀")

    st.markdown("""
    <style>
    .stButton>button {width: 100%; background-color: #FF4B4B; color: white;}
    </style>
    """, unsafe_allow_html=True)

    st.title("🚀 Free Google Ads Strategy Generator")
    st.markdown("Enter your business details below to get a **custom roadmap**, **competitor analysis**, and **budget plan**.")

    # Initialize Session State
    if 'step' not in st.session_state:
        st.session_state['step'] = 1
    if 'strategy_data' not in st.session_state:
        st.session_state['strategy_data'] = ""

    # --- STEP 1: COLLECT DATA ---
    if st.session_state['step'] == 1:
        with st.form("input_form"):
            col1, col2 = st.columns(2)
            with col1:
                company = st.text_input("Company Name")
                industry = st.text_input("Industry (e.g., Plumber)")
                competitor = st.text_input("Competitor URL")
            with col2:
                goal = st.selectbox("Primary Goal", ["Leads/Calls", "E-commerce Sales", "Brand Awareness"])
                # Changed currency to GBP (£)
                budget = st.number_input("Monthly Budget (£)", min_value=500, value=1500)

            # New Question Added Here
            problems = st.text_area("What are your biggest problems with Google Ads right now?", 
                                  placeholder="e.g. High cost per click, getting clicks but no sales, low quality leads...")

            submitted = st.form_submit_button("GENERATE MY STRATEGY")

            if submitted:
                if not company or not industry:
                    st.warning("Please fill in all required fields.")
                else:
                    with st.spinner("🕵️ Analyzing your specific challenges and generating roadmap..."):
                        # Updated to pass 'problems' to the function
                        strategy = generate_ppc_strategy(company, industry, goal, budget, competitor, problems)
                        
                        st.session_state['strategy_data'] = strategy
                        st.session_state['user_info'] = {'company': company, 'budget': budget}
                        st.session_state['step'] = 2
                        st.rerun()

    # --- STEP 2: THE TEASER & EMAIL GATE ---
    if st.session_state['step'] == 2:
        st.success("✅ Strategy Generated Successfully!")
        
        st.markdown(f"### 🔍 Analysis for {st.session_state['user_info']['company']}")
        st.info("We have analyzed your pain points and found a **Budget Efficiency Fix**.")
        
        st.markdown("---")
        st.markdown("### 🔒 Unlock Full Report")
        st.markdown("Enter your email to receive the full PDF report with Keyword Lists and Ad Copy.")

        with st.form("email_gate"):
            email = st.text_input("Your Email Address")
            unlock_btn = st.form_submit_button("SEND ME THE REPORT")
            
            if unlock_btn:
                if "@" not in email:
                    st.error("Please enter a valid email.")
                else:
                    with st.spinner("📧 Sending report to your inbox..."):
                        success = send_email_report(
                            email, 
                            st.session_state['strategy_data'], 
                            st.session_state['user_info']['company']
                        )
                        
                        if success:
                            st.session_state['step'] = 3
                            st.rerun()

    # --- STEP 3: SUCCESS & DISPLAY ---
    if st.session_state['step'] == 3:
        st.balloons()
        st.success("Report Sent! Check your inbox.")
        
        with st.expander("👀 View Report in Browser"):
            st.markdown(st.session_state['strategy_data'])
        
        if st.button("Start Over"):
            st.session_state['step'] = 1
            st.rerun()

if __name__ == "__main__":
    main()
