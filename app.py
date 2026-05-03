import streamlit as st
import database as db
import pytesseract
from PIL import Image
import PyPDF2
import re

# Initialize the database on startup
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
        
        st.subheader(f"Structured Vitals History for {selected_patient}")
        history_df = db.get_structured_history(patient_id)
        
        if not history_df.empty:
            st.dataframe(history_df, use_container_width=True)
        else:
            st.info("No reports found for this patient.")
    else:
        st.warning("No patients found in the database. Please upload a report to create one.")

elif page == "Upload New Report":
    st.title("📤 Intelligent Ingestion Pipeline")
    
    patients_df = db.get_patient_data()
    doctors_df = db.get_doctor_data()
    
    existing_patients = patients_df['name'].tolist() if not patients_df.empty else []
    existing_doctors = doctors_df['name'].tolist() if not doctors_df.empty else []

    st.markdown("### Assignment Details")
    
    # --- PATIENT SELECTION UI ---
    p_col1, p_col2 = st.columns([1, 2])
    with p_col1:
        patient_mode = st.radio("Patient Entry Mode", ["Select Existing", "Enter Manually"], key="p_mode")
    with p_col2:
        if patient_mode == "Select Existing":
            if existing_patients:
                final_patient_name = st.selectbox("Select Patient", existing_patients)
            else:
                st.warning("No patients in DB. Please use manual entry.")
                final_patient_name = None
        else:
            final_patient_name = st.text_input("Enter New Patient Name")
            
    st.markdown("---")
            
    # --- DOCTOR SELECTION UI ---
    d_col1, d_col2 = st.columns([1, 2])
    with d_col1:
        doctor_mode = st.radio("Doctor Entry Mode", ["Select Existing", "Enter Manually"], key="d_mode")
    with d_col2:
        if doctor_mode == "Select Existing":
            if existing_doctors:
                final_doctor_name = st.selectbox("Select Doctor", existing_doctors)
            else:
                st.warning("No doctors in DB. Please use manual entry.")
                final_doctor_name = None
        else:
            final_doctor_name = st.text_input("Enter New Doctor Name")

    st.markdown("### Document Upload")
    uploaded_file = st.file_uploader("Upload Medical Report (PDF/Image)", type=["png", "jpg", "jpeg", "pdf"])
    
    if st.button("Process & Extract Data"):
        if uploaded_file is not None and final_patient_name and final_doctor_name:
            with st.spinner('Running OCR and Parsing Agent...'):
                
                # 1. Resolve IDs dynamically
                patient_id = db.get_or_create_patient(final_patient_name.strip())
                doctor_id = db.get_or_create_doctor(final_doctor_name.strip())
                
                extracted_text = ""
                
                # 2. OCR EXTRACTION
                try:
                    if uploaded_file.type in ["image/png", "image/jpeg", "image/jpg"]:
                        image = Image.open(uploaded_file)
                        extracted_text = pytesseract.image_to_string(image)
                    elif uploaded_file.type == "application/pdf":
                        pdf_reader = PyPDF2.PdfReader(uploaded_file)
                        for page in range(len(pdf_reader.pages)):
                            extracted_text += pdf_reader.pages[page].extract_text()
                            
                    if not extracted_text.strip():
                        extracted_text = "Status: Could not extract text. Image may be too blurry."
                except Exception as e:
                    st.error(f"Extraction Failed: {e}")
                    extracted_text = f"Status: Extraction Failed. Error: {e}"
                
                # 3. STRUCTURED PARSING AGENT
                bp_match = re.search(r'(?i)blood pressure.*?(\d{2,3}\s*/\s*\d{2,3})', extracted_text)
                bp_value = bp_match.group(1) if bp_match else "Not Found"
                
                hr_match = re.search(r'(?i)(?:heart rate|pulse).*?(\d{2,3})\s*bpm', extracted_text)
                hr_value = int(hr_match.group(1)) if hr_match else None
                
                # 4. DATABASE INGESTION
                db.add_full_report(
                    patient_id, 
                    doctor_id, 
                    extracted_text, 
                    bp_value, 
                    hr_value
                )
                
            st.success(f"Report assigned to **{final_patient_name}** by **{final_doctor_name}** and digitized successfully!")
            st.info(f"**Extracted Blood Pressure:** {bp_value}  \n**Extracted Heart Rate:** {hr_value} bpm")
        else:
            st.error("Missing Information: Please ensure you have provided a Patient Name, a Doctor Name, and uploaded a file.")