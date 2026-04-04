import streamlit as st
import re
import json
import io
import hashlib
import streamlit.components.v1 as components
from dateutil import parser as date_parser
from PIL import Image
from streamlit_paste_button import paste_image_button as pbutton
import google.generativeai as genai 
from google.api_core.exceptions import ResourceExhausted 

# --- Configuração da Página (DEVE SER O PRIMEIRO COMANDO STREAMLIT) ---
st.set_page_config(page_title="ClipDoc", layout="wide")

# ============================================================
# CHANGE 1 + 5: Custom CSS Theme + Hide Streamlit defaults
# ============================================================
st.markdown("""
<style>
/* --- Hide Streamlit defaults for cleaner look --- */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
div[data-testid="stDecoration"] {display: none;}

/* --- Brand Colors --- */
:root {
    --cd-primary: #0F6E56;
    --cd-primary-light: #E1F5EE;
    --cd-primary-dark: #085041;
    --cd-amber: #854F0B;
    --cd-amber-bg: #FAEEDA;
    --cd-red: #A32D2D;
    --cd-red-bg: #FCEBEB;
    --cd-surface: #f8f9fa;
    --cd-border: #e2e4e8;
    --cd-text: #1a1a1a;
    --cd-text-muted: #6b7280;
    --cd-radius: 10px;
}

/* --- Global typography polish --- */
.main .block-container {
    padding-top: 2rem;
    max-width: 1100px;
}

/* --- Tab styling --- */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid var(--cd-border);
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    padding: 0.75rem 1.5rem;
    font-size: 0.95rem;
    font-weight: 500;
    color: var(--cd-text-muted);
    border-bottom: 2px solid transparent;
    background: transparent;
}
.stTabs [aria-selected="true"] {
    color: var(--cd-primary) !important;
    border-bottom: 2px solid var(--cd-primary) !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--cd-primary-dark);
}

/* --- Primary buttons --- */
.stButton > button[kind="primary"],
div[data-testid="stButton"] > button[kind="primary"] {
    background-color: var(--cd-primary);
    border: none;
    color: white;
    border-radius: 8px;
    font-weight: 500;
    padding: 0.5rem 1.25rem;
    transition: background-color 0.2s;
}
.stButton > button[kind="primary"]:hover {
    background-color: var(--cd-primary-dark);
    border: none;
    color: white;
}

/* --- Secondary buttons --- */
.stButton > button:not([kind="primary"]) {
    border-radius: 8px;
    border: 1px solid var(--cd-border);
    font-weight: 500;
    color: var(--cd-text);
    padding: 0.5rem 1.25rem;
    transition: all 0.2s;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: var(--cd-primary);
    color: var(--cd-primary);
}

/* --- Text areas --- */
.stTextArea textarea {
    border-radius: 8px !important;
    border: 1px solid var(--cd-border) !important;
    font-size: 0.9rem;
    transition: border-color 0.2s;
}
.stTextArea textarea:focus {
    border-color: var(--cd-primary) !important;
    box-shadow: 0 0 0 1px var(--cd-primary) !important;
}

/* --- Select box --- */
.stSelectbox [data-baseweb="select"] {
    border-radius: 8px;
}

/* --- Card containers --- */
.cd-card {
    background: white;
    border: 1px solid var(--cd-border);
    border-radius: var(--cd-radius);
    padding: 1.25rem;
    margin-bottom: 1rem;
}
.cd-card-surface {
    background: var(--cd-surface);
    border-radius: var(--cd-radius);
    padding: 1.25rem;
    margin-bottom: 1rem;
}
.cd-section-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--cd-text-muted);
    margin-bottom: 0.5rem;
}

/* --- Output display with color coding --- */
.cd-output-box {
    background: white;
    border: 1px solid var(--cd-border);
    border-radius: 8px;
    padding: 1rem;
    font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', 'Consolas', monospace;
    font-size: 0.85rem;
    line-height: 1.8;
    height: 320px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
    box-sizing: border-box;
}
.cd-val-alert {
    color: var(--cd-amber);
    font-weight: 600;
    background: var(--cd-amber-bg);
    padding: 1px 4px;
    border-radius: 3px;
}
.cd-val-crit {
    color: var(--cd-red);
    font-weight: 700;
    background: var(--cd-red-bg);
    padding: 1px 4px;
    border-radius: 3px;
}
.cd-datetime {
    color: var(--cd-primary);
    font-weight: 600;
}

/* --- Step indicator for AI workflow --- */
.cd-steps {
    display: flex;
    align-items: center;
    gap: 0;
    margin-bottom: 1.5rem;
}
.cd-step {
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.cd-step-num {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    font-weight: 600;
}
.cd-step-num.active {
    background: var(--cd-primary);
    color: white;
}
.cd-step-num.done {
    background: var(--cd-primary-light);
    color: var(--cd-primary);
}
.cd-step-num.pending {
    background: #f1f1f1;
    color: #bbb;
}
.cd-step-label {
    font-size: 0.75rem;
    font-weight: 500;
}
.cd-step-label.active { color: var(--cd-primary); }
.cd-step-label.done { color: var(--cd-primary); }
.cd-step-label.pending { color: #bbb; }
.cd-step-line {
    flex: 0 0 30px;
    height: 2px;
    margin: 0 0.3rem;
}
.cd-step-line.done { background: var(--cd-primary-light); }
.cd-step-line.pending { background: #eee; }

/* --- Copy button override (embedded HTML) --- */
.cd-copy-btn {
    padding: 10px 15px;
    background-color: var(--cd-primary) !important;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    width: 100%;
    margin-top: 10px;
    font-weight: 500;
    font-size: 0.9rem;
    transition: background-color 0.2s;
}
.cd-copy-btn:hover {
    background-color: var(--cd-primary-dark) !important;
}
.cd-copy-btn-outline {
    padding: 10px 15px;
    background-color: transparent !important;
    color: var(--cd-primary);
    border: 1px solid var(--cd-primary);
    border-radius: 8px;
    cursor: pointer;
    width: 100%;
    margin-top: 10px;
    font-weight: 500;
    font-size: 0.9rem;
    transition: all 0.2s;
}
.cd-copy-btn-outline:hover {
    background-color: var(--cd-primary-light) !important;
}

/* --- Expander styling --- */
.streamlit-expanderHeader {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--cd-text-muted);
}

/* --- Spinner --- */
.stSpinner > div {
    border-top-color: var(--cd-primary) !important;
}

/* --- File uploader area --- */
.cd-file-upload-label {
    font-size: 0.75rem;
    color: var(--cd-text-muted);
    margin-top: 0.5rem;
    margin-bottom: 0.25rem;
    display: flex;
    align-items: center;
    gap: 6px;
}
.cd-file-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
}
.cd-file-chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 500;
}
.cd-file-chip.image {
    background: #E6F1FB;
    color: #0C447C;
}
.cd-file-chip.pdf {
    background: #FCEBEB;
    color: #791F1F;
}
.cd-file-chip.text {
    background: #E1F5EE;
    color: #085041;
}

/* --- Dark mode support --- */
@media (prefers-color-scheme: dark) {
    :root {
        --cd-surface: #1e1e1e;
        --cd-border: #333;
        --cd-text: #e0e0e0;
        --cd-text-muted: #999;
    }
    .cd-card { background: #1a1a1a; border-color: #333; }
    .cd-output-box { background: #1a1a1a; border-color: #333; }
}
</style>
""", unsafe_allow_html=True)


# --- Padrões Regex Globais ---
NUM_PATTERN = r"([<>]{0,1}\d{1,6}(?:[,.]\d{1,3})?)"
GAS_NUM_PATTERN = r"([<>]{0,1}-?\d{1,6}(?:[,.]\d{1,3})?)"

# --- Configuração de Valores de Referência ---
VALORES_REFERENCIA = {
    "Hb": {"min": 13.0, "max": 17.0, "crit_low": 7.0, "crit_high": 20.0},
    "Ht": {"min": 40.0, "max": 50.0, "crit_low": 20.0},
    "VCM": {"min": 83.0, "max": 101.0},
    "HCM": {"min": 27.0, "max": 32.0},
    "CHCM": {"min": 31.0, "max": 35.0},
    "RDW": {"min": 11.6, "max": 14.0},
    "Leuco": {"min": 4000, "max": 10000, "crit_low": 1000, "crit_high": 30000},
    "Plaq": {"min": 150000, "max": 450000, "crit_low": 20000, "crit_high": 1000000},
    "PCR": {"max": 0.30, "crit_high": 100.0},
    "U": {"min": 15, "max": 50},
    "Cr": {"min": 0.50, "max": 1.30},
    "eGFR": {"min": 90},
    "K": {"min": 3.5, "max": 5.1, "crit_low": 2.5, "crit_high": 6.5},
    "Na": {"min": 136, "max": 145, "crit_low": 120, "crit_high": 160},
    "Mg": {"min": 1.8, "max": 2.4},
    "CaI": {"min": 1.12, "max": 1.32},
    "CaT": {"min": 8.6, "max": 10.0},
    "P": {"min": 2.5, "max": 4.5},
    "Cl": {"min": 98, "max": 107},
    "Gli": {"min": 70, "max": 99, "crit_high": 400, "crit_low": 40},
    "INR": {"min": 0.96, "max": 1.30, "crit_high": 5.0},
    "TTPA_s": {"min": 27.80, "max": 38.60, "crit_high": 100.0},
    "TTPA_R": {"min": 0.90, "max": 1.25, "crit_high": 3.0},
    "TGO": {"min": 15, "max": 37},
    "TGP": {"min": 6, "max": 45},
    "GGT": {"max": 71}, 
    "FA": {"max": 129}, 
    "BT": {"min": 0.30, "max": 1.20},
    "BD": {"max": 0.30},
    "BI": {"min": 0.10, "max": 1.00},
    "ALB": {"min": 3.5, "max": 5.2},
    "AML": {"max": 100},
    "LIP": {"max": 160},
    "Vanco": {"min": 15.0, "max": 20.0, "crit_low": 10.0, "crit_high": 25.0},
    "pH_gas": {"min": 7.35, "max": 7.45, "crit_low": 7.2, "crit_high": 7.6},
    "pCO2_gas": {"min": 35.0, "max": 45.0, "crit_low": 20, "crit_high": 80},
    "HCO3_gas": {"min": 21.0, "max": 28.0, "crit_low": 10, "crit_high": 40},
    "BE_gas": {"min": -3.0, "max": 3.0},
    "pO2_gas": {"min": 80.0, "max": 95.0, "crit_low": 40},
    "SatO2_gas": {"min": 95.0, "max": 99.0, "crit_low": 88},
    "Lac_gas": {"min": 4.5, "max": 20, "crit_high": 40},
    "Lac": {"min": 4, "max": 20, "crit_high": 30.0},
    "cCO2_gas": {"min": 23.0, "max": 29.0}
}


# --- Configuração da API Key do Gemini (Após st.set_page_config) ---
GOOGLE_API_KEY = None
gemini_model = None
gemini_available = False
api_key_source = None

try:
    if hasattr(st, 'secrets') and "GOOGLE_API_KEY" in st.secrets:
        GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
        api_key_source = "secrets"
except Exception:
    pass

if not GOOGLE_API_KEY:
    GOOGLE_API_KEY_LOCAL_FALLBACK = "AIzaSyB3YgdL-zUid_nV2fbT0jzIOdMt_gUXCrQ"
    if GOOGLE_API_KEY_LOCAL_FALLBACK != "SUA_API_KEY_AQUI_NO_CODIGO_GENERICO_PLACEHOLDER":
        GOOGLE_API_KEY = GOOGLE_API_KEY_LOCAL_FALLBACK
        api_key_source = "local_code"

if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model_pro = genai.GenerativeModel('gemini-2.5-pro')
        gemini_model_flash = genai.GenerativeModel('gemini-2.5-flash')
        gemini_available = True
    except Exception as e:
        st.session_state.gemini_config_error = f"Erro ao configurar a API do Gemini: {e}. Verifique sua chave de API."
        gemini_available = False
else:
    gemini_available = False

# --- Funções Auxiliares ---
def clean_number_format(value_str):
    if not value_str: return ""
    s = str(value_str).strip().lstrip('<>')
    if '.' in s and ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    return s

def convert_to_float(cleaned_value_str):
    if not cleaned_value_str: return None
    try: return float(cleaned_value_str)
    except ValueError: return None

def format_value_with_alert(label, raw_value_str, key_ref, unit_suffix=""):
    if raw_value_str == "" or raw_value_str is None: return ""
    cleaned_value = clean_number_format(raw_value_str)
    if not cleaned_value: return f"{label} {raw_value_str}"
    
    if key_ref == "eGFR" and '-' in cleaned_value:
        parts = cleaned_value.split('-')
        return f"{label} {parts[0]}-{parts[1]}"
        
    display_text = f"{label} {cleaned_value}{unit_suffix}"
    
    val_to_check = float(cleaned_value)
    if unit_suffix == " mil":
        val_to_check *= 1000

    val_float = convert_to_float(str(val_to_check))
    alert_suffix = ""
    if val_float is not None and key_ref in VALORES_REFERENCIA:
        ref = VALORES_REFERENCIA[key_ref]
        crit_high, crit_low = ref.get("crit_high"), ref.get("crit_low")
        max_val, min_val = ref.get("max"), ref.get("min")
        
        is_crit_high = crit_high is not None and val_float > crit_high
        is_crit_low = crit_low is not None and val_float < crit_low
        is_high = max_val is not None and val_float > max_val
        is_low = min_val is not None and val_float < min_val
        
        if is_crit_high or is_crit_low:
            alert_suffix = " (!)"
        elif is_high or is_low:
            alert_suffix = " *"
            
    return f"{display_text}{alert_suffix}"


