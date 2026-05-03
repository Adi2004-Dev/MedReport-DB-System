import streamlit as st
import database as db
import pytesseract
from PIL import Image
import PyPDF2
import re
import spacy
import spacy.cli
import plotly.express as px
import pandas as pd

# --- BULLETPROOF MODEL LOADING ---
@st.cache_resource
def load_nlp_model():
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        st.info("System Initializing: Downloading AI Model... this will only take a moment.")
        spacy.cli.download("en_core_web_sm")
        return spacy.load("en_core_web_sm")

nlp = load_nlp_model()
# ---------------------------------

# Initialize the database
db.init_db()

st.set_page_config(page_title="MedReport DB System", layout="wide")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Upload New Report"])

if page == "Dashboard":
    st.title("🏥 Patient Report Dashboard")
    
    patients_df = db.get_patient_data()
    
    if not patients_df.empty:
        selected_patient = st.selectbox("Select Patient", patients_df['name'])
        patient_id = patients_df.loc[patients_df['name'] == selected_patient, 'patient_id'].values[0]
        
        st.subheader(f"Medical History for {selected_patient}")
        history_df = db.get_structured_history(patient_id)
        
        if not history_df.empty:
            st.dataframe(history_df, use_container_width=True)
            
            # Interactive Visualization
            st.markdown("---")
            st.subheader("📈 Heart Rate Trend")
            
            chart_df = history_df.copy()
            chart_df['upload_date'] = pd.to_datetime(chart_df['upload_date'])
            chart_df = chart_df.sort_values(by="upload_date")
            chart_df = chart_df.dropna(subset=['heart_rate'])
            
            if not chart_df.empty:
                fig = px.line(
                    chart_df, 
                    x="upload_date", 
                    y="heart_rate", 
                    markers=True,
                    title=f"Heart Rate over Time for {selected_patient}",
                    labels={"upload_date": "Date of Report", "heart_rate": "Heart Rate (bpm)"}
                )
                fig.update_traces(line_color="#FF4B4B")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough heart rate data to plot a trend line.")
        else:
            st.info("No reports found for this patient.")
    else:
        st.warning("No patients found in the database.")

elif page == "Upload New Report":
    st.title("📤 Intelligent Ingestion Pipeline")
    
    patients_df = db.get_patient_data()
    doctors_df = db.get_doctor_data()
    
    existing_patients = patients_df['name'].tolist() if not patients_df.empty else []
    existing_doctors = doctors_df['name'].tolist() if not doctors_df.empty else []

    st.markdown("### Assignment Details")
    
    p_col1, p_col2 = st.columns([1, 2])
    with p_col1:
        patient_mode = st.radio("Patient Entry Mode", ["Select Existing", "Enter Manually"], key="p_mode")
    with p_col2:
        if patient_mode == "Select Existing" and existing_patients:
            final_patient_name = st.selectbox("Select Patient", existing_patients)
        else:
            final_patient_name = st.text_input("Enter New Patient Name")
            
    st.markdown("---")
            
    d_col1, d_col2 = st.columns([1, 2])
    with d_col1:
        doctor_mode = st.radio("Doctor Entry Mode", ["Select Existing", "Enter Manually"], key="d_mode")
    with d_col2:
        if doctor_mode == "Select Existing" and existing_doctors:
            final_doctor_name = st.selectbox("Select Doctor", existing_doctors)
        else:
            final_doctor_name = st.text_input("Enter New Doctor Name")

    st.markdown("### Document Upload")
    uploaded_file = st.file_uploader("Upload Medical Report (PDF/Image)", type=["png", "jpg", "jpeg", "pdf"])
    
    if st.button("Process & Extract Data"):
        if uploaded_file is not None and final_patient_name and final_doctor_name:
            with st.spinner('Running AI Extraction Agents...'):
                
                patient_id = db.get_or_create_patient(final_patient_name.strip())
                doctor_id = db.get_or_create_doctor(final_doctor_name.strip())
                
                extracted_text = ""
                
                # 1. OCR Extraction
                try:
                    if uploaded_file.type in ["image/png", "image/jpeg", "image/jpg"]:
                        image = Image.open(uploaded_file)
                        extracted_text = pytesseract.image_to_string(image)
                    elif uploaded_file.type == "application/pdf":
                        pdf_reader = PyPDF2.PdfReader(uploaded_file)
                        for page in range(len(pdf_reader.pages)):
                            extracted_text += pdf_reader.pages[page].extract_text()
                except Exception as e:
                    st.error(f"Extraction Failed: {e}")
                
                # 2. Regex Parsing (Numbers)
                bp_match = re.search(r'(?i)blood pressure.*?(\d{2,3}\s*/\s*\d{2,3})', extracted_text)
                bp_value = bp_match.group(1) if bp_match else "Not Found"
                hr_match = re.search(r'(?i)(?:heart rate|pulse).*?(\d{2,3})\s*bpm', extracted_text)
                hr_value = int(hr_match.group(1)) if hr_match else None
                
                # 3. Named Entity Recognition
                diseases = []
                medications = []
                if nlp and extracted_text:
                    doc = nlp(extracted_text)
                    for ent in doc.ents:
                        if ent.label_ in ["DISEASE", "SYMPTOM", "PERSON", "ORG"]: 
                            diseases.append(ent.text)
                        elif ent.label_ in ["CHEMICAL", "PRODUCT"]:
                            medications.append(ent.text)
                
                diseases = list(set([d.title() for d in diseases]))
                medications = list(set([m.title() for m in medications]))

                # 4. Database Ingestion
                db.add_full_report(patient_id, doctor_id, extracted_text, bp_value, hr_value)
                
            st.success(f"Report assigned to **{final_patient_name}** and digitized successfully!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**Extracted Blood Pressure:** {bp_value}  \n**Extracted Heart Rate:** {hr_value} bpm")
            with col2:
                if diseases or medications:
                    st.warning("**🧠 AI Semantic Extraction**")
                    if diseases:
                        st.write(f"*Potential Conditions Detected:* {', '.join(diseases)}")
                    if medications:
                        st.write(f"*Medications Detected:* {', '.join(medications)}")
        else:
            st.error("Please provide a Patient, Doctor, and File.")