import streamlit as st
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURATION ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]      # mail@jellywebstudio.com
    EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]    # Your Email Password
    SMTP_SERVER = st.secrets["SMTP_SERVER"]          # mail.jellywebstudio.com
    # We default to 465 now based on your successful test
    SMTP_PORT = int(st.secrets.get("SMTP_PORT", 465))     
    YOUR_ADMIN_EMAIL = "joe@profitable.digital"          # Where you receive the leads
except FileNotFoundError:
    st.error("Secrets not found. Please set up your .streamlit/secrets.toml file.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# --- FUNCTION 1: GENERATE STRATEGY WITH GEMINI ---
def generate_ppc_strategy(first_name, last_name, company_name, company_url, industry, goal, budget, competitor_url, problems):
    
    # REQUIRED: Use the 'gemini-flash-latest' model
    model = genai.GenerativeModel('gemini-flash-latest')
    
    prompt = f"""
    Act as a Senior Google Ads Strategist.
    Create a tactical proposal for a UK-based client named {first_name} {last_name}.
    
    ### CLIENT PROFILE
    - **Client Name:** {first_name} {last_name}
    - **Company:** {company_name}
    - **Client Website:** {company_url}
    - **Industry:** {industry}
    - **Goal:** {goal}
    - **Budget:** £{budget}/month
    - **Current Pain Points:** {problems}
    - **Competitor:** {competitor_url}

    ### REQUIRED OUTPUT (Markdown):
    1. **Executive Summary**: 2 sentences on potential ROI for {company_name} given the £{budget} budget.
    2. **Website & Context Analysis**:
       - Briefly mention how their website ({company_url}) aligns with their goals.
    3. **Pain Point Analysis**: 
       - Address their specific problem ("{problems}") and explain exactly how to fix it.
    4. **Competitor Reconnaissance**: 
       - Analyze {competitor_url}. Identify 2 specific weaknesses.
    5. **Budget Split Table**: 
       - Exact breakdown of the £{budget} (e.g., Search vs. Retargeting). Use £ symbols.
    6. **Keyword Strategy**:
       - 10 High-Intent Keywords (relevant to the UK market).
       - 5 Negative Keywords to block.
    7. **Ad Copy Blueprint**:
       - 1 Responsive Search Ad (3 Headlines, 2 Descriptions).
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating strategy: {e}"
            
# --- FUNCTION 2: SEND EMAIL (FIXED FOR HOSTGATOR SSL PORT 465) ---
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
        # --- FIXED CONNECTION LOGIC FOR PORT 465 ---
        # Confirmed working via local test
        server = smtplib.SMTP_SSL(SMTP_SERVER, 465)
        
        # Login
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        
        # Send to User
        server.sendmail(EMAIL_ADDRESS, user_email, msg.as_string())
        
        # Send Copy to YOU
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
                first_name = st.text_input("First Name")
                company = st.text_input("Company Name")
                company_url = st.text_input("Your Website URL") # New Field
                competitor = st.text_input("Competitor URL")
                
            with col2:
                last_name = st.text_input("Last Name")
                industry = st.text_input("Industry (e.g., Plumber)")
                goal = st.selectbox("Primary Goal", ["Leads/Calls", "E-commerce Sales", "Brand Awareness"])
                budget = st.number_input("Monthly Budget (£)", min_value=500, value=1500)

            # Problems Question
            problems = st.text_area("What are your biggest problems with Google Ads right now?", 
                                    placeholder="e.g. High cost per click, getting clicks but no sales, low quality leads...")

            submitted = st.form_submit_button("GENERATE MY STRATEGY")

            if submitted:
                # Validate inputs
                if not first_name or not company or not company_url:
                    st.warning("Please fill in your Name, Company, and Website URL.")
                else:
                    with st.spinner("🕵️ Analyzing your website and generating roadmap..."):
                        strategy = generate_ppc_strategy(
                            first_name, last_name, company, company_url, 
                            industry, goal, budget, competitor, problems
                        )
                        
                        st.session_state['strategy_data'] = strategy
                        st.session_state['user_info'] = {'company': company, 'budget': budget}
                        st.session_state['step'] = 2
                        st.rerun()

    # --- STEP 2: THE TEASER & EMAIL GATE ---
    if st.session_state['step'] == 2:
        st.success("✅ Strategy Generated Successfully!")
        
        st.markdown(f"### 🔍 Analysis for {st.session_state['user_info']['company']}")
        st.info("We have analyzed your website and pain points to find a **Budget Efficiency Fix**.")
        
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
