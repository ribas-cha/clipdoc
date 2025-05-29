import streamlit as st
import re
import json
import streamlit.components.v1 as components
from dateutil import parser as date_parser
import google.generativeai as genai # Importa a biblioteca do Gemini

# --- Configuração da Página (DEVE SER O PRIMEIRO COMANDO STREAMLIT) ---
st.set_page_config(page_title="ClipDoc", layout="wide")

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
    "PCR": {"max": 0.30, "crit_high": 10.0}, 
    "U": {"min": 15, "max": 50},
    "Cr": {"min": 0.50, "max": 1.30}, 
    "eGFR": {"min": 90},
    "K": {"min": 3.5, "max": 5.1, "crit_low": 2.5, "crit_high": 6.5},
    "Na": {"min": 136, "max": 145, "crit_low": 120, "crit_high": 160},
    "Mg": {"min": 1.8, "max": 2.4},
    "CaI": {"min": 1.12, "max": 1.32},
    "P": {"min": 2.5, "max": 4.5},
    "Cl": {"min": 98, "max": 107},
    "Gli": {"min": 70, "max": 99, "crit_high": 400, "crit_low": 40},
    "INR": {"min": 0.96, "max": 1.30, "crit_high": 5.0},
    "TTPA_s": {"min": 27.80, "max": 38.60, "crit_high": 100.0},
    "TTPA_R": {"min": 0.90, "max": 1.25, "crit_high": 3.0},
    "TGO": {"min": 15, "max": 37},
    "TGP": {"min": 6, "max": 45},
    "BT": {"min": 0.30, "max": 1.20},
    "BD": {"max": 0.20},
    "BI": {"min": 0.10, "max": 1.00},
    "ALB": {"min": 3.5, "max": 5.2},
    "AML": {"max": 100},
    "LIP": {"max": 160},
    "Vanco": {"min": 15.0, "max": 20.0, "crit_low": 10.0, "crit_high": 25.0}, 
    "pH_gas": {"min": 7.35, "max": 7.45, "crit_low": 7.0, "crit_high": 7.8},
    "pCO2_gas": {"min": 35, "max": 45, "crit_low": 20, "crit_high": 80},
    "HCO3_gas": {"min": 21.0, "max": 28.0, "crit_low": 10, "crit_high": 40}, 
    "BE_gas": {"min": -3.0, "max": 3.0}, 
    "pO2_gas": {"min": 80.0, "max": 95.0}, 
    "SatO2_gas": {"min": 95.0, "max": 99.0}, 
    "Lac_gas": {"max": 2.0, "crit_high": 4.0}, 
    "Lac": {"min": 0.50, "max": 1.60, "crit_high": 4.0}, 
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
    GOOGLE_API_KEY_LOCAL_FALLBACK = "AIzaSyA-EL0K8UbV6aCnHKFZECVQaRskYsp_jgQ" 
    if GOOGLE_API_KEY_LOCAL_FALLBACK != "SUA_API_KEY_AQUI_NO_CODIGO_GENERICO_PLACEHOLDER": 
        GOOGLE_API_KEY = GOOGLE_API_KEY_LOCAL_FALLBACK
        api_key_source = "local_code"

if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-1.5-flash-latest') 
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
    if '.' in s and ',' in s: s = s.replace('.', '').replace(',', '.')
    elif '.' in s:
        parts = s.split('.')
        if len(parts) > 1 and len(parts[-1]) == 3 and all(p.isdigit() for p in parts) and len(parts) <= 2 : s = "".join(parts)
        elif all(len(p) == 3 for p in parts[1:-1]) and all(p.isdigit() for p in parts): s = "".join(parts)
    elif ',' in s: s = s.replace(',', '.')
    return s

def convert_to_float(cleaned_value_str):
    if not cleaned_value_str: return None
    try: return float(cleaned_value_str)
    except ValueError: return None

def format_value_with_alert(label, raw_value_str, key_ref):
    if raw_value_str == "" or raw_value_str is None: return ""
    cleaned_value = clean_number_format(raw_value_str)
    if not cleaned_value: return f"{label} {raw_value_str}"
    display_text = f"{label} {cleaned_value}"
    val_float = convert_to_float(cleaned_value)
    alert_suffix = ""
    if val_float is not None and key_ref in VALORES_REFERENCIA:
        ref = VALORES_REFERENCIA[key_ref]
        crit_high, crit_low = ref.get("crit_high"), ref.get("crit_low")
        max_val, min_val = ref.get("max"), ref.get("min")
        is_crit_high = crit_high is not None and val_float > crit_high
        is_crit_low = crit_low is not None and val_float < crit_low
        is_high = max_val is not None and val_float > max_val
        is_low = min_val is not None and val_float < min_val
        if is_crit_high or is_crit_low: alert_suffix = " (!)"
        elif is_high or is_low: alert_suffix = " *"
        if key_ref == "eGFR" and min_val is not None and val_float < min_val:
            if not (is_crit_high or is_crit_low): alert_suffix = " *"
        elif key_ref == "eGFR" and alert_suffix == " *" and not ref.get("max") and not ref.get("crit_high"):
            alert_suffix = ""
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
def anonimizar_texto(texto):
    def substituir_nome_por_iniciais(match):
        nome_completo = match.group(0)
        partes_nome = nome_completo.split()
        # Verifica se tem pelo menos duas partes e se todas começam com maiúscula (indicativo de nome próprio)
        # e não é tudo maiúsculo (para não pegar siglas como HDA) e não termina com ':' (para não pegar headers)
        if len(partes_nome) > 1 and all(p[0].isupper() for p in partes_nome if p) and not nome_completo.isupper() and not nome_completo.endswith(":"):
            iniciais = [p[0] + "." for p in partes_nome if p] # Garante que p não é uma string vazia
            return " ".join(iniciais)
        return nome_completo 
    
    # Padrão mais específico para nomes com "de", "da", "dos", "das" no meio
    padrao_nome_composto = r"\b([A-ZÀ-Ú][a-zà-ú]+(?:\s+(?:de|da|do|dos|das)\s+[A-ZÀ-Ú][a-zà-ú]+)+)\b"
    texto_anonimizado = re.sub(padrao_nome_composto, substituir_nome_por_iniciais, texto)

    # Padrão geral para sequências de palavras capitalizadas (2 ou mais)
    padrao_nome_geral = r"\b(?!DR\b|DRA\b|Dr\b|Dra\b|SR\b|SRA\b|Sr\b|Sra\b)([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)+)\b"
    texto_anonimizado = re.sub(padrao_nome_geral, substituir_nome_por_iniciais, texto_anonimizado)
    
    return texto_anonimizado

# --- Funções de Extração Específicas ---
def extract_datetime_info(lines):
    for line in lines:
        # Regex para o formato específico: "Data de Coleta/Recebimento: DD/MM/AAAA, Hora Aproximada: HH:MM BRT"
        # O '.*?' no final permite qualquer texto após a hora (como BRT)
        m_specific = re.search(r"Data de Coleta/Recebimento:\s*(\d{2}/\d{2}/\d{4}),\s*Hora Aproximada:\s*(\d{2}:\d{2}).*?", line, re.IGNORECASE)
        if m_specific:
            date_part = m_specific.group(1)  # DD/MM/AAAA
            time_part = m_specific.group(2)  # HH:MM
            day_month_match = re.match(r"(\d{2}/\d{2})", date_part) # Pega DD/MM
            if day_month_match:
                return f"{day_month_match.group(1)} {time_part.replace(':', 'h')}"
        
        # Fallback para o padrão genérico se o específico não for encontrado
        m_generic = re.search(r"(data|coleta|recebimento)[:\s]*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})?[^0-9]*(\d{1,2}[:hH]\d{1,2})?", line, re.IGNORECASE)
        if m_generic:
            date_str, time_str = m_generic.group(2), m_generic.group(3)
            full_dt_str = (date_str.strip() if date_str else "") + ((" " + time_str.strip()) if time_str and date_str else (time_str.strip() if time_str else ""))
            if full_dt_str:
                try: 
                    dt_obj = date_parser.parse(full_dt_str.replace('h', ':'), dayfirst=True, fuzzy=True)
                    return dt_obj.strftime("%d/%m %Hh%M") 
                except: pass 
    return ""


