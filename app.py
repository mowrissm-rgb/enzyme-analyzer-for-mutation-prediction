import streamlit as st
import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import subprocess
from Bio.PDB import PDBParser, PDBList
from docx import Document
import io

# Page Setup
st.set_page_config(page_title="Enzyme Mutation Predictor", layout="wide")
st.title("🧬 Enzyme Optimization & Mutation Pipeline")
st.markdown("Predict structural hotspots and generate engineering reports using DSSP and B-Factor analysis.")

# --- 1. THE REPAIRED ANALYSIS ENGINE ---
def run_analysis(pdb_path):
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("protein", pdb_path)
    model = structure[0]
    
    # Identify the correct executable on the Linux server
    executable = "mkdssp" if shutil.which("mkdssp") else "dssp"

    # DIRECT SYSTEM CALL with crash protection (--na flag)
    try:
        # We try with --na to ignore non-standard atoms that cause SIGABRT errors
        result = subprocess.run([executable, "--na", pdb_path], capture_output=True, text=True)
        
        # If that fails or produces nothing, try the standard command
        if not result.stdout:
            result = subprocess.run([executable, pdb_path], capture_output=True, text=True)
            
        dssp_output = result.stdout
    except Exception as e:
        st.error(f"System DSSP Error: {e}")
        return None

    if not dssp_output:
        st.error("DSSP failed to generate output. The PDB file might be corrupted or incompatible.")
        return None

    # Step A: Extract B-Factors from the PDB file
    b_factors = {}
    target_chain = list(model.child_dict.keys())[0]
    for residue in model[target_chain]:
        if 'CA' in residue:
            b_factors[residue.id[1]] = residue['CA'].get_bfactor()

    # Step B: Parse DSSP Text Output manually for SASA
    res_data = []
    lines = dssp_output.splitlines()
    start_parsing = False
    
    for line in lines:
        if line.startswith("  #  RESIDUE"):
            start_parsing = True
            continue
        
        if start_parsing and len(line) > 38:
            try:
                res_num = int(line[5:10].strip())
                chain = line[11:12].strip()
                aa = line[13:14].strip()
                sasa = float(line[35:38].strip())
                
                # Match DSSP residue with PDB B-Factor
                if (chain == target_chain or chain == "") and res_num in b_factors:
                    res_data.append({
                        "Residue": aa,
                        "Position": res_num,
                        "rSASA": sasa / 200, # Normalized SASA
                        "B_Factor": b_factors[res_num]
                    })
            except:
                continue

    df = pd.DataFrame(res_data)
    if df.empty:
        return None

    # Step C: Calculation Logic (The details you requested)
    b_min, b_max = df['B_Factor'].min(), df['B_Factor'].max()
    df['Norm_B'] = (df['B_Factor'] - b_min) / (b_max - b_min) * 100 if b_max != b_min else 0
    df['Hotspot_Score'] = (0.5 * df['Norm_B']) + (0.5 * (df['rSASA'] * 100))
    
    return df

# --- 2. REPLACEMENT LOGIC ---
def get_replacements(wt):
    if wt in ['A', 'V', 'L', 'I', 'M', 'F', 'W', 'P']: return "S, T, A, Q, N"
    elif wt in ['R', 'K', 'D', 'E', 'H']: return "A, N, Q, S, T"
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
        raw = pdbl.retrieve_pdb_file(pdb_id, pdir='.', file_format='pdb')
        if os.path.exists(raw):
            shutil.move(raw, "input.pdb")
            pdb_file = "input.pdb"
            pdb_name = pdb_id

# --- 4. THE RESULT SECTION (Standard Table & Graph) ---
if pdb_file:
    with st.spinner("Analyzing structural dynamics..."):
        df = run_analysis(pdb_file)

    if df is not None:
        st.success(f"Analysis for {pdb_name} complete!")
        
        # A. Visual Graph
        st.subheader("Structural Hotspot Landscape")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.fill_between(df['Position'], df['Hotspot_Score'], color="#4e79a7", alpha=0.3)
        ax.plot(df['Position'], df['Hotspot_Score'], color="#4e79a7", lw=2)
        ax.set_ylabel("Mutation Hotspot Score")
        ax.set_xlabel("Residue Index")
        st.pyplot(fig)

        # B. Top 10 Mutation Candidates Table
        st.subheader("🔥 Top 10 Mutation Hotspots")
        top_10 = df.sort_values("Hotspot_Score", ascending=False).head(10)
        
        display_df = top_10[['Position', 'Residue', 'Hotspot_Score']].copy()
        display_df['Suggested Replacements'] = display_df['Residue'].apply(get_replacements)
        st.table(display_df)

        # C. Professional Report Generation
        doc = Document()
        doc.add_heading(f"Enzyme Mutation Report: {pdb_name}", 0)
        doc.add_paragraph(f"Methodology: Analysis based on rSASA (Solvent Accessibility) and B-Factor (Flexibility).")
        
        table = doc.add_table(rows=1, cols=4)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text = 'Pos', 'Res', 'Score', 'Replacements'

        for _, row in display_df.iterrows():
            row_cells = table.add_row().cells
            row_cells[0].text = str(int(row['Position']))
            row_cells[1].text = str(row['Residue'])
            row_cells[2].text = str(round(row['Hotspot_Score'], 2))
            row_cells[3].text = str(row['Suggested Replacements'])

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        st.download_button(
            label="📄 Download Full Report",
            data=buffer,
            file_name=f"Mutation_Report_{pdb_name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
