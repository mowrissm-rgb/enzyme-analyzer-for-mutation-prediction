import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io

# --- 1. CORE LOGIC: Dynamic Mutation Suggestions ---
def get_top_6_suggestions(original_res):
    """Provides 5-6 suggestions based on biochemical similarity/stability."""
    # Mapping for common mutation strategies
    suggestions_map = {
        'GLY': 'ALA, PRO, SER, VAL, ILE, LEU',
        'ALA': 'VAL, LEU, ILE, SER, THR, MET',
        'ASP': 'GLU, ASN, GLN, HIS, LYS, ARG',
        'SER': 'THR, ALA, CYS, ASN, GLN, TYR',
        # Default fallback for others
        'DEFAULT': 'ALA, VAL, LEU, ILE, SER, THR'
    }
    return suggestions_map.get(original_res.upper(), suggestions_map['DEFAULT'])

# --- 2. REPORT GENERATION: Professional Docx ---
def generate_professional_report(pdb_id, df, plot_image=None):
    doc = Document()
    
    # Dynamic Title
    title = doc.add_heading(f'Enzyme Mutation Strategy Report: {pdb_id}', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Methodology & Formula Section
    doc.add_heading('1. Methodology', level=1)
    para = doc.add_paragraph(
        'This pipeline identifies structural mutation hotspots by integrating '
        'Solvent Accessible Surface Area (SASA) via the Shrake-Rupley algorithm '
        'and B-factor flexibility analysis.'
    )
    
    # Add Formula
    doc.add_heading('2. Scoring Formula', level=2)
    formula_para = doc.add_paragraph()
    run = formula_para.add_run('Score = (w1 × Normalized SASA) + (w2 × Normalized B-factor)')
    run.italic = True
    run.font.size = Pt(12)

    # Table with "Cooler" Formatting
    doc.add_heading('3. Mutation Candidate Analysis', level=1)
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Light Shading Accent 1' # Professional striped style
    
    hdr_cells = table.rows[0].cells
    for i, text in enumerate(['Position', 'Residue', 'Hotspot Score', 'Top 6 Suggestions']):
        hdr_cells[i].text = text
        hdr_cells[i].paragraphs[0].runs[0].font.bold = True

    for _, row in df.iterrows():
        row_cells = table.add_row().cells
        row_cells[0].text = str(row['Pos'])
        row_cells[1].text = str(row['Res'])
        row_cells[2].text = f"{row['Score']:.2f}"
        row_cells[3].text = get_top_6_suggestions(row['Res'])

    # References Section
    doc.add_page_break()
    doc.add_heading('References', level=1)
    refs = [
        'Shrake, A., & Rupley, J. A. (1973). Environment and exposure to solvent of protein atoms. J. Mol. Biol.',
        'Cock, P. J., et al. (2009). Biopython: freely available Python tools for computational biology. Bioinformatics.',
        'Schrödinger Release 2024-1: BioLuminate, Schrödinger, LLC, New York, NY.'
    ]
    for ref in refs:
        doc.add_paragraph(ref, style='List Bullet')

    # Save to buffer for Streamlit download
    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- 3. STREAMLIT INTERFACE ---
st.set_page_config(page_title="Enzyme Pipeline", layout="wide")
st.title("🧬 Enzyme Engineering & Mutation Pipeline")

# Sidebar
with st.sidebar:
    st.header("Project Configuration")
    pdb_input = st.text_input("Enter PDB ID", value="4TKX")
    st.divider()
    run_btn = st.button("🚀 Run Full Analysis", use_container_width=True)

# Main Dashboard Layout
if 'df_results' not in st.session_state:
    st.info("Please enter a PDB ID and run the analysis to view results.")
else:
    df = st.session_state.df_results
    tab1, tab2, tab3 = st.tabs(["📊 Analysis Dashboard", "📋 Mutation Table", "📑 Export Report"])

    with tab1:
        st.subheader("Structural Hotspot Landscape")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Pos'], 
            y=df['Score'], 
            mode='lines+markers',
            fill='tozeroy', 
            line=dict(color='#1f77b4', width=2),
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
        # Add the 6 suggestions to the interactive dataframe view
        df['Top 6 Suggestions'] = df['Res'].apply(get_top_6_suggestions)
        
        st.dataframe(
            df.style.background_gradient(subset=['Score'], cmap='YlGnBu'),
            use_container_width=True,
            height=400
        )

    with tab3:
        st.subheader("Final Documentation")
        st.write("Generate a professional research report including methodology, formula, and results.")
        
        # Report generation trigger
        report_file = generate_professional_report(pdb_input, df)
        
        st.download_button(
            label=f"📥 Download {pdb_input}_Report.docx",
            data=report_file,
            file_name=f"{pdb_input}_Mutation_Strategy.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

# --- Dummy Data Logic (For testing purposes) ---
if run_btn:
    # This is where your actual PDB processing logic goes
    # Using dummy data for demonstration
    data = {
        'Pos': [575, 574, 573, 576, 572, 571],
        'Res': ['HIS', 'THR', 'ILE', 'ILE', 'ASN', 'GLY'],
        'Score': [65.78, 64.33, 62.73, 59.53, 57.92, 55.11]
    }
    st.session_state.df_results = pd.DataFrame(data)
    st.rerun()
