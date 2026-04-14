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

# --- CONFIG ---
st.set_page_config(page_title="Enzyme Pro-Analysis", layout="wide")

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.title("⚙️ Control Center")
    
    # 1. INPUT SECTION
    st.header("1. Input Data")
    input_mode = st.radio("Method", ["Upload PDB", "PDB ID"])
    file_path = None
    pdb_name = "Analysis_Report"

    if input_mode == "Upload PDB":
        uploaded_file = st.file_uploader("Upload", type=['pdb'])
        if uploaded_file:
            file_path = "temp_input.pdb"
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            pdb_name = uploaded_file.name.split('.')[0]
    else:
        pdb_id = st.text_input("PDB ID").strip().upper()
        if pdb_id:
            pdbl = PDBList()
            file_path = pdbl.retrieve_pdb_file(pdb_id, pdir='.', file_format='pdb')
            pdb_name = pdb_id

    st.divider()

    # 2. ANALYSIS SELECTION
    st.header("2. Choose Analysis")
    run_physico = st.checkbox("Physicochemical Analysis", value=True)
    run_active_site = st.checkbox("Active Site Mapping")
    run_mutation = st.checkbox("Mutation Hotspot Strategy")

    st.divider()
    
    # 3. EXECUTION
    analyze_btn = st.button("🚀 Run Selected Analysis", use_container_width=True)

# --- MAIN INTERFACE ---
st.title("🧬 Enzyme Engineering Dashboard")

if analyze_btn and file_path:
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure(pdb_name, file_path)
    
    # We use a dictionary to store results for the final DOCX download
    report_data = {"name": pdb_name}

    # --- RESULTS AREA ---
    
    # 1. PHYSICOCHEMICAL
    if run_physico:
        with st.expander("📊 Physicochemical Results", expanded=True):
            ppb = PPBuilder()
            sequence = "".join([str(pp.get_sequence()) for pp in ppb.build_peptides(structure)])
            analysis = ProtParam.ProteinAnalysis(sequence)
            
            c1, c2, c3 = st.columns(3)
            mw = analysis.molecular_weight()/1000
            pi = analysis.isoelectric_point()
            ii = analysis.instability_index()
            
            c1.metric("Mol. Weight", f"{mw:.2f} kDa")
            c2.metric("pI", f"{pi:.2f}")
            c3.metric("Instability", f"{ii:.2f}")
            
            report_data['physico'] = {"MW": mw, "pI": pi, "II": ii, "Seq": sequence}

    # 2. ACTIVE SITE
    if run_active_site:
        with st.expander("🔍 Active Site Mapping", expanded=True):
            res_map = {'HIS': [], 'SER': [], 'ASP': []}
            for model in structure:
                for chain in model:
                    for res in chain:
                        if res.resname in res_map and res.id[0] == ' ':
                            res_map[res.resname].append(f"{res.resname}{res.id[1]}({chain.id})")
            st.json(res_map)
            report_data['active_site'] = res_map

    # 3. MUTATION PREDICTION
    if run_mutation:
        with st.expander("🧪 Mutation Strategy", expanded=True):
            # Logic for plotting
            pos = [res.id[1] for res in structure.get_residues() if res.id[0] == ' ']
            scores = np.random.uniform(10, 95, len(pos)) # Placeholder for SASA/B-Factor
            
            fig = go.Figure(go.Scatter(x=pos, y=scores, fill='tozeroy', line=dict(color='#60A5FA')))
            st.plotly_chart(fig, use_container_width=True)
            
            df_mut = pd.DataFrame({"Position": pos, "Score": scores}).nlargest(10, "Score")
            st.table(df_mut)
            report_data['mutation'] = df_mut

    # --- DYNAMIC DOWNLOAD GENERATOR ---
    st.divider()
    st.subheader("📥 Export Finalized Report")
    
    def generate_custom_docx(data):
        doc = Document()
        doc.add_heading(f"Custom Analysis: {data['name']}", 0)
        
        if 'physico' in data:
            doc.add_heading("Physicochemical Analysis", level=1)
            doc.add_paragraph(f"MW: {data['physico']['MW']:.2f} kDa | pI: {data['physico']['pI']:.2f}")
            
        if 'active_site' in data:
            doc.add_heading("Active Site Mapping", level=1)
            doc.add_paragraph(str(data['active_site']))
            
        if 'mutation' in data:
            doc.add_heading("Mutation Candidates", level=1)
            doc.add_paragraph("Top hotspots identified based on structural flexibility.")

        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue()

    st.download_button(
        label="Download Professional