def extract_hemograma_completo(lines):
    results = {}
    red_idx = next((i for i, l in enumerate(lines) if "série vermelha" in l.lower() or "eritrograma" in l.lower()), -1)
    search_red = lines[red_idx:] if red_idx != -1 else lines
    for k, lbls in [("Hb", ["Hemoglobina", "Hb"]), ("Ht", ["Hematócrito", "Ht"]), ("VCM", "VCM"), ("HCM", "HCM"), ("CHCM", "CHCM"), ("RDW", "RDW")]:
        results[k] = extract_labeled_value(search_red, lbls, label_must_be_at_start=True)
    leuco_val = ""
    for i, line in enumerate(lines):
        l_line = line.lower()
        if l_line.startswith("leucócitos") or "leucócitos totais" in l_line:
            txt_after = re.sub(r"^(leucócitos|leucócitos totais)[\s:]*", "", line, flags=re.IGNORECASE).strip()
            parts = txt_after.split()
            nums = [p for p in parts if clean_number_format(p) and convert_to_float(clean_number_format(p)) is not None]
            if len(nums) == 1: leuco_val = nums[0]
            elif len(nums) > 1:
                if nums[0] == "100" and len(nums) > 1 and ('.' in nums[1] or (clean_number_format(nums[1]).isdigit() and float(clean_number_format(nums[1])) > 500)):
                    leuco_val = nums[1]
                elif '.' in nums[0] or (clean_number_format(nums[0]).isdigit() and float(clean_number_format(nums[0])) > 500):
                    leuco_val = nums[0]
                elif len(nums) > 1: leuco_val = nums[1] 
            if not leuco_val: 
                m = re.search(NUM_PATTERN, txt_after)
                if m: leuco_val = m.group(1)
            if "mil" in txt_after.lower() and leuco_val:
                try: leuco_val = str(int(float(clean_number_format(leuco_val)) * 1000))
                except: pass
            if leuco_val: break
    results["Leuco"] = leuco_val
    diff = []
    for lbls, key in [(["Metamielócitos", "Meta"], "MM"), (["Bastonetes", "Bastões", "Bast"], "Bast")]:
        val = extract_labeled_value(lines, lbls, search_window_lines=1)
        if val: diff.append(f"{key} {clean_number_format(val)}%")
    seg_val = extract_labeled_value(lines, "Segmentados", search_window_lines=1)
    if not seg_val:
        n_line = next((l for l in lines if l.lower().startswith("neutrófilos")), "")
        if n_line:
            m = re.search(r"Neutrófilos\s*([<>]{0,1}\d{1,3}(?:[,.]\d{1,2})?)", n_line, re.IGNORECASE)
            if m: seg_val = m.group(1)
    if seg_val: diff.append(f"Seg {clean_number_format(seg_val)}%")
    linf_val = ""
    for l_line_idx, l_line_content in enumerate(lines):
        if any(lbl.lower() in l_line_content.lower() for lbl in ["Linfócitos TOTAIS", "Linfócitos"]):
            m_linf = re.search(r"(?:Linfócitos TOTAIS|Linfócitos)\s*([<>]{0,1}\d{1,3}(?:[,.]\d{1,2})?)", l_line_content, re.IGNORECASE)
            if m_linf: linf_val = m_linf.group(1); break
            if l_line_idx + 1 < len(lines):
                m_linf_next = re.search(NUM_PATTERN, lines[l_line_idx+1])
                if m_linf_next: linf_val = m_linf_next.group(1); break
    if linf_val: diff.append(f"Linf {clean_number_format(linf_val)}%")
    results["Leuco_Diff"] = f"({', '.join(diff)})" if diff else ""
    results["Plaq"] = extract_labeled_value(lines, ["Plaquetas", "Contagem de Plaquetas"], label_must_be_at_start=False)
    if not results["Plaq"]:
        for i, line in enumerate(lines):
            if "plaquetas" in line.lower():
                m = re.search(r"(?:plaquetas|contagem de plaquetas)[\s:.]*([<>]{0,1}\d{1,3}(?:[.,]\d{3})*\d{0,3})", line, re.IGNORECASE)
                if m: results["Plaq"] = m.group(1); break
                if i + 1 < len(lines):
                    m_next = re.search(NUM_PATTERN, lines[i+1])
                    if m_next: results["Plaq"] = m_next.group(1); break
    return results

def extract_coagulograma(lines):
    results = {}
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

def extract_funcao_renal_e_eletrólitos(lines):
    results = {}
    results["U"] = extract_labeled_value(lines, "Ureia", label_must_be_at_start=True)
    if not results["U"]: results["U"] = extract_labeled_value(lines, "U ", label_must_be_at_start=True)
    results["Cr"] = extract_labeled_value(lines, "Creatinina ", label_must_be_at_start=True)
    results["eGFR"] = extract_labeled_value(lines, ["eGFR", "*eGFR", "Ritmo de Filtração Glomerular"], label_must_be_at_start=True)
    for k, lbls in [("K", ["Potássio", "K "]), ("Na", ["Sódio", "Na "]), ("Mg", "Magnésio"), 
                    ("P", "Fósforo"), ("CaI", "Cálcio Iônico"), ("Cl", "Cloreto"), ("Gli", ["Glicose", "Glicemia"])]:
        results[k] = extract_labeled_value(lines, lbls, label_must_be_at_start=k not in ["CaI"])
    return results

def extract_marcadores_inflamatorios_cardiacos(lines):
    results = {}
    for k, lbls, start in [("PCR",["Proteína C Reativa","PCR"],True), ("Lac","Lactato",True), ("Trop","Troponina",False), ("DD","D-Dímero",False)]:
        results[k] = extract_labeled_value(lines, lbls, label_must_be_at_start=start)
    return results

def extract_hepatograma_pancreas(lines):
    results = {}
    tgo_val, tgp_val = "", ""
    hepatograma_keywords = ["bilirrubina", "fosfatase alcalina", "gama-gt", "ggt", "albumina", 
                            "transaminase", "ast", "alt", "tgo", "tgp"]
    is_hepatograma_context = any(keyword in line.lower() for line in lines for keyword in hepatograma_keywords) 
    
    if is_hepatograma_context:
        for i, line in enumerate(lines):
            if not tgo_val and "Transaminase oxalacética - TGO" in line:
                for offset in range(1, 4): 
                    if i + offset < len(lines):
                        m = re.match(r"^\s*" + NUM_PATTERN + r"\s*U/L", lines[i+offset]) 
                        if m: tgo_val = m.group(1); break
                if not tgo_val and i + 2 < len(lines):
                     m = re.search(NUM_PATTERN, lines[i+2])
                     if m: tgo_val = m.group(1)
            if not tgp_val and "Transaminase pirúvica - TGP" in line:
                for offset in range(1, 4):
                    if i + offset < len(lines):
                        m = re.match(r"^\s*" + NUM_PATTERN + r"\s*U/L", lines[i+offset])
                        if m: tgp_val = m.group(1); break
                if not tgp_val and i + 2 < len(lines):
                     m = re.search(NUM_PATTERN, lines[i+2])
                     if m: tgp_val = m.group(1)
            if tgo_val and tgp_val: break 
        results["TGO"] = tgo_val
        results["TGP"] = tgp_val
        if not results["TGO"]: results["TGO"] = extract_labeled_value(lines, ["TGO", "AST", "Aspartato amino transferase"], label_must_be_at_start=False, search_window_lines=1, require_unit="U/L")
        if not results["TGP"]: results["TGP"] = extract_labeled_value(lines, ["TGP", "ALT", "Alanina amino transferase"], label_must_be_at_start=False, search_window_lines=1, require_unit="U/L")
    
    for k, lbls in [("GGT", ["Gama-Glutamil Transferase","GGT"]), ("FA", "Fosfatase Alcalina"),
                    ("BT", "Bilirrubina Total"), ("BD", "Bilirrubina Direta"), ("BI", "Bilirrubina Indireta"),
                    ("ALB", "Albumina"), ("AML", "Amilase"), ("LIP", "Lipase")]:
        if k not in results or not results[k]:
            results[k] = extract_labeled_value(lines, lbls, label_must_be_at_start=True, search_window_lines=1)
    return results

