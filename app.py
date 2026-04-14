import streamlit as st
import io
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from Bio.PDB import PDBParser, PPBuilder, PDBList
from Bio.SeqUtils import ProtParam
from docx import Document
from docx.shared import Inches, RGBColor
from streamlit_molstar import st_molstar

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="Enzyme Optimization Hub", layout="wide")

st.markdown("""
    <style>
    .reportview-container .main .block-container { padding-top: 2rem; }
    .main-header { font-size: 28px; font-weight: bold; color: #1E3A8A; border-bottom: 3px solid #1E3A8A; padding-bottom: 10px; }
    .method-text { font-style: italic; color: #4B5563; font-size: 0.9rem; }
    </style>
""", unsafe_allow_html=True)

# --- 2. PROFESSIONAL REPORT GENERATOR ---
def create_prof_report(title, methodology, formulas, df, plot_buf=None):
    doc = Document()
    # Header
    header = doc.add_heading(title, 0)
    header.runs[0].font.color.rgb = RGBColor(30, 58, 138)
    
    # Methodology
    doc.add_heading('Methodology', level=1)
    doc.add_paragraph(methodology)
    
    # Formula Section
    if formulas:
        doc.add_heading('Mathematical Basis', level=2)
        for f in formulas:
            doc.add_paragraph(f, style='Quote')
    
    # Data Table
    doc.add_heading('Analysis Results', level=1)
    t = doc.add_table(df.shape[0] + 1, df.shape[1])
    t.style = 'Table Grid'
    for j, col in enumerate(df.columns):
        t.cell(0, j).text = col
    for i, row in enumerate(df.values):
        for j, val in enumerate(row):
            t.cell(i + 1, j).text = str(val)
            
    # Graph
    if plot_buf:
        doc.add_heading('Visualization', level=1)
        doc.add_picture(plot_buf, width=Inches(5))
        
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. ANALYSIS UTILITIES ---
def get_mutation_suggestions(res):
    sug = {'GLY': 'ALA, PRO, SER', 'ALA': 'VAL, LEU, ILE', 'ASP': 'GLU, ASN, GLN', 'SER': 'THR, ALA, CYS'}
    return sug.get(res.upper(), 'ALA, VAL, LEU')

# --- 4. UI LAYOUT ---
col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    st.markdown('<p class="main-header">Research Input</p>', unsafe_allow_html=True)
    input_mode = st.radio("Protocol", ["Upload PDB", "Remote PDB ID"])
    file_path = None
    pdb_name = "Target_Enzyme"

    if input_mode == "Upload PDB":
        uploaded_file = st.file_uploader("Select Structure", type=['pdb'])
        if uploaded_file:
            file_path = "temp.pdb"
            with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
            pdb_name = uploaded_file.name.split('.')[0]
    else:
        pdb_id = st.text_input("Enter 4-Letter PDB Code").upper()
        if pdb_id:
            file_path = PDBList().retrieve_pdb_file(pdb_id, pdir='.', file_format='pdb')
            pdb_name = pdb_id

    st.divider()
    run_1 = st.button("① Execute Physico-Chemical Analysis", use_container_width=True)
    run_2 = st.button("② Map Catalytic Active Site", use_container_width=True)
    run_3 = st.button("③ Predict Mutation Landscape", use_container_width=True)

with col_right:
    st.markdown('<p class="main-header">Scientific Output</p>', unsafe_allow_html=True)
    
    if not file_path:
        st.info("System Ready. Please initialize analysis from the input panel.")

    # SECTION 1: PHYSICO
    if run_1 and file_path:
        st.subheader("I. Molecular Characterization")
        st.latex(r"II = \frac{10}{L} \sum_{i=1}^{L-1} DIWV(x_i, x_{i+1})")
        st.write("The Instability Index (II) calculates protein viability based on dipeptide composition.")
        
        parser = PDBParser(QUIET=True)
        structure = parser.get_structure(pdb_name, file_path)
        ppb = PPBuilder()
        seq = "".join([str(p.get_sequence()) for p in ppb.build_peptides(structure)])
        analysis = ProtParam.ProteinAnalysis(seq)
        
        p_df = pd.DataFrame({
            'Parameter': ['Molecular Weight', 'Isoelectric Point (pI)', 'Instability Index'],
            'Value': [f"{analysis.molecular_weight()/1000:.2f} kDa", f"{analysis.isoelectric_point():.2f}", f"{analysis.instability_index():.2f}"]
        })
        st.table(p_df)
        
        methods = "Analysis performed using the ExPASy ProtParam protocol. Instability Index > 40 indicates potential in-vivo instability."
        formulas = ["MW = Σ(Atomic Weights)", "pI = pH where Net Charge = 0"]
        rep = create_prof_report("Physico-Chemical Analysis", methods, formulas, p_df)
        st.download_button("📥 Download Technical Report", rep, f"{pdb_name}_Physico.docx")

    # SECTION 3: MUTATION (Including Graph)
    if run_3 and file_path:
        st.subheader("III. Mutation Prediction & Flexibility Landscape")
        
        # Data Generation
        res_list = []
        for atom in structure.get_atoms():
            res_list.append({"Pos": atom.get_parent().id[1], "B": atom.get_bfactor(), "Res": atom.get_parent().resname})
        df_mut = pd.DataFrame(res_list).groupby(['Pos', 'Res']).mean().reset_index()
        df_mut['Score'] = (df_mut['B'] / df_mut['B'].max()) * 100
        df_mut['Suggestions'] = df_mut['Res'].apply(get_mutation_suggestions)
        
        # Plotting
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df_mut['Pos'], df_mut['Score'], color='#1E3A8A', linewidth=1.5)
        ax.fill_between(df_mut['Pos'], df_mut['Score'], alpha=0.2, color='#1E3A8A')
        ax.set_xlabel("Residue Position")
        ax.set_ylabel("Flexibility Score (Normalized B-Factor)")
        st.pyplot(fig)
        
        # Save plot to buffer for report
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        
        st.dataframe(df_mut.nlargest(10, 'Score').style.format({'Score': '{:.2f}'}))
        
        m_methods = "Mutational hotspots identified via normalized B-factor analysis (atomic displacement parameters)."
        m_formulas = ["Score = (B_observed / B_max) * 100"]
        rep_m = create_prof_report("Mutation Landscape", m_methods, m_formulas, df_mut.nlargest(10, 'Score'), buf)
        st.download_button("📥 Download Mutation Strategy", rep_m, f"{pdb_name}_Mutation.docx")
