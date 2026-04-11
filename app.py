import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from Bio.PDB import PDBParser, PDBList
from Bio.PDB.SASA import ShrakeRupley
from docx import Document
import io

# Page Setup
st.set_page_config(page_title="Enzyme Mutation Predictor", layout="wide")
st.title("🧬 Professional Enzyme Mutation Pipeline")

# --- 1. REFINED ANALYSIS ENGINE ---
def run_analysis(pdb_path):
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("protein", pdb_path)
    model = structure[0]
    
    # Using ShrakeRupley for cross-platform stability
    sr = ShrakeRupley()
    sr.compute(model, level="R")

    res_data = []
    target_chain = list(model.child_dict.keys())[0]

    for residue in model[target_chain]:
        if 'CA' in residue:
            try:
                sasa_val = residue.sasa
                b_factor = residue['CA'].get_bfactor()
                
                res_data.append({
                    "Residue": residue.get_resname(),
                    "Position": residue.id[1],
                    "SASA": sasa_val,
                    "B_Factor": b_factor
                })
            except: continue

    df = pd.DataFrame(res_data)
    if df.empty: return None

    # --- ADVANCED SCORING ---
    # Normalizing values for a balanced score
    df['Norm_B'] = (df['B_Factor'] - df['B_Factor'].min()) / (df['B_Factor'].max() - df['B_Factor'].min())
    df['Norm_SASA'] = (df['SASA'] - df['SASA'].min()) / (df['SASA'].max() - df['SASA'].min())
    
    # Weighted Score: Priority on B-factor (Flexibility) for stability prediction
    df['Raw_Score'] = (0.6 * df['Norm_B'] + 0.4 * df['Norm_SASA']) * 100
    
    # SMOOTHING: Moving Average (Standard Window of 5 residues)
    # This removes the noise seen in previous versions without needing scipy
    df['Hotspot_Score'] = df['Raw_Score'].rolling(window=5, center=True).mean().fillna(df['Raw_Score'])
    
    return df

# --- 2. REPLACEMENT LOGIC ---
def get_replacements(wt):
    mapping = {
        'ALA': 'SER, THR', 'VAL': 'ILE, LEU', 'ILE': 'VAL, LEU',
        'LEU': 'ILE, VAL', 'MET': 'ALA, LEU', 'PHE': 'TYR, TRP',
        'TRP': 'PHE, TYR', 'PRO': 'ALA, GLY', 'SER': 'THR, ALA',
        'THR': 'SER, ALA', 'CYS': 'SER, ALA', 'TYR': 'PHE, HIS',
        'ASN': 'GLN, ASP', 'GLN': 'ASN, GLU', 'ASP': 'GLU, ASN',
        'GLU': 'ASP, GLN', 'LYS': 'ARG, GLN', 'ARG': 'LYS, GLN',
        'HIS': 'TYR, ASN', 'GLY': 'ALA, PRO'
    }
    return mapping.get(wt, "ALA, GLY")

# --- 3. SIDEBAR & INPUT ---
st.sidebar.header("Pipeline Controls")
pdb_id = st.sidebar.text_input("Enter 4-Digit PDB ID", value="4TKX").strip().upper()
fetch = st.sidebar.button("Fetch & Analyze")

# --- 4. EXECUTION & VISUALS ---
if fetch:
    pdbl = PDBList()
    with st.spinner("Processing structural data..."):
        raw = pdbl.retrieve_pdb_file(pdb_id, pdir='.', file_format='pdb')
        df = run_analysis(raw)

    if df is not None:
        st.success(f"Analysis for {pdb_id} complete!")
        
        # PROFESSIONAL GRAPH
        st.subheader("📍 Smoothed Structural Hotspot Landscape")
        fig, ax = plt.subplots(figsize=(12, 5))
        
        # Line plot with shaded area
        ax.plot(df['Position'], df['Hotspot_Score'], color="#1f77b4", lw=2, label="Flexibility Score")
        ax.fill_between(df['Position'], df['Hotspot_Score'], color="#1f77b4", alpha=0.2)
        
        # Clean aesthetics for pharmaceutical reports
        ax.set_title(f"Residue Hotspot Mapping: {pdb_id}", fontsize=14, fontweight='bold')
        ax.set_ylabel("Mutation Hotspot Score", fontsize=12)
        ax.set_xlabel("Residue Position", fontsize=12)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        st.pyplot(fig)

        # TOP CANDIDATES TABLE
        st.subheader("🔥 Strategic Mutation Candidates")
        top_10 = df.sort_values("Hotspot_Score", ascending=False).head(10)
        
        display_df = top_10[['Position', 'Residue', 'Hotspot_Score']].copy()
        display_df['Suggestions'] = display_df['Residue'].apply(get_replacements)
        
        # Using background gradient for visual heat-mapping
        st.dataframe(display_df.style.background_gradient(subset=['Hotspot_Score'], cmap='OrRd'))

        # WORD REPORT GENERATION
        doc = Document()
        doc.add_heading(f"Enzyme Mutation Strategy: {pdb_id}", 0)
        doc.add_paragraph(f"Targeting high-flexibility residues in {pdb_id} to optimize enzymatic potential.")
        
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text = 'Pos', 'Res', 'Score', 'Replacements'

        for _, row in display_df.iterrows():
            cells = table.add_row().cells
            cells[0].text, cells[1].text = str(int(row['Position'])), row['Residue']
            cells[2].text, cells[3].text = str(round(row['Hotspot_Score'], 2)), row['Suggestions']

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        st.download_button("📄 Download Professional Report", buffer, f"Strategy_{pdb_id}.docx")
