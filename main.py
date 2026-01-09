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
def generate_ppc_strategy(company_name, industry, goal, budget, competitor_url):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Act as a Senior Google Ads Strategist.
    Create a tactical proposal for a client.
    
    ### CLIENT PROFILE
    - **Company:** {company_name}
    - **Industry:** {industry}
    - **Goal:** {goal}
    - **Budget:** ${budget}/month
    - **Competitor:** {competitor_url}

    ### REQUIRED OUTPUT (Markdown):
    1. **Executive Summary**: 2 sentences on potential ROI.
    2. **Competitor Reconnaissance**: 
       - Analyze {competitor_url}. Identify 2 specific weaknesses in their likely digital strategy.
    3. **Budget Split Table**: 
       - Exact breakdown of the ${budget} (e.g., Search vs. Retargeting).
    4. **Keyword Strategy**:
       - 10 High-Intent Keywords.
       - 5 Negative Keywords to block.
    5. **Ad Copy Blueprint**:
       - 1 Responsive Search Ad (3 Headlines, 2 Descriptions) that directly counters the competitor's weakness.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating strategy: {e}"

# --- FUNCTION 2: SEND EMAIL (Via HostGator SMTP) ---
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
        # Connect to HostGator SMTP (SSL)
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) 
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, user_email, msg.as_string())
        
        # Send a Copy to YOU (The Agency)
        admin_msg = MIMEMultipart()
        admin_msg['From'] = EMAIL_ADDRESS
        admin_msg['To'] = YOUR_ADMIN_EMAIL