def extract_labeled_value(lines, labels_to_search, pattern_to_extract=NUM_PATTERN,
                          search_window_lines=3, label_must_be_at_start=False,
                          ignore_case=True, line_offset_for_value=0, require_unit=None):
    if isinstance(labels_to_search, str): labels_to_search = [labels_to_search]
    for i, current_line in enumerate(lines):
        processed_line = current_line.lower() if ignore_case else current_line
        for label in labels_to_search:
            processed_label = label.lower() if ignore_case else label
            label_found_in_line, text_to_search_value_in = False, current_line
            start_index_of_label = -1
            if label_must_be_at_start:
                if processed_line.startswith(processed_label): start_index_of_label = 0
            else: start_index_of_label = processed_line.find(processed_label)
            if start_index_of_label != -1:
                label_found_in_line = True
                text_to_search_value_in = current_line[start_index_of_label + len(label):].strip()
            if label_found_in_line:
                target_line_idx = i + line_offset_for_value
                if 0 <= target_line_idx < len(lines):
                    line_content_for_search = lines[target_line_idx] if line_offset_for_value != 0 else text_to_search_value_in
                    match = None
                    if line_content_for_search:
                        if require_unit:
                            pat_with_unit = pattern_to_extract + r"\s*" + re.escape(require_unit)
                            m_unit = re.search(pat_with_unit, line_content_for_search, re.IGNORECASE)
                            if m_unit: match = m_unit
                        else:
                            match = re.search(pattern_to_extract, line_content_for_search)
                    if match: return match.group(1)
                    if line_offset_for_value == 0 :
                        for j_offset in range(1, search_window_lines + 1):
                            next_line_idx_abs = i + j_offset
                            if next_line_idx_abs < len(lines):
                                line_to_check_next = lines[next_line_idx_abs]
                                match_next = None
                                if require_unit:
                                    pat_with_unit_next = pattern_to_extract + r"\s*" + re.escape(require_unit)
                                    m_unit_next = re.search(pat_with_unit_next, line_to_check_next, re.IGNORECASE)
                                    if m_unit_next: match_next = m_unit_next
                                else:
                                    match_next = re.search(pattern_to_extract, line_to_check_next)
                                if match_next: return match_next.group(1)
                return ""
    return ""

# --- Função de Anonimização ---
def anonimizar_texto(texto_original):
    linhas_processadas = []
    for linha in texto_original.splitlines():
        linha_strip = linha.strip()
        if linha_strip.startswith("#ID:"):
            partes = linha.split(":", 1)
            id_tag = partes[0] + ":"
            conteudo_id = partes[1].strip() if len(partes) > 1 else ""
            
            def substituir_nome_id_por_iniciais(match):
                nome_completo = match.group(0).strip()
                partes_nome = nome_completo.split()
                PALAVRAS_EXCLUIR_DA_ABREVIACAO_ID = ["Pronto", "Socorro", "Centro", "Clínicas", "Hospital"]
                
                if len(partes_nome) > 1 and \
                   all(p and p[0].isupper() for p in partes_nome) and \
                   not nome_completo.isupper() and \
                   not any(palavra_excluir.lower() in nome_completo.lower() for palavra_excluir in PALAVRAS_EXCLUIR_DA_ABREVIACAO_ID):
                    
                    partes_para_iniciais = [p for p in partes_nome if p.lower() not in ["de", "da", "do", "dos", "das", "e"]]
                    if len(partes_para_iniciais) >= 2:
                        iniciais = [p[0] + "." for p in partes_para_iniciais]
                        return " ".join(iniciais)
                return nome_completo

            padrao_nome_composto_id = r"\b([A-ZÀ-Ú][a-zà-ú'-]+(?:\s+(?:de|da|do|dos|das|e)\s+[A-ZÀ-Ú][a-zà-ú'-]+){1,3})\b"
            conteudo_id_anonimizado = re.sub(padrao_nome_composto_id, substituir_nome_id_por_iniciais, conteudo_id)
            padrao_nome_geral_id = r"\b([A-ZÀ-Ú][a-zà-ú'-]+(?:\s+[A-ZÀ-Ú][a-zà-ú'-]+){1,2})\b"
            conteudo_id_anonimizado = re.sub(padrao_nome_geral_id, substituir_nome_id_por_iniciais, conteudo_id_anonimizado)
            
            linhas_processadas.append(f"{id_tag} {conteudo_id_anonimizado}")
        else:
            linhas_processadas.append(linha)
            
    return "\n".join(linhas_processadas)
    
# --- Funções de Extração Específicas ---

def extract_datetime_info(lines, is_tecnolab):
    if is_tecnolab:
        for line in lines:
            m_tecnolab = re.search(r"Coleta\((\d{1,2}/\d{1,2}/\d{2,4})\s+(\d{1,2}:\d{2})\)", line, re.IGNORECASE)
            if m_tecnolab:
                date_part, time_part = m_tecnolab.group(1), m_tecnolab.group(2)
                try:
                    dt_obj_date = date_parser.parse(date_part, dayfirst=True)
                    day_month = dt_obj_date.strftime("%d/%m")
                    h_part, m_part = time_part.split(':')
                    return f"{day_month} {h_part.zfill(2)}h{m_part.zfill(2)}"
                except (ValueError, TypeError):
                    continue
        return "" 

    for line in lines:
        m_specific = re.search(
            r"Data de Coleta/Recebimento:\s*(\d{1,2}/\d{1,2}/\d{2,4}),\s*Hora Aproximada:\s*(\d{1,2}:\d{2})(?:\s+\w{2,4})?",
            line, re.IGNORECASE
        )
        if m_specific:
            date_part_full, time_part = m_specific.group(1), m_specific.group(2)
            try:
                dt_obj_date = date_parser.parse(date_part_full, dayfirst=True, fuzzy=False)
                day_month = dt_obj_date.strftime("%d/%m")
                h_part, m_part = time_part.split(':')
                return f"{day_month} {h_part.zfill(2)}h{m_part.zfill(2)}"
            except (ValueError, TypeError):
                day_month_match = re.match(r"(\d{1,2}/\d{1,2})", date_part_full)
                if day_month_match:
                    h_part, m_part = time_part.split(':')
                    return f"{day_month_match.group(1)} {h_part.zfill(2)}h{m_part.zfill(2)}"
    return ""


def extract_hemograma_completo(lines, is_tecnolab):
    results = {}
    
    red_idx = next((i for i, l in enumerate(lines) if "série vermelha" in l.lower() or "eritrograma" in l.lower()), -1)
    search_scope = lines[red_idx:] if red_idx != -1 else lines
    
    mapa_vermelha = {
        "Hb": ["Hemoglobina", "Hb"],
        "Ht": ["Hematócrito", "Ht"],
        "VCM": ["VCM", "Volume Corpuscular"],
        "HCM": ["HCM", "Hemoglobina Corpuscular"],
        "CHCM": ["CHCM", "Concentração"],
        "RDW": ["RDW", "Red Cell"]
    }

    for key, labels in mapa_vermelha.items():
        for line in search_scope:
            for label in labels:
                if label.lower() in line.lower():
                    pattern = re.escape(label) + r"[.:\s]*" + NUM_PATTERN
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        results[key] = match.group(1)
                        break 
            if key in results: break

    leuco_val = ""
    for i, line in enumerate(lines):
        if "leucócitos" in line.lower() and "urina" not in line.lower(): 
            nums = re.findall(NUM_PATTERN, line)
            for num in nums:
                clean_n = clean_number_format(num)
                try:
                    val_float = float(clean_n)
                    if 1000 < val_float < 500000: 
                        leuco_val = clean_n; break
                    if val_float < 100 and ("mil" in line.lower() or "x10^3" in line.lower()):
                         leuco_val = str(int(val_float * 1000)); break
                except: continue
            if leuco_val: break     
    results["Leuco"] = leuco_val

    diff = []
    
    def extract_diff_item(label_list):
        for line in lines:
            if "valor de referência" in line.lower(): continue
            if any(l.lower() in line.lower() for l in label_list):
                pattern_percent = r"(?:" + "|".join(label_list) + r")[.:\s]*(" + NUM_PATTERN + r")\s*%"
                m_perc = re.search(pattern_percent, line, re.IGNORECASE)
                if m_perc: return m_perc.group(1)
                
                pattern_num = r"(?:" + "|".join(label_list) + r")[.:\s]*(" + NUM_PATTERN + r")"
                m_num = re.search(pattern_num, line, re.IGNORECASE)
                if m_num:
                    try:
                        v = float(clean_number_format(m_num.group(1)))
                        if 0 <= v <= 100: return m_num.group(1)
                    except: pass
        return ""

    bast = extract_diff_item(["Bastonetes", "Bastões"])
    if bast: diff.append(f"Bast {bast}%")

    seg = extract_diff_item(["Segmentados", "Segs"])
    if not seg: seg = extract_diff_item(["Neutrófilos", "Neutrofilos"])
    if seg: diff.append(f"Seg {seg}%")

    linf = extract_diff_item(["Linfócitos", "Linfocitos"])
    if linf: diff.append(f"Linf {linf}%")
    
    eos = extract_diff_item(["Eosinófilos"])
    if eos and float(clean_number_format(eos)) > 0:
        diff.append(f"Eos {eos}%")

    results["Leuco_Diff"] = f"({', '.join(diff)})" if diff else ""

    results["Plaq"] = ""
    for line in lines:
        if "plaquetas" in line.lower() and "volume" not in line.lower():
             m = re.search(r"Plaquetas[.:\s]*(" + NUM_PATTERN + r")", line, re.IGNORECASE)
             if m:
                 val_plaq = m.group(1)
                 results["Plaq"] = val_plaq
                 try:
                     if "mil" in line.lower() or float(clean_number_format(val_plaq)) < 1000:
                         results["Plaq_unit"] = " mil"
                 except: pass
                 break
    
    return results

def extract_coagulograma(lines, is_tecnolab):
    results = {}
    if is_tecnolab:
        results["TP_s"] = extract_labeled_value(lines, "TEMPO DE PROTROMBINA....:", search_window_lines=0)
        results["INR"] = extract_labeled_value(lines, "I.N.R...................:", search_window_lines=0)
        ttpa_idx = next((i for i, l in enumerate(lines) if "tempo tromboplastina parcial ativada" in l.lower()), -1)
        if ttpa_idx != -1 and ttpa_idx + 1 < len(lines):
            match = re.search(r"RESULTADO:\s*" + NUM_PATTERN, lines[ttpa_idx + 1])
            if match:
                results["TTPA_s"] = match.group(1)
        return results

    results["TP_s"] = extract_labeled_value(lines, "Tempo em segundos:", label_must_be_at_start=False, search_window_lines=0)
    inr_val = ""
    for i, line in enumerate(lines):
        if "Internacional (RNI):" in line:
            if i + 1 < len(lines):
                m_inr = re.search(NUM_PATTERN, lines[i+1])
                if m_inr:
                    inr_val = m_inr.group(1)
                    break
    if not inr_val:
        inr_val = extract_labeled_value(lines, ["RNI:", "INR:"], label_must_be_at_start=False, search_window_lines=1)
    results["INR"] = inr_val

    ttpa_idx = next((i for i, l in enumerate(lines) if ("tempo de tromboplastina parcial ativado" in l.lower() or "ttpa" in l.lower()) and "tempo de protrombina" not in l.lower()), -1)
    if ttpa_idx != -1:
        search_ttpa = lines[ttpa_idx:]
        results["TTPA_s"] = extract_labeled_value(search_ttpa, "Tempo em segundos", label_must_be_at_start=False, search_window_lines=1)
        results["TTPA_R"] = extract_labeled_value(search_ttpa, "Relação:", label_must_be_at_start=False, search_window_lines=1)
    return results

def extract_tecnolab_generic(lines, labels):
    if isinstance(labels, str): labels = [labels]
    for i, line in enumerate(lines):
        if any(label.lower() in line.lower() for label in labels) and "resultado" not in line.lower():
            for j in range(i, min(i + 4, len(lines))):
                if "RESULTADO:" in lines[j]:
                    match = re.search(r"RESULTADO:\s*" + NUM_PATTERN, lines[j], re.IGNORECASE)
                    if match:
                        return match.group(1)
    return ""

def extract_funcao_renal_e_eletrólitos(lines, is_tecnolab):
    results = {}
    if is_tecnolab:
        results["U"] = extract_labeled_value(lines, ["Ureia", "Uréia"], label_must_be_at_start=False)
        results["Cr"] = extract_tecnolab_generic(lines, "CREATININA")
        
        egfr_afro = extract_labeled_value(lines, "*eGFR - Afro Descendente:")
        egfr_non_afro = extract_labeled_value(lines, "*eGFR Não Afro Descendente:")
        if egfr_afro and egfr_non_afro:
             results["eGFR"] = f"{clean_number_format(egfr_afro)}-{clean_number_format(egfr_non_afro)}"
        
        results["K"] = extract_tecnolab_generic(lines, ["DOSAGEM DE POTÁSSIO", "POTÁSSIO"])
        results["Na"] = extract_tecnolab_generic(lines, ["DOSAGEM DE SÓDIO", "SÓDIO"])
        results["Mg"] = extract_tecnolab_generic(lines, ["DOSAGEM DE MAGNÉSIO", "MAGNÉSIIO"])
        results["CaT"] = extract_tecnolab_generic(lines, "CALCIO") 
        results["Gli"] = extract_tecnolab_generic(lines, ["DOSAGEM DE GLICOSE", "GLICOSE"])
        return results

    results["U"] = extract_labeled_value(lines, "Ureia", label_must_be_at_start=True)
    if not results["U"]: results["U"] = extract_labeled_value(lines, "U ", label_must_be_at_start=True)
    results["Cr"] = extract_labeled_value(lines, "Creatinina ", label_must_be_at_start=True)
    results["eGFR"] = extract_labeled_value(lines, ["eGFR", "*eGFR", "Ritmo de Filtração Glomerular"], label_must_be_at_start=True)
    for k, lbls in [("K", ["Potássio", "K "]), ("Na", ["Sódio", "Na "]), ("Mg", "Magnésio"),
                    ("P", "Fósforo"), ("CaI", "Cálcio Iônico"), ("Cl", ["Cloro","Cloreto", "Cl "]), ("Gli", ["Glicose", "Glicemia"])]:
        results[k] = extract_labeled_value(lines, lbls, label_must_be_at_start=k not in ["CaI"])
    return results

def extract_marcadores_inflamatorios_cardiacos(lines, is_tecnolab):
    results = {}
    if is_tecnolab:
        results["PCR"] = extract_tecnolab_generic(lines, 'PROTEINA "C" REATIVA')
        results["Trop"] = extract_tecnolab_generic(lines, 'TROPONINA T (ALTA SENSIBILIDADE)')
        results["NT-proBNP"] = extract_tecnolab_generic(lines, 'NT-proBNP')
        return results

    for k, lbls, start in [("PCR",["Proteína C Reativa","PCR"],True), ("Lac","Lactato",True), ("Trop","Troponina",False), ("DD","D-Dímero",False)]:
        results[k] = extract_labeled_value(lines, lbls, label_must_be_at_start=start)
    return results

