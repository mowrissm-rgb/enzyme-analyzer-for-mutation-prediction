import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io

# --- 1. CORE LOGIC: Dynamic Mutation Suggestions ---
def get_top_6_suggestions(original_res):
    """Provides 6 suggestions based on biochemical similarity and stability."""
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

# --- 2. REPORT GENERATION: Professional Docx ---
def generate_professional_report(pdb_id, df, fig):
    doc = Document()
    
    # Header
    doc.add_heading(f'Enzyme Mutation Strategy Report: {pdb_id}', 0) [cite: 4]
    
    # 1. Methodology
    doc.add_heading('1. Methodology', level=1) [cite: 5]
    doc.add_paragraph(
        "This pipeline identifies structural mutation hotspots by integrating Solvent Accessible "
        "Surface Area (SASA) via the Shrake-Rupley algorithm and B-factor flexibility analysis[cite: 6]. "
        "Targeting residues with high exposure and thermal displacement allows for the optimization "
        "of enzymatic potential while maintaining structural integrity."
    )
    
    # 2. Scoring Formula & "Where" Section
    doc.add_heading('2. Scoring Formula', level=1) [cite: 7]
    formula = doc.add_paragraph()
    run = formula.add_run('Score = (w1 × Normalized SASA) + (w2 × Normalized B-factor)') [cite: 8]
    run.bold = True
    run.italic = True

    doc.add_heading('Where:', level=2)
    defs = [
        ("w1 / w2", "Weighting factors assigned to exposure and flexibility (Standard: 0.5/0.5)."),
        ("Normalized SASA", "The relative solvent accessibility of the residue calculated via Shrake-Rupley (0-100 scale)."),
        ("Normalized B-factor", "The atomic displacement parameter representing local chain flexibility.")
    ]
    for term, definition in defs:
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(f'{term}: ').bold = True
        p.add_run(definition)

    # 3. Embedded Graph
    doc.add_heading('3. Structural Hotspot Landscape', level=1)
    # Converts Plotly figure to a high-res PNG for Word
    img_bytes = fig.to_image(format="png", width=1000, height=500)
    doc.add_picture(io.BytesIO(img_bytes), width=Inches(6))

    # 4. Clean Mutation Table
    doc.add_heading('4. Mutation Candidate Analysis', level=1) [cite: 9]
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Light Shading Accent 1'
    
    hdr_cells = table.rows[0].cells
    headers = ['Position', 'Residue', 'Hotspot Score', 'Top 6 Suggestions'] [cite: 10]
    for i, h in enumerate(headers):
        hdr_cells[i].text = h

    for _, row in df.iterrows():
        row_cells = table.add_row().cells
        row_cells[0].text = str(row['Pos']) [cite: 10]
        row_cells[1].text = str(row['Res']) [cite: 10]
        row_cells[2].text = f"{row['Score']:.2f}" [cite: 10]
        row_cells[3].text = row['Top 6 Suggestions'] [cite: 10]

    # 5. References
    doc.add_page_break()
    doc.add_heading('References', level=1) [cite: 11]
    refs = [
        "Shrake, A., & Rupley, J. A. (1973). Environment and exposure to solvent of protein atoms. J. Mol. Biol. [cite: 12]",
        "Cock, P. J., et al. (2009). Biopython: tools for computational biology. Bioinformatics. [cite: 13]",
        "Schrödinger Release 2024-1: BioLuminate, Schrödinger, LLC, New York, NY. [cite: 14]",
        "Eyal, E., et al. (2005). The use of electrostatic parameters in predictor of residue flexibility. Proteins."
    ]
    for ref in refs:
        doc.add_paragraph(ref, style='List Bullet')

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- 3. STREAMLIT INTERFACE ---
st.set_page_config(page_title="Enzyme Pipeline", layout="wide")
st.title("🧬 Enzyme Engineering & Mutation Pipeline")

with st.sidebar:
    st.header("Project Configuration")
    pdb_input = st.text_input("Enter PDB ID", value="4TKX")
    st.divider()
    run_btn = st.button("🚀 Run Full Analysis", use_container_width=True)

if 'df_results' not in st.session_state:
    st.info("Please enter a PDB ID and run the analysis to view results.")
else:
    # SORTING: Fixes the graph line so it follows the residue order correctly
    df = st.session_state.df_results.sort_values(by='Pos')
    df['Top 6 Suggestions'] = df['Res'].apply(get_top_6_suggestions)

    tab1, tab2, tab3 = st.tabs(["📊 Analysis Dashboard", "📋 Mutation Table", "📑 Export Report"])

    with tab1:
        st.subheader("Structural Hotspot Landscape")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Pos'], y=df['Score'], mode='lines+markers',
            fill='tozeroy', line=dict(color='#1f77b4', width=2),
            name='Flexibility Score'
        ))
        fig.update_layout(
            hovermode="x unified",
            xaxis_title="Residue Position",
            yaxis_title="Mutation Score",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Optimized Mutation Candidates")
        # height=None removes the empty rows/space from the interface
        st.dataframe(
            df.style.background_gradient(subset=['Score'], cmap='YlGnBu'),
            use_container_width=True,
            height=None
        )

    with tab3:
        st.subheader("Final Documentation")
        st.write("Generate a professional research report including the landscape graph, formula, and methodology.")
        
        # We pass 'fig' here so it can be saved into the Word doc
        report_file = generate_professional_report(pdb_input, df, fig)
        
        st.download_button(
            label=f"📥 Download {pdb_input}_Report.docx",
            data=report_file,
            file_name=f"{pdb_input}_Mutation_Strategy.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

if run_btn:
    # Dummy Data for demonstration - actual processing logic would replace this
    data = {
        'Pos': [575, 574, 573, 576, 572, 571],
        'Res': ['HIS', 'THR', 'ILE', 'ILE', 'ASN', 'GLY'],
        'Score': [65.78, 64.33, 62.73, 59.53, 57.92, 55.11]
    }
    st.session_state.df_results = pd.DataFrame(data)
    st.rerun()