def extract_medicamentos(lines):
    results = {}
    results["Vanco"] = extract_labeled_value(lines, "Vancomicina", label_must_be_at_start=False, search_window_lines=0, require_unit="µg/mL")
    return results

def extract_gasometria(lines):
    results, exam_prefix, gas_idx = {}, "", -1
    for i, line in enumerate(lines):
        l_line = line.lower()
        if "gasometria venosa" in l_line: exam_prefix, gas_idx = "GV_", i; break
        elif "gasometria arterial" in l_line: exam_prefix, gas_idx = "GA_", i; break
    if gas_idx == -1: return results
    gas_map = {"ph":"pH_gas","pco2":"pCO2_gas","hco3":"HCO3_gas","bicarbonato":"HCO3_gas","excesso de bases":"BE_gas",
               "be":"BE_gas","po2":"pO2_gas","saturação de o2":"SatO2_gas","sato2":"SatO2_gas","lactato":"Lac_gas",
               "conteúdo de co2": "cCO2_gas"}
    for line_num in range(gas_idx, min(gas_idx + len(gas_map) + 5, len(lines))):
        curr_line, l_curr_line = lines[line_num], lines[line_num].lower()
        for lbl_srch, out_k in gas_map.items():
            if out_k not in results:
                if l_curr_line.startswith(lbl_srch):
                    value_text = curr_line[len(lbl_srch):].strip()
                    m = re.search(GAS_NUM_PATTERN, value_text)
                    if m: results[out_k] = m.group(1); continue 
                m_any = re.search(re.escape(lbl_srch) + r"[\s:.-]*" + GAS_NUM_PATTERN, curr_line, re.IGNORECASE)
                if m_any: results[out_k] = m_any.group(1); continue
    return {exam_prefix + k: v for k, v in results.items()}

def extract_sorologias(lines):
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

def extract_urina_tipo_i(lines):
    results, found = {}, False
    for i, line in enumerate(lines):
        l_line = line.lower()
        if any(t in l_line for t in ["urina tipo i","eas","sumário de urina"]): found = True
        if not found: continue
        if "assinado eletronicamente" in l_line or ("método:" in l_line and "urina tipo i" not in l_line):
            if found: break 
        if "nitrito" in l_line: results["U1_Nit"] = "(+)" if "positivo" in l_line else "(-)"
        for k, lbls, terms in [("U1_Leuco",["leucócitos"],{"numerosos":"Num","inumeros":"Num","raros":"Raros","campos cobertos":"Cob"}),
                               ("U1_Hem",["hemácias","eritrócitos"],{"numerosas":"Num","inumeras":"Num","raras":"Raras","campos cobertos":"Cob"})]:
            if any(lbl in l_line for lbl in lbls):
                search_text = line.split(lbls[0])[-1] if lbls[0] in line else line 
                m = re.search(NUM_PATTERN, search_text)
                if m and clean_number_format(m.group(1)).isdigit(): 
                    results[k] = clean_number_format(m.group(1)); break 
                for term, abbr in terms.items():
                    if term in l_line: results[k] = abbr; break
                if k in results: break 
    return results

def extract_culturas(lines):
    found_cultures = []
    processed_block_indices = set() 
    germe_regex = r"([A-Z][a-z]+\s(?:cf\.\s)?[A-Z]?[a-z]+)" 
    current_culture_block_lines = []
    block_start_index = -1
    for i, line_content in enumerate(lines):
        l_line = line_content.lower()
        is_new_culture_header = "cultura de urina" in l_line or \
                                "urocultura" in l_line or \
                                "hemocultura" in l_line
        if is_new_culture_header:
            if block_start_index != -1 and current_culture_block_lines: 
                culture_data = process_single_culture_block(current_culture_block_lines, germe_regex)
                if culture_data: found_cultures.append(culture_data)
                for proc_idx in range(block_start_index, i): processed_indices.add(proc_idx) 
            current_culture_block_lines = [] 
            block_start_index = i
        if block_start_index != -1 and i not in processed_indices: 
            current_culture_block_lines.append(line_content)
    if current_culture_block_lines and block_start_index != -1: 
        culture_data = process_single_culture_block(current_culture_block_lines, germe_regex)
        if culture_data: found_cultures.append(culture_data)
        for proc_idx in range(block_start_index, len(lines)): processed_indices.add(proc_idx)

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
def gerar_resposta_ia(prompt_text):
    if not gemini_available or not gemini_model:
        return "Funcionalidade de IA indisponível. Verifique a configuração da API Key."
    try
        # Adicionando configurações de segurança para evitar bloqueios comuns
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        response = gemini_model.generate_content(prompt_text, safety_settings=safety_settings)
        
        # Pós-processamento para garantir linhas em branco e remover placeholders da IA
        processed_text = response.text
        
        # Remove placeholders como "[IA: ...]"
        processed_text = re.sub(r"\[IA:[^\]]*\]", "", processed_text)
        
        # Garante linha em branco após cada header principal
        # (exceto o último antes de um possível "Data Provável da Alta")
        headers_para_espaco = [
            "#CUIDADOS PALIATIVOS:", "#ID:", "#HD:", "#AP:", "#HDA:", "#MUC:", 
            "#ALERGIAS:", "#ATB:", "#TEV:", "#EXAMES:", "#EVOLUÇÃO:", 
            "#EXAME FÍSICO:", "#PLANO TERAPÊUTICO:", "#CONDUTA:"
        ]
        
        final_lines = []
        lines_response = processed_text.splitlines()
        for i, line in enumerate(lines_response):
            final_lines.append(line)
            # Verifica se a linha atual é um header que precisa de espaço depois
            # e se a próxima linha não é já uma linha em branco ou outro header
            if any(line.strip().startswith(h) for h in headers_para_espaco):
                if i + 1 < len(lines_response) and lines_response[i+1].strip() != "" and not lines_response[i+1].strip().startswith("#"):
                    final_lines.append("") # Adiciona linha em branco
                elif i + 1 == len(lines_response): # Se for a última linha e é um header
                    final_lines.append("")


        # Remove linhas em branco duplicadas que podem ter sido adicionadas
        # e garante que não haja mais de uma linha em branco consecutiva
        cleaned_final_lines = []
        previous_line_was_blank = False
        for line in final_lines:
            is_current_line_blank = not line.strip()
            if not (previous_line_was_blank and is_current_line_blank):
                cleaned_final_lines.append(line)
            previous_line_was_blank = is_current_line_blank
        
        processed_text = "\n".join(cleaned_final_lines)

        return anonimizar_texto(processed_text)
    except Exception as e:
        return f"Erro ao comunicar com a API do Gemini: {e}"

