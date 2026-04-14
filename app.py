import streamlit as st
import os
import io
import pandas as pd
import numpy as np
from Bio.PDB import PDBParser, PPBuilder, PDBList
from Bio.SeqUtils import ProtParam
from docx import Document
from docx.shared import Pt, RGBColor
from streamlit_molstar import st_molstar

# --- 1. CONFIG ---
st.set_page_config(page_title="Enzyme Optimization Hub", layout="wide")

# --- 2. CORE UTILITIES ---
def get_top_6_suggestions(res):
    suggestions = {
        'GLY': 'ALA, PRO, SER, VAL, ILE, LEU', 'ALA': 'VAL, LEU, ILE, SER, THR, MET', 
        'ASP': 'GLU, ASN, GLN, HIS, LYS, ARG', 'SER': 'THR, ALA, CYS, ASN, GLN, TYR',
        'HIS': 'PHE, TYR, TRP, ASN, GLN, LYS', 'THR': 'SER, VAL, ALA, ILE, MET, ASN'
    }
    return suggestions.get(res.upper(), 'ALA, VAL, LEU, ILE, SER, THR')

# --- 3. REPORT GENERATORS ---
def apply_report_style(doc, title):
    heading = doc.add_heading(level=0)
    run = heading.add_run(title)
    run.font.color.rgb = RGBColor(0, 112, 192)

def add_vancouver_refs(doc):
    doc.add_page_break()
    doc.add_heading('References', level=1)
    refs = [
        "Gasteiger E, et al. Protein Identification and Analysis Tools on the ExPASy Server. 2005.",
        "Cock PJ, et al. Biopython: computational biology. 2009.",
        "Berman HM, et al. The Protein Data Bank. 2000."
    ]
    for i, r in enumerate(refs, 1):
        doc.add_paragraph(f"[{i}] {r}", style='List Number')

def gen_physico_report(data, name):
    doc = Document()
    apply_report_style(doc, f'Physicochemical Characterization: {name}')
    table = doc.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text = 'Parameter', 'Value'
    params = [('Molecular Weight', f"{data['MW']:.2f} kDa"), ('pI', f"{data['pI']:.2f}"), ('Instability Index', f"{data['II']:.2f}")]
    for p, v in params:
        row = table.add_row().cells
        row[0].text, row[1].text = p, v
    add_vancouver_refs(doc)
    bio = io.BytesIO(); doc.save(bio); return bio.getvalue()

def gen_active_site_report(data, name):
    doc = Document()
    apply_report_style(doc, f'Active Site & Catalytic Residue Mapping: {name}')
    for res_type, residues in data.items():
        if residues:
            doc.add_heading(f'Table: {res_type} Residues', level=2)
            t = doc.add_table(rows=1, cols=1); t.style = 'Light Shading Accent 1'
            t.rows[0].cells[0].text = 'Residue Position'
            for r in residues: t.add_row().cells[0].text = r
    add_vancouver_refs(doc)
    bio = io.BytesIO(); doc.save(bio); return bio.getvalue()

def gen_mutation_report(df, name):
    doc = Document()
    apply_report_style(doc, f'Mutation Hotspot Strategy: {name}')
    table = doc.add_table(rows=1, cols=4); table.style = 'Medium List 1 Accent 1'
    cols = ['Position', 'Residue', 'Flexibility Score', 'Substitution Suggestions']
    for i, h in enumerate(cols): table.rows[0].cells[i].text = h
    for _, r in df.iterrows():
        row = table.add_row().cells
        row[0].text, row[1].text = str(r['Pos']), r['Res']
        row[2].text, row[3].text = f"{r['Score']:.2f}", r['Suggestions']
    add_vancouver_refs(doc)
    bio = io.BytesIO(); doc.save(bio); return bio.getvalue()

