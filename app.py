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

    doc.add_heading('3. Structural Hotspot Landscape', level=1)
    # Convert Plotly graph to image for Word
    img_bytes = fig.to_image(format="png", width=1000, height=450)
    doc.add_picture(io.BytesIO(img_bytes), width=Inches(6))

    doc.add_heading('4. Mutation Candidate Analysis', level=1)
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Light Shading Accent 1'
    for i, h in enumerate(['Position', 'Residue', 'Hotspot Score', 'Top 6 Suggestions']):
        table.rows[0].cells[i].text = h

    for _, row in df.iterrows():
        row_cells = table.add_row().cells
        row_cells[0].text = str(row['Pos'])
        row_cells[1].text = str(row['Res'])
        row_cells[2].text = f"{row['Score']:.2f}"
        row_cells[3].text = row['Top 6 Suggestions']

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- 3. STREAMLIT INTERFACE ---
st.set_page_config(page_title="Enzyme Pipeline", layout="wide")
st.title("🧬 Enzyme Engineering & Mutation Pipeline")

with st.sidebar:
    st.header("Project Configuration")
    input_mode = st.radio("Input Method", ["Upload PDB File", "Fetch by PDB ID"])
    
    if input_mode == "Fetch by PDB ID":
        pdb_id_display = st.text_input("Enter PDB ID", value="4TKX")
    else:
        uploaded_file = st.file_uploader("Choose a PDB file", type=["pdb"])
        pdb_id_display = "Uploaded_PDB"
        
    st.divider()
    run_btn = st.button("🚀 Run Full Analysis", use_container_width=True)

if 'df_results' in st.session_state:
    df = st.session_state.df_results.sort_values(by='Pos')
    df['Top 6 Suggestions'] = df['Res'].apply(get_top_6_suggestions)

    tab1, tab2, tab3 = st.tabs(["📊 Analysis Dashboard", "📋 Mutation Table", "📑 Export Report"])

    with tab1:
        st.subheader(f"Structural Hotspot Landscape: {pdb_id_display}")
        fig = go.Figure()
        # Purple line with light blue shaded area
        fig.add_trace(go.Scatter(
            x=df['Pos'], y=df['Score'], mode='lines', fill='tozeroy', 
            line=dict(color='rgba(135, 131, 216, 1)', width=2),
            fillcolor='rgba(173, 216, 230, 0.4)',
            name='Hotspot Score'
        ))
        fig.update_layout(xaxis_title="Residue Position", yaxis_title="Hotspot Score", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Optimized Mutation Candidates")
        try:
            # Color gradient requires 'matplotlib' in requirements.txt
            st.dataframe(df.style.background_gradient(subset=['Score'], cmap='YlGnBu'), use_container_width=True, height="auto")
        except:
            st.dataframe(df, use_container_width=True, height="auto")

    with tab3:
        st.subheader("Final Documentation")
        report_file = generate_professional_report(pdb_id_display, df, fig)
        st.download_button(label=f"📥 Download Report", data=report_file, file_name=f"{pdb_id_display}_Report.docx")

if run_btn:
    # Dummy data for demonstration
    data = {
        'Pos': [575, 574, 573, 576, 572, 571, 577, 338, 229, 339],
        'Res': ['HIS', 'THR', 'ILE', 'ILE', 'ASN', 'GLY', 'GLY', 'GLY', 'ASP', 'ASP'],
        'Score': [65.78, 64.33, 62.73, 59.53, 57.92, 55.11, 53.08, 52.83, 52.29, 50.47]
    }
    st.session_state.df_results = pd.DataFrame(data)
    st.rerun()