def evoluir_paciente_enfermaria_ia_fase1(evolucao_anterior): 
    prompt = f"""Você é um médico hospitalista experiente e suas orientações são guiadas por evidência científica.
Abaixo está a evolução de um paciente do dia anterior. Faça o seguinte, de modo sucinto e direto, sem devaneios:
1. Resumo do caso em um parágrafo conciso (como se fosse uma passagem de caso para colega médico): inclua antecedentes relevantes para internação, queixa principal e duração, hipóteses diagnósticas principais, resultados pertinentes de exames que corroboram ou afastam as hipóteses, planejamento terapêutico atual e futuro, e previsão de alta hospitalar (se inferível).
2. Pontos cruciais a serem discutidos com o paciente e/ou acompanhante hoje.
3. Pontos essenciais a serem avaliados no exame físico de hoje.
4. Sugestões de condutas e investigações para o dia de hoje, baseadas no quadro e evidências. Se houver múltiplas condutas possíveis por evidência fraca, mencione-as brevemente.

Evolução do dia anterior:
---
{anonimizar_texto(evolucao_anterior)}
---
Sua análise (Resumo, Pontos de Discussão, Exame Físico a Avaliar, Sugestões de Conduta):
"""
    return gerar_resposta_ia(prompt)

def evoluir_paciente_enfermaria_ia_fase2(resumo_ia_fase1, dados_medico_hoje, evolucao_anterior_original):
    linhas_evol_anterior = evolucao_anterior_original.splitlines()
    campos_fixos_dict = {}
    # Mapeia variações de HDA para uma chave padronizada
    hda_keys = {"#HDA:", "#HMA:", "#HPMA:"}
    # Campos a manter, usando a chave padronizada para HDA
    campos_para_manter_padronizados = {"#ID:", "#HD:", "#AP:", "#HDA:", "#MUC:", "#ALERGIAS:", "#ATB:", "#TEV:"}
    
    current_field_content = []
    current_field_label_padronizado = None 

    for linha in linhas_evol_anterior:
        linha_strip = linha.strip()
        
        matched_label_original = None
        matched_label_padronizado = None

        # Verifica se a linha começa com um dos labels de HDA
        for hda_var in hda_keys:
            if linha_strip.startswith(hda_var):
                matched_label_original = hda_var
                matched_label_padronizado = "#HDA:" # Padroniza para #HDA:
                break
        
        # Se não for HDA, verifica outros labels fixos
        if not matched_label_original:
            for label_fixo in campos_para_manter_padronizados:
                if label_fixo != "#HDA:" and linha_strip.startswith(label_fixo): # Evita re-checar HDA
                    matched_label_original = label_fixo
                    matched_label_padronizado = label_fixo
                    break
        
        # Verifica o campo de cuidados paliativos separadamente
        if linha_strip.startswith("#CUIDADOS PALIATIVOS:"):
            matched_label_original = "#CUIDADOS PALIATIVOS:"
            matched_label_padronizado = "#CUIDADOS PALIATIVOS:"


        is_outro_header_que_quebra_bloco = any(linha_strip.startswith(h) for h in ["#EXAMES:", "#EVOLUÇÃO:", "#EXAME FÍSICO:", "#PLANO TERAPÊUTICO:", "#CONDUTA:", "#DATA PROVÁVEL DA ALTA:"])
        
        if matched_label_original: # Se encontrou um header que queremos manter ou HDA/HMA/HPMA
            if current_field_label_padronizado: # Salva o campo anterior
                campos_fixos_dict[current_field_label_padronizado] = "\n".join(current_field_content).strip()
            
            current_field_label_padronizado = matched_label_padronizado
            current_field_content = [linha_strip.split(matched_label_original, 1)[-1].strip()]
        elif is_outro_header_que_quebra_bloco: # Se é um header que não queremos manter o conteúdo, mas quebra o bloco
            if current_field_label_padronizado:
                campos_fixos_dict[current_field_label_padronizado] = "\n".join(current_field_content).strip()
            current_field_label_padronizado = None 
            current_field_content = []
        elif current_field_label_padronizado: # Continuação do conteúdo de um campo que estamos capturando
            current_field_content.append(linha_strip)
            
    if current_field_label_padronizado: # Adiciona o último campo capturado
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
    if cuidados_paliativos_texto and cuidados_paliativos_texto.lower().strip() not in ["não", "nao", "no", "", "n", "negativo", "ausente"]:
        template_evolucao_parts.append(f"#CUIDADOS PALIATIVOS: {cuidados_paliativos_texto}\n\n")
    
    for label in ["#ID:", "#HD:", "#AP:", "#HDA:", "#MUC:", "#ALERGIAS:", "#ATB:", "#TEV:"]:
        template_evolucao_parts.append(f"{label} {campos_fixos_dict.get(label, '')}\n\n")

    template_evolucao_parts.append(f"#EXAMES:\n{exames_bloco_anterior_str}\n[NOVOS EXAMES AQUI]\n\n") # Placeholder para IA
    template_evolucao_parts.append("#EVOLUÇÃO:\n[NARRATIVA DO DIA AQUI]\n\n")
    template_evolucao_parts.append("#EXAME FÍSICO:\n[EXAME FÍSICO ATUALIZADO AQUI, ITENS COM HÍFEN]\n\n")
    template_evolucao_parts.append("#PLANO TERAPÊUTICO:\n[PLANO EM ITENS COM HÍFEN AQUI]\n\n")
    template_evolucao_parts.append("#CONDUTA:\n[CONDUTA EM PRIMEIRA PESSOA E ITENS COM HÍFEN AQUI]\n\n")
    template_evolucao_parts.append(f"#DATA PROVÁVEL DA ALTA: {campos_fixos_dict.get('#DATA PROVÁVEL DA ALTA:', 'SEM PREVISÃO')}")
    
    template_evolucao_final = "".join(template_evolucao_parts)

    prompt = f"""Você é um médico hospitalista experiente.
Sua tarefa é gerar uma nota de EVOLUÇÃO MÉDICA para HOJE.
MANTENHA OS SEGUINTES CAMPOS EXATAMENTE COMO ESTÃO NA 'Evolução Anterior Original', A MENOS QUE HAJA INFORMAÇÃO CONTRADITÓRIA DIRETA NOS 'Novos dados e observações do médico para a evolução de HOJE' que claramente substitua o conteúdo anterior:
#ID, #HD (Hipótese Diagnóstica), #AP (Antecedentes Patológicos), #HDA (História da Doença Atual - use o conteúdo de #HDA, #HMA ou #HPMA da evolução anterior para este campo), #MUC (Medicações em Uso Contínuo), #ALERGIAS, #ATB (Antibióticos), #TEV (Profilaxia para TEV).
O campo #CUIDADOS PALIATIVOS: deve ser omitido se não houver informação relevante ou se for negativo/não aplicável na evolução anterior.
Para o campo #EXAMES, mantenha os exames da evolução anterior e ADICIONE os novos exames/resultados fornecidos pelo médico.
A IA DEVE GERAR NOVO CONTEÚDO principalmente para #EVOLUÇÃO (narrativa do dia), #EXAME FÍSICO (integrando novos achados, com cada item iniciando com hífen), #PLANO TERAPÊUTICO (lista com hífen) e #CONDUTA (em primeira pessoa e com hífens).
Remova TODAS as instruções entre colchetes (como "[IA: ...]", "[NOVOS EXAMES AQUI]", etc.) da saída final.
ADICIONE UMA LINHA EM BRANCO APÓS CADA CAMPO PRINCIPAL (ex: após o conteúdo de #HDA:, antes de #MUC:).

(1) Análise da IA sobre a evolução anterior (Resumo do caso, Pontos de discussão, Exame físico a avaliar, Sugestões de conduta da IA):
---
{resumo_ia_fase1}
---

(2) Evolução Anterior Original (Fonte para os campos que devem ser mantidos e para o formato do exame físico anterior):
---
{anonimizar_texto(evolucao_anterior_original)}
---

(3) Novos dados e observações do médico para a evolução de HOJE (anamnese, exame físico, resultados de exames, intercorrências, etc.):
---
{anonimizar_texto(dados_medico_hoje)}
---

Gere a nota de EVOLUÇÃO MÉDICA para HOJE, preenchendo o modelo abaixo com base em TODAS as informações disponíveis e seguindo as instruções específicas para cada campo:
{template_evolucao_final}
"""
    return gerar_resposta_ia(prompt)


