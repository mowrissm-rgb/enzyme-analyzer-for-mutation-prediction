import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from docx import Document
from docx.shared import Pt, Inches
import io

# --- 1. CORE LOGIC: Mutation Suggestions ---
def get_top_6_suggestions(original_res):
    """Provides 6 suggestions based on biochemical similarity."""
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

# --- 2. PROFESSIONAL REPORT GENERATION ---
def generate_professional_report(pdb_id, df, fig):
    doc = Document()
    doc.add_heading(f'Enzyme Mutation Strategy Report: {pdb_id}', 0)
    
    # Methodology & Formula
    doc.add_heading('1. Methodology', level=1)
    doc.add_paragraph(
        "This pipeline identifies structural mutation hotspots by integrating Solvent Accessible "
        "Surface Area (SASA) via the Shrake-Rupley algorithm and B-factor flexibility analysis."
    )
    
    doc.add_heading('2. Scoring Formula', level=1)
    doc.add_paragraph('Score = (w1 × Normalized SASA) + (w2 × Normalized B-factor)')
    
    doc.add_heading('Where:', level=2)
    defs = [
        ("w1 / w2", "Weighting factors (Standard: 0.5/0.5)."),
        ("Normalized SASA", "Relative solvent accessibility (0-100 scale)."),
        ("Normalized B-factor", "Atomic displacement parameter for local chain flexibility.")
    ]
    for term, definition in defs:
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(f'{term}: ').bold = True
        p.add_run(definition)

    # Embedded Graph
    doc.add_heading('3. Structural Hotspot Landscape', level=1)
    img_bytes = fig.to_image(format="png", width=1000, height=450)
    doc.add_picture(io.BytesIO(img_bytes), width=Inches(6))

    # Mutation Table
    doc.add_heading('4. Mutation Candidate Analysis', level=1)
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Light Shading Accent 1'
    for i, h in enumerate(['Position', 'Residue', 'Hotspot Score', 'Top 6 Suggestions']):
        table.rows[0].cells[i].text = h

    for _, row in df.iterrows():
        row_cells = table.add_row().cells
        row_cells[0].text, row_cells[1].text = str(row['Pos']), str(row['Res'])
        row_cells[2].text, row_cells[3].text = f"{row['
