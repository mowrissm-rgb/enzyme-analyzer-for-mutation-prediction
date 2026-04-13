import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import time
import requests
import numpy as np
from streamlit_lottie import st_lottie

# --- 1. SET THEME & UI CONFIG ---
st.set_page_config(page_title="Enzyme Pipeline Pro", layout="wide", page_icon="🧬")

# Custom CSS for the Black/Blue/White theme and the Animated Arrow
st.markdown("""
    <style>
    /* Main App Background and Text */
    .stApp {
        background-color: #000000;
        color: #FFFFFF;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #0e1117;
        border-right: 1px solid #007BFF;
    }

    /* Professional Blue Glow for Buttons */
    .stButton>button {
        background-color: #000000;
        color: #007BFF;
        border: 2px solid #007BFF;
        border-radius: 8px;
        font-weight: bold;
        width: 100%;
        transition: 0.3s ease-in-out;
    }
    
    .stButton>button:hover {
        background-color: #007BFF;
        color: white;
        box-shadow: 0 0 20px rgba(0, 123, 255, 0.6);
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        color: #FFFFFF;
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        color: #007BFF !important;
        border-bottom-color: #007BFF !important;
    }

    /* Animated Downward Arrow for Download */
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-15px); }
    }

    .download-indicator {
        position: fixed;
        top: 70px;
        right: 45px;
        font-size: 45px;
        color: #007BFF;
        animation: bounce 1.5s infinite;
        z-index: 1000;
        pointer-events: none;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOTTIE ANIMATION HELPER (WITH SAFETY GATES) ---
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None

# Load the animations (using stable lottie.host links)
lottie_analyze = load_lottieurl("https://lottie.host/76e936b1-090c-4034-8977-16017366d6d4/X8q9f6R8A2.json") 
lottie_download = load_lottieurl("https://lottie.host/80c6c739-166b-4e6f-998a-777c59c49d97/5K8uR6uR9a.json")

# --- 3. CORE COMPUTATIONAL LOGIC ---
def get_top_6_suggestions(original_res):
    suggestions_map = {
        'GLY': 'ALA, PRO, SER, VAL, ILE, LEU', 'ALA': 'VAL, LEU, ILE, SER, THR, MET',
        'ASP': 'GLU, ASN, GLN, HIS, LYS, ARG', 'SER': 'THR, ALA, CYS, ASN, GLN, TYR',
        'HIS': 'PHE, TYR, TRP, ASN, GLN, LYS', 'THR': 'SER, VAL, ALA, ILE, MET, ASN',
        'ILE': 'VAL, LEU, MET, PHE, ALA, TRP', 'ASN': 'GLN, ASP, GLU, HIS, SER, THR',
        'DEFAULT': 'ALA, VAL, LEU, ILE, SER, THR'
    }
    return suggestions_map.get(original_res.upper(), suggestions_map['DEFAULT'])

def generate_professional_report(pdb_id, df):
    doc = Document()
    doc.add_heading(f'Enzyme Mutation Strategy Report: {pdb_id}', 0)
    
    doc.add_heading('1. Methodology', level=1)
    doc.add_paragraph("This pipeline identifies structural mutation hotspots by integrating SASA and B-factor flexibility analysis.")
    
    doc.add_heading('2. Mathematical Foundation', level=1)
    formula_p = doc.add_paragraph()
    formula_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = formula_p.add_run("Score = (w_SASA × [SASA_i / SASA_max]) + (w_B × [B_i / B_max])")
    run.bold = True
    
    # Plot for Report (Dark Style)
    plt.style.use('dark_background')
    plt.figure(figsize=(12, 4))
    plt.plot(df['Pos'], df['Score'], color='#007BFF', linewidth=1.5) 
    plt.fill_between(df['Pos'], df['Score'], 0, color='#007BFF', alpha=0.2)
    plt.title(f'Hotspot Landscape: {pdb_id}')
    
    img_stream = io.BytesIO()
    plt.savefig(img_stream, format='png', bbox_inches='tight', dpi=200)
    plt.close()
    img_stream.seek(0)
    doc.add_picture(img_stream, width=Inches(6))

    doc.add_heading('3. Mutation Candidates', level=1)
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Light Shading Accent 1'
    for i, h in enumerate(['Pos', 'Res', 'Score', 'Suggestions']):
        table.rows[0].cells[i].text = h

    top_candidates = df.nlargest(15, 'Score').sort_values('Pos')
    for _, row in top_candidates.iterrows():
        cells = table.add_row().cells
        cells[0].text, cells[1].text = str(row['Pos']), str(row['Res'])
        cells[2].text = f"{row['Score']:.2f}"
        cells[3].text = row['Top 6 Suggestions']

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

# --- 4. MAIN APP INTERFACE ---
st.title("🧬 Enzyme Analysis Pipeline")
st.markdown("<p style='color: #007BFF;'>Advanced Computational Hotspot Identification</p>", unsafe_allow_html=True)
st.markdown("---")

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/dna-helix.png")
    st.header("Project Configuration")
    pdb_id_display = st.text_input("Target PDB ID", value="4TKX")
    run_btn = st.button("🚀 RUN FULL ANALYSIS")

# --- 5. ANALYSIS EXECUTION ---
if run_btn:
    status_placeholder = st.empty()
    
    with status_placeholder.container():
        st.markdown("<h3 style='text-align: center; color: #007BFF;'>Running Molecular Dynamics...</h3>", unsafe_allow_html=True)
        
        # Check if Lottie loaded before displaying to prevent crash
        if lottie_analyze:
            st_lottie(lottie_analyze, height=250, key="main_loader")
        else:
            st.info("Computing structural hotspots... please wait.")
            st.progress(40)
            
        time.sleep(3) # Simulation of heavy computation

    status_placeholder.empty() # Clear animation when done
    
    # Generate simulation
