import streamlit as st
from PIL import Image
import moondream as md
import json
import os
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Retrieve API key from environment variable
MOONDREAM_API_KEY = os.getenv("MOONDREAM_API_KEY")

if not MOONDREAM_API_KEY:
    st.error("API Key is missing. Please set it in the .env file.")
    st.stop()

# Initialize Moondream model with API key
model = md.vl(api_key=MOONDREAM_API_KEY)

# Initialize session state to persist data
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "pdf_buffer" not in st.session_state:
    st.session_state.pdf_buffer = None

# Streamlit UI
st.title("Fire-NOC Agent 🚒")

# Site address input
site_address = st.text_input("Enter the Site Address", "e.g., 123 Fire Safety Lane, City, Country")

# Define required image categories
required_categories = [
    "Fire Extinguisher",
    "Fire Exit",
    "Fire Safety Warning Sign",
    "Water Infrastructure"
]

# Dictionary to store uploaded images
uploaded_images = {}

# Image upload section
st.subheader("Upload Required Images")
for category in required_categories:
    uploaded_file = st.file_uploader(f"Upload {category} Image", type=["jpg", "jpeg", "png"], key=category)
    if uploaded_file:
        uploaded_images[category] = Image.open(uploaded_file)
        st.image(uploaded_images[category], caption=category, use_container_width=True)

# Analysis function
def analyze_fire_safety(images):
    results = {}
    for category, image in images.items():
        encoded_image = model.encode_image(image)
        
        # Define prompts based on category
        if category == "Fire Extinguisher":
            prompt = """
            Analyze this fire extinguisher image for:
            1. Rust or corrosion
            2. Pressure gauge visibility and status
            3. Physical damage
            Respond in JSON: {"rust": "...", "pressure_gauge": "...", "damage": "...", "status": "..."}
            """
        elif category == "Fire Exit":
            prompt = """
            Analyze this fire exit image for:
            1. Blockages or obstructions
            2. Signage visibility
            3. Accessibility
            Respond in JSON: {"blockages": "...", "signage": "...", "accessibility": "...", "status": "..."}
            """
        elif category == "Fire Safety Warning Sign":
            prompt = """
            Analyze this fire safety warning sign image for:
            1. Legibility
            2. Placement appropriateness
            3. Fading or damage
            Respond in JSON: {"legibility": "...", "placement": "...", "condition": "...", "status": "..."}
            """
        elif category == "Water Infrastructure":
            prompt = """
            Analyze this water infrastructure image for:
            1. Leaks or corrosion
            2. Pipe condition
            3. Pressure indicators (if visible)
            Respond in JSON: {"leaks": "...", "condition": "...", "pressure": "...", "status": "..."}
            """

        # Query Moondream API
        with st.spinner(f"Analyzing {category}..."):
            analysis = model.query(encoded_image, prompt)["answer"]
            results[category] = json.loads(analysis)
    
    return results

# Generate PDF with README, dynamic date, and site address
def generate_noc_pdf(analysis_results, site_address):
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        story.append(Paragraph("Temporary Fire No Objection Certificate (NOC)", styles['Title']))
        story.append(Spacer(1, 12))

        # Dynamic date
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Site address and date section
        story.append(Paragraph(f"<b>Site Address:</b> {site_address}", styles['Normal']))
        story.append(Paragraph(f"<b>Issued on:</b> {current_date}", styles['Normal']))
        story.append(Spacer(1, 12))

        # README Section
        readme_text = f"""
        <b>Temporary NOC</b><br/>
        This document is a temporary Fire No Objection Certificate (NOC) issued based on an automated analysis of uploaded images by the Fire-NOC Agent, powered by Moondream AI. It is valid only until an on-site inspection is conducted by a fire safety officer. The certificate confirms that the provided images meet preliminary fire safety requirements as per AI analysis and human verification for the site at {site_address}. Please note:<br/>
        - This is not a final NOC.<br/>
        - On-site verification by an officer is mandatory for official approval.<br/>
        - Ensure all identified issues (if any) are addressed before the inspection.<br/>
        """
        story.append(Paragraph(readme_text, styles['Normal']))
        story.append(Spacer(1, 12))

        # Analysis Results
        story.append(Paragraph("<b>Analysis Results</b>", styles['Heading2']))
        for category, result in analysis_results.items():
            result_text = f"<b>{category}</b><br/>"
            for key, value in result.items():
                result_text += f"{key.capitalize()}: {value}<br/>"
            story.append(Paragraph(result_text, styles['Normal']))
            story.append(Spacer(1, 6))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Error generating PDF: {e}")
        return None

# Analyze button
if len(uploaded_images) == len(required_categories) and site_address and st.button("Analyze Images"):
    st.session_state.analysis_results = analyze_fire_safety(uploaded_images)

# Display analysis results if they exist
if st.session_state.analysis_results:
    st.subheader("Analysis Results")
    all_passed = True
    for category, result in st.session_state.analysis_results.items():
        st.markdown(f"### {category}")
        for key, value in result.items():
            if key == "status":
                if value.lower() == "fail":
                    st.error(f"❌ **{key.capitalize()}:** {value}")
                    all_passed = False
                else:
                    st.success(f"✅ **{key.capitalize()}:** {value}")
            else:
                st.info(f"ℹ️ **{key.capitalize()}:** {value}")
    
    # Human verification
    st.subheader("Human Verification")
    verification = st.checkbox("I have verified the AI suggestions and approve them")
    
    # Issue temporary NOC and provide download button
    if all_passed and verification:
        st.success("🎉 Temporary NOC Issued! Download below.")
        # Generate PDF only once and store in session state
        if st.session_state.pdf_buffer is None:
            st.session_state.pdf_buffer = generate_noc_pdf(st.session_state.analysis_results, site_address)
        
        if st.session_state.pdf_buffer:
            st.download_button(
                label="Download Temporary NOC",
                data=st.session_state.pdf_buffer,
                file_name=f"Temporary_Fire_NOC_{site_address.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
        else:
            st.error("Failed to generate PDF. Please check the error above.")
    elif not all_passed:
        st.warning("⚠️ Some checks failed. Temporary NOC cannot be issued until issues are resolved.")
    elif not verification:
        st.info("ℹ️ Please verify the suggestions to issue a temporary NOC.")
else:
    if not site_address:
        st.warning("⚠️ Please enter the site address before analyzing.")