def extract_hepatograma_pancreas(lines, is_tecnolab):
    results = {}
    if is_tecnolab:
        results["TGO"] = extract_tecnolab_generic(lines, "TRANSAMINASE OXALACETICA - TGO")
        results["TGP"] = extract_tecnolab_generic(lines, "TRANSAMINASE PIRUVICA (TGP)")
        results["FA"] = extract_tecnolab_generic(lines, "FOSFATASE ALCALINA")
        results["GGT"] = extract_tecnolab_generic(lines, "GAMA-GLUTAMIL TRANSFERASE")
        results["AML"] = extract_tecnolab_generic(lines, "AMILASE")
        
        bili_idx = next((i for i, l in enumerate(lines) if "bilirrubina" in l.lower() and "resultado" in l.lower()), -1)
        if bili_idx == -1:
             bili_idx = next((i for i, l in enumerate(lines) if l.strip().upper() == "BILIRRUBINA"),-1)
        if bili_idx != -1:
            search_bili = lines[bili_idx : bili_idx + 5]
            results["BT"] = extract_labeled_value(search_bili, "TOTAL....:", search_window_lines=0)
            results["BD"] = extract_labeled_value(search_bili, "DIRETA...:", search_window_lines=0)
            results["BI"] = extract_labeled_value(search_bili, "INDIRETA.:", search_window_lines=0)
        
        return results
        
    tgo_val, tgp_val = "", ""
    for i, line in enumerate(lines):
        if not tgo_val and ("Transaminase oxalacética - TGO" in line or ("Aspartato amino transferase" in line and "TGO" in line.upper())):
            for offset in range(1, 4):
                if i + offset < len(lines):
                    target_line = lines[i + offset]
                    match_ul = re.match(r"^\s*" + NUM_PATTERN + r"\s*U/L", target_line)
                    if match_ul: tgo_val = match_ul.group(1); break
            if not tgo_val and i + 2 < len(lines):
                 m = re.search(NUM_PATTERN, lines[i+2])
                 if m: tgo_val = m.group(1)
        if not tgp_val and ("Transaminase pirúvica - TGP" in line or ("Alanina amino transferase" in line and "TGP" in line.upper())):
            for offset in range(1, 4):
                if i + offset < len(lines):
                    target_line = lines[i + offset]
                    match_ul = re.match(r"^\s*" + NUM_PATTERN + r"\s*U/L", target_line)
                    if match_ul: tgp_val = match_ul.group(1); break
            if not tgp_val and i + 2 < len(lines):
                 m = re.search(NUM_PATTERN, lines[i+2])
                 if m: tgp_val = m.group(1)
    results["TGO"] = tgo_val
    results["TGP"] = tgp_val
    if not results.get("TGO"): results["TGO"] = extract_labeled_value(lines, ["TGO", "AST"], label_must_be_at_start=False, search_window_lines=1, require_unit="U/L")
    if not results.get("TGP"): results["TGP"] = extract_labeled_value(lines, ["TGP", "ALT"], label_must_be_at_start=False, search_window_lines=1, require_unit="U/L")
    results["GGT"] = extract_labeled_value(lines, ["Gama-Glutamil Transferase", "GGT"], label_must_be_at_start=True, search_window_lines=0, require_unit="U/L")
    if not results["GGT"]: results["GGT"] = extract_labeled_value(lines, ["Gama-Glutamil Transferase", "GGT"], label_must_be_at_start=True, search_window_lines=0)
    results["FA"] = extract_labeled_value(lines, "Fosfatase Alcalina", label_must_be_at_start=True, search_window_lines=0, require_unit="U/L")
    if not results["FA"]: results["FA"] = extract_labeled_value(lines, "Fosfatase Alcalina", label_must_be_at_start=True, search_window_lines=0)
    bilirrubina_section_found = False
    bilirrubina_start_index = -1
    for i, line in enumerate(lines):
        if "bilirrubinas total, direta e indireta" in line.lower():
            bilirrubina_section_found = True
            bilirrubina_start_index = i
            break
    search_scope_bilirrubinas = lines[bilirrubina_start_index:] if bilirrubina_section_found else lines
    results["BT"] = extract_labeled_value(search_scope_bilirrubinas, "Bilirrubina Total", label_must_be_at_start=True, search_window_lines=1)
    results["BD"] = extract_labeled_value(search_scope_bilirrubinas, "Bilirrubina Direta", label_must_be_at_start=True, search_window_lines=1)
    results["BI"] = extract_labeled_value(search_scope_bilirrubinas, "Bilirrubina Indireta", label_must_be_at_start=True, search_window_lines=1)
    if not results.get("BT"): results["BT"] = extract_labeled_value(lines, "Bilirrubina Total", label_must_be_at_start=True, search_window_lines=1)
    if not results.get("BD"): results["BD"] = extract_labeled_value(lines, "Bilirrubina Direta", label_must_be_at_start=True, search_window_lines=1)
    if not results.get("BI"): results["BI"] = extract_labeled_value(lines, "Bilirrubina Indireta", label_must_be_at_start=True, search_window_lines=1)
    results["ALB"] = extract_labeled_value(lines, "Albumina", label_must_be_at_start=True, search_window_lines=1)
    results["AML"] = extract_labeled_value(lines, "Amilase", label_must_be_at_start=True, search_window_lines=1)
    results["LIP"] = extract_labeled_value(lines, "Lipase", label_must_be_at_start=True, search_window_lines=1)
    return results

def extract_medicamentos(lines, is_tecnolab):
    results = {}
    results["Vanco"] = extract_labeled_value(lines, "Vancomicina", label_must_be_at_start=False, search_window_lines=0, require_unit="µg/mL")
    return results

def extract_gasometria(lines, is_tecnolab):
    results = {}
    exam_prefix = ""
    gas_idx = -1
    gas_header_found = False

    for i, line in enumerate(lines):
        l_line = line.lower()
        if "gasometria arterial" in l_line:
            exam_prefix = "GA_"
            gas_idx = i
            gas_header_found = True
            break
        elif "gasometria venosa" in l_line:
            exam_prefix = "GV_"
            gas_idx = i
            gas_header_found = True
            break
    
    if not gas_header_found:
        for i, line in enumerate(lines):
            l_line = line.lower()
            if "gasometria" in l_line:
                gas_idx = i
                if "arterial" in l_line: exam_prefix = "GA_"
                elif "venosa" in l_line: exam_prefix = "GV_"
                gas_header_found = True
                break

    if not gas_header_found:
        return results

    gas_map = {
        "ph": "pH_gas", "pco2": "pCO2_gas", "hco3": "HCO3_gas",
        "bicarbonato": "HCO3_gas", "be": "BE_gas", "excesso de bases": "BE_gas",
        "po2": "pO2_gas", "saturação de o2": "SatO2_gas", "sato2": "SatO2_gas",
        "lactato": "Lac_gas", "lac": "Lac_gas", "co2 total": "cCO2_gas", "conteúdo de co2": "cCO2_gas"
    }

    search_lines = lines[gas_idx + 1 : min(gas_idx + 20, len(lines))]
    
    for line_content in search_lines:
        if any(hdr in line_content.lower() for hdr in ["hemograma", "coagulograma", "bioquimica", "cultura", "urina tipo i", "assinado eletronicamente", "material:"]):
            break
        
        match = re.match(r"^\s*([a-zA-Z0-9+\s]+?)\s*:\s*" + GAS_NUM_PATTERN, line_content)
        if match:
            label = match.group(1).strip().lower()
            value = match.group(2)
            if label in gas_map:
                out_key = gas_map[label]
                if out_key not in results:
                    results[out_key] = value
            continue

    if exam_prefix:
        return {exam_prefix + k: v for k, v in results.items() if v}
    elif results:
        return {k: v for k, v in results.items() if v}
    return {}


def extract_sorologias(lines, is_tecnolab):
    results = {}
    tests = [("Anti HIV 1/2","HIV"),("Anti-HAV (IgM)","HAV_IgM"),("HBsAg","HBsAg"),("Anti-HBs","AntiHBs"),
             ("Anti-HBc Total","AntiHBc_Total"),("Anti-HCV","HCV"),("VDRL","VDRL")]
    for i, line in enumerate(lines):
        l_line = line.lower()
        for srch_k, dict_k in tests:
            if srch_k.lower() in l_line:
                res_txt = ""
                for k_rng in range(i, min(i + 3, len(lines))):
                    s_line = lines[k_rng].lower()
                    if any(t in s_line for t in ["não reagente","nao reagente","negativo"]): res_txt = "(-)"; break
                    elif any(t in s_line for t in ["reagente","positivo"]): res_txt = "(+)"; break
                    elif srch_k.lower() in s_line:
                        m = re.search(r"(\d+[:/]\d+)", lines[k_rng])
                        if m: res_txt = f"({m.group(1)})"; break
                if res_txt: results[dict_k] = res_txt; break
    return results

def extract_urina_tipo_i(lines, is_tecnolab):
    results = {}
    u1_idx = next((i for i, l in enumerate(lines) if "urina tipo i" in l.lower()), -1)
    if u1_idx == -1: return {}

    search_u1 = lines[u1_idx : min(u1_idx + 25, len(lines))]
    
    if is_tecnolab:
        for line in search_u1:
            # Regex inclui letras acentuadas maiúsculas (À-Ú) para capturar PROTEÍNA, HEMÁCIAS, LEUCÓCITOS, REAÇÃO etc.
            match = re.match(r"\s*([A-ZÀ-Ú\s-]+)\s*:\s*(.+)", line)
            if match:
                key, value = match.group(1).strip().lower(), match.group(2).strip()
                val_num_match = re.search(NUM_PATTERN, value)
                if "ph" in key: results["U1_pH"] = val_num_match.group(1) if val_num_match else ""
                elif "densidade" in key: results["U1_dens"] = value.split()[0]
                elif "proteína" in key: results["U1_prot"] = "(-)" if "negativo" in value.lower() else "(+)"
                elif "glicose" in key: results["U1_glic"] = "(-)" if "negativo" in value.lower() else "(+)"
                elif "nitrito" in key: results["U1_nit"] = "(-)" if "negativo" in value.lower() else "(+)"
                elif "corpos cetônicos" in key: results["U1_CC"] = "(-)" if "negativo" in value.lower() else "(+)"
                elif "hemácias" in key:
                     # Preserva formato brasileiro com ponto como separador de milhar (ex: 3.000)
                     if val_num_match: results["U1_hem"] = val_num_match.group(1)
                elif "leucócitos" in key:
                    if "acima de" in value.lower() and val_num_match:
                        results["U1_leuco"] = ">" + val_num_match.group(1)
                    elif val_num_match:
                        results["U1_leuco"] = val_num_match.group(1)
        return results

    for line in search_u1:
        l_line = line.lower()
        if "assinado eletronicamente" in l_line or ("método:" in l_line and "urina tipo i" not in l_line): break
        if "nitrito" in l_line: results["U1_nit"] = "(+)" if "positivo" in l_line else "(-)"
        for k, lbls, terms in [("U1_leuco",["leucócitos"],{"numerosos":"Num","inumeros":"Num","raros":"Raros","campos cobertos":"Cob"}),
                               ("U1_hem",["hemácias","eritrócitos"],{"numerosas":"Num","inumeras":"Num","raras":"Raras","campos cobertos":"Cob"})]:
            if any(lbl in l_line for lbl in lbls):
                search_text = line.split(lbls[0])[-1] if lbls[0] in line else line
                m = re.search(NUM_PATTERN, search_text)
                if m and clean_number_format(m.group(1)).isdigit():
                    results[k] = clean_number_format(m.group(1)); break
                for term, abbr in terms.items():
                    if term in l_line: results[k] = abbr; break
                if k in results: break
    return results

def extract_culturas(lines, is_tecnolab):
    found_cultures = []
    if is_tecnolab:
        for i, line in enumerate(lines):
            l_line = line.lower()
            cult_type, cult_result = None, None
            if l_line.startswith("urocultura"):
                cult_type = "URC"
                if i + 2 < len(lines) and "resultado:" in lines[i+1].lower():
                    if "não houve crescimento" in lines[i+2].lower(): cult_result = "(-)"
            elif l_line.startswith("hemocultura"):
                cult_type = "HMC"
                if i + 1 < len(lines) and "resultado parcial:" in lines[i+1].lower():
                    if "parcialmente negativo" in lines[i+1].lower(): cult_result = "PN"

            if cult_type and cult_result:
                found_cultures.append({"Tipo": cult_type, "Resultado": cult_result})
        
        unique_cultures = []
        seen = set()
        for cult in found_cultures:
            identifier = cult["Tipo"] 
            if identifier not in seen:
                unique_cultures.append(cult)
                seen.add(identifier)
        return unique_cultures

    germe_regex = r"([A-Z][a-z]+\s(?:cf\.\s)?[A-Z]?[a-z]+)"
    i = 0
    while i < len(lines):
        line_content = lines[i]
        l_line = line_content.lower()
        is_culture_header = "cultura de urina" in l_line or \
                            "urocultura" in l_line or \
                            "hemocultura" in l_line
        if is_culture_header:
            current_culture_block_lines = [line_content]
            j = i + 1
            while j < len(lines):
                next_line_lower = lines[j].lower()
                is_next_block_header = "cultura de urina" in next_line_lower or "urocultura" in next_line_lower or "hemocultura" in next_line_lower or "hemograma" in next_line_lower or "coagulograma" in next_line_lower or "bioquimica" in next_line_lower or "urina tipo i" in next_line_lower or "assinado eletronicamente" in next_line_lower
                if is_next_block_header:
                    break
                current_culture_block_lines.append(lines[j])
                j += 1
            culture_data = process_single_culture_block(current_culture_block_lines, germe_regex)
            if culture_data: found_cultures.append(culture_data)
            i = j
            continue
        i += 1
    final_cultures = []
    seen_types_and_results = set()
    for cult in found_cultures:
        cult_id_tuple = (cult.get("Tipo"), cult.get("Resultado","").split(" / ")[0])
        is_meaningful_hmc_negative = "HMC" in cult.get("Tipo","") and cult.get("Resultado","") == "(-)"
        is_positive_result = "(+)" in cult.get("Resultado","")
        has_antibiogram = any(val for val in cult.get("Antibiograma", {}).values())
        if is_meaningful_hmc_negative or is_positive_result or has_antibiogram:
            if cult_id_tuple not in seen_types_and_results or is_meaningful_hmc_negative:
                final_cultures.append(cult)
                if not is_meaningful_hmc_negative:
                    seen_types_and_results.add(cult_id_tuple)
    return final_cultures


