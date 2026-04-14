import streamlit as st
import os
import io
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from Bio.PDB import PDBParser, PPBuilder, PDBList
from Bio.SeqUtils import ProtParam
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from streamlit_molstar import st_molstar

# --- 1. CONFIG & STYLING (WHITE & SKY BLUE THEME) ---
st.set_page_config(page_title="Enzyme Hub", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    h1, h2, h3 { color: #0284C7 !important; font-family: 'Segoe UI', sans-serif; }
    .stButton>button {
        background-color: #0284C7;
        color: white;
        border-radius: 8px;
        border: none;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #F0F9FF;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        color: #0369A1;
    }
    .stTabs [aria-selected="true"] {
        background-color: #E0F2FE !important;
        border-bottom: 3px solid #0284C7 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE UTILITIES ---
def get_top_6_suggestions(res):
    suggestions = {
        'GLY': 'ALA, PRO, SER, VAL, ILE, LEU', 'ALA': 'VAL, LEU, ILE, SER, THR, MET', 
        'ASP': 'GLU, ASN, GLN, HIS, LYS, ARG', 'SER': 'THR, ALA, CYS, ASN, GLN, TYR',
        'HIS': 'PHE, TYR, TRP, ASN, GLN, LYS', 'THR': 'SER, VAL, ALA, ILE, MET, ASN'
    }
    return suggestions.get(res.upper(), 'ALA, VAL, LEU, ILE, SER, THR')

def set_sky_blue_heading(heading, text):
    run = heading.add_run(text)
    run.font.color.rgb = RGBColor(2, 132, 199) # Sky Blue

# --- 3. INDIVIDUAL REPORT GENERATORS ---
def gen_physico_report(data, name):
    doc = Document()
    set_sky_blue_heading(doc.add_heading(level=0), f'Physicochemical Analysis: {name}')
    doc.add_paragraph("Analysis of molecular properties using ProtParam methodology.")
    
    table = doc.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text = 'Parameter', 'Value'
    
    params = [('MW', f"{data['MW']:.2f} kDa"), ('pI', f"{data['pI']:.2f}"), ('Instability Index', f"{data['II']:.2f}")]
    for p, v in params:
        row = table.add_row().cells
        row[0].text, row[1].text = p, v
    
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def gen_active_site_report(data, name):
    doc = Document()
    set_sky_blue_heading(doc.add_heading(level=0), f'Active Site Map: {name}')
    for res_type, residues in data.items():
        if residues:
            doc.add_heading(f'Residue: {res_type}', level=2)
            doc.add_paragraph(", ".join(residues))
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def gen_mutation_report(df, name):
    doc = Document()
    set_sky_blue_heading(doc.add_heading(level=0), f'Mutation Strategy: {name}')
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Light Grid Accent 1'
    for i, h in enumerate(['Pos', 'Res', 'Score', 'Suggestions']):
        table.rows[0].cells[i].text = h
    for _, r in df.iterrows():
        row = table.add_row().cells
        row[0].text, row[1].text, row[2].text, row[3].text = str(r['Pos']), r['Res'], f"{r['Score']:.1f}", r['Suggestions']
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("💠 Enzyme Control")
    input_mode = st.radio("Input Type", ["Upload PDB", "PDB ID"])
    file_path = None
    pdb_name = "Analysis"

    if input_mode == "Upload PDB":
        uploaded_file = st.file_uploader("Upload", type=['pdb'])
        if uploaded_file:
            file_path = "temp.pdb"
            with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
            pdb_name = uploaded_file.name.split('.')[0]
    else:
        pdb_id = st.text_input("Enter ID (e.g., 1A2B)").upper()
        if pdb_id:
            file_path = PDBList().retrieve_pdb_file(pdb_id, pdir='.', file_format='pdb')
            pdb_name = pdb_id

    analyze_btn = st.button("🚀 Analyze Enzyme")

# --- 5. MAIN INTERFACE ---
if analyze_btn and file_path:
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure(pdb_name, file_path)
    
    t1, t2, t3 = st.tabs(["📊 Physicochemical", "🔍 Active Site", "🧪 Mutation Details"])

    with t1:
        ppb = PPBuilder()
        seq = "".join([str(p.get_sequence()) for p in ppb.build_peptides(structure)])
        analysis = ProtParam.ProteinAnalysis(seq)
        p_data = {"MW": analysis.molecular_weight()/1000, "pI": analysis.isoelectric_point(), "II": analysis.instability_index()}
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Weight", f"{p_data['MW']:.1f} kDa")
        c2.metric("pI", f"{p_data['pI']:.2f}")
        c3.metric("Instability", f"{p_data['II']:.1f}")
        
        rep_p = gen_physico_report(p_data, pdb_name)
        st.download_button("📘 Download Physico Report", rep_p, f"{pdb_name}_Physico.docx")
        st_molstar(file_path, height=400)

    with t2:
        res_map = {'HIS': [], 'SER': [], 'ASP': []}
        for res in structure.get_residues():
            if res.resname in res_map and res.id[0] == ' ':
                res_map[res.resname].append(f"{res.resname}{res.id[1]}")
        
        st.write("### Identified Catalytic Candidates")
        st.json(res_map)
        rep_a = gen_active_site_report(res_map, pdb_name)
        st.download_button("🔍 Download Active Site Report", rep_a, f"{pdb_name}_ActiveSite.docx")

    with t3:
        res_list = [{"Pos": r.id[1], "Res": r.resname} for r in structure.get_residues() if r.id[0] == ' ']
        df = pd.DataFrame(res_list)
        df['Score'] = np.random.uniform(70, 99, len(df))
        df['Suggestions'] = df['Res'].apply(get_top_6_suggestions)
        top_df = df.nlargest(10, 'Score')
        
        st.table(top_df)
        rep_m = gen_mutation_report(top_df, pdb_name)
        st.download_button("🧪 Download Mutation Strategy", rep_m, f"{pdb_name}_Mutation.docx")
