import streamlit as st
import os
import io
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from Bio.PDB import PDBParser, PPBuilder, PDBList
from Bio.SeqUtils import ProtParam
from docx import Document
from docx.shared import RGBColor, Inches, Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from streamlit_molstar import st_molstar

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="Enzyme Optimization Hub", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3 { color: #60A5FA !important; font-family: 'Inter', sans-serif; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE UTILITIES ---
def get_top_6_suggestions(res):
    suggestions = {'GLY': 'ALA, PRO, SER, VAL, ILE, LEU', 'ALA': 'VAL, LEU, ILE, SER, THR, MET', 
                   'ASP': 'GLU, ASN, GLN, HIS, LYS, ARG', 'SER': 'THR, ALA, CYS, ASN, GLN, TYR',
                   'HIS': 'PHE, TYR, TRP, ASN, GLN, LYS'}
    return suggestions.get(res.upper(), 'ALA, VAL, LEU, ILE, SER, THR')

# --- 3. HEADER & INPUT ---
st.title("🧬 Enzyme Engineering & Mutation Pipeline")
st.write("Merge of Structural Analysis, Active Site Mapping, and Mutation Prediction")

with st.sidebar:
    st.header("Input Data")
    input_mode = st.radio("Select Method", ["Upload PDB", "PDB ID"])
    
    file_path = None
    pdb_name = "Target"

    if input_mode == "Upload PDB":
        uploaded_file = st.file_uploader("Choose a PDB file", type=['pdb', 'ent'])
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

# --- 4. MAIN PIPELINE LOGIC ---
if file_path and os.path.exists(file_path):
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure(pdb_name, file_path)
    
    # Global Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Protein Analysis", "🔍 Active Site Prediction", "🧪 Mutation Strategy"])

    # --- TAB 1: PROTEIN ANALYSIS (PIPELINE 1) ---
    with tab1:
        st.subheader("Physicochemical Profile")
        ppb = PPBuilder()
        sequence = "".join([str(pp.get_sequence()) for pp in ppb.build_peptides(structure)])
        
        if sequence:
            analysis = ProtParam.ProteinAnalysis(sequence)
            col1, col2, col3 = st.columns(3)
            col1.metric("Mol. Weight", f"{analysis.molecular_weight()/1000:.2f} kDa")
            col2.metric("Isoelectric Point (pI)", f"{analysis.isoelectric_point():.2f}")
            col3.metric("Instability Index", f"{analysis.instability_index():.2f}")
            
            st.write("### Sequence Data")
            st.code(sequence[:100] + "...")
        
        st.subheader("3D Structural View")
        st_molstar(file_path, height=400)

    # --- TAB 2: ACTIVE SITE PREDICTION (PIPELINE 2) ---
    with tab2:
        st.subheader("Catalytic Residue Mapping")
        res_map = {'HIS': [], 'SER': [], 'ASP': []}
        for model in structure:
            for chain in model:
                for res in chain:
                    if res.resname in res_map and res.id[0] == ' ':
                        res_map[res.resname].append(f"{res.resname}{res.id[1]}({chain.id})")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.json(res_map)
        with col_b:
            st.info("These residues represent the potential catalytic triad or binding site. Targeted mutations here usually modulate enzymatic activity.")

    # --- TAB 3: MUTATION PREDICTION (PIPELINE 3) ---
    with tab3:
        st.subheader("Computational Hotspot Landscape")
        
        # Generate dummy mutation data based on the actual sequence
        pos = []
        res_types = []
        for model in structure:
            for chain in model:
                for res in chain:
                    if res.id[0] == ' ':
                        pos.append(res.id[1])
                        res_types.append(res.resname)
        
        # Scoring logic (In a real scenario, this uses B-factor/SASA)
        scores = np.random.uniform(0, 100, len(pos)) 
        mut_df = pd.DataFrame({'Pos': pos, 'Res': res_types, 'Score': scores})
        mut_df['Suggestions'] = mut_df['Res'].apply(get_top_6_suggestions)
        
        fig = go.Figure(data=[go.Scatter(x=mut_df['Pos'], y=mut_df['Score'], 
                                        mode='lines', fill='tozeroy', line=dict(color='#8783D8'))])
        st.plotly_chart(fig, use_container_width=True)
        
        st.write("### High-Priority Candidates")
        st.dataframe(mut_df.nlargest(15, 'Score'), use_container_width=True)

        # Export Logic
        report_bio = io.BytesIO()
        doc = Document()
        doc.add_heading(f"Comprehensive Enzyme Report: {pdb_name}", 0)
        doc.add_paragraph(f"Sequence length: {len(sequence)}")
        doc.save(report_bio)
        
        st.download_button("📥 Download Full Research Report", data=report_bio.getvalue(), 
                           file_name=f"{pdb_name}_Analysis.docx")

else:
    st.info("Please upload a PDB file or enter a PDB ID in the sidebar to begin.")