# --- 4. SIDEBAR & INPUT ---
with st.sidebar:
    st.header("⚙️ Control Center")
    input_mode = st.radio("Input Method", ["Upload PDB", "PDB ID"])
    file_path = None
    pdb_name = "Analysis"

    if input_mode == "Upload PDB":
        uploaded_file = st.file_uploader("Choose PDB file", type=['pdb'])
        if uploaded_file:
            file_path = "temp.pdb"
            with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
            pdb_name = uploaded_file.name.split('.')[0]
    else:
        pdb_id = st.text_input("Enter PDB ID").upper()
        if pdb_id:
            file_path = PDBList().retrieve_pdb_file(pdb_id, pdir='.', file_format='pdb')
            pdb_name = pdb_id

    st.divider()
    analyze_btn = st.button("🚀 Run Full Pipeline")

# --- 5. EXECUTION & REPOSITIONED UI ---
if analyze_btn and file_path:
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure(pdb_name, file_path)
    
    # 1. Pipeline: Physicochemical
    ppb = PPBuilder()
    seq = "".join([str(p.get_sequence()) for p in ppb.build_peptides(structure)])
    analysis = ProtParam.ProteinAnalysis(seq)
    p_data = {"MW": analysis.molecular_weight()/1000, "pI": analysis.isoelectric_point(), "II": analysis.instability_index()}
    rep_p = gen_physico_report(p_data, pdb_name)

    # 2. Pipeline: Active Site
    res_map = {'HIS': [], 'SER': [], 'ASP': []}
    for res in structure.get_residues():
        if res.resname in res_map and res.id[0] == ' ':
            res_map[res.resname].append(f"{res.resname}{res.id[1]}")
    rep_a = gen_active_site_report(res_map, pdb_name)

    # 3. Pipeline: Mutation (SASA/B-Factor Landscape)
    res_list = []
    for atom in structure.get_atoms():
        # Capturing B-factor (Flexibility) as a proxy for hotspot identification
        res_list.append({"Pos": atom.get_parent().id[1], "Res": atom.get_parent().resname, "B_factor": atom.get_bfactor()})
    df_atoms = pd.DataFrame(res_list).groupby(['Pos', 'Res']).mean().reset_index()
    df_atoms['Score'] = (df_atoms['B_factor'] / df_atoms['B_factor'].max()) * 100
    df_atoms['Suggestions'] = df_atoms['Res'].apply(get_top_6_suggestions)
    top_df = df_atoms.nlargest(15, 'Score')
    rep_m = gen_mutation_report(top_df, pdb_name)

    # --- THE REPOSITIONED DOWNLOAD SECTION ---
    # This now appears immediately after clicking 'Run' but before the big tabs
    st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #0070c0; margin-bottom: 20px;">
            <p style="font-size: 1.1rem; color: #333; margin: 0;">
                <b>Pipeline Finished!</b> Download your research docs here: ⬇️
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    with btn_col1:
        st.download_button("📥 Physico docx", rep_p, f"{pdb_name}_Physico.docx", use_container_width=True)
    with btn_col2:
        st.download_button("📥 Active Site docx", rep_a, f"{pdb_name}_ActiveSite.docx", use_container_width=True)
    with btn_col3:
        st.download_button("📥 Mutation docx", rep_m, f"{pdb_name}_Mutation.docx", use_container_width=True)

    st.divider()

    # --- TABS FOR VISUALIZATION ---
    t1, t2, t3 = st.tabs(["📊 Physicochemical", "🔍 Active Site", "🧪 Mutation Strategy"])
    with t1:
        c1, c2, c3 = st.columns(3)
        c1.metric("Weight (kDa)", f"{p_data['MW']:.2f}")
        c2.metric("pI", f"{p_data['pI']:.2f}")
        c3.metric("Instability Index", f"{p_data['II']:.2f}")
        st_molstar(file_path, height=500)
    with t2:
        st.write("### Structural Mapping of Catalytic Residues")
        st.json(res_map)
    with t3:
        st.write("### B-Factor Flexibility Landscape")
        st.dataframe(top_df, use_container_width=True)

else:
    st.info("Upload a structure to begin the optimization pipeline.")