def process_single_culture_block(block_lines, germe_regex):
    current_culture_data = {}
    culture_type_label, culture_type_detail, sample_info = None, "", ""
    first_line_lower = block_lines[0].lower()
    if "cultura de urina" in first_line_lower or "urocultura" in first_line_lower:
        culture_type_label = "URC"
    elif "hemocultura" in first_line_lower:
        culture_type_detail = "Aeróbio" if "aeróbios" in first_line_lower or "aerobio" in first_line_lower else \
                              "Anaeróbio" if "anaeróbios" in first_line_lower or "anaerobio" in first_line_lower else ""
        culture_type_label = f"HMC {culture_type_detail}".strip()
        sample_match = re.search(r"\(Amostra\s*(\d+/\d+)\)", block_lines[0], re.IGNORECASE) or \
                       (1 < len(block_lines) and re.search(r"\(Amostra\s*(\d+/\d+)\)", block_lines[1], re.IGNORECASE))
        if sample_match: culture_type_label += f" Amostra {sample_match.group(1)}"
    if not culture_type_label: return None
    current_culture_data["Tipo"] = culture_type_label.strip()
    result_text_found = "(-)"
    for r_line in block_lines:
        lc_r_line = r_line.lower()
        if lc_r_line.startswith("resultado:") or "resultado da cultura:" in lc_r_line:
            res_text = re.sub(r"(?i)(resultado:|resultado da cultura:)", "", r_line, count=1).strip()
            germe_match = re.search(germe_regex, res_text)
            if germe_match:
                result_text_found = f"{germe_match.group(1).strip()} (+)"
            elif any(neg in res_text.lower() for neg in ["negativo", "negativa", "não houve crescimento", "ausência de crescimento"]):
                result_text_found = "(-)"
            elif res_text:
                result_text_clean = res_text.split("Negativo")[0].strip()
                if result_text_clean: result_text_found = f"{result_text_clean} (+)"
            break
    current_culture_data["Resultado"] = result_text_found
    antibiogram_results, antibiogram_start_idx_in_block = {"S": [], "I": [], "R": []}, -1
    for k, abg_line in enumerate(block_lines):
        if any(term in abg_line.lower() for term in ["antibiograma", "tsa", "teste de sensibilidade"]):
            antibiogram_start_idx_in_block = k; break
    if antibiogram_start_idx_in_block != -1:
        for k_abg in range(antibiogram_start_idx_in_block + 1, len(block_lines)):
            line_abg = block_lines[k_abg].strip()
            if not line_abg or "legenda:" in line_abg.lower() or "valor de referência" in line_abg.lower() or \
               line_abg.lower().startswith("método:") or line_abg.lower().startswith("nota:"): break
            m = re.match(r"^\s*([a-zA-ZÀ-ÿ0-9\s.,()/-]+?)\s+[.,:]*\s*([SIR])\b", line_abg, re.IGNORECASE) or \
                re.match(r"^\s*([a-zA-ZÀ-ÿ0-9\s.,()/-]+?)\s+.*?\b([SIR])\s*$", line_abg, re.IGNORECASE)
            if m:
                name, code = re.sub(r'\s*\.\s*', '', m.group(1).strip()).strip(), m.group(2).upper()
                if code in antibiogram_results: antibiogram_results[code].append(name)
    current_culture_data["Antibiograma"] = antibiogram_results
    return current_culture_data

# --- Funções de Interação com IA Gemini ---
# --- Função de Processamento de Arquivos para Gemini ---
def process_uploaded_files_for_gemini(uploaded_files):
    """Convert Streamlit uploaded files to Gemini-compatible content parts."""
    parts = []
    file_descriptions = []
    
    if not uploaded_files:
        return parts, file_descriptions
    
    for f in uploaded_files:
        try:
            file_bytes = f.getvalue()
            
            if f.type and f.type.startswith('image/'):
                img = Image.open(io.BytesIO(file_bytes))
                # Convert RGBA to RGB if needed (Gemini prefers RGB)
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                parts.append(img)
                file_descriptions.append(f"Imagem: {f.name}")
                
            elif f.type == 'application/pdf':
                # Send PDF directly to Gemini (supports native PDF understanding)
                parts.append({
                    "mime_type": "application/pdf",
                    "data": file_bytes
                })
                file_descriptions.append(f"PDF: {f.name}")
            else:
                # Try to read as text for other file types
                try:
                    text_content = file_bytes.decode('utf-8')
                    parts.append(f"\n--- Conteúdo do arquivo {f.name} ---\n{text_content}\n---\n")
                    file_descriptions.append(f"Texto: {f.name}")
                except UnicodeDecodeError:
                    file_descriptions.append(f"(Arquivo não suportado: {f.name})")
        except Exception as e:
            file_descriptions.append(f"(Erro ao processar {f.name}: {e})")
    
    return parts, file_descriptions


def gerar_resposta_ia(prompt_text, file_parts=None):
    if not gemini_available:
        return "Funcionalidade de IA indisponível. Verifique a configuração da API Key."
    try:
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        # Build multimodal content: text + files
        if file_parts:
            content = [prompt_text] + file_parts
        else:
            content = prompt_text
        
        try:
            response = gemini_model_pro.generate_content(content, safety_settings=safety_settings)
        except ResourceExhausted:
            print("LOG: Cota do 3.0 Pro excedida. Fallback acionado para o 3.0 Flash.")
            response = gemini_model_flash.generate_content(content, safety_settings=safety_settings)

        processed_text = response.text
        processed_text = re.sub(r"\[IA:[^\]]*?\]", "", processed_text)
        
        headers_para_espaco = [
            "#CUIDADOS PALIATIVOS:", "#ID:", "#HD:", "#AP:", "#HDA:", "#MUC:",
            "#ALERGIAS:", "#ATB:", "#TEV:", "#EXAMES:", "#EVOLUÇÃO:",
            "#EXAME FÍSICO:", "#PLANO TERAPÊUTICO:", "#CONDUTA:"
        ]
        final_lines_with_spacing = []
        lines_response = processed_text.splitlines()
        for i, line in enumerate(lines_response):
            final_lines_with_spacing.append(line)
            if line.strip() and any(line.strip().startswith(h) for h in headers_para_espaco):
                if i + 1 < len(lines_response):
                    if lines_response[i+1].strip() != "" and not lines_response[i+1].strip().startswith("#"):
                        final_lines_with_spacing.append("")
                elif i + 1 == len(lines_response):
                     final_lines_with_spacing.append("")
        cleaned_final_lines = []
        previous_line_was_blank = False
        for line in final_lines_with_spacing:
            is_current_line_blank = not line.strip()
            if not (previous_line_was_blank and is_current_line_blank):
                cleaned_final_lines.append(line)
            previous_line_was_blank = is_current_line_blank
        processed_text = "\n".join(cleaned_final_lines)
        return anonimizar_texto(processed_text)
    except Exception as e:
        return f"Erro ao comunicar com a API do Gemini: {e}"

def evoluir_paciente_enfermaria_ia_fase1(evolucao_anterior, file_parts=None):
    prompt = f"""Você é um médico hospitalista sênior, especialista em clínica médica, atuando como consultor de um médico diarista durante a visita de enfermaria. Seu ambiente é um convênio verticalizado: a eficiência (giro de leito, redução do tempo de permanência - LOS) e a prevenção de iatrogenias são tão vitais quanto a precisão diagnóstica. Todas as suas análises são baseadas nas melhores evidências (diretrizes, RCTs).
O usuário enviará informações por texto ou foto. Se houver dados cruciais ilegíveis/ausentes, aponte-os imediatamente. Você apoia a decisão médica, nunca a substitui. Seja implacável na objetividade. Use linguagem clínica árida e direta.

Abaixo está a evolução de um paciente. Para cada caso, gere a resposta EXATAMENTE nesta estrutura:

1. One-Liner (Resumo)
Parágrafo único. ID do paciente, motivo da internação, D-internação, D-antibiótico (se aplicável), evolução macro e estado atual.

2. Foco Operacional de Hoje
Bullet points curtos. O que destrava o caso hoje? (Ex: pendências de exames críticos, retornos de interconsultas, gargalos que impedem a progressão do cuidado).

3. Raciocínio Diagnóstico (Tabela de Decisão)
Caso a hipótese do usuário pareça frágil, confronte-a polidamente. Apresente as hipóteses em formato de tabela para leitura rápida:
| Hipótese | Pontos a Favor | Pontos Contra | Próximo Passo (Exame de alto impacto/baixo custo) |
| :--- | :--- | :--- | :--- |
| [Doença] | [Clínica/Labs] | [Clínica/Labs] | [Conduta] |

4. Conduta e Desprescrição
* Adicionar/Ajustar: Terapias e exames estritamente necessários (evite overtesting). Justifique brevemente a mudança.
* Desprescrever: Identifique ativamente polifarmácia, medicações sem indicação atual ou exames de rotina desnecessários que podem ser suspensos.

5. Checklist de Segurança (Giro de Leito & Iatrogenia)
Responda em linha, apenas com "Sim/Não/Avaliar":
* Dispositivos invasivos (Acesso/SVD/SNE) podem ser sacados hoje?
* Profilaxia TVP/Gástrica otimizada?
* Transição ATB IV para VO possível?

6. Alerta de Risco (Apenas se houver)
Destaque em negrito se houver sinais de deterioração (qSOFA, instabilidade, delírio hipoativo mascarado). Se não houver, omita esta seção.

7. Gargalo da Alta (Discharge Planning)
Qual é o fator limitante para a alta deste paciente neste exato momento? (Ex: Término de ATB IV, instabilidade hemodinâmica, aguardando vaga de transição, dependência de O2). O que precisamos fazer HOJE para resolver esse gargalo amanhã?

---
REFERÊNCIAS DE STEWARDSHIP DE ANTIBIÓTICO (use ao sugerir duração, switch IV→VO ou de-escalação):

Duração recomendada (IDSA/SBI/Sanford):
- PAC não grave (CURB-65 < 2): 5 dias, desde que afebril 48h e estável
- PAC grave ou bacterêmica: 7 dias
- ITU baixa não complicada: 3-5 dias (nitrofurantoína 5d, fosfomicina 1d, SMX-TMP 3d)
- Pielonefrite/ITU complicada: 7 dias (fluoroquinolona) ou 10-14 dias (betalactâmico)
- Celulite não purulenta: 5-6 dias, estendível se resposta lenta
- Infecção intra-abdominal com controle de foco: 4-7 dias
- Bacteriemia por BGN (foco controlado): 7 dias
- Bacteriemia por S. aureus: 14 dias mínimo (investigar endocardite)
- Meningite bacteriana: depende do agente (pneumococo 10-14d, N. meningitidis 7d, Listeria 21d)

Critérios para switch IV→VO (COMS - todos devem estar presentes):
- Clinical improvement (melhora clínica sustentada)
- Oral route available (tolerando VO, sem vômitos/íleo/má-absorção)
- Markers improving (febre em queda 24h, leucócitos caindo)
- Stable hemodynamic 24-48h

Sinais de alerta para escalonamento/revisão:
- Piora clínica após 72h de ATB adequado → reavaliar diagnóstico, cobertura, foco
- Cultura positiva com resistência à cobertura empírica → ajustar imediatamente
- Cultura negativa após 48h em paciente estável com baixa probabilidade pré-teste → considerar suspender

Evolução do paciente:
---
{evolucao_anterior}
---
"""
    return gerar_resposta_ia(prompt, file_parts=file_parts)

