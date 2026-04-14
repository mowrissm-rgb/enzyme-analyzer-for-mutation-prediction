import streamlit as st
import os
import io
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from Bio.PDB import PDBParser, PPBuilder, PDBList
from Bio.SeqUtils import ProtParam
from docx import Document
from streamlit_molstar import st_molstar

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="Enzyme Optimization Hub", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3 { color: #60A5FA !important; font-family: 'Inter', sans-serif; }
    div.stButton > button { width: 100%; border-radius: 10px; background-color: #1F2937; color: white; border: 1px solid #374151; }
    div.stButton > button:hover { border-color: #8783D8; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE UTILITIES ---
def get_top_6_suggestions(res):
    suggestions = {
        'GLY': 'ALA, PRO, SER, VAL, ILE, LEU', 
        'ALA': 'VAL, LEU, ILE, SER, THR, MET', 
        'ASP': 'GLU, ASN, GLN, HIS, LYS, ARG', 
        'SER': 'THR, ALA, CYS, ASN, GLN, TYR',
        'HIS': 'PHE, TYR, TRP, ASN, GLN, LYS'
    }
    return suggestions.get(res.upper(), 'ALA, VAL, LEU, ILE, SER, THR')

# --- 3. SIDEBAR CONTROL CENTER ---
with st.sidebar:
    st.title("⚙️ Control Center")
    st.header("1. Input Data")
    input_mode = st.radio("Select Method", ["Upload PDB", "PDB ID"])
    
    file_path = None
    pdb_name = "Analysis_Report"

    if input_mode == "Upload PDB":
        uploaded_file = st.file_uploader("Choose PDB file", type=['pdb', 'ent'])
        if uploaded_file:
            file_path = "temp_input.pdb"
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            pdb_name = uploaded_file.name.split('.')[0]
    else:
        pdb_id = st.text_input("Enter PDB ID (e.g., 4NOS)").strip().upper()
        if pdb_id:
            pdbl = PDBList()
            file_path = pdbl.retrieve_pdb_file(pdb_id, pdir='.', file_format='pdb')
            pdb_name = pdb_id

    st.divider()
    st.header("2. Analysis Selection")
    run_physico = st.checkbox("Physicochemical Analysis", value=True)
    run_active_site = st.checkbox("Active Site Mapping", value=True)
    run_mutation = st.checkbox("Mutation Strategy", value=True)
    
    st.divider()
    analyze_btn = st.button("🚀 Run Full Pipeline")

# --- 4. MAIN INTERFACE LOGIC ---
st.title("🧬 Enzyme Engineering & Mutation Pipeline")

if analyze_btn and file_path:
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure(pdb_name, file_path)
    report_data = {"name": pdb_name}

    tab1, tab2, tab3 = st.tabs(["📊 Analysis", "🔍 Active Site", "🧪 Mutation Strategy"])

    # PIPELINE 1: Physicochemical
    with tab1:
        if run_physico:
            st.subheader("Structural & Physicochemical Profile")
            ppb = PPBuilder()
            sequence = "".join([str(pp.get_sequence()) for pp in ppb.build_peptides(structure)])
            
            if sequence:
                analysis = ProtParam.ProteinAnalysis(sequence)
                c1, c2, c3 = st.columns(3)
                mw = analysis.molecular_weight()/1000
                pi = analysis.isoelectric_point()
                ii = analysis.instability_index()
                
                c1.metric("Mol. Weight", f"{mw:.2f} kDa")
                c2.metric("pI", f"{pi:.2f}")
                c3.metric("Instability", f"{ii:.2f}")
                
                report_data['physico'] = {"MW": mw, "pI": pi, "II": ii, "Seq": sequence}
                st.write("### 3D Visualization")
                st_mol
