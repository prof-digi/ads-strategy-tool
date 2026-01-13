import streamlit as st
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from fpdf import FPDF
import os

# --- CONFIGURATION ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
    EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
    SMTP_SERVER = st.secrets["SMTP_SERVER"]
    SMTP_PORT = 587
    YOUR_ADMIN_EMAIL = "joe@profitable.digital"
except FileNotFoundError:
    st.error("Secrets not found. Please set up your .streamlit/secrets.toml file.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

# --- HELPER: TEXT SANITIZER ---
def clean_for_pdf(text):
    if not isinstance(text, str):
        return str(text)
    
    # 1. Replace "Smart Quotes" and formatting chars
    replacements = {
        "’": "'", "‘": "'", "“": '"', "”": '"', 
        "–": "-", "—": "-", "…": "...",
        "**": "", "__": "", # Remove bold/italic markers
        "##": "", "###": "", "#": "", # Remove header hashes
        "`": "" # Remove code ticks
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
        
    # 2. Latin-1 encoding for PDF compatibility
    return text.encode('latin-1', 'ignore').decode('latin-1')

# --- PROFESSIONAL PDF CLASS ---
class PDFReport(FPDF):
    def header(self):
        # Logo
        if os.path.exists("logo.png"):
            self.image("logo.png", 10, 8, 33)
            
        # Title Styling
        self.set_font('Arial', 'B', 15)
        self.set_text_color(0, 51, 102) # Brand Navy Blue
        self.cell(0, 10, 'Google Ads Strategy Roadmap', 0, 1, 'R')
        
        # Decorative Line
        self.set_draw_color(200, 200, 200) # Light Grey Line
        self.set_line_width(0.5)
        self.line(10, 32, 200, 32)
        self.ln(25) # Space after header

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Profitable Digital | Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, label):
        # Section Headers
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 51, 102) # Brand Navy Blue
        self.cell(0, 8, label, 0, 1, 'L')
        self.ln(1)

    def body_text(self, text):
        # Regular Text
        self.set_font('Arial', '', 10)
        self.set_text_color(50, 50, 50) # Dark Grey
        self.multi_cell(0, 5, text)
        self.ln(3)

def create_pdf_report(raw_text, filename):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    lines = raw_text.split('\n')
    
    for line in lines:
        clean_line = clean_for_pdf(line.strip())
        
        # Skip empty table lines or separators
        if "---" in clean_line or clean_line.startswith("|"):
            continue

        if not clean_line:
            pdf.ln(2) # Small space for empty lines
            continue
            
        # Detect Headers based on content or previous formatting
        # (Since we removed #, we check if the line looks like a title)
        if len(clean_line) < 60 and (line.startswith('#') or line.startswith('**')):
            pdf.ln(3)
            pdf.chapter_title(clean_line)
        
        # Detect Bullet Points
        elif line.strip().startswith('-') or line.strip().startswith('*'):
            pdf.set_font('Arial', '', 10)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(5) # Indent
            # Clean the bullet marker itself
            content = clean_line.lstrip('-').lstrip('*').strip()
            pdf.multi_cell(0, 5, f"{chr(149)} {content}")
            pdf.ln(1)
            
        # Regular Paragraph
        else:
            pdf.body_text(clean_line)
                
    pdf.output(filename)
    return filename