def evoluir_paciente_enfermaria_ia_fase2(resumo_ia_fase1, dados_medico_hoje, evolucao_anterior_original, file_parts=None):
    evolucao_anterior_original_anon = anonimizar_texto(evolucao_anterior_original)
    dados_medico_hoje_anon = anonimizar_texto(dados_medico_hoje)

    linhas_evol_anterior = evolucao_anterior_original_anon.splitlines()
    campos_fixos_dict = {}
    hda_labels_map = {"#HDA:": "#HDA:", "#HMA:": "#HDA:", "#HPMA:": "#HDA:"}
    campos_para_manter_padronizados = {"#CUIDADOS PALIATIVOS:", "#ID:", "#HD:", "#AP:", "#HDA:", "#MUC:", "#ALERGIAS:", "#ATB:", "#TEV:"}

    current_field_content = []
    current_field_label_padronizado = None

    for linha in linhas_evol_anterior:
        linha_strip = linha.strip()
        matched_label_original = None
        matched_label_padronizado_para_este_header = None

        for label_original_evol, label_padronizado_map in hda_labels_map.items():
            if linha_strip.startswith(label_original_evol):
                matched_label_original = label_original_evol
                matched_label_padronizado_para_este_header = label_padronizado_map
                break

        if not matched_label_original:
            for label_fixo in campos_para_manter_padronizados:
                if label_fixo not in hda_labels_map and linha_strip.startswith(label_fixo):
                    matched_label_original = label_fixo
                    matched_label_padronizado_para_este_header = label_fixo
                    break

        if linha_strip.startswith("#CUIDADOS PALIATIVOS:") and not matched_label_original :
            matched_label_original = "#CUIDADOS PALIATIVOS:"
            matched_label_padronizado_para_este_header = "#CUIDADOS PALIATIVOS:"

        is_outro_header_que_quebra_bloco = any(linha_strip.startswith(h) for h in ["#EXAMES:", "#EVOLUÇÃO:", "#EXAME FÍSICO:", "#PLANO TERAPÊUTICO:", "#CONDUTA:", "#DATA PROVÁVEL DA ALTA:"])

        if matched_label_original:
            if current_field_label_padronizado:
                campos_fixos_dict[current_field_label_padronizado] = "\n".join(current_field_content).strip()

            current_field_label_padronizado = matched_label_padronizado_para_este_header
            current_field_content = [linha_strip.split(matched_label_original, 1)[-1].strip()]
        elif is_outro_header_que_quebra_bloco:
            if current_field_label_padronizado:
                campos_fixos_dict[current_field_label_padronizado] = "\n".join(current_field_content).strip()
            current_field_label_padronizado = None
            current_field_content = []
        elif current_field_label_padronizado:
            current_field_content.append(linha_strip)

    if current_field_label_padronizado:
        campos_fixos_dict[current_field_label_padronizado] = "\n".join(current_field_content).strip()

    exames_bloco_anterior_str = ""
    capturando_exames = False
    temp_exames_lines = []
    for linha in linhas_evol_anterior:
        if linha.strip().startswith("#EXAMES:"): capturando_exames = True
        elif capturando_exames and linha.strip().startswith("#"): capturando_exames = False
        if capturando_exames: temp_exames_lines.append(linha)
    if temp_exames_lines:
        exames_bloco_anterior_str = "\n".join([l.replace("#EXAMES:", "", 1).strip() for l in temp_exames_lines if l.strip() and l.strip() != "#EXAMES:"]).strip()

    template_evolucao_parts = ["# UNIDADE DE INTERNAÇÃO - EVOLUÇÃO#\n"]
    cuidados_paliativos_texto = campos_fixos_dict.get("#CUIDADOS PALIATIVOS:", "")
    if cuidados_paliativos_texto and cuidados_paliativos_texto.lower().strip() not in ["não", "nao", "no", "", "n", "negativo", "ausente", "nada digno de nota", "ndn", "0", "zero", "desconhecido", "ignorado"]:
        template_evolucao_parts.append(f"#CUIDADOS PALIATIVOS: {cuidados_paliativos_texto}\n\n")

    for label in ["#ID:", "#HD:", "#AP:", "#HDA:", "#MUC:", "#ALERGIAS:", "#ATB:", "#TEV:"]:
        template_evolucao_parts.append(f"{label} {campos_fixos_dict.get(label, '')}\n\n")

    template_evolucao_parts.append(f"#EXAMES:\n{exames_bloco_anterior_str}\n\n")
    template_evolucao_parts.append("#EVOLUÇÃO:\n\n")
    template_evolucao_parts.append("#EXAME FÍSICO:\n\n")
    template_evolucao_parts.append("#PLANO TERAPÊUTICO:\n\n")
    template_evolucao_parts.append("#CONDUTA:\n\n")
    template_evolucao_parts.append(f"#DATA PROVÁVEL DA ALTA: {campos_fixos_dict.get('#DATA PROVÁVEL DA ALTA:', 'SEM PREVISÃO')}")

    template_evolucao_final = "".join(template_evolucao_parts)

    prompt = f"""Você é um médico hospitalista sênior em convênio verticalizado. Sua tarefa é gerar a nota de EVOLUÇÃO MÉDICA para HOJE. Neste modelo, ofereça APENAS as terapias essenciais baseadas em evidência — nada a mais, nada a menos. Evite overtesting e polifarmácia.

REGRA FUNDAMENTAL DE FORMATO: A evolução gerada DEVE preservar a estrutura e formato da 'Evolução Anterior Original' (fornecida em (2)). Tudo que puder ser mantido, DEVE ser mantido. Copie os campos inalterados VERBATIM. Atualize APENAS o que for necessário com base nos novos dados (fornecidos em (3)).

REGRAS ESPECÍFICAS:
- NÃO use abreviações no texto clínico (anamnese, exame físico, conduta). Escreva por extenso (ex: "Murmúrio vesicular" e não "MV"; "Ruídos hidroaéreos" e não "RHA"; "Membros inferiores" e não "MMII"; "Bulhas rítmicas normofonéticas" e não "BRNF"). EXCEÇÃO: abreviações de exames laboratoriais (Hb, Ht, PCR, TGO, TGP, Na, K, Cr, BNP, etc.) DEVEM ser mantidas como estão — não as expanda.
- #EXAME FÍSICO: PRESERVE o exame físico da evolução anterior como base. Altere APENAS os itens que o médico explicitamente atualizou nos novos dados. Se o médico informou apenas um achado novo (ex: "edema de membros inferiores"), atualize SOMENTE esse item e mantenha todos os demais itens do exame físico anterior intactos e na mesma ordem.
- #ID, #HD, #AP, #HDA (ou #HMA/#HPMA): Mantenha EXATAMENTE como estão na evolução anterior, a menos que haja informação diretamente contraditória nos novos dados.
- #MUC (Medicamentos de Uso Contínuo): Refere-se aos medicamentos que o paciente JÁ USAVA em casa antes da internação (uso crônico/domiciliar). NÃO inclua aqui medicações iniciadas durante a internação atual.
- #ATB (Antibióticos): Inclua TODOS os antibióticos usados durante esta internação — tanto os já suspensos (com data de início e término) quanto os em uso atual (com data de início e dia de terapia D+X).
- #ALERGIAS, #TEV (Profilaxia para TEV): Mantenha como na evolução anterior, salvo mudança explícita.
- #CUIDADOS PALIATIVOS: Omita se não houver informação relevante ou se indicar "não"/"ausente"/"ndn"/vazio.
- #EXAMES: Mantenha os exames anteriores e ADICIONE os novos resultados fornecidos.
- #EVOLUÇÃO: Narrativa objetiva do dia, em linguagem clínica direta.
- #PLANO TERAPÊUTICO e #CONDUTA: Gere novo conteúdo focado no essencial — ajustes necessários, desprescrição ativa de medicações sem indicação, progressão do cuidado. Conduta em primeira pessoa, com hífens.
- ADICIONE UMA LINHA EM BRANCO APÓS CADA CAMPO PRINCIPAL.

DIRETRIZES DE STEWARDSHIP DE ANTIBIÓTICO (aplicar ao gerar #PLANO TERAPÊUTICO e #CONDUTA):
Ao recomendar início, manutenção, de-escalação ou término de antibiótico, consulte estas durações baseadas em IDSA/SBI/Sanford:
- PAC não grave: 5 dias; PAC grave/bacterêmica: 7 dias
- ITU baixa não complicada: 3-5 dias; Pielonefrite/ITU complicada: 7 dias (fluoroquinolona) ou 10-14 dias (betalactâmico)
- Celulite não purulenta: 5-6 dias
- Infecção intra-abdominal com controle de foco: 4-7 dias
- Bacteriemia por BGN (foco controlado): 7 dias; Bacteriemia por S. aureus: 14 dias mínimo
Switch IV→VO (COMS - todos presentes): melhora clínica sustentada, via oral disponível, marcadores inflamatórios em queda, estabilidade hemodinâmica ≥24h.
Quando sugerir início de ATB no #CONDUTA, inclua duração estimada. Quando sugerir switch ou suspensão, justifique com base nos critérios acima.

VERIFICADOR DE SEGURANÇA DE PRESCRIÇÃO (CONDICIONAL):
Se — e APENAS SE — os 'Novos dados de HOJE' (fornecidos em (3)) incluírem uma prescrição ou lista de medicamentos em uso hospitalar, analise-a silenciosamente e mencione no #CONDUTA QUALQUER um dos seguintes pontos que identificar:
- Medicações que precisam de ajuste por função renal (use a Cr/eGFR disponíveis): ex. enoxaparina em ClCr<30, metformina em ClCr<45, gabapentina em ClCr<60, ATB nefrotóxicos.
- Duplicidade terapêutica na mesma classe (ex. dois IECAs, dois BZD, dois IBPs).
- Interações clinicamente relevantes (ex. AAS+clopidogrel+anticoagulante sem indicação clara, amiodarona+warfarina sem monitoramento).
- Critérios de Beers em idoso (>65a): BZD de ação prolongada, anti-histamínicos de 1ª geração, relaxantes musculares centrais, antipsicóticos sem indicação psiquiátrica clara.
- Polifarmácia (>10 medicamentos ativos) — sugerir revisão formal.
- Profilaxias em falta: TVP farmacológica em paciente de risco (Padua ≥4) sem contraindicação, profilaxia gástrica em paciente com indicação válida (UTI + ventilação mecânica OU coagulopatia, NÃO apenas por uso de corticoide).
Se NÃO houver prescrição nos dados fornecidos, ignore completamente esta seção — NÃO mencione nada sobre segurança de prescrição.

(1) Análise da IA (consultor hospitalista) sobre a evolução anterior:
---
{resumo_ia_fase1}
---

(2) Evolução Anterior Original (FONTE PRIMÁRIA para formato e conteúdo a ser preservado):
---
{evolucao_anterior_original_anon}
---

(3) Novos dados e observações do médico para a evolução de HOJE:
---
{dados_medico_hoje_anon}
---

Gere a nota de EVOLUÇÃO MÉDICA para HOJE, preenchendo o modelo abaixo. Lembre-se: preserve o formato e conteúdo da evolução anterior, atualizando SOMENTE o necessário:
{template_evolucao_final}
"""
    return gerar_resposta_ia(prompt, file_parts=file_parts)


def gerar_passagem_caso_sbar_ia(evolucao_final):
    evolucao_anon = anonimizar_texto(evolucao_final)
    prompt = f"""Você é um médico hospitalista sênior preparando uma passagem de caso para o plantão noturno ou cobertura de fim de semana.

Gere uma passagem de caso estruturada no formato SBAR, em linguagem clínica direta e objetiva. A passagem deve ser CONCISA (máximo 1 página), acionável e focada no que o colega precisa saber para tomar decisões seguras.

Estrutura OBRIGATÓRIA:

**S — Situação**
Uma frase: paciente, idade, D+X de internação, diagnóstico principal, estado atual em uma palavra (estável/instável/piorando/melhorando).

**B — Background**
Bullet points curtos com o essencial: antecedentes relevantes, evolução resumida da internação, resultados-chave de exames/imagens, ATB em uso (com D+X) ou procedimentos realizados.

**A — Avaliação**
- Status hemodinâmico e respiratório atual
- Principais pendências diagnósticas abertas (exames aguardando, interconsultas aguardando retorno)
- Problemas ativos (lista numerada curta)

**R — Recomendação (o que o colega deve fazer)**
- O que monitorar esta noite / neste plantão (sinais vitais específicos, débito urinário, sintomas de alerta)
- Parâmetros de alerta que justificam ligação (ex: "Chamar se FC>120, PAS<90, SpO2<92% em ar ambiente")
- Pendências de exames/interconsultas que podem chegar durante o plantão e o que fazer com eles
- Código de Reanimação / Diretivas antecipadas (se conhecido)
- Medicações SOS prescritas disponíveis

REGRAS:
- NÃO use abreviações clínicas (escreva "Pressão arterial sistólica" e não "PAS" no texto corrido — mas em valores numéricos você pode manter as siglas comuns).
- Mantenha abreviações de exames laboratoriais (Hb, PCR, Cr, etc.).
- Seja direto. O colega que recebe a passagem tem 5-10 minutos para ler. Elimine qualquer palavra que não agregue decisão.
- Se a evolução fornecida não contém informação para uma seção, indique "(não disponível na evolução)".

Evolução atual do paciente:
---
{evolucao_anon}
---

Gere a passagem de caso SBAR:
"""
    return gerar_resposta_ia(prompt)


def preencher_admissao_ia(info_caso_original, file_parts=None):
    info_caso = anonimizar_texto(info_caso_original)
    template_admissao = """# UNIDADE DE INTERNAÇÃO - ADMISSÃO #

#ID:

#HD:

#AP:

#HDA:

#MUC:

#ALERGIAS:

#ATB:

#TEV:

#EXAMES:
>MICROBIOLOGIA:
>IMAGEM:
>LABS:

#AVALIAÇÃO:

#EXAME FÍSICO:

#PLANO TERAPÊUTICO:

#CONDUTA:

#DATA PROVÁVEL DA ALTA: SEM PREVISÃO"""

    prompt = f"""Você é um médico hospitalista sênior em convênio verticalizado. Neste modelo, ofereça APENAS as terapias essenciais baseadas em evidência — nada a mais, nada a menos. Evite overtesting e polifarmácia desde a admissão.

Sua tarefa é preencher o modelo de ADMISSÃO HOSPITALAR com as informações fornecidas sobre o caso. Siga as regras rigorosamente:

REGRAS DE PREENCHIMENTO:
- Se alguma informação específica para um campo não for fornecida no caso, deixe o campo em branco.
- É crucial NÃO inventar (alucinar) informações que não estão presentes no texto fornecido.
- Após cada campo preenchido, adicione uma linha em branco antes do próximo campo.

REGRAS DE ABREVIAÇÕES:
- NÃO use abreviações no texto clínico (HDA, exame físico, conduta). Escreva por extenso (ex: "Murmúrio vesicular" e não "MV"; "Ruídos hidroaéreos" e não "RHA"; "Membros inferiores" e não "MMII").
- EXCEÇÃO: abreviações de exames laboratoriais (Hb, Ht, PCR, TGO, TGP, Na, K, Cr, BNP, etc.) DEVEM ser mantidas como estão.

DEFINIÇÕES IMPORTANTES DOS CAMPOS:
- #MUC (Medicamentos de Uso Contínuo): Refere-se aos medicamentos que o paciente JÁ USAVA em casa antes da internação (uso crônico/domiciliar). NÃO inclua aqui medicações iniciadas durante esta internação.
- #ATB (Antibióticos): Inclua TODOS os antibióticos já usados ou em uso atual durante esta internação, com datas de início (e término, se suspenso).
- #TEV: Profilaxia para tromboembolismo venoso (medicamentosa ou mecânica).
- #CUIDADOS PALIATIVOS: ADICIONE este campo no TOPO da nota (acima de #ID) APENAS se o caso indicar explicitamente que o paciente está em cuidados paliativos. Caso contrário, OMITA completamente este campo — não o escreva.
- #EXAMES > MICROBIOLOGIA: Culturas (urocultura, hemocultura), antígenos (pneumocócico, legionella), PCR viral, etc.
- #PLANO TERAPÊUTICO e #CONDUTA: Proponha APENAS o essencial. Justifique brevemente cada intervenção. Evite rotinas desnecessárias.

BUNDLE DE ADMISSÃO (preencha proativamente #PLANO TERAPÊUTICO e #CONDUTA com base na hipótese diagnóstica):
Quando a HD for identificável a partir do caso, proponha no #PLANO TERAPÊUTICO:
1. Investigação direcionada: exames estritamente necessários para confirmar/refinar a HD (evite painéis amplos). Exemplos:
   - Suspeita de PAC: hemograma, PCR, gasometria se SatO2<94%, radiografia de tórax, hemocultura se sepse/grave, antígenos urinários (pneumococo/legionella) se grave.
   - Suspeita de ITU: urina tipo I, urocultura, hemograma, PCR, creatinina, hemocultura se sepse.
   - Suspeita de sepse: hemograma, PCR, lactato, gasometria, função renal, hemoculturas 2 sítios, cultura do foco suspeito.
   - Síndrome coronariana: ECG seriado, troponina alta sensibilidade seriada, escore GRACE.
2. Estratificação de risco: calcule ou mencione o escore apropriado quando aplicável (CURB-65 para PAC, qSOFA para sepse, GRACE/HEART para SCA, Wells para TEP, Padua para profilaxia de TEV, CHA2DS2-VASc para FA).
3. Profilaxias indicadas: TEV (calcule Padua — ≥4 indica profilaxia farmacológica, se sem contraindicação), profilaxia gástrica APENAS se houver indicação formal (UTI com ventilação mecânica OU coagulopatia OU sangramento digestivo prévio — NÃO apenas por corticoide ou estresse).

DIRETRIZES DE STEWARDSHIP DE ANTIBIÓTICO (aplicar ao sugerir início de ATB na admissão):
Baseado em IDSA/SBI/Sanford. Ao propor ATB empírico, SEMPRE inclua duração estimada e critérios de descalonamento:
- PAC não grave (CURB-65<2): amoxicilina-clavulanato ou ceftriaxona + macrolídeo se grave; duração 5 dias se afebril em 48h.
- PAC grave: ceftriaxona + macrolídeo (ou fluoroquinolona respiratória); 7 dias.
- ITU complicada/pielonefrite: ceftriaxona ou fluoroquinolona; 7 dias (FQ) ou 10-14 dias (betalactâmico).
- Celulite não purulenta: cefazolina/cefalexina; 5-6 dias.
- Infecção intra-abdominal com controle de foco: 4-7 dias após controle.
- Sepse sem foco definido: ampla cobertura (piperacilina-tazobactam ou cefepime, ± vancomicina); ajustar em 48-72h com culturas.
Nunca iniciar ATB sem: (1) coleta prévia de culturas sempre que possível, (2) diagnóstico presuntivo claro, (3) duração estimada, (4) plano de reavaliação em 48-72h.

Informações do caso:
---
{info_caso}
---

Preencha o modelo abaixo:
{template_admissao}
"""
    return gerar_resposta_ia(prompt, file_parts=file_parts)

