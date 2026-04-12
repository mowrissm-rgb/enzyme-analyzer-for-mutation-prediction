import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Inches
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

# --- 2. PROFESSIONAL REPORT GENERATOR ---
def generate_professional_report(pdb_id, df):
    doc = Document()
    doc.add_heading(f'Enzyme Mutation Strategy Report: {pdb_id}', 0)
    
    doc.add_heading('1. Methodology', level=1)
    doc.add_paragraph("This pipeline identifies structural mutation hotspots by integrating SASA and B-factor flexibility analysis.")
    
    doc.add_heading('2. Scoring Formula', level=1)
    doc.add_paragraph('Score = (w1 × Normalized SASA) + (w2 × Normalized B-factor)')
    
    doc.add_heading('3. Structural Hotspot Landscape', level=1)
    
    # MATPLOTLIB VERSION FOR DOCX (Red line, Green fill)
    plt.figure(figsize=(10, 4))
    plt.plot(df['Pos'], df['Score'], color='#FF0000', linewidth=1.5) # Red Line
    plt.fill_between(df['Pos'], df['Score'], 0, color='#90EE90', alpha=0.5) # Light Green Fill
    plt.xlabel('Residue Position')
    plt.ylabel('Hotspot Score')
    plt.title(f'Structural Hotspot Landscape: {pdb_id}')
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    
    img_stream = io.BytesIO()
    plt.savefig(img_stream, format='png', bbox_inches='tight', dpi=150)
    plt.close()
    img_stream.seek(0)
    
    doc.add_picture(img_stream, width=Inches(6))

    doc.add_heading('4. Mutation Candidate Analysis', level=1)
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Light Shading Accent 1'
    for i, h in enumerate(['Position', 'Residue', 'Score', 'Suggestions']):
        table.rows[0].cells[i].text = h

    for _, row in df.iterrows():
        cells = table.add_row().cells
        cells[0].text = str(row['Pos'])
        cells[1].text = str(row['Res'])
        cells[2].text = f"{row['Score']:.2f}"
        cells[3].text = row['Top 6 Suggestions']

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
    pdb_id_display = st.text_input("Project ID", value="4TKX")
    run_btn = st.button("🚀 Run Full Analysis", use_container_width=True)

if 'df_results' in st.session_state:
    df = st.session_state.df_results.sort_values(by='Pos')
    df['Top 6 Suggestions'] = df['Res'].apply(get_top_6_suggestions)

    tab1, tab2, tab3 = st.tabs(["📊 Web Dashboard", "📋 Mutation Table", "📑 Export Report"])

    with tab1:
        st.subheader(f"Structural Hotspot Landscape: {pdb_id_display}")
        # PLOTLY VERSION FOR WEB (Red line, Green fill)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Pos'], y=df['Score'], mode='lines', 
            fill='tozeroy', 
            line=dict(color='red', width=2),       # Red Line
            fillcolor='rgba(0, 255, 0, 0.3)',      # Transparent Green Fill
            name='Hotspot Score'
        ))
        fig.update_layout(
            xaxis_title="Residue Position", 
            yaxis_title="Hotspot Score", 
            template="plotly_white",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Optimized Mutation Candidates")
        try:
            st.dataframe(df.style.background_gradient(subset=['Score'], cmap='RdYlGn'), use_container_width=True, height="auto")
        except:
            st.dataframe(df, use_container_width=True)

    with tab3:
        st.subheader("Final Documentation")
        report_file = generate_professional_report(pdb_id_display, df)
        st.download_button("📥 Download .docx Report", data=report_file, file_name=f"{pdb_id_display}_Report.docx")

if run_btn:
    # Dummy data for demonstration
    data = {
        'Pos': [229, 338, 339, 571, 572, 573, 574, 575, 576, 577],
        'Res': ['ASP', 'GLY', 'ASP', 'GLY', 'ASN', 'ILE', 'THR', 'HIS', 'ILE', 'GLY'],
        'Score': [52.29, 52.83, 50.47, 55.11, 57.92, 62.73, 64.33, 65.78, 59.53, 53.08]
    }
    st.session_state.df_results = pd.DataFrame(data)
    st.rerun()