# --- FUNCTION 1: GENERATE STRATEGY ---
def generate_ppc_strategy(first_name, last_name, company_name, company_url, industry, goal, budget, competitor_url, problems):
    model = genai.GenerativeModel('gemini-flash-latest')
    
    # UPDATED PROMPT: Explicitly forbids tables and weird symbols
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

    ### REQUIRED OUTPUT FORMAT:
    - Write in clean, professional paragraphs and bullet points.
    - **DO NOT** use Markdown tables, pipes (|), or code blocks.
    - **DO NOT** use hashtags (#) for headers, just write the header name clearly.
    - **DO NOT** use bolding asterisks (**) in the final output, just write plain text.

    ### REPORT SECTIONS:
    1. Executive Summary (2 sentences on ROI).
    2. Website Analysis (How {company_url} aligns with goals).
    3. Pain Point Solutions (Fixes for: {problems}).
    4. Competitor Weaknesses (Analysis of {competitor_url}).
    5. Budget Split (Exact breakdown of £{budget} using a bulleted list).
    6. Keyword Strategy (10 Keywords & 5 Negatives).
    7. Ad Copy Blueprint (3 Headlines, 2 Descriptions).
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating strategy: {e}"

# --- FUNCTION 2: SEND EMAIL WITH PDF ---
def send_email_with_pdf(user_email, strategy_text, company_name):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = user_email
    msg['Subject'] = f"🚀 Your Strategy Report for {company_name}"

    body = f"""
    <p>Hi {first_name},</p>
    <p>Please find attached your custom Google Ads strategy report for <b>{company_name}</b>.</p>
    <p>We have analyzed your website and competitors to build this roadmap and we hope you find it useful. Please get in touch if you have any questions or would like to discuss your Google Ads campaignd further.</p>
    <p>Best regards,<br>Profitable Digital Team</p>
    """
    msg.attach(MIMEText(body, 'html'))
    
    # Generate PDF
    safe_name = "".join([c for c in company_name if c.isalnum() or c==' ']).strip().replace(' ', '_')
    pdf_filename = f"{safe_name}_Strategy.pdf"
    
    try:
        create_pdf_report(strategy_text, pdf_filename)
        
        with open(pdf_filename, "rb") as f:
            attach = MIMEApplication(f.read(),_subtype="pdf")
            attach.add_header('Content-Disposition', 'attachment', filename=pdf_filename)
            msg.attach(attach)

        server = smtplib.SMTP(SMTP_SERVER, 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        
        server.sendmail(EMAIL_ADDRESS, user_email, msg.as_string())
        server.sendmail(EMAIL_ADDRESS, YOUR_ADMIN_EMAIL, msg.as_string())
        
        server.quit()
        return True
        
    except Exception as e:
        st.error(f"❌ Email/PDF Failed: {e}")
        return False

# --- MAIN UI ---
def main():
    st.set_page_config(page_title="Free Google Ads Strategy Generator", page_icon="🚀")
    st.markdown("""<style>.stButton>button {width: 100%; background-color: #000000; color: white; border-radius: 5px;}</style>""", unsafe_allow_html=True)
    
    if os.path.exists("logo.png"):
        st.image("logo.png", width=150)
        
    st.title("🚀 Free Google Ads Strategy Generator")
    st.markdown("Enter your business details below to get a **custom roadmap**, **competitor analysis**, and **budget plan**.")

    if 'step' not in st.session_state: st.session_state['step'] = 1
    if 'strategy_data' not in st.session_state: st.session_state['strategy_data'] = ""

    # STEP 1
    if st.session_state['step'] == 1:
        with st.form("input_form"):
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First Name")
                company = st.text_input("Company Name")
                company_url = st.text_input("Your Website URL") 
                competitor = st.text_input("Competitor URL")
            with col2:
                last_name = st.text_input("Last Name")
                industry = st.text_input("Industry (e.g. E-commerce, Sass)")
                goal = st.selectbox("Primary Goal", ["Leads/Calls", "E-commerce Sales", "Brand Awareness"])
                budget = st.number_input("Monthly Budget (£)", min_value=500, value=1500)
            problems = st.text_area("What are your biggest problems with Google Ads right now?", placeholder="e.g. Getting clicks but no conversions, High CPC...")
            
            # --- DISCLAIMER TEXT ---
            st.markdown("""
            <div style='font-size: 11px; color: #666; margin-top: 10px; margin-bottom: 20px; line-height: 1.4;'>
            Profitable Digital needs the contact information you provide to us to contact you about our products and services. 
            You may unsubscribe from these communications at any time. For information on how to unsubscribe, as well as our 
            privacy practices and commitment to protecting your privacy, please review our <a href="https://profitable.digital/privacy-policy/">Privacy Policy</a>.
            </div>
            """, unsafe_allow_html=True)

            if st.form_submit_button("GENERATE MY STRATEGY"):
                if not first_name or not last_name or not company or not company_url:
                    st.warning("Please fill in all required fields: First Name, Last Name, Company Name, and Website URL.")
                else:
                    with st.spinner("Creating your PDF report..."):
                        strategy = generate_ppc_strategy(first_name, last_name, company, company_url, industry, goal, budget, competitor, problems)
                        st.session_state['strategy_data'] = strategy
                        st.session_state['user_info'] = {'company': company, 'budget': budget}
                        st.session_state['step'] = 2
                        st.rerun()

    # STEP 2
    if st.session_state['step'] == 2:
        st.success("✅ Analysis Complete!")
        st.info("We have generated a PDF report analyzing your website and competitors.")
        
        st.markdown("### 🔒 Unlock Your PDF Report")
        with st.form("email_gate"):
            email = st.text_input("Where should we send the PDF?")
            
            # --- DISCLAIMER TEXT ---
            st.markdown("""
            <div style='font-size: 11px; color: #666; margin-top: 10px; margin-bottom: 20px; line-height: 1.4;'>
            Profitable Digital needs the contact information you provide to us to contact you about our products and services. 
            You may unsubscribe from these communications at any time. For information on how to unsubscribe, as well as our 
            privacy practices and commitment to protecting your privacy, please review our <a href="https://profitable.digital/privacy-policy/">Privacy Policy</a>.
            </div>
            """, unsafe_allow_html=True)

            if st.form_submit_button("SEND ME THE PDF"):
                if "@" not in email:
                    st.error("Please enter a valid email.")
                else:
                    with st.spinner("Sending PDF..."):
                        success = send_email_with_pdf(email, st.session_state['strategy_data'], st.session_state['user_info']['company'])
                        if success:
                            st.session_state['step'] = 3
                            st.rerun()

    # STEP 3
    if st.session_state['step'] == 3:
        st.balloons()
        st.success("PDF Report Sent! Check your inbox.")
        if st.button("Start Over"):
            st.session_state['step'] = 1
            st.rerun()

if __name__ == "__main__":
    main()
