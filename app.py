import streamlit as st
import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
from Bio.PDB import PDBParser, PDBList
from Bio.PDB.SASA import ShrakeRupley
from docx import Document
import io

# Page Setup
st.set_page_config(page_title="Enzyme Mutation Predictor", layout="wide")
st.title("🧬 Enzyme Optimization & Mutation Pipeline")
st.markdown("Predict structural hotspots using Shrake-Rupley SASA and B-Factor analysis.")

# --- 1. STABLE ANALYSIS ENGINE ---
def run_analysis(pdb_path):
    parser = PDBParser(QUIET=True)
    try:
        structure = parser.get_structure("protein", pdb_path)
    except Exception as e:
        st.error(f"Error parsing PDB file: {e}")
        return None
        
    model = structure[0]
    
    # ShrakeRupley is built-in to Biopython. No extra installs needed.
    sr = ShrakeRupley()
    try:
        sr.compute(model, level="R")
    except Exception as e:
        st.error(f"SASA Computation failed: {e}")
        return None

    res_data = []
    # Identify the target chain (Chain A / first chain)
    target_chain = list(model.child_dict.keys())[0]

    for residue in model[target_chain]:
        if 'CA' in residue:
            try:
                # Retrieve SASA and B-Factor
                sasa_val = residue.sasa
                b_factor = residue['CA'].get_bfactor()
                
                res_data.append({
                    "Residue": residue.get_resname(),
                    "Position": residue.id[1],
                    "rSASA": sasa_val / 200, 
                    "B_Factor": b_factor
                })
            except:
                continue

    df = pd.DataFrame(res_data)
    if df.empty:
        return None

    # Normalization & Hotspot Scoring
    b_min, b_max = df['B_Factor'].min(), df['B_Factor'].max()
    df['Norm_B'] = (df['B_Factor'] - b_min) / (b_max - b_min) * 100 if b_max != b_min else 0
    df['Hotspot_Score'] = (0.5 * df['Norm_B']) + (0.5 * (df['rSASA'] * 100))
    
    return df

# --- 2. REPLACEMENT LOGIC ---
def get_replacements(wt):
    hydrophobic = ['ALA', 'VAL', 'LEU', 'ILE', 'MET', 'PHE', 'TRP', 'PRO']
    charged = ['ARG', 'LYS', 'ASP', 'GLU', 'HIS']
    if wt in hydrophobic: return "S, T, A, Q, N"
    elif wt in charged: return "A, N, Q, S, T"
    else: return "A, V, I, L, F"

# --- 3. SIDEBAR & INPUT ---
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
        with st.spinner("Downloading..."):
            raw = pdbl.retrieve_pdb_file(pdb_id, pdir='.', file_format='pdb')
            if os.path.exists(raw):
                shutil.move(raw, "input.pdb")
                pdb_file = "input.pdb"
                pdb_name = pdb_id

# --- 4. THE RESULT SECTION ---
if pdb_file:
    with st.spinner("Running Analysis..."):
        df = run_analysis(pdb_file)

    if df is not None:
        st.success(f"Analysis for {pdb_name} complete!")
        
        # Graph
        st.subheader("Structural Hotspot Landscape")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.fill_between(df['Position'], df['Hotspot_Score'], color="#4e79a7", alpha=0.3)
        ax.plot(df['Position'], df['Hotspot_Score'], color="#4e79a7", lw=2)
        ax.set_ylabel("Mutation Hotspot Score")
        ax.set_xlabel("Residue Position")
        st.pyplot(fig)

        # Table
        st.subheader("🔥 Top 10 Mutation Hotspots")
        top_10 = df.sort_values("Hotspot_Score", ascending=False).head(10)
        display_df = top_10[['Position', 'Residue', 'Hotspot_Score']].copy()
        display_df['Suggested Replacements'] = display_df['Residue'].apply(get_replacements)
        st.table(display_df)

        # Report Generation
        doc = Document()
        doc.add_heading(f"Enzyme Mutation Report: {pdb_name}", 0)
        doc.add_paragraph("Analysis using Shrake-Rupley SASA and B-Factor flexibility.")
        
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text = 'Pos', 'Res', 'Score', 'Replacements'
        for _, row in display_df.iterrows():
            row_cells = table.add_row().cells
            row_cells[0].text, row_cells[1].text = str(int(row['Position'])), str(row['Residue'])
            row_cells[2].text, row_cells[3].text = str(round(row['Hotspot_Score'], 2)), str(row['Suggested Replacements'])

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        st.download_button("📄 Download Report (.docx)", buffer, f"Report_{pdb_name}.docx")
