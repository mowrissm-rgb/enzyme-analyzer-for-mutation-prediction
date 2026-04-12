import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from docx import Document
from docx.shared import Inches
import io

# --- 1. DYNAMIC SUGGESTIONS ---
def get_top_6_suggestions(original_res):
    suggestions_map = {
        'GLY': 'ALA, PRO, SER, VAL, ILE, LEU',
        'ALA': 'VAL, LEU, ILE, SER, THR, MET',
        'ASP': 'GLU, ASN, GLN, HIS, LYS, ARG',
        'SER': 'THR, ALA, CYS, ASN, GLN, TYR',
        'HIS': 'PHE, TYR, TRP, ASN, GLN, LYS',
        'THR': 'SER, VAL, ALA, ILE, MET, ASN',
        'ILE': 'VAL, LEU, MET, PHE, ALA, TRP',
        'ASN': 'GLN, ASP, GLU, HIS, SER, THR',
        'DEFAULT': 'ALA, VAL, LEU, ILE, SER, THR'
    }
    return suggestions_map.get(original_res.upper(), suggestions_map['DEFAULT'])

# --- 2. REPORT GENERATOR ---
def generate_professional_report(pdb_id, df, fig):
    doc = Document()
    doc.add_heading(f'Enzyme Mutation Strategy Report: {pdb_id}', 0)
    
    doc.add_heading('1. Methodology', level=1)
    doc.add_paragraph("This pipeline identifies structural mutation hotspots by integrating Solvent Accessible Surface Area (SASA) and B-factor flexibility analysis.")
    
    doc.add_heading('2. Scoring Formula', level=1)
    doc.add_paragraph('Score = (w1 × Normalized SASA) + (w2 × Normalized B-factor)')
    
    doc.add_heading('3. Structural Hotspot Landscape', level=1)
    try:
        # Attempt to render the image for the Word doc
        img_bytes = fig.to_image(format="png", engine="kaleido", width=1000, height=450)
        doc.add_picture(io.BytesIO(img_bytes), width=Inches(6))
    except Exception:
        doc.add_paragraph("[Graph rendering skipped for compatibility]")

    doc.add_heading('4. Mutation Candidate Analysis', level=1)
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Light Shading Accent 1'
    for i, h in enumerate(['Position', 'Residue', 'Score', 'Suggestions']):
        table.rows[0].cells[i].text = h

    for _, row in df.iterrows():
        cells = table.add_row().cells
        cells[0].text, cells[1].text = str(row['Pos']), str(row['Res'])
        cells[2].text, cells[3].text = f"{row['Score']:.2f}", row['Top 6 Suggestions']

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- 3. UI ---
st.set_page_config(page_title="Enzyme Pipeline", layout="wide")
st.title("🧬 Enzyme Engineering & Mutation Pipeline")

with st.sidebar:
    st.header("Settings")
    input_mode = st.radio("Input Method", ["Upload PDB File", "Fetch by PDB ID"])
    pdb_id = st.text_input("Project Name/ID", value="4TKX")
    if input_mode == "Upload PDB File":
        uploaded_file = st.file_uploader("Upload PDB", type=["pdb"])
    run_btn = st.button("🚀 Run Analysis", use_container_width=True)

if 'df_results' in st.session_state:
    df = st.session_state.df_results.sort_values(by='Pos')
    df['Top 6 Suggestions'] = df['Res'].apply(get_top_6_suggestions)

    t1, t2, t3 = st.tabs(["📊 Landscape", "📋 Table", "📑 Report"])

    with t1:
        st.subheader(f"Hotspot Landscape: {pdb_id}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Pos'], y=df['Score'], mode='lines', fill='tozeroy',
            line=dict(color='rgba(135, 131, 216, 1)', width=2),
            fillcolor='rgba(173, 216, 230, 0.4)'
        ))
