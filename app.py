import streamlit as st
import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
from Bio.PDB import PDBParser, DSSP, PDBList
from docx import Document
from docx.shared import Inches
import io

# Page Setup
st.set_page_config(page_title="Enzyme Mutation Predictor", layout="wide")
st.title("🧬 Enzyme Optimization & Mutation Pipeline")
st.markdown("Predict structural hotspots and generate engineering reports using DSSP and B-Factor analysis.")

# --- Analysis Functions ---
def run_analysis(pdb_path):
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("protein", pdb_path)
    model = structure[0]
    
    # Check for DSSP executable (Streamlit servers usually use 'mkdssp' or 'dssp')
    executable = "mkdssp" if shutil.which("mkdssp") else "dssp"

    try:
        # CRITICAL FIX: file_type="PDB" is required for modern DSSP 4+ versions
        dssp = DSSP(model, pdb_path, dssp=executable, file_type="PDB")
    except Exception as e:
        # Fallback for older versions if the new command fails
        try:
            dssp = DSSP(model, pdb_path, dssp=executable)
        except Exception as e2:
            st.error(f"DSSP computation failed: {e2}")
            return None

    res_data = []
    # Automatically identify the first chain in the PDB file
    target_chain = list(model.child_dict.keys())[0]

    for key in dssp.keys():
        chain_id, res_info = key[0], key[1]
        if chain_id != target_chain: continue
        
        dssp_data = dssp[key]
        amino_acid, rSASA = dssp_data[1], dssp_data[4]

        try:
            residue_obj = model[chain_id][res_info]
            if 'CA' in residue_obj:
                b_factor = residue_obj['CA'].get_bfactor()
                res_data.append({
                    "Residue": amino_acid, "Position": res_info[1],
                    "rSASA": rSASA, "B_Factor": b_factor
                })
        except: continue

    df = pd.DataFrame(res_data)
    if df.empty: return None

    # Normalization & Hotspot Scoring
    b_min, b_max = df['B_Factor'].min(), df['B_Factor'].max()
    df['Norm_B'] = (df['B_Factor'] - b_min) / (b_max - b_min) * 100 if b_max != b_min else 0
    df['Hotspot_Score'] = (0.5 * df['Norm_B']) + (0.5 * (df['rSASA'] * 100))
    
    return df

def get_replacements(wt):
    if wt in ['A', 'V', 'L', 'I', 'M', 'F', 'W', 'P']: return "S, T, A, Q, N"
    elif wt in ['R', 'K', 'D', 'E', 'H']: return "A, N, Q, S, T"
    else: return "A, V, I, L, F"

# --- Sidebar / Input ---
st.sidebar.header("Input Settings")
mode = st.sidebar.selectbox("Select Mode", ["Upload PDB", "Download from PDB Bank"])

pdb_file = None
pdb_name = "protein"

if mode == "Upload PDB":
    file_upload = st.sidebar.file_uploader("Upload .pdb file", type="pdb")
    if file_upload:
        with open("input.pdb", "wb") as f:
            f.write(file_upload.getbuffer())
        pdb_file = "input.pdb"
        pdb_name = file_upload.name.split('.')[0]
else:
    pdb_id = st.sidebar.text_input("Enter 4-Digit PDB ID", value="4TKX").strip().upper()
    if st.sidebar.button("Fetch PDB"):
        pdbl = PDBList()
        raw = pdbl.retrieve_pdb_file(pdb_id, pdir='.', file_format='pdb')
        # Handle different PDBList naming conventions
        if os.path.exists(raw):
            shutil.move(raw, "input.pdb")
            pdb_file = "input.pdb"
            pdb_name = pdb_id
        else:
            st.error("Could not locate the downloaded PDB file.")

# --- Execution ---
if pdb_file:
    with st.spinner("Analyzing structural dynamics..."):
        df = run_analysis(pdb_file)

    if df is not None:
        st.success(f"Analysis for {pdb_name} complete!")
        
        # Plotting
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.fill_between(df['Position'], df['Hotspot_Score'], color="#4e79a7", alpha=0.3)
        ax.plot(df['Position'], df['Hotspot_Score'], color="#4e79a7", lw=2)
        ax.set_ylabel("Mutation Hotspot Score")
        ax.set_xlabel("Residue Index")
        st.pyplot(fig)

        # Top Candidates Table
        top_10 = df.sort_values("Hotspot_Score", ascending=False).head(10)
        st.subheader("🔥 Top 10 Mutation Hotspots")
        
        display_df = top_10[['Position', 'Residue', 'Hotspot_Score']].copy()
        display_df['Suggested Replacements'] = display_df['Residue'].apply(get_replacements)
        st.table(display_df)

        # Word Report Generation
        doc = Document()
        doc.add_heading(f"Enzyme Mutation Report: {pdb_name}", 0)
        doc.add_paragraph("Identified hotspots based on solvent accessibility and B-factor flexibility.")
        
        # Table in Word
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Position'
        hdr_cells[1].text = 'Residue'
        hdr_cells[2].text = 'Score'
        hdr_cells[3].text = 'Replacements'

        for _, row in display_df.iterrows():
            row_cells = table.add_row().cells
            row_cells[0].text = str(int(row['Position']))
            row_cells[1].text = str(row['Residue'])
            row_cells[2].text = str(round(row['Hotspot_Score'], 2))
            row_cells[3].text = str(row['Suggested Replacements'])

        # Save to buffer for download
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        st.download_button(
            label="📄 Download Report (.docx)",
            data=buffer,
            file_name=f"Mutation_Report_{pdb_name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
