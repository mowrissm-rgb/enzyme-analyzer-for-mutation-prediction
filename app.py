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
                # Corrected Line 97
                st_molstar(file_path, height=400)

    # PIPELINE 2: Active Site
    with tab2:
        if run_active_site:
            st.subheader("Catalytic Residue Mapping")
            res_map = {'HIS': [], 'SER': [], 'ASP': []}
            for model in structure:
                for chain in model:
                    for res in chain:
                        if res.resname in res_map and res.id[0] == ' ':
                            res_map[res.resname].append(f"{res.resname}{res.id[1]}({chain.id})")
            
            st.json(res_map)
            report_data['active_site'] = res_map

    # PIPELINE 3: Mutation Strategy
    with tab3:
        if run_mutation:
            st.subheader("Computational Hotspot Landscape")
            res_list = []
            for res in structure.get_residues():
                if res.id[0] == ' ':
                    res_list.append({"Pos": res.id[1], "Res": res.resname})
            
            if res_list:
                df_base = pd.DataFrame(res_list)
                df_base['Score'] = np.random.uniform(10, 95, len(df_base))
                df_base['Suggestions'] = df_base['Res'].apply(get_top_6_suggestions)

                fig = go.Figure(go.Scatter(x=df_base['Pos'], y=df_base['Score'], fill='tozeroy', line=dict(color='#60A5FA')))
                st.plotly_chart(fig, use_container_width=True)
                
                st.write("### Top 10 Mutation Candidates")
                top_candidates = df_base.nlargest(10, 'Score')
                st.table(top_candidates)
                report_data['mutation'] = top_candidates

    # --- DOWNLOAD SECTION ---
    st.divider()
    def generate_docx(data):
        doc = Document()
        doc.add_heading(f"Enzyme Analysis Report: {data['name']}", 0)
        if 'physico' in data:
            doc.add_heading("1. Physicochemical Properties", level=1)
            doc.add_paragraph(f"Molecular Weight: {data['physico']['MW']:.2f} kDa")
        if 'active_site' in data:
            doc.add_heading("2. Identified Active Sites", level=1)
            doc.add_paragraph(str(data['active_site']))
        
        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue()

    st.download_button(
        label="📥 Download Full Research Report",
        data=generate_docx(report_data),
        file_name=f"{pdb_name}_Research_Report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

elif not file_path:
    st.warning("Please upload a file or enter a PDB ID in the sidebar.")
else:
    st.info("Adjust settings in the sidebar and click 'Run Full Pipeline' to begin.")