def preencher_admissao_ia(info_caso_original):
    info_caso = anonimizar_texto(info_caso_original)
    template_admissao = """# UNIDADE DE INTERNAÇÃO - ADMISSÃO #

#CUIDADOS PALIATIVOS:

#ID: 

#HD: 

#AP: 

#HDA: 

#MUC:

#ALERGIAS:

#ATB: 

#TEV: 

#EXAMES:
>CULTURAS/ANTÍGENOS:
>IMAGEM:
>LABS: 

#AVALIAÇÃO: 

#EXAME FÍSICO:

#PLANO TERAPÊUTICO: 

#CONDUTA:

#DATA PROVÁVEL DA ALTA: SEM PREVISÃO"""

    prompt = f"""Você é um assistente médico eficiente. Preencha o seguinte modelo de admissão hospitalar com as informações fornecidas sobre o caso do paciente.
Se alguma informação específica para um campo não for fornecida no texto do caso, deixe o campo correspondente em branco.
É crucial não inventar (alucinar) informações que não estão presentes no texto fornecido.
Após cada campo preenchido (ex: #HD: texto), adicione uma linha em branco antes do próximo campo (ex: #AP:).

Informações do caso:
---
{info_caso}
---

Preencha o modelo abaixo:
{template_admissao}
"""
    return gerar_resposta_ia(prompt)

def gerar_resumo_alta_ia(ultima_evolucao_original):
    ultima_evolucao = anonimizar_texto(ultima_evolucao_original)
    prompt = f"""Você é um médico hospitalista experiente. Suas orientações sempre são guiadas por evidência científica e, em casos em que há evidência fraca, você levanta e discute quais são as condutas possíveis. Para orientações de alta, você utiliza uma linguagem clara e direta e evita jargão médico.

Com base na última evolução do paciente fornecida abaixo, redija um resumo de alta hospitalar conciso e claro, estruturado em dois ou três parágrafos.
O resumo deve incluir:
1. Diagnóstico(s) principal(is) da internação.
2. Breve resumo de como o(s) diagnóstico(s) foi(ram) estabelecido(s) (exames chave, achados).
3. Principais tratamentos realizados durante a internação.
4. Condições do paciente no momento da alta hospitalar.
Adicione uma linha em branco entre cada parágrafo.

Última Evolução:
---
{ultima_evolucao}
---
Resumo de Alta (em 2 ou 3 parágrafos):
"""
    return gerar_resposta_ia(prompt)

def gerar_orientacoes_alta_ia(caso_paciente_original):
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
    return gerar_resposta_ia(prompt)