def gerar_resumo_alta_ia(ultima_evolucao_original, file_parts=None):
    ultima_evolucao = anonimizar_texto(ultima_evolucao_original)
    prompt = f"""Você é um médico hospitalista experiente. Suas orientações sempre são guiadas por evidência científica e, em casos em que há evidência fraca, você levanta e discute quais são as condutas possíveis. Para orientações de alta, você utiliza uma linguagem clara e direta e evita jargão médico.

Com base na última evolução do paciente fornecida abaixo, redija um resumo de alta hospitalar conciso e claro, estruturado em dois ou três parágrafos.
O resumo deve incluir:
1. Diagnóstico(s) principal(is) da internação.
2. Breve resumo de como o(s) diagnóstico(s) foi(ram) estabelecido(s) (exames chave, achados).
3. Principais tratamentos realizados durante a internação.
4. Condições do paciente no momento da alta hospitalar.
Adicione uma linha em branco entre cada parágrafo.
Não utilizar tags de formatação, como "**" para negrito.

Última Evolução:
---
{ultima_evolucao}
---
Resumo de Alta (em 2 ou 3 parágrafos):
"""
    return gerar_resposta_ia(prompt, file_parts=file_parts)

def gerar_orientacoes_alta_ia(caso_paciente_original, file_parts=None):
    caso_paciente = anonimizar_texto(caso_paciente_original)
    prompt = f"""Você é um médico hospitalista experiente, e suas orientações sempre são guiadas por evidência científica. Em casos em que há evidência fraca, você levanta e discute quais são as condutas possíveis.
Para orientações de alta, você utiliza uma linguagem clara e direta e evita jargão médico.

Com base no caso do paciente descrito abaixo (diagnóstico e antecedentes), gere orientações de alta pertinentes sobre sinais e sintomas de alerta que indicariam a necessidade de retornar ao Pronto-Socorro.
Apresente as orientações em formato de lista, com cada item iniciando com um hífen. Adicione uma linha em branco entre cada item da lista.

Caso do Paciente:
---
{caso_paciente}
---
Orientações de Alta (Sinais de Alerta para Retorno ao PS):
"""
    return gerar_resposta_ia(prompt, file_parts=file_parts)



