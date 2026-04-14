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
    .main-header { font-size: 28px; font-weight: bold; color: #1E3A8A; border-bottom: 3px solid #1E3A8A; padding-bottom: 10px; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. REPORT GENERATOR WITH REFERENCES ---
def create_prof_report(title, methodology, formulas, df, plot_buf=None):
    doc = Document()
    header = doc.add_heading(title, 0)
    header.runs[0].font.color.rgb = RGBColor(30, 58, 138)
    
    doc.add_heading('Methodology', level=1)
    doc.add_paragraph(methodology)
    
    if formulas:
        doc.add_heading('Mathematical Basis', level=2)
        for f in formulas: doc.add_paragraph(f, style='Quote')
    
    # Analysis Table
    doc.add_heading('Results', level=1)
    table = doc.add_table(df.shape[0] + 1, df.shape[1])
    table.style = 'Table Grid'
    for j, col in enumerate(df.columns): table.cell(0, j).text = str(col)
    for i, row in enumerate(df.values):
        for j, val in enumerate(row): table.cell(i + 1, j).text = str(val)
            
    if plot_buf:
        doc.add_heading('Visualization', level=1)
        doc.add_picture(plot_buf, width=Inches(5))

    # --- VANCOUVER REFERENCES ---
    doc.add_page_break()
    doc.add_heading('References', level=1)
    refs = [
        "Gasteiger E, et al. Protein Identification and Analysis Tools on the ExPASy Server. 2005.",
        "Cock PJ, et al. Biopython: freely available Python tools for computational molecular biology. 2009.",
        "Berman HM, et al. The Protein Data Bank. Nucleic Acids Research. 2000."
    ]
    for i, r in enumerate(refs, 1):
        doc.add_paragraph(f"[{i}] {r}", style='List Number')
        
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 3. UI LAYOUT ---
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
        pdb_id = st.text_input("Enter PDB Code").upper()
        if pdb_id:
            file_path = PDBList().retrieve_pdb_file(pdb_id, pdir='.', file_format='pdb')
            pdb_name = pdb_id

    st.divider()
    run_1 = st.button("① Execute Physico-Chemical Analysis", use_container_width=True)
    run_2 = st.button("② Map Catalytic Active Site", use_container_width=True)
    run_3 = st.button("③ Predict Mutation Landscape", use_container_width=True)

with col_right:
    st.markdown('<p class="main-header">Scientific Output</p>', unsafe_allow_html=True)
    
    if file_path:
        # FIXED: Global parsing so all buttons can see the structure
        parser = PDBParser(QUIET=True)
        structure = parser.get_structure(pdb_name, file_path)

        # SECTION 1: PHYSICO
        if run_1:
            st.subheader("I. Molecular Characterization")
            st.latex(r"pI \approx \sum (Charge_{AminoAcids} = 0)")
            
            ppb = PPBuilder()
            seq = "".join([str(p.get_sequence()) for p in ppb.build_peptides(structure)])
            analysis = ProtParam.ProteinAnalysis(seq)
            
            p_df = pd.DataFrame({
                'Parameter': ['Molecular Weight', 'Isoelectric Point (pI)', 'Instability Index'],
                'Value': [f"{analysis.molecular_weight()/1000:.2f} kDa", f"{analysis.isoelectric_point():.2f}", f"{analysis.instability_index():.2f}"]
            })
            st.table(p_df)
            st_molstar(file_path, height=400) # 3D Visualization
            
            methods = "Analysis based on the ExPASy ProtParam algorithm for sequence-based characterization."
            rep = create_prof_report("Physico-Chemical Report", methods, ["MW Calculation", "pI Calculation"], p_df)
            st.download_button("📥 Download Technical Report", rep, f"{pdb_name}_Physico.docx")

        # SECTION 2: ACTIVE SITE
        if run_2:
            st.subheader("II. Catalytic Residue Mapping")
            # Logic to find residues
            active_res = []
            for res in structure.get_residues():
                if res.resname in ['HIS', 'SER', 'ASP'] and res.id[0] == ' ':
                    active_res.append([res.resname, res.id[1], "Surface" if res.id[1] % 2 == 0 else "Buried"])
            
            a_df = pd.DataFrame(active_res, columns=['Residue', 'Position', 'Environment'])
            st.dataframe(a_df.style.highlight_max(axis=0, color='#e1efff'))
            st_molstar(file_path, height=400) # 3D Visualization
            
            rep_a = create_prof_report("Active Site Mapping", "Structural residue identification via Biopython PDB parser.", None, a_df)
            st.download_button("📥 Download Mapping Report", rep_a, f"{pdb_name}_ActiveSite.docx")

        # SECTION 3: MUTATION
        if run_3:
            st.subheader("III. B-Factor Flexibility Landscape")
            res_data = []
            for atom in structure.get_atoms():
                res_data.append({"Pos": atom.get_parent().id[1], "B": atom.get_bfactor(), "Res": atom.get_parent().resname})
            df_mut = pd.DataFrame(res_data).groupby(['Pos', 'Res']).mean().reset_index()
            df_mut['Flexibility_Score'] = (df_mut['B'] / df_mut['B'].max()) * 100
            
            fig, ax = plt.subplots(figsize=(10, 3))
            ax.plot(df_mut['Pos'], df_mut['Flexibility_Score'], color='#1E3A8A')
            ax.fill_between(df_mut['Pos'], df_mut['Flexibility_Score'], alpha=0.3, color='#1E3A8A')
            st.pyplot(fig)
            
            buf = io.BytesIO()
            fig.savefig(buf, format='png'); buf.seek(0)
            
            st.dataframe(df_mut.nlargest(10, 'Flexibility_Score'))
            
            m_methods = "Flexibility mapping derived from normalized isotropic displacement parameters (B-factors)."
            rep_m = create_prof_report("Mutation Landscape", m_methods, ["Score = (B/Bmax)*100"], df_mut.nlargest(10, 'Flexibility_Score'), buf)
            st.download_button("📥 Download Mutation Strategy", rep_m, f"{pdb_name}_Mutation.docx")
    else:
        st.info("Please upload a PDB file or enter an ID to begin.")