# --- Função Principal de Análise de Exames (parse_lab_report) ---
def parse_lab_report(text):
    # A anonimização agora é feita antes de chamar parse_lab_report ou nas funções de IA
    # text = anonimizar_texto(text) # Removido daqui para ser chamado externamente se necessário

    subs = [("ur[eé]ia","Ureia"),("pot[aá]ssio","Potássio"),("s[oó]dio","Sódio"),
            ("c[aá]lcio i[oô]nico","Cálcio Iônico"),("magn[eé]sio","Magnésio"),
            ("Creatinina(?!\s*Kinase|\s*quinase)","Creatinina ")] 
    for p, r in subs: text = re.sub(f"(?i){p}", r, text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    all_res = {"datetime": extract_datetime_info(lines)}
    for ext in [extract_hemograma_completo, extract_coagulograma, extract_funcao_renal_e_eletrólitos,
                extract_marcadores_inflamatorios_cardiacos, extract_hepatograma_pancreas,
                extract_medicamentos, extract_gasometria, extract_sorologias, extract_urina_tipo_i]:
        all_res.update(ext(lines))
    all_res["culturas_list"] = extract_culturas(lines)

    out_sections = {s: [] for s in ["HEADER", "HEMOGRAMA", "COAGULOGRAMA", "FUNCAO_RENAL_ELETRÓLITOS_GLI", 
                                     "MARCADORES_INFLAM_CARD", "HEPATOGRAMA_PANCREAS", "MEDICAMENTOS", "GASOMETRIA", 
                                     "URINA_I", "SOROLOGIAS", "CULTURAS", "OUTROS"]}

    if all_res.get("datetime"): out_sections["HEADER"].append(all_res["datetime"])

    for k, lbl in [("Hb","Hb"),("Ht","Ht"),("VCM","VCM"),("HCM","HCM"),("CHCM","CHCM"),("RDW","RDW")]:
        if all_res.get(k): out_sections["HEMOGRAMA"].append(format_value_with_alert(lbl, all_res[k], k))
    l_str = format_value_with_alert("Leuco", all_res.get("Leuco",""), "Leuco") if all_res.get("Leuco") else ""
    if l_str and all_res.get("Leuco_Diff") and all_res["Leuco_Diff"] != "()": l_str += f" {all_res['Leuco_Diff']}"
    if l_str: out_sections["HEMOGRAMA"].append(l_str)
    if all_res.get("Plaq"): out_sections["HEMOGRAMA"].append(format_value_with_alert("Plaq", all_res["Plaq"], "Plaq"))

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
    if coag_p: out_sections["COAGULOGRAMA"].append(" // ".join(coag_p))
    
    if all_res.get("U"): out_sections["FUNCAO_RENAL_ELETRÓLITOS_GLI"].append(format_value_with_alert("Ureia", all_res["U"], "U"))
    cr_raw, egfr_raw = all_res.get("Cr",""), all_res.get("eGFR","")
    cr_fmt = format_value_with_alert("Cr", cr_raw, "Cr").replace("Cr ", "") if cr_raw else ""
    egfr_fmt = format_value_with_alert("eGFR", egfr_raw, "eGFR").replace("eGFR ", "") if egfr_raw else ""
    cr_egfr_s = f"Cr {cr_fmt}" if cr_fmt else ""
    if egfr_fmt: cr_egfr_s = (cr_egfr_s + f" (eGFR {egfr_fmt})") if cr_egfr_s else f"eGFR {egfr_fmt}"
    if cr_egfr_s: out_sections["FUNCAO_RENAL_ELETRÓLITOS_GLI"].append(cr_egfr_s)

    for k, lbl in [("Na","Na"),("K","K"),("Cl","Cl"),("Mg","Mg"),("CaI","CaI"),("P","P"),("Gli","Gli")]:
        if all_res.get(k): out_sections["FUNCAO_RENAL_ELETRÓLITOS_GLI"].append(format_value_with_alert(lbl, all_res[k], k))
    try:
        na,cl = convert_to_float(clean_number_format(all_res.get("Na",""))), convert_to_float(clean_number_format(all_res.get("Cl","")))
        hco3_s = next((all_res.get(k) for k in [f"{p}HCO3_gas" for p in ["GA_","GV_",""]] if all_res.get(k)), None)
        hco3 = convert_to_float(clean_number_format(hco3_s if hco3_s else ""))
        if na and cl and hco3: out_sections["FUNCAO_RENAL_ELETRÓLITOS_GLI"].append(f"AGap {(na-(cl+hco3)):.1f}")
    except: pass

    for k, lbl in [("PCR","PCR"),("Lac","Lactato"),("Trop","Trop"),("DD","D-Dímero")]:
         if all_res.get(k): out_sections["MARCADORES_INFLAM_CARD"].append(format_value_with_alert(lbl, all_res[k], k))
    
    if all_res.get("Vanco"): out_sections["MEDICAMENTOS"].append(format_value_with_alert("Vanco", all_res["Vanco"], "Vanco"))

    for k, lbl in [("TGO","TGO"),("TGP","TGP"),("GGT","GGT"),("FA","FA")]:
        if all_res.get(k): out_sections["HEPATOGRAMA_PANCREAS"].append(format_value_with_alert(lbl, all_res[k], k))
    bili_p = [format_value_with_alert(lbl,all_res[k],k) for k,lbl in [("BT","BT"),("BD","BD"),("BI","BI")] if all_res.get(k)]
    if bili_p: out_sections["HEPATOGRAMA_PANCREAS"].append(" ".join(bili_p))
    for k, lbl in [("ALB","ALB"),("AML","AML"),("LIP","LIP")]:
        if all_res.get(k): out_sections["HEPATOGRAMA_PANCREAS"].append(format_value_with_alert(lbl, all_res[k], k))

    gas_pfx = next((p for p in ["GA_","GV_"] if any(k.startswith(p) for k in all_res)),"")
    if gas_pfx:
        gas_order = ["pH_gas", "pCO2_gas", "pO2_gas", "HCO3_gas", "BE_gas", "SatO2_gas", "Lac_gas", "cCO2_gas"]
        for k_sfx in gas_order:
            full_key = gas_pfx + k_sfx
            if all_res.get(full_key):
                display_label = gas_pfx + k_sfx.replace("_gas","") 
                out_sections["GASOMETRIA"].append(format_value_with_alert(display_label, all_res[full_key], k_sfx))

    for k, lbl in [("U1_Nit","Nit"),("U1_Leuco","Leuco Ur"),("U1_Hem","Hem Ur")]:
        if all_res.get(k): out_sections["URINA_I"].append(f"{lbl} {all_res[k]}")
    
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
    final_out = [" // ".join(out_sections[s_k]) for s_k in section_order if out_sections[s_k]]
    return " // ".join(filter(None, final_out)) + (" //" if any(final_out) else "")


# --- Interface Streamlit ---
st.title("🧪 ClipDoc")
st.markdown("""
Cole o texto do exame laboratorial no campo abaixo.
A formatação da saída busca ser concisa para prontuários. Valores alterados são marcados com `*` e críticos com `(!)`.
""")

# Avisos sobre API Key (somente se a chave não for de 'secrets' e não estiver definida localmente)
if not GOOGLE_API_KEY and api_key_source != "secrets": 
    st.warning("Chave da API do Google não configurada para desenvolvimento local. Funcionalidades de IA estarão desabilitadas. Defina-a na variável `GOOGLE_API_KEY_LOCAL_FALLBACK` no código ou como variável de ambiente `GOOGLE_API_KEY`.")
elif GOOGLE_API_KEY and not gemini_available and 'gemini_config_error' in st.session_state: 
     st.error(st.session_state.gemini_config_error)


# Inicialização do estado da sessão para IA
if "ia_output_evolucao_enf_fase1" not in st.session_state: 
    st.session_state.ia_output_evolucao_enf_fase1 = ""
if "evolucao_anterior_original_para_fase2" not in st.session_state: 
    st.session_state.evolucao_anterior_original_para_fase2 = ""
if "ia_output_admissao" not in st.session_state:
    st.session_state.ia_output_admissao = ""
if "ia_fase_evolucao_interativa" not in st.session_state: 
    st.session_state.ia_fase_evolucao_interativa = 1 
if "ia_dados_medico_hoje" not in st.session_state:
    st.session_state.ia_dados_medico_hoje = ""
if "ia_output_evolucao_final" not in st.session_state: 
    st.session_state.ia_output_evolucao_final = ""
if "ia_output_resumo_alta" not in st.session_state: 
    st.session_state.ia_output_resumo_alta = ""
if "ia_output_orientacoes_alta" not in st.session_state: 
    st.session_state.ia_output_orientacoes_alta = ""


# Aba principal para extração de exames
tab1, tab2 = st.tabs(["Extrair Exames", "🧑‍⚕️ Agente IA Hospitalista"])

with tab1:
    if "input_text_area_content_tab1" not in st.session_state: st.session_state.input_text_area_content_tab1 = "" 
    if "saida_exames" not in st.session_state: st.session_state["saida_exames"] = "" 
    if "show_about_tab1" not in st.session_state: st.session_state["show_about_tab1"] = False
    if "show_compatible_exams_detailed_tab1" not in st.session_state: st.session_state["show_compatible_exams_detailed_tab1"] = False

    col1_tab1, col2_tab1 = st.columns(2)
    with col1_tab1:
        st.subheader("Entrada do Exame:")
        st.session_state.input_text_area_content_tab1 = st.text_area(
            "Cole o texto do exame aqui:", 
            value=st.session_state.input_text_area_content_tab1, 
            key="entrada_widget_tab1",
            height=350, 
            label_visibility="collapsed"
        )
        action_cols_tab1 = st.columns(4)
        if action_cols_tab1[0].button("🔍 Analisar Exame", use_container_width=True, type="primary", key="btn_analisar_exame_tab1"):
            current_input_tab1 = st.session_state.entrada_widget_tab1
            if current_input_tab1:
                with st.spinner("Analisando Exames..."): 
                    # Anonimiza o input antes de passar para o parse_lab_report
                    texto_anonimizado_exames = anonimizar_texto(current_input_tab1)
                    st.session_state["saida_exames"] = parse_lab_report(texto_anonimizado_exames)
                st.session_state.input_text_area_content_tab1 = "" 
                st.success("Análise de exames concluída!")
                st.rerun()
            else: 
                st.error("Por favor, insira o texto do exame.")
        if action_cols_tab1[1].button("ℹ️ Sobre", use_container_width=True, key="btn_sobre_tab1"):
            st.session_state["show_about_tab1"] = not st.session_state["show_about_tab1"]
            st.session_state["show_compatible_exams_detailed_tab1"] = False
        if action_cols_tab1[2].button("📋 Exames Compatíveis", use_container_width=True, key="btn_compat_tab1"):
            st.session_state["show_compatible_exams_detailed_tab1"] = not st.session_state["show_compatible_exams_detailed_tab1"]
            st.session_state["show_about_tab1"] = False
        if action_cols_tab1[3].button("✨ Limpar Tudo", use_container_width=True, key="btn_limpar_tab1"):
            st.session_state["saida_exames"] = ""
            st.session_state.input_text_area_content_tab1 = "" 
            st.rerun()
    with col2_tab1:
        st.subheader("Saída Formatada dos Exames:")
        st.text_area("Resultados formatados:", value=st.session_state.get("saida_exames", ""), height=350, key="saida_text_main_display_tab1", label_visibility="collapsed", disabled=True)
        if st.session_state.get("saida_exames"):
            components.html( 
                f"""<textarea id="cClipExames" style="opacity:0;position:absolute;left:-9999px;top:-9999px;">{st.session_state['saida_exames'].replace("'", "&apos;").replace('"',"&quot;")}</textarea>
                <button onclick="var t=document.getElementById('cClipExames');t.select();t.setSelectionRange(0,99999);try{{var s=document.execCommand('copy');var m=document.createElement('div');m.textContent=s?'Resultados copiados!':'Falha.';m.style.cssText='position:fixed;bottom:20px;left:50%;transform:translateX(-50%);padding:10px 20px;background-color:'+(s?'#28a745':'#dc3545')+';color:white;border-radius:5px;z-index:1000;';document.body.appendChild(m);setTimeout(function(){{document.body.removeChild(m);}},2000);}}catch(e){{alert('Não foi possível copiar.');}}" style="padding:10px 15px;background-color:#007bff;color:white;border:none;border-radius:5px;cursor:pointer;width:100%;margin-top:10px;">📋 Copiar Resultados dos Exames</button>""",
                height=65
            )
    if st.session_state.get("show_about_tab1", False): 
        st.info(
            """
            **Autor do Código Original:** Charles Ribas
            - Medicina (2016 - 2021) - Universidade de São Paulo
            - Letras - Tradução (2009 - 2012) - Universidade Nova de Lisboa

            **Aprimoramentos e Refatoração:** Modelo de IA Gemini
            **Objetivo:** Facilitar a extração e formatação de dados de exames laboratoriais para agilizar o trabalho de profissionais de saúde.
            """
        )
    if st.session_state.get("show_compatible_exams_detailed_tab1", False):
        st.warning(
             """
            **Principais Exames Compatíveis (Tentativa de Extração):**
            - **Hemograma:** Hemoglobina, Hematócrito, VCM, HCM, CHCM, RDW, Leucócitos (com diferencial básico: Metamielócitos, Bastonetes, Segmentados/Neutrófilos, Linfócitos), Plaquetas.
            - **Coagulograma:** Tempo de Protrombina (TP em segundos), INR, Tempo de Tromboplastina Parcial Ativado (TTPA em segundos e Relação).
            - **Função Renal e Eletrólitos:** Ureia, Creatinina (com eGFR), Sódio (Na), Potássio (K), Cloreto (Cl), Magnésio (Mg), Cálcio Iônico (CaI), Fósforo (P).
            - **Glicemia (Gli).**
            - **Marcadores Inflamatórios/Cardíacos:** Proteína C Reativa (PCR), Lactato, Troponina (Trop), D-Dímero (DD) - extração básica.
            - **Hepatograma/Pâncreas:** Transaminase Oxalacética (TGO/AST), Transaminase Pirúvica (TGP/ALT), Gama-GT (GGT), Fosfatase Alcalina (FA), Bilirrubinas (Total, Direta, Indireta), Albumina (ALB), Amilase (AML), Lipase (LIP).
            - **Monitoramento de Drogas:** Vancomicina (Vancocinemia).
            - **Gasometria:** Arterial e Venosa (pH, pCO2, pO2, HCO3, Excesso de Bases (BE), Saturação de O2 (SatO2), Conteúdo de CO2 (cCO2), Lactato da gasometria).
            - **Urina Tipo I (EAS):** Nitrito, Leucócitos, Hemácias (extração básica de outros como pH, densidade, proteínas, glicose, cetonas pode ocorrer).
            - **Sorologias Comuns:** Anti HIV 1/2, Anti-HAV (IgM), HBsAg, Anti-HBs, Anti-HBc Total, Anti-HCV, VDRL.
            - **Culturas:** Urocultura (URC) e Hemocultura (HMC Aeróbio/Anaeróbio, com número da amostra), com identificação do germe (se presente) e antibiograma (Sensível/Intermediário/Resistente).

            A capacidade de extração pode variar.
            """
        )

with tab2: # Aba do Agente IA
    st.header("🧑‍⚕️ Agente IA Hospitalista")
    st.write("Use a IA para auxiliar em tarefas como resumir evoluções, preencher admissões e mais.")

    if not gemini_available:
        st.error("O Agente IA Hospitalista está indisponível no momento. Verifique a configuração da chave API ou o erro de configuração acima.")
    else:
        ia_task_options = [
            "Selecione uma tarefa...",
            "Evoluir Paciente (Enfermaria - Interativo)", 
            "Auxiliar na Admissão de Paciente",
            "Redigir Resumo de Alta", 
            "Gerar Orientações de Alta"
        ]
        tarefa_ia_selecionada = st.selectbox("Qual tarefa o Agente IA deve realizar?", ia_task_options, key="ia_task_selector_tab2")

        if tarefa_ia_selecionada == "Evoluir Paciente (Enfermaria - Interativo)":
            st.subheader("Auxiliar na Evolução de Paciente (Interativo)")
            if st.session_state.ia_fase_evolucao_interativa == 1:
                evolucao_anterior_input_ia = st.text_area("1. Cole a evolução do dia ANTERIOR aqui:", height=200, key="ia_evol_enf_input_fase1_widget")
                if st.button("Analisar Evolução Anterior com IA", key="btn_ia_evol_enf_fase1"):
                    if evolucao_anterior_input_ia:
                        with st.spinner("IA processando a evolução anterior..."):
                            st.session_state.evolucao_anterior_original_para_fase2 = evolucao_anterior_input_ia 
                            st.session_state.ia_output_evolucao_enf_fase1 = evoluir_paciente_enfermaria_ia_fase1(evolucao_anterior_input_ia)
                        st.session_state.ia_fase_evolucao_interativa = 2 
                        st.rerun() 
                    else: st.warning("Por favor, cole a evolução anterior.")
            
            if st.session_state.ia_fase_evolucao_interativa == 2:
                if st.session_state.ia_output_evolucao_enf_fase1:
                    st.markdown("---"); st.markdown("**Análise e Sugestões da IA (baseado na evolução anterior):**"); st.markdown(st.session_state.ia_output_evolucao_enf_fase1); st.markdown("---")
                
                st.session_state.ia_dados_medico_hoje = st.text_area(
                    "2. Adicione seus achados de HOJE (anamnese, exame físico, novos exames, intercorrências, etc.):", 
                    height=200, 
                    key="ia_dados_medico_input_fase2_widget", 
                    value=st.session_state.ia_dados_medico_hoje 
                )
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Gerar Evolução Final com IA", key="btn_ia_evol_enf_fase2"):
                        dados_medico_hoje_input = st.session_state.ia_dados_medico_input_fase2_widget 
                        if dados_medico_hoje_input: 
                            st.session_state.ia_dados_medico_hoje = dados_medico_hoje_input 
                            with st.spinner("IA gerando a evolução final..."):
                                st.session_state.ia_output_evolucao_final = evoluir_paciente_enfermaria_ia_fase2(
                                    st.session_state.ia_output_evolucao_enf_fase1,
                                    st.session_state.ia_dados_medico_hoje,
                                    st.session_state.evolucao_anterior_original_para_fase2 
                                )
                            st.session_state.ia_fase_evolucao_interativa = 3; st.rerun()
                        else: st.warning("Por favor, adicione seus achados de hoje.")
                with col_btn2:
                    if st.button("Voltar/Reiniciar Evolução Interativa", key="btn_reset_evol_interativa"):
                        st.session_state.ia_fase_evolucao_interativa = 1; st.session_state.ia_output_evolucao_enf_fase1 = ""; st.session_state.ia_dados_medico_hoje = ""; st.session_state.ia_output_evolucao_final = ""; st.session_state.evolucao_anterior_original_para_fase2 = ""; st.rerun()
            
            if st.session_state.ia_fase_evolucao_interativa == 3:
                if st.session_state.ia_output_evolucao_enf_fase1: st.markdown("---"); st.markdown("**Análise e Sugestões da IA (baseado na evolução anterior):**"); st.markdown(st.session_state.ia_output_evolucao_enf_fase1)
                if st.session_state.ia_dados_medico_hoje: st.markdown("---"); st.markdown("**Seus achados de HOJE (fornecidos à IA):**"); st.markdown(st.session_state.ia_dados_medico_hoje)
                if st.session_state.ia_output_evolucao_final:
                    st.markdown("---"); st.subheader("Evolução Médica Final (Gerada pela IA):")
                    st.text_area("Evolução:", value=st.session_state.ia_output_evolucao_final, height=400, key="ia_evolucao_final_display", disabled=True)
                    components.html(f"""<textarea id="cClipEvolFinal" style="opacity:0;position:absolute;left:-9999px;top:-9999px;">{st.session_state.ia_output_evolucao_final.replace("'", "&apos;").replace('"','&quot;')}</textarea><button onclick="var t=document.getElementById('cClipEvolFinal');t.select();t.setSelectionRange(0,99999);try{{var s=document.execCommand('copy');var m=document.createElement('div');m.textContent=s?'Evolução copiada!':'Falha.';m.style.cssText='position:fixed;bottom:20px;left:50%;transform:translateX(-50%);padding:10px 20px;background-color:'+(s?'#28a745':'#dc3545')+';color:white;border-radius:5px;z-index:1000;';document.body.appendChild(m);setTimeout(function(){{document.body.removeChild(m);}},2000);}}catch(e){{alert('Não foi possível copiar.');}}" style="padding:10px 15px;background-color:#28a745;color:white;border:none;border-radius:5px;cursor:pointer;width:100%;margin-top:10px;">📋 Copiar Evolução Final</button>""", height=65)
                if st.button("Iniciar Nova Evolução Interativa", key="btn_nova_evol_interativa"):
                    st.session_state.ia_fase_evolucao_interativa = 1; st.session_state.ia_output_evolucao_enf_fase1 = ""; st.session_state.ia_dados_medico_hoje = ""; st.session_state.ia_output_evolucao_final = ""; st.session_state.evolucao_anterior_original_para_fase2 = ""; st.rerun()

        elif tarefa_ia_selecionada == "Auxiliar na Admissão de Paciente":
            st.subheader("Gerar Rascunho de Admissão")
            info_caso_input_ia = st.text_area("Forneça as informações do caso para admissão:", height=300, key="ia_adm_info_input_tab2")
            if st.button("Gerar Admissão com IA", key="btn_ia_adm_tab2"):
                if info_caso_input_ia:
                    with st.spinner("IA gerando o rascunho da admissão..."):
                        st.session_state.ia_output_admissao = preencher_admissao_ia(info_caso_input_ia)
                else: st.warning("Por favor, forneça as informações do caso.")
            if st.session_state.ia_output_admissao:
                st.markdown("---"); st.subheader("Rascunho da Admissão (gerado pela IA):")
                st.text_area("Modelo Preenchido:", value=st.session_state.ia_output_admissao, height=400, key="ia_admissao_output_display_tab2", disabled=True)
                components.html(f"""<textarea id="cClipAdmissaoTab2" style="opacity:0;position:absolute;left:-9999px;top:-9999px;">{st.session_state['ia_output_admissao'].replace("'", "&apos;").replace('"',"&quot;")}</textarea><button onclick="var t=document.getElementById('cClipAdmissaoTab2');t.select();t.setSelectionRange(0,99999);try{{var s=document.execCommand('copy');var m=document.createElement('div');m.textContent=s?'Admissão copiada!':'Falha.';m.style.cssText='position:fixed;bottom:20px;left:50%;transform:translateX(-50%);padding:10px 20px;background-color:'+(s?'#28a745':'#dc3545')+';color:white;border-radius:5px;z-index:1000;';document.body.appendChild(m);setTimeout(function(){{document.body.removeChild(m);}},2000);}}catch(e){{alert('Não foi possível copiar.');}}" style="padding:10px 15px;background-color:#28a745;color:white;border:none;border-radius:5px;cursor:pointer;width:100%;margin-top:10px;">📋 Copiar Rascunho da Admissão</button>""", height=65)
                if st.button("Limpar Rascunho da Admissão", key="btn_clear_ia_adm_tab2"):
                    st.session_state.ia_output_admissao = ""; st.rerun()
        
        elif tarefa_ia_selecionada == "Redigir Resumo de Alta":
            st.subheader("Redigir Resumo de Alta Hospitalar")
            ultima_evolucao_input_alta = st.text_area("Cole a ÚLTIMA evolução completa do paciente aqui:", height=300, key="ia_input_resumo_alta")
            if st.button("Gerar Resumo de Alta com IA", key="btn_ia_resumo_alta"):
                if ultima_evolucao_input_alta:
                    with st.spinner("IA gerando o resumo de alta..."):
                        st.session_state.ia_output_resumo_alta = gerar_resumo_alta_ia(ultima_evolucao_input_alta)
                else:
                    st.warning("Por favor, cole a última evolução do paciente.")
            if st.session_state.ia_output_resumo_alta:
                st.markdown("---"); st.subheader("Resumo de Alta (Gerado pela IA):")
                st.text_area("Resumo:", value=st.session_state.ia_output_resumo_alta, height=400, key="ia_resumo_alta_display", disabled=True)
                components.html(f"""<textarea id="cClipResumoAlta" style="opacity:0;position:absolute;left:-9999px;top:-9999px;">{st.session_state.ia_output_resumo_alta.replace("'", "&apos;").replace('"',"&quot;")}</textarea><button onclick="var t=document.getElementById('cClipResumoAlta');t.select();t.setSelectionRange(0,99999);try{{var s=document.execCommand('copy');var m=document.createElement('div');m.textContent=s?'Resumo copiado!':'Falha.';m.style.cssText='position:fixed;bottom:20px;left:50%;transform:translateX(-50%);padding:10px 20px;background-color:'+(s?'#28a745':'#dc3545')+';color:white;border-radius:5px;z-index:1000;';document.body.appendChild(m);setTimeout(function(){{document.body.removeChild(m);}},2000);}}catch(e){{alert('Não foi possível copiar.');}}" style="padding:10px 15px;background-color:#007bff;color:white;border:none;border-radius:5px;cursor:pointer;width:100%;margin-top:10px;">📋 Copiar Resumo de Alta</button>""", height=65)
                if st.button("Limpar Resumo de Alta", key="btn_clear_ia_resumo_alta"):
                    st.session_state.ia_output_resumo_alta = ""; st.rerun()

        elif tarefa_ia_selecionada == "Gerar Orientações de Alta":
            st.subheader("Gerar Orientações de Alta (Sinais de Alerta)")
            caso_paciente_input_orient = st.text_area("Descreva o caso do paciente (diagnóstico principal, comorbidades relevantes, pontos chave da internação):", height=200, key="ia_input_orientacoes_alta")
            if st.button("Gerar Orientações de Alta com IA", key="btn_ia_orientacoes_alta"):
                if caso_paciente_input_orient:
                    with st.spinner("IA gerando as orientações de alta..."):
                        st.session_state.ia_output_orientacoes_alta = gerar_orientacoes_alta_ia(caso_paciente_input_orient)
                else:
                    st.warning("Por favor, descreva o caso do paciente.")
            if st.session_state.ia_output_orientacoes_alta:
                st.markdown("---"); st.subheader("Orientações de Alta (Geradas pela IA):")
                st.markdown(st.session_state.ia_output_orientacoes_alta) 
                components.html(f"""<textarea id="cClipOrientAlta" style="opacity:0;position:absolute;left:-9999px;top:-9999px;">{st.session_state.ia_output_orientacoes_alta.replace("'", "&apos;").replace('"',"&quot;")}</textarea><button onclick="var t=document.getElementById('cClipOrientAlta');t.select();t.setSelectionRange(0,99999);try{{var s=document.execCommand('copy');var m=document.createElement('div');m.textContent=s?'Orientações copiadas!':'Falha.';m.style.cssText='position:fixed;bottom:20px;left:50%;transform:translateX(-50%);padding:10px 20px;background-color:'+(s?'#28a745':'#dc3545')+';color:white;border-radius:5px;z-index:1000;';document.body.appendChild(m);setTimeout(function(){{document.body.removeChild(m);}},2000);}}catch(e){{alert('Não foi possível copiar.');}}" style="padding:10px 15px;background-color:#007bff;color:white;border:none;border-radius:5px;cursor:pointer;width:100%;margin-top:10px;">📋 Copiar Orientações de Alta</button>""", height=65)
                if st.button("Limpar Orientações de Alta", key="btn_clear_ia_orientacoes_alta"): 
                    st.session_state.ia_output_orientacoes_alta = ""; st.rerun()


# Rodapé comum
st.markdown("---")
st.caption("Este aplicativo é uma ferramenta de auxílio e não substitui a análise crítica e o julgamento clínico profissional. Verifique sempre os resultados e a formatação final antes de usar em prontuários.")

