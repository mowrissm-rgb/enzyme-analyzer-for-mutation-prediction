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

# --- 3. REPORT GENERATORS (PROFESSIONAL WORD STYLING) ---
def apply_report_style(doc, title):
    heading = doc.add_heading(level=0)
    run = heading.add_run(title)
    run.font.color.rgb = RGBColor(0, 112, 192) # Professional Sky Blue

def add_vancouver_refs(doc):
    doc.add_page_break()
    doc.add_heading('References', level=1)
    refs = [
        "Gasteiger E, et al. Protein Identification and Analysis Tools on the ExPASy Server. 2005.",
        "Cock PJ, et al. Biopython: freely available Python tools for computational molecular biology and bioinformatics. 2009.",
        "Berman HM, et al. The Protein Data Bank. Nucleic Acids Research. 2000."
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
    params = [('Molecular Weight', f"{data['MW']:.2f} kDa"), 
              ('Isoelectric Point (pI)', f"{data['pI']:.2f}"), 
              ('Instability Index', f"{data['II']:.2f}")]
    for p, v in params:
        row = table.add_row().cells
        row[0].text, row[1].text = p, v
    add_vancouver_refs(doc)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def gen_active_site_report(data, name):
    doc = Document()
    apply_report_style(doc, f'Active Site & Catalytic Residue Mapping: {name}')
    for res_type, residues in data.items():
        if residues:
            doc.add_heading(f'Table: {res_type} Residues', level=2)
            t = doc.add_table(rows=1, cols=1)
            t.style = 'Light Shading Accent 1'
            t.rows[0].cells[0].text = 'Residue Position'
            for r in residues:
                t.add_row().cells[0].text = r
    add_vancouver_refs(doc)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def gen_mutation_report(df, name):
    doc = Document()
    apply_report_style(doc, f'Mutation Hotspot Strategy: {name}')
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Medium List 1 Accent 1'
    cols = ['Position', 'Residue', 'Flexibility Score', 'Substitution Suggestions']