# --- Função Principal de Análise de Exames (parse_lab_report) ---
def parse_lab_report(text):
    is_tecnolab = "tecnolab.com.br" in text.lower()
    
    subs = [(r"Creatinina(?!\s*Kinase|\s*quinase)", "Creatinina ")]
    for p, r in subs: text = re.sub(f"(?i){p}", r, text)
    text = re.sub(r"(?i)ur[eé]ia", "Ureia", text)
    text = re.sub(r"(?i)pot[aá]ssio", "Potássio", text)
    text = re.sub(r"(?i)s[oó]dio", "Sódio", text)
    text = re.sub(r"(?i)c[aá]lcio i[oô]nico", "Cálcio Iônico", text)
    text = re.sub(r"(?i)magn[eé]sio", "Magnésio", text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    all_res = {"datetime": extract_datetime_info(lines, is_tecnolab)}
    for ext_func in [extract_hemograma_completo, extract_coagulograma, extract_funcao_renal_e_eletrólitos,
                     extract_marcadores_inflamatorios_cardiacos, extract_hepatograma_pancreas,
                     extract_medicamentos, extract_gasometria, extract_sorologias, extract_urina_tipo_i]:
        all_res.update(ext_func(lines, is_tecnolab))

    all_res["culturas_list"] = extract_culturas(lines, is_tecnolab)

    out_sections = {s: [] for s in ["HEADER", "HEMOGRAMA", "COAGULOGRAMA", "FUNCAO_RENAL_ELETRÓLITOS_GLI",
                                     "MARCADORES_INFLAM_CARD", "HEPATOGRAMA_PANCREAS", "MEDICAMENTOS", "GASOMETRIA",
                                     "URINA_I", "SOROLOGIAS", "CULTURAS", "OUTROS"]}

    if all_res.get("datetime"): out_sections["HEADER"].append(all_res["datetime"])

    for k, lbl in [("Hb","Hb"),("Ht","Ht"),("VCM","VCM"),("HCM","HCM"),("CHCM","CHCM"),("RDW","RDW")]:
        if all_res.get(k): out_sections["HEMOGRAMA"].append(format_value_with_alert(lbl, all_res[k], k))
    
    l_str = format_value_with_alert("Leuco", all_res.get("Leuco",""), "Leuco", unit_suffix=all_res.get("Leuco_unit", ""))
    if l_str:
        diff_str = all_res.get("Leuco_Diff", "")
        if "Neut" in diff_str or "Linf" in diff_str:
            l_str += f" {diff_str}"
        out_sections["HEMOGRAMA"].append(l_str)
    
    p_str = format_value_with_alert("Plaq", all_res.get("Plaq", ""), "Plaq", unit_suffix=all_res.get("Plaq_unit", ""))
    if p_str:
        out_sections["HEMOGRAMA"].append(p_str)

    tp_raw, inr_raw = all_res.get("TP_s",""), all_res.get("INR","")
    tp_fmt = format_value_with_alert("TP", tp_raw, "TP_s").replace("TP ","") if tp_raw else ""
    inr_fmt = format_value_with_alert("INR", inr_raw, "INR").replace("INR ","") if inr_raw else ""
    coag_p = []
    if tp_fmt:
        tp_inr_s = f"TP {tp_fmt}"
        if inr_fmt: tp_inr_s += f" (INR {inr_fmt})"
        coag_p.append(tp_inr_s)
    ttpa_s_raw, ttpa_r_raw = all_res.get("TTPA_s",""), all_res.get("TTPA_R","")
    ttpa_s_fmt = format_value_with_alert("TTPA", ttpa_s_raw, "TTPA_s").replace("TTPA ","") if ttpa_s_raw else ""
    ttpa_r_fmt = format_value_with_alert("R", ttpa_r_raw, "TTPA_R").replace("R ","") if ttpa_r_raw else ""
    if ttpa_s_fmt:
        ttpa_s = f"TTPA {ttpa_s_fmt}"
        if ttpa_r_fmt: ttpa_s += f" (R {ttpa_r_fmt})"
        coag_p.append(ttpa_s)
    if coag_p: out_sections["COAGULOGRAMA"].append(" ; ".join(coag_p))

    if all_res.get("U"): out_sections["FUNCAO_RENAL_ELETRÓLITOS_GLI"].append(format_value_with_alert("U", all_res["U"], "U"))
    cr_raw, egfr_raw = all_res.get("Cr",""), all_res.get("eGFR","")
    cr_fmt = format_value_with_alert("Cr", cr_raw, "Cr").replace("Cr ", "") if cr_raw else ""
    egfr_fmt = format_value_with_alert("eGFR", egfr_raw, "eGFR").replace("eGFR ", "") if egfr_raw else ""
    cr_egfr_s = f"Cr {cr_fmt}" if cr_fmt else ""
    if egfr_fmt:
        cr_egfr_s = (cr_egfr_s + f" ({egfr_fmt})") if cr_egfr_s else egfr_fmt

    if cr_egfr_s: out_sections["FUNCAO_RENAL_ELETRÓLITOS_GLI"].append(cr_egfr_s)

    for k, lbl in [("Na","Na"),("K","K"),("Cl","Cl"),("Mg","Mg"),("CaI","CaI"), ("CaT","CaT"), ("P","P"),("Gli","Gli")]:
        if all_res.get(k): out_sections["FUNCAO_RENAL_ELETRÓLITOS_GLI"].append(format_value_with_alert(lbl, all_res[k], k))
    try:
        na,cl = convert_to_float(clean_number_format(all_res.get("Na",""))), convert_to_float(clean_number_format(all_res.get("Cl","")))
        hco3_s = next((all_res.get(k) for k in [f"{p}HCO3_gas" for p in ["GA_","GV_",""]] if all_res.get(k)), None)
        hco3 = convert_to_float(clean_number_format(hco3_s if hco3_s else ""))
        if na and cl and hco3: out_sections["FUNCAO_RENAL_ELETRÓLITOS_GLI"].append(f"AGap {(na-(cl+hco3)):.1f}")
    except: pass

    for k, lbl in [("PCR","PCR"),("Lac","Lactato"),("Trop","TnT-hs"),("DD","D-Dímero"), ("NT-proBNP", "NT-proBNP")]:
         if all_res.get(k): out_sections["MARCADORES_INFLAM_CARD"].append(format_value_with_alert(lbl, all_res[k], k))
    
    if all_res.get("Vanco"): out_sections["MEDICAMENTOS"].append(format_value_with_alert("Vanco", all_res["Vanco"], "Vanco"))

    for k, lbl in [("TGO","TGO"),("TGP","TGP"),("GGT","GGT"),("FA","FA")]:
        if all_res.get(k): out_sections["HEPATOGRAMA_PANCREAS"].append(format_value_with_alert(lbl, all_res[k], k))
    bili_p = [format_value_with_alert(lbl,all_res[k],k) for k,lbl in [("BT","BT"),("BD","BD"),("BI","BI")] if all_res.get(k)]
    if bili_p: out_sections["HEPATOGRAMA_PANCREAS"].append(" ".join(bili_p))
    for k, lbl in [("ALB","ALB"),("AML","AML"),("LIP","LIP")]:
        if all_res.get(k): out_sections["HEPATOGRAMA_PANCREAS"].append(format_value_with_alert(lbl, all_res[k], k))

    gas_pfx = ""
    if any(k.startswith("GA_") for k in all_res.keys()): gas_pfx = "GA_"
    elif any(k.startswith("GV_") for k in all_res.keys()): gas_pfx = "GV_"
    
    gas_params_output = []
    if gas_pfx or any("_gas" in k and all_res[k] for k in all_res.keys()):
        gas_order_map = {"pH": "pH_gas", "pCO2": "pCO2_gas", "pO2": "pO2_gas", "HCO3": "HCO3_gas", "BE": "BE_gas", "SatO2": "SatO2_gas", "Lac": "Lac_gas", "cCO2": "cCO2_gas"}
        for display_label, dict_key_suffix in gas_order_map.items():
            full_key_to_check = (gas_pfx + dict_key_suffix) if gas_pfx else dict_key_suffix
            if full_key_to_check in all_res and all_res[full_key_to_check]:
                gas_params_output.append(format_value_with_alert(display_label, all_res[full_key_to_check], dict_key_suffix))

    if gas_params_output:
        gas_header = "Gasometria Arterial: " if gas_pfx == "GA_" else "Gasometria Venosa: " if gas_pfx == "GV_" else "Gasometria: "
        out_sections["GASOMETRIA"].append(gas_header + "; ".join(gas_params_output))

    u1_parts = []
    for k, lbl in [("U1_pH", "U1_pH"),("U1_dens", "U1_dens"), ("U1_prot", "U1_prot"), ("U1_glic", "U1_glic"),
                   ("U1_nit", "U1_nit"), ("U1_CC", "U1_CC"), ("U1_hem", "U1_hem"), ("U1_leuco", "U1_leuco")]:
        if all_res.get(k):
             u1_parts.append(f"{lbl} {all_res[k]}")
    if u1_parts:
        out_sections["URINA_I"].append(" ; ".join(u1_parts))

    soro_map = {"HIV":"Anti HIV 1/2","HAV_IgM":"Anti-HAV IgM","HBsAg":"HBsAg","AntiHBs":"Anti-HBs",
                "AntiHBc_Total":"Anti-HBc Total","HCV":"Anti-HCV","VDRL":"VDRL"}
    for k, lbl in soro_map.items():
        if all_res.get(k): out_sections["SOROLOGIAS"].append(f"{lbl} {all_res[k]}")

    if all_res.get("culturas_list"):
        for cult_info in all_res["culturas_list"]:
            c_str = f"{cult_info.get('Tipo','')} {cult_info.get('Resultado','')}"
            abg = cult_info.get("Antibiograma",{})
            abg_p = [f"{s[0]}: {', '.join(abg[s[0]])}" for s in ["S","I","R"] if abg.get(s[0])]
            if abg_p: c_str += " / "+" | ".join(abg_p)
            out_sections["CULTURAS"].append(c_str.strip())

    section_order = ["HEADER","HEMOGRAMA","COAGULOGRAMA","FUNCAO_RENAL_ELETRÓLITOS_GLI",
                     "MARCADORES_INFLAM_CARD", "MEDICAMENTOS", "HEPATOGRAMA_PANCREAS",
                     "GASOMETRIA","URINA_I","SOROLOGIAS","CULTURAS","OUTROS"]
    final_out = [" ; ".join(out_sections[s_k]) for s_k in section_order if out_sections[s_k]]
    return " ; ".join(filter(None, final_out)) + (";" if any(final_out) else "")


# ============================================================
# CHANGE 3: Color-coded HTML output function
# ============================================================
def colorize_output_html(plain_text):
    """Convert plain text output to color-coded HTML for display."""
    if not plain_text:
        return '<span style="color: #999; font-style: italic;">Aguardando análise...</span>'
    
    import html as html_module
    safe = html_module.escape(plain_text)
    
    # Highlight critical values (!)
    safe = re.sub(
        r'(\S+\s+\S+)\s+\(!?\)',
        r'<span class="cd-val-crit">\1 (!)</span>',
        safe
    )
    # More precise: find "value (!)" pattern
    safe = re.sub(
        r'([A-Za-z0-9.]+\s+[0-9.,]+(?:\s*mil)?)\s*\(\!\)',
        r'<span class="cd-val-crit">\1 (!)</span>',
        safe
    )
    
    # Highlight altered values *
    safe = re.sub(
        r'([A-Za-z0-9.]+\s+[0-9.,]+(?:\s*mil)?)\s*\*',
        r'<span class="cd-val-alert">\1 *</span>',
        safe
    )
    
    # Highlight datetime at the beginning
    safe = re.sub(
        r'^(\d{2}/\d{2}\s+\d{2}h\d{2})',
        r'<span class="cd-datetime">\1</span>',
        safe
    )
    
    return safe


# ============================================================
# CHANGE 6: Step indicator helper for AI workflow
# ============================================================
def render_step_indicator(current_step, steps_info):
    """Render a step indicator bar. steps_info = [(num, label), ...]"""
    html_parts = ['<div class="cd-steps">']
    for i, (num, label) in enumerate(steps_info):
        if num < current_step:
            state = "done"
        elif num == current_step:
            state = "active"
        else:
            state = "pending"
        
        html_parts.append(f'<div class="cd-step"><div class="cd-step-num {state}">{num}</div>')
        html_parts.append(f'<span class="cd-step-label {state}">{label}</span></div>')
        
        if i < len(steps_info) - 1:
            line_state = "done" if num < current_step else "pending"
            html_parts.append(f'<div class="cd-step-line {line_state}"></div>')
    
    html_parts.append('</div>')
    return "".join(html_parts)


def make_copy_button_html(element_id, text_content, label="Copiar", style="filled"):
    """Generate a styled copy button HTML component."""
    safe_content = text_content.replace("'", "&apos;").replace('"', "&quot;")
    btn_class = "cd-copy-btn" if style == "filled" else "cd-copy-btn-outline"
    return f"""<textarea id="{element_id}" style="opacity:0;position:absolute;left:-9999px;top:-9999px;">{safe_content}</textarea>
    <button class="{btn_class}" onclick="var t=document.getElementById('{element_id}');t.select();t.setSelectionRange(0,99999);try{{var s=document.execCommand('copy');var m=document.createElement('div');m.textContent=s?'Copiado!':'Falha ao copiar.';m.style.cssText='position:fixed;bottom:20px;left:50%;transform:translateX(-50%);padding:10px 24px;background-color:'+(s?'#0F6E56':'#A32D2D')+';color:white;border-radius:8px;z-index:1000;font-size:14px;font-weight:500;box-shadow:0 4px 12px rgba(0,0,0,0.15);';document.body.appendChild(m);setTimeout(function(){{document.body.removeChild(m);}},2000);}}catch(e){{alert('Não foi possível copiar.');}}">📋 {label}</button>"""


def render_file_uploader(key_suffix, help_text="Anexe imagens ou PDFs com exames, evoluções, etc."):
    """Render a file uploader + paste button and return (uploaded_files, file_parts, file_descriptions)."""
    
    # Session state key for accumulating pasted images
    paste_state_key = f"pasted_imgs_{key_suffix}"
    if paste_state_key not in st.session_state:
        st.session_state[paste_state_key] = []  # list of (hash, PIL.Image) tuples
    
    # Layout: uploader on left (wider), paste button on right
    col_upload, col_paste = st.columns([3, 1])
    
    with col_upload:
        uploaded_files = st.file_uploader(
            "Anexar arquivos (opcional)",
            type=["png", "jpg", "jpeg", "gif", "webp", "bmp", "pdf", "txt"],
            accept_multiple_files=True,
            key=f"file_upload_{key_suffix}",
            help=help_text,
            label_visibility="collapsed"
        )
    
    with col_paste:
        paste_result = pbutton(
            label="📋 Colar",
            text_color="#ffffff",
            background_color="#0F6E56",
            hover_background_color="#085041",
            key=f"paste_btn_{key_suffix}",
            errors="ignore"
        )
        
        # If user just pasted something, add to accumulator (deduped by content hash)
        if paste_result and paste_result.image_data is not None:
            try:
                img_bytes_io = io.BytesIO()
                paste_result.image_data.save(img_bytes_io, format='PNG')
                img_bytes = img_bytes_io.getvalue()
                img_hash = hashlib.md5(img_bytes).hexdigest()
                
                existing_hashes = [h for h, _ in st.session_state[paste_state_key]]
                if img_hash not in existing_hashes:
                    # Convert RGBA to RGB if needed
                    img = paste_result.image_data
                    if img.mode == 'RGBA':
                        img = img.convert('RGB')
                    st.session_state[paste_state_key].append((img_hash, img))
                    st.rerun()
            except Exception:
                pass
    
    # Process uploaded files
    file_parts = []
    file_descriptions = []
    if uploaded_files:
        file_parts, file_descriptions = process_uploaded_files_for_gemini(uploaded_files)
    
    # Add pasted images to file_parts
    pasted_imgs = st.session_state[paste_state_key]
    for idx, (_, img) in enumerate(pasted_imgs, start=1):
        file_parts.append(img)
        file_descriptions.append(f"Colada: Imagem colada {idx}")
    
    # Render chips for all attachments
    if file_descriptions:
        chips_html = '<div class="cd-file-chips">'
        for desc in file_descriptions:
            if desc.startswith("Imagem:"):
                chips_html += f'<span class="cd-file-chip image">🖼 {desc.replace("Imagem: ", "")}</span>'
            elif desc.startswith("PDF:"):
                chips_html += f'<span class="cd-file-chip pdf">📄 {desc.replace("PDF: ", "")}</span>'
            elif desc.startswith("Texto:"):
                chips_html += f'<span class="cd-file-chip text">📝 {desc.replace("Texto: ", "")}</span>'
            elif desc.startswith("Colada:"):
                chips_html += f'<span class="cd-file-chip image">📋 {desc.replace("Colada: ", "")}</span>'
            else:
                chips_html += f'<span class="cd-file-chip text">⚠ {desc}</span>'
        chips_html += '</div>'
        st.markdown(chips_html, unsafe_allow_html=True)
        
        # Clear button for pasted images (only if there are any)
        if pasted_imgs:
            if st.button(f"✕ Limpar {len(pasted_imgs)} imagem(ns) colada(s)",
                         key=f"clear_pasted_{key_suffix}",
                         help="Remove as imagens coladas via clipboard"):
                st.session_state[paste_state_key] = []
                st.rerun()
    
    return uploaded_files, file_parts, file_descriptions


# ============================================================
# INTERFACE STREAMLIT — REDESIGNED
# ============================================================

# --- CHANGE 5: Branded Header ---
st.markdown("""
<div style="display: flex; align-items: center; gap: 14px; margin-bottom: 4px;">
    <div style="width: 44px; height: 44px; border-radius: 10px; background: linear-gradient(135deg, #0F6E56, #1D9E75); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 3h6l2 4H7l2-4z"/>
            <path d="M7 7v10a2 2 0 002 2h6a2 2 0 002-2V7"/>
            <line x1="12" y1="11" x2="12" y2="15"/>
            <line x1="10" y1="13" x2="14" y2="13"/>
        </svg>
    </div>
    <div>
        <h1 style="margin: 0; font-size: 1.8rem; font-weight: 700; letter-spacing: -0.5px; color: inherit;">ClipDoc</h1>
        <p style="margin: 0; font-size: 0.85rem; color: #6b7280; font-weight: 400;">Formatação inteligente de exames laboratoriais para prontuários</p>
    </div>
</div>
<div style="height: 1px; background: linear-gradient(to right, #0F6E56, transparent); margin: 12px 0 24px 0; opacity: 0.3;"></div>
""", unsafe_allow_html=True)


if not GOOGLE_API_KEY and api_key_source != "secrets":
    st.warning("Chave da API do Google não configurada. Funcionalidades de IA estarão desabilitadas.")
elif GOOGLE_API_KEY and not gemini_available and 'gemini_config_error' in st.session_state:
     st.error(st.session_state.gemini_config_error)

# --- Session State Initialization ---
for key, default in [
    ("ia_output_evolucao_enf_fase1", ""),
    ("evolucao_anterior_original_para_fase2", ""),
    ("ia_output_admissao", ""),
    ("ia_fase_evolucao_interativa", 1),
    ("ia_dados_medico_hoje", ""),
    ("ia_output_evolucao_final", ""),
    ("ia_output_sbar", ""),
    ("ia_output_resumo_alta", ""),
    ("ia_output_orientacoes_alta", ""),
    ("input_text_area_content_tab1", ""),
    ("saida_exames", ""),
    ("show_about_tab1", False),
    ("show_compatible_exams_detailed_tab1", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


tab1, tab2 = st.tabs(["🧪  Extrair Exames", "🧑‍⚕️  Agente IA Hospitalista"])

# ============================================================
# TAB 1 — EXAM EXTRACTION (Redesigned)
# ============================================================
with tab1:
    col1_tab1, col2_tab1 = st.columns(2, gap="large")
    
    with col1_tab1:
        st.markdown('<p class="cd-section-label">Colar texto do exame</p>', unsafe_allow_html=True)
        st.session_state.input_text_area_content_tab1 = st.text_area(
            "Cole o texto do exame aqui:",
            value=st.session_state.input_text_area_content_tab1,
            key="entrada_widget_tab1",
            height=320,
            label_visibility="collapsed",
            placeholder="Cole aqui o texto copiado do sistema de exames laboratoriais..."
        )
        
        # CHANGE 4: Streamlined to 2 main buttons
        btn_col1, btn_col2 = st.columns([3, 1])
        with btn_col1:
            if st.button("🔍  Analisar Exame", use_container_width=True, type="primary", key="btn_analisar_exame_tab1"):
                current_input_tab1 = st.session_state.entrada_widget_tab1
                if current_input_tab1:
                    with st.spinner("Analisando..."):
                        texto_anonimizado_exames = anonimizar_texto(current_input_tab1)
                        resultado_processado = parse_lab_report(texto_anonimizado_exames)
                        st.session_state["saida_exames"] = resultado_processado
                    st.session_state.input_text_area_content_tab1 = ""
                    st.rerun()
                else:
                    st.error("Insira o texto do exame para analisar.")
        with btn_col2:
            if st.button("Limpar", use_container_width=True, key="btn_limpar_tab1"):
                st.session_state["saida_exames"] = ""
                st.session_state.input_text_area_content_tab1 = ""
                st.rerun()
    
    with col2_tab1:
        st.markdown('<p class="cd-section-label">Resultado formatado</p>', unsafe_allow_html=True)
        
        # CHANGE 3: Color-coded HTML output
        output_text = st.session_state.get("saida_exames", "")
        colorized_html = colorize_output_html(output_text)
        st.markdown(
            f'<div class="cd-output-box">{colorized_html}</div>',
            unsafe_allow_html=True
        )
        
        if output_text:
            # Plain text copy button (copies raw text for EMR pasting)
            components.html(make_copy_button_html("cClipExames", output_text, "Copiar para prontuário"), height=55)
        
        # Legend for markers
        if output_text:
            st.markdown("""
            <div style="display: flex; gap: 16px; margin-top: 8px; font-size: 0.75rem;">
                <span><span class="cd-val-alert" style="font-size: 0.7rem;">K 5.8 *</span> = valor alterado</span>
                <span><span class="cd-val-crit" style="font-size: 0.7rem;">Na 118 (!)</span> = valor crítico</span>
            </div>
            """, unsafe_allow_html=True)

    # CHANGE 4: Info sections moved to expanders
    with st.expander("ℹ️  Sobre o ClipDoc"):
        st.markdown("""
        **Autor do Código Original:** Charles Ribas  
        Medicina (2016–2021) — Universidade de São Paulo  
        Letras / Tradução (2009–2012) — Universidade Nova de Lisboa

        **Aprimoramentos e Refatoração:** Modelo de IA Gemini  
        **Objetivo:** Facilitar a extração e formatação de dados de exames laboratoriais para agilizar o trabalho de profissionais de saúde.
        """)
    
    with st.expander("📋  Exames compatíveis"):
        st.markdown("""
        **Hemograma:** Hb, Ht, VCM, HCM, CHCM, RDW, Leucócitos (diferencial: Bastonetes, Segmentados, Linfócitos, Eosinófilos), Plaquetas.  
        **Coagulograma:** TP (segundos), INR, TTPA (segundos e Relação).  
        **Função Renal e Eletrólitos:** Ureia, Creatinina (eGFR), Na, K, Cl, Mg, CaI, CaT, P.  
        **Glicemia.**  
        **Marcadores Inflamatórios/Cardíacos:** PCR, Lactato, Troponina, D-Dímero, NT-proBNP.  
        **Hepatograma/Pâncreas:** TGO, TGP, GGT, FA, Bilirrubinas (BT, BD, BI), Albumina, Amilase, Lipase.  
        **Medicamentos:** Vancomicina.  
        **Gasometria:** Arterial e Venosa (pH, pCO2, pO2, HCO3, BE, SatO2, cCO2, Lactato).  
        **Urina Tipo I:** Nitrito, Leucócitos, Hemácias, pH, Densidade, Proteínas, Glicose, Cetonas.  
        **Sorologias:** HIV, HAV IgM, HBsAg, Anti-HBs, Anti-HBc Total, Anti-HCV, VDRL.  
        **Culturas:** Urocultura e Hemocultura (com antibiograma).
        """)

# ============================================================
# TAB 2 — AI AGENT (Redesigned with step indicators + cards)
# ============================================================
with tab2:
    if not gemini_available:
        st.error("O Agente IA está indisponível. Verifique a configuração da chave API.")
    else:
        ia_task_options = [
            "Selecione uma tarefa...",
            "Evoluir Paciente (Enfermaria - Interativo)",
            "Auxiliar na Admissão de Paciente",
            "Redigir Resumo de Alta",
            "Gerar Orientações de Alta"
        ]
        tarefa_ia_selecionada = st.selectbox(
            "Qual tarefa o Agente IA deve realizar?",
            ia_task_options,
            key="ia_task_selector_tab2"
        )

        # --- Evoluir Paciente (Interativo) ---
        if tarefa_ia_selecionada == "Evoluir Paciente (Enfermaria - Interativo)":
            
            # CHANGE 6: Step indicator
            current_fase = st.session_state.ia_fase_evolucao_interativa
            st.markdown(render_step_indicator(current_fase, [
                (1, "Evolução anterior"),
                (2, "Achados de hoje"),
                (3, "Evolução final")
            ]), unsafe_allow_html=True)
            
            if 'evolucao_anterior_input_fase1' not in st.session_state:
                st.session_state.evolucao_anterior_input_fase1 = ""

            if current_fase == 1:
                st.markdown('<p class="cd-section-label">Passo 1 — Cole a evolução do dia anterior</p>', unsafe_allow_html=True)
                st.session_state.evolucao_anterior_input_fase1 = st.text_area(
                    "Cole a evolução do dia anterior aqui:",
                    value=st.session_state.evolucao_anterior_input_fase1,
                    height=250,
                    key="ia_evol_enf_input_fase1_widget",
                    label_visibility="collapsed",
                    placeholder="Cole aqui a evolução completa do dia anterior..."
                )
                st.markdown('<p class="cd-file-upload-label">📎 Anexar arquivos ou colar do clipboard (Ctrl+V após Win+Shift+S) — opcional</p>', unsafe_allow_html=True)
                _, file_parts_fase1, _ = render_file_uploader("evol_fase1")
                
                if st.button("Analisar Evolução Anterior →", key="btn_ia_evol_enf_fase1", type="primary"):
                    if st.session_state.evolucao_anterior_input_fase1 or file_parts_fase1:
                        with st.spinner("IA analisando a evolução anterior..."):
                            st.session_state.evolucao_anterior_original_para_fase2 = st.session_state.evolucao_anterior_input_fase1
                            st.session_state.ia_output_evolucao_enf_fase1 = evoluir_paciente_enfermaria_ia_fase1(
                                st.session_state.evolucao_anterior_input_fase1,
                                file_parts=file_parts_fase1 if file_parts_fase1 else None
                            )
                        st.session_state.ia_fase_evolucao_interativa = 2
                        st.rerun()
                    else:
                        st.warning("Cole a evolução anterior ou anexe arquivos para continuar.")

            if current_fase == 2:
                if st.session_state.ia_output_evolucao_enf_fase1:
                    with st.expander("📝 Análise da IA (evolução anterior)", expanded=True):
                        st.markdown(st.session_state.ia_output_evolucao_enf_fase1)

                st.markdown('<p class="cd-section-label">Passo 2 — Adicione seus achados de hoje</p>', unsafe_allow_html=True)
                st.session_state.ia_dados_medico_hoje = st.text_area(
                    "Achados de hoje:",
                    value=st.session_state.ia_dados_medico_hoje,
                    height=250,
                    key="ia_dados_medico_input_fase2_widget",
                    label_visibility="collapsed",
                    placeholder="Anamnese, exame físico, novos exames, intercorrências..."
                )
                st.markdown('<p class="cd-file-upload-label">📎 Anexar arquivos ou colar do clipboard (Ctrl+V após Win+Shift+S) — opcional</p>', unsafe_allow_html=True)
                _, file_parts_fase2, _ = render_file_uploader("evol_fase2")

                col_btn1, col_btn2 = st.columns([3, 1])
                with col_btn1:
                    if st.button("Gerar Evolução Final →", key="btn_ia_evol_enf_fase2", type="primary"):
                        if st.session_state.ia_dados_medico_hoje or file_parts_fase2:
                            with st.spinner("IA gerando a evolução final..."):
                                st.session_state.ia_output_evolucao_final = evoluir_paciente_enfermaria_ia_fase2(
                                    st.session_state.ia_output_evolucao_enf_fase1,
                                    st.session_state.ia_dados_medico_hoje,
                                    st.session_state.evolucao_anterior_original_para_fase2,
                                    file_parts=file_parts_fase2 if file_parts_fase2 else None
                                )
                            st.session_state.ia_fase_evolucao_interativa = 3
                            st.rerun()
                        else:
                            st.warning("Adicione seus achados de hoje.")
                with col_btn2:
                    if st.button("← Voltar", key="btn_reset_evol_interativa"):
                        st.session_state.ia_fase_evolucao_interativa = 1
                        st.session_state.evolucao_anterior_input_fase1 = ""
                        st.session_state.ia_output_evolucao_enf_fase1 = ""
                        st.session_state.ia_dados_medico_hoje = ""
                        st.session_state.ia_output_evolucao_final = ""
                        st.session_state.evolucao_anterior_original_para_fase2 = ""
                        st.session_state.ia_output_sbar = ""
                        st.rerun()

            if current_fase == 3:
                with st.expander("📝 Análise da IA (evolução anterior)"):
                    st.markdown(st.session_state.ia_output_evolucao_enf_fase1)
                with st.expander("🩺 Seus achados de hoje"):
                    st.markdown(st.session_state.ia_dados_medico_hoje)
                
                if st.session_state.ia_output_evolucao_final:
                    st.markdown('<p class="cd-section-label">Evolução médica final</p>', unsafe_allow_html=True)
                    st.text_area(
                        "Evolução:",
                        value=st.session_state.ia_output_evolucao_final,
                        height=400,
                        key="ia_evolucao_final_display",
                        disabled=True,
                        label_visibility="collapsed"
                    )
                    components.html(make_copy_button_html("cClipEvolFinal", st.session_state.ia_output_evolucao_final, "Copiar evolução final"), height=55)
                    
                    st.markdown("---")
                    st.markdown('<p class="cd-section-label">📋 Passagem de caso (SBAR) — opcional</p>', unsafe_allow_html=True)
                    st.caption("Gera uma passagem estruturada para o plantão noturno ou cobertura de fim de semana.")
                    
                    col_sbar1, col_sbar2 = st.columns([3, 1])
                    with col_sbar1:
                        if st.button("Gerar Passagem de Caso (SBAR)", key="btn_gerar_sbar", type="primary"):
                            with st.spinner("IA gerando a passagem SBAR..."):
                                st.session_state.ia_output_sbar = gerar_passagem_caso_sbar_ia(
                                    st.session_state.ia_output_evolucao_final
                                )
                            st.rerun()
                    with col_sbar2:
                        if st.session_state.get("ia_output_sbar"):
                            if st.button("Limpar SBAR", key="btn_limpar_sbar"):
                                st.session_state.ia_output_sbar = ""
                                st.rerun()
                    
                    if st.session_state.get("ia_output_sbar"):
                        st.markdown(st.session_state.ia_output_sbar)
                        components.html(make_copy_button_html("cClipSBAR", st.session_state.ia_output_sbar, "Copiar passagem SBAR"), height=55)
                
                st.markdown("---")
                if st.button("Iniciar nova evolução", key="btn_nova_evol_interativa"):
                    st.session_state.ia_fase_evolucao_interativa = 1
                    st.session_state.evolucao_anterior_input_fase1 = ""
                    st.session_state.ia_output_evolucao_enf_fase1 = ""
                    st.session_state.ia_dados_medico_hoje = ""
                    st.session_state.ia_output_evolucao_final = ""
                    st.session_state.evolucao_anterior_original_para_fase2 = ""
                    st.session_state.ia_output_sbar = ""
                    st.rerun()

        # --- Auxiliar na Admissão ---
        elif tarefa_ia_selecionada == "Auxiliar na Admissão de Paciente":
            st.markdown('<p class="cd-section-label">Informações do caso para admissão</p>', unsafe_allow_html=True)
            if 'ia_input_admissao_caso' not in st.session_state:
                st.session_state.ia_input_admissao_caso = ""
            st.session_state.ia_input_admissao_caso = st.text_area(
                "Informações do caso:",
                value=st.session_state.ia_input_admissao_caso,
                height=300,
                key="ia_adm_info_input_widget",
                label_visibility="collapsed",
                placeholder="Forneça as informações do caso para admissão..."
            )
            st.markdown('<p class="cd-file-upload-label">📎 Anexar arquivos ou colar do clipboard (Ctrl+V após Win+Shift+S) — opcional</p>', unsafe_allow_html=True)
            _, file_parts_adm, _ = render_file_uploader("admissao")
            
            if st.button("Gerar Admissão com IA", key="btn_ia_adm_tab2", type="primary"):
                if st.session_state.ia_input_admissao_caso or file_parts_adm:
                    with st.spinner("IA gerando o rascunho da admissão..."):
                        st.session_state.ia_output_admissao = preencher_admissao_ia(
                            st.session_state.ia_input_admissao_caso,
                            file_parts=file_parts_adm if file_parts_adm else None
                        )
                else:
                    st.warning("Forneça as informações do caso.")
            if st.session_state.ia_output_admissao:
                st.markdown("---")
                st.markdown('<p class="cd-section-label">Rascunho da admissão</p>', unsafe_allow_html=True)
                st.text_area("Modelo:", value=st.session_state.ia_output_admissao, height=400, key="ia_admissao_output_display_tab2", disabled=True, label_visibility="collapsed")
                components.html(make_copy_button_html("cClipAdmissao", st.session_state.ia_output_admissao, "Copiar admissão"), height=55)
                if st.button("Limpar rascunho", key="btn_clear_ia_adm_tab2"):
                    st.session_state.ia_output_admissao = ""
                    st.session_state.ia_input_admissao_caso = ""
                    st.rerun()

        # --- Resumo de Alta ---
        elif tarefa_ia_selecionada == "Redigir Resumo de Alta":
            st.markdown('<p class="cd-section-label">Última evolução do paciente</p>', unsafe_allow_html=True)
            if 'ia_input_ultima_evolucao_alta' not in st.session_state:
                st.session_state.ia_input_ultima_evolucao_alta = ""
            st.session_state.ia_input_ultima_evolucao_alta = st.text_area(
                "Última evolução:",
                value=st.session_state.ia_input_ultima_evolucao_alta,
                height=300,
                key="ia_input_resumo_alta_widget",
                label_visibility="collapsed",
                placeholder="Cole a última evolução completa do paciente..."
            )
            st.markdown('<p class="cd-file-upload-label">📎 Anexar arquivos ou colar do clipboard (Ctrl+V após Win+Shift+S) — opcional</p>', unsafe_allow_html=True)
            _, file_parts_resumo, _ = render_file_uploader("resumo_alta")
            
            if st.button("Gerar Resumo de Alta", key="btn_ia_resumo_alta", type="primary"):
                if st.session_state.ia_input_ultima_evolucao_alta or file_parts_resumo:
                    with st.spinner("IA gerando o resumo de alta..."):
                        st.session_state.ia_output_resumo_alta = gerar_resumo_alta_ia(
                            st.session_state.ia_input_ultima_evolucao_alta,
                            file_parts=file_parts_resumo if file_parts_resumo else None
                        )
                else:
                    st.warning("Cole a última evolução do paciente.")
            if st.session_state.ia_output_resumo_alta:
                st.markdown("---")
                st.markdown('<p class="cd-section-label">Resumo de alta</p>', unsafe_allow_html=True)
                st.text_area("Resumo:", value=st.session_state.ia_output_resumo_alta, height=400, key="ia_resumo_alta_display", disabled=True, label_visibility="collapsed")
                components.html(make_copy_button_html("cClipResumoAlta", st.session_state.ia_output_resumo_alta, "Copiar resumo de alta"), height=55)
                if st.button("Limpar resumo", key="btn_clear_ia_resumo_alta"):
                    st.session_state.ia_output_resumo_alta = ""
                    st.session_state.ia_input_ultima_evolucao_alta = ""
                    st.rerun()

        # --- Orientações de Alta ---
        elif tarefa_ia_selecionada == "Gerar Orientações de Alta":
            st.markdown('<p class="cd-section-label">Caso do paciente</p>', unsafe_allow_html=True)
            if 'ia_input_caso_orientacoes' not in st.session_state:
                st.session_state.ia_input_caso_orientacoes = ""
            st.session_state.ia_input_caso_orientacoes = st.text_area(
                "Caso do paciente:",
                value=st.session_state.ia_input_caso_orientacoes,
                height=200,
                key="ia_input_orientacoes_alta_widget",
                label_visibility="collapsed",
                placeholder="Diagnóstico principal, comorbidades relevantes, pontos chave da internação..."
            )
            st.markdown('<p class="cd-file-upload-label">📎 Anexar arquivos ou colar do clipboard (Ctrl+V após Win+Shift+S) — opcional</p>', unsafe_allow_html=True)
            _, file_parts_orient, _ = render_file_uploader("orientacoes_alta")
            
            if st.button("Gerar Orientações de Alta", key="btn_ia_orientacoes_alta", type="primary"):
                if st.session_state.ia_input_caso_orientacoes or file_parts_orient:
                    with st.spinner("IA gerando as orientações de alta..."):
                        st.session_state.ia_output_orientacoes_alta = gerar_orientacoes_alta_ia(
                            st.session_state.ia_input_caso_orientacoes,
                            file_parts=file_parts_orient if file_parts_orient else None
                        )
                else:
                    st.warning("Descreva o caso do paciente.")
            if st.session_state.ia_output_orientacoes_alta:
                st.markdown("---")
                st.markdown('<p class="cd-section-label">Orientações de alta — sinais de alerta</p>', unsafe_allow_html=True)
                st.markdown(st.session_state.ia_output_orientacoes_alta)
                components.html(make_copy_button_html("cClipOrientAlta", st.session_state.ia_output_orientacoes_alta, "Copiar orientações"), height=55)
                if st.button("Limpar orientações", key="btn_clear_ia_orientacoes_alta"):
                    st.session_state.ia_output_orientacoes_alta = ""
                    st.session_state.ia_input_caso_orientacoes = ""
                    st.rerun()


# --- Footer ---
st.markdown("""
<div style="margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #e2e4e8;">
    <p style="font-size: 0.75rem; color: #9ca3af; text-align: center;">
        Este aplicativo é uma ferramenta de auxílio e não substitui a análise crítica e o julgamento clínico profissional. 
        Verifique sempre os resultados e a formatação final antes de usar em prontuários.
    </p>
</div>
""", unsafe_allow_html=True)
