import streamlit as st
import os
import io
import pandas as pd
import numpy as np
from Bio.PDB import PDBParser, PPBuilder, PDBList
from Bio.SeqUtils import ProtParam
from docx import Document
from docx.shared import RGBColor
from streamlit_molstar import st_molstar

# --- 1. CONFIG ---
st.set_page_config(page_title="Enzyme Optimization Hub", layout="wide")

# --- 2. STYLING ---
st.markdown("""
    <style>
    .main-header { font-size: 24px; font-weight: bold; color: #0070c0; border-bottom: 2px solid #0070c0; margin-bottom: 20px; }
    .section-box { padding: 15px; border: 1px solid #e6e6e6; border-radius: 10px; margin-bottom: 20px; background-color: #ffffff; }
    </style>
""", unsafe_allow_html=True)

# --- 3. CORE LOGIC ---
def get_top_6_suggestions(res):
    suggestions = {'GLY': 'ALA, PRO, SER', 'ALA': 'VAL, LEU, ILE', 'ASP': 'GLU, ASN, GLN', 'SER': 'THR, ALA, CYS'}
    return suggestions.get(res.upper(), 'ALA, VAL, LEU')

def gen_report(title, content_list, table_df=None):
    doc = Document()
    h = doc.add_heading(title, level=1)
    h.runs[0].font.color.rgb = RGBColor(0, 112, 192)
    for item in content_list: doc.add_paragraph(item)
    if table_df is not None:
        t = doc.add_table(df.shape[0]+1, df.shape[1]); t.style = 'Table Grid'
        # Table filling logic...
    bio = io.BytesIO(); doc.save(bio); return bio.getvalue()

# --- 4. APP LAYOUT (SPLIT COLUMN) ---
col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    st.markdown('<p class="main-header">Input Panel</p>', unsafe_allow_html=True)
    
    # Input Section
    input_mode = st.radio("Choose Input Method", ["Upload PDB", "Enter PDB ID"])
    file_path = None
    pdb_name = "Analysis"

    if input_mode == "Upload PDB":
        uploaded_file = st.file_uploader("Upload PDB File", type=['pdb'])
        if uploaded_file:
            file_path = "temp.pdb"
            with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
            pdb_name = uploaded_file.name.split('.')[0]
    else:
        pdb_id = st.text_input("PDB ID (e.g., 1A2B)").upper()
        if pdb_id:
            file_path = PDBList().retrieve_pdb_file(pdb_id, pdir='.', file_format='pdb')
            pdb_name = pdb_id

    st.divider()
    
    # Run Buttons (As drawn in your sketch)
    run_1 = st.button("① Run Protein Analysis", use_container_width=True)
    run_2 = st.button("② Active Site Prediction", use_container_width=True)
    run_3 = st.button("③ Mutation Prediction", use_container_width=True)
    
    if any([run_1, run_2, run_3]):
        st.markdown("<h1 style='text-align: center; color: orange;'>⮕</h1>", unsafe_allow_html=True)
        st.info("Check results on the right")

with col_right:
    st.markdown('<p class="main-header">Analyzed Results</p>', unsafe_allow_html=True)
    
    if not file_path:
        st.info("Waiting for input and 'Run' command...")

    # SECTION 1: PROTEIN ANALYSIS
    if run_1 and file_path:
        with st.container():
            st.markdown("### ① Protein Physicochemical Analysis")
            col1, col2 = st.columns([2, 1])
            with col1:
                st_molstar(file_path, height=400)
            with col2:
                # Logic
                ppb = PPBuilder()
                seq = "".join([str(p.get_sequence()) for p in ppb.build_peptides(PDBParser(QUIET=True).get_structure(pdb_name, file_path))])
                analysis = ProtParam.ProteinAnalysis(seq)
                st.metric("MW (kDa)", f"{analysis.molecular_weight()/1000:.2f}")
                st.metric("pI", f"{analysis.isoelectric_point():.2f}")
                
                rep = gen_report("Physico Report", [f"MW: {analysis.molecular_weight()}"])
                st.download_button("📥 Download Report", rep, f"{pdb_name}_Physico.docx")
        st.divider()

    # SECTION 2: ACTIVE SITE
    if run_2 and file_path:
        with st.container():
            st.markdown("### ② Active Site Result Table")
            # Simulated data for the table in your sketch
            active_site_data = pd.DataFrame({
                'Residue': ['HIS', 'SER', 'ASP'],
                'Position': [57, 195, 102],
                'Distance (Å)': [3.2, 2.8, 3.5]
            })
            st.table(active_site_data)
            
            # Position for the download button as per sketch
            c_spacer, c_btn = st.columns([2, 1])
            with c_btn:
                rep_a = gen_report("Active Site", ["Active Site Analysis"])
                st.download_button("📥 Download Report", rep_a, f"{pdb_name}_ActiveSite.docx")
        st.divider()

    # SECTION 3: MUTATION
    if run_3 and file_path:
        with st.container():
            st.markdown("### ③ Mutation Prediction Table")
            mut_data = pd.DataFrame({
                'Original': ['GLY', 'ALA', 'SER'],
                'Pos': [12, 45, 88],
                'Score': [92.5, 88.2, 85.0],
                'Suggestions': ['ALA
