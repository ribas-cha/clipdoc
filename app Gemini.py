import streamlit as st
import re
import json
import streamlit.components.v1 as components
from dateutil import parser as date_parser

# --- Padrões Regex Globais ---
NUM_PATTERN = r"([<>]{0,1}\d{1,6}(?:[,.]\d{1,3})?)"
GAS_NUM_PATTERN = r"([<>]{0,1}-?\d{1,6}(?:[,.]\d{1,3})?)"

# --- Configuração de Valores de Referência (Atualizados) ---
VALORES_REFERENCIA = {
    "Hb": {"min": 13.0, "max": 17.0, "crit_low": 7.0, "crit_high": 20.0},
    "Ht": {"min": 40.0, "max": 50.0, "crit_low": 20.0},
    "VCM": {"min": 83.0, "max": 101.0},
    "HCM": {"min": 27.0, "max": 32.0},
    "CHCM": {"min": 31.0, "max": 35.0},
    "RDW": {"min": 11.6, "max": 14.0},
    "Leuco": {"min": 4000, "max": 10000, "crit_low": 1000, "crit_high": 30000},
    "Plaq": {"min": 150000, "max": 450000, "crit_low": 20000, "crit_high": 1000000},
    "PCR": {"max": 5.0, "crit_high": 100.0},
    "U": {"min": 15, "max": 50},
    "Cr": {"min": 0.50, "max": 1.50, "crit_high": 5.0},
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
    "Vanco": {"min": 15.0, "max": 20.0, "crit_low": 10.0, "crit_high": 25.0},  # Vancomicina atualizado
    "pH_gas": {"min": 7.35, "max": 7.45, "crit_low": 7.0, "crit_high": 7.8},
    "pCO2_gas": {"min": 35, "max": 45, "crit_low": 20, "crit_high": 80},
    "HCO3_gas": {"min": 22, "max": 28, "crit_low": 10, "crit_high": 40},
    "Lac_gas": {"max": 2.0, "crit_high": 4.0},
    "Lac": {"max": 2.0, "crit_high": 4.0},
}


# --- Funções Auxiliares ---

def clean_number_format(value_str):
    # Limpa e padroniza strings de números.
    if not value_str: return ""
    s = str(value_str).strip().lstrip('<>')
    if '.' in s and ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif '.' in s:
        parts = s.split('.')
        if len(parts) > 1 and len(parts[-1]) == 3 and all(p.isdigit() for p in parts) and len(parts) <= 2:
            s = "".join(parts)
        elif all(len(p) == 3 for p in parts[1:-1]) and all(p.isdigit() for p in parts):
            s = "".join(parts)
    elif ',' in s:
        s = s.replace(',', '.')
    return s


def convert_to_float(cleaned_value_str):
    # Converte string de número limpa para float.
    if not cleaned_value_str: return None
    try:
        return float(cleaned_value_str)
    except ValueError:
        return None


def format_value_with_alert(label, raw_value_str, key_ref):
    # Formata valor com alerta textual e sem unidades.
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

        if is_crit_high or is_crit_low:
            alert_suffix = " (!)"
        elif is_high or is_low:
            alert_suffix = " *"

        if key_ref == "eGFR" and min_val is not None and val_float < min_val:
            if not (is_crit_high or is_crit_low): alert_suffix = " *"
        elif key_ref == "eGFR" and alert_suffix == " *" and not ref.get("max") and not ref.get("crit_high"):
            alert_suffix = ""

    return f"{display_text}{alert_suffix}"


def extract_labeled_value(lines, labels_to_search, pattern_to_extract=NUM_PATTERN,
                          search_window_lines=3, label_must_be_at_start=False,
                          ignore_case=True, line_offset_for_value=0, require_unit=None):
    # Extrai valor associado a rótulos.
    if isinstance(labels_to_search, str): labels_to_search = [labels_to_search]
    for i, current_line in enumerate(lines):
        processed_line = current_line.lower() if ignore_case else current_line
        for label in labels_to_search:
            processed_label = label.lower() if ignore_case else label
            label_found_in_line, text_to_search_value_in = False, current_line
            start_index_of_label = -1
            if label_must_be_at_start:
                if processed_line.startswith(processed_label): start_index_of_label = 0
            else:
                start_index_of_label = processed_line.find(processed_label)

            if start_index_of_label != -1:
                label_found_in_line = True
                text_to_search_value_in = current_line[start_index_of_label + len(label):].strip()

            if label_found_in_line:
                target_line_idx = i + line_offset_for_value
                if 0 <= target_line_idx < len(lines):
                    line_content_for_search = lines[
                        target_line_idx] if line_offset_for_value != 0 else text_to_search_value_in
                    match = None
                    if line_content_for_search:
                        if require_unit:
                            pat_with_unit = pattern_to_extract + r"\s*" + re.escape(require_unit)
                            m_unit = re.search(pat_with_unit, line_content_for_search, re.IGNORECASE)
                            if m_unit: match = m_unit
                        else:
                            match = re.search(pattern_to_extract, line_content_for_search)
                    if match: return match.group(1)
                    if line_offset_for_value == 0:
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


# --- Funções de Extração Específicas ---

def extract_datetime_info(lines):
    # Extrai data e hora da coleta.
    for line in lines:
        m_generic = re.search(
            r"(data|coleta|recebimento)[:\s]*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})?[^0-9]*(\d{1,2}[:hH]\d{1,2})?", line,
            re.IGNORECASE)
        if m_generic:
            date_str, time_str = m_generic.group(2), m_generic.group(3)
            full_dt_str = (date_str.strip() if date_str else "") + (
                (" " + time_str.strip()) if time_str and date_str else (time_str.strip() if time_str else ""))
            if full_dt_str:
                try:
                    return date_parser.parse(full_dt_str.replace('h', ':'), dayfirst=True, fuzzy=True).strftime(
                        "%d/%m %Hh%M")
                except:
                    pass
        m_orig = re.search(r"(\d{2}/\d{2})/\d{4},\s*Hora Aproximada:\s*(\d{2}:\d{2})", line, re.IGNORECASE)
        if m_orig: return f"{m_orig.group(1)} {m_orig.group(2).replace(':', 'h')}"
    return ""


def extract_hemograma_completo(lines):
    # Extrai dados do hemograma.
    results = {}
    red_idx = next((i for i, l in enumerate(lines) if "série vermelha" in l.lower() or "eritrograma" in l.lower()), -1)
    search_red = lines[red_idx:] if red_idx != -1 else lines
    for k, lbls in [("Hb", ["Hemoglobina", "Hb"]), ("Ht", ["Hematócrito", "Ht"]), ("VCM", "VCM"), ("HCM", "HCM"),
                    ("CHCM", "CHCM"), ("RDW", "RDW")]:
        results[k] = extract_labeled_value(search_red, lbls, label_must_be_at_start=True)

    leuco_val = ""
    for i, line in enumerate(lines):
        l_line = line.lower()
        if l_line.startswith("leucócitos") or "leucócitos totais" in l_line:
            txt_after = re.sub(r"^(leucócitos|leucócitos totais)[\s:]*", "", line, flags=re.IGNORECASE).strip()
            parts = txt_after.split()
            nums = [p for p in parts if clean_number_format(p) and convert_to_float(clean_number_format(p)) is not None]
            if len(nums) == 1:
                leuco_val = nums[0]
            elif len(nums) > 1:
                if nums[0] == "100" and len(nums) > 1 and ('.' in nums[1] or (
                        clean_number_format(nums[1]).isdigit() and float(clean_number_format(nums[1])) > 500)):
                    leuco_val = nums[1]
                elif '.' in nums[0] or (
                        clean_number_format(nums[0]).isdigit() and float(clean_number_format(nums[0])) > 500):
                    leuco_val = nums[0]
                elif len(nums) > 1:
                    leuco_val = nums[1]
            if not leuco_val:
                m = re.search(NUM_PATTERN, txt_after)
                if m: leuco_val = m.group(1)
            if "mil" in txt_after.lower() and leuco_val:
                try:
                    leuco_val = str(int(float(clean_number_format(leuco_val)) * 1000))
                except:
                    pass
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
            m_linf = re.search(r"(?:Linfócitos TOTAIS|Linfócitos)\s*([<>]{0,1}\d{1,3}(?:[,.]\d{1,2})?)", l_line_content,
                               re.IGNORECASE)
            if m_linf: linf_val = m_linf.group(1); break
            if l_line_idx + 1 < len(lines):
                m_linf_next = re.search(NUM_PATTERN, lines[l_line_idx + 1])
                if m_linf_next: linf_val = m_linf_next.group(1); break
    if linf_val: diff.append(f"Linf {clean_number_format(linf_val)}%")
    results["Leuco_Diff"] = f"({', '.join(diff)})" if diff else ""

    results["Plaq"] = extract_labeled_value(lines, ["Plaquetas", "Contagem de Plaquetas"], label_must_be_at_start=False)
    if not results["Plaq"]:
        for i, line in enumerate(lines):
            if "plaquetas" in line.lower():
                m = re.search(r"(?:plaquetas|contagem de plaquetas)[\s:.]*([<>]{0,1}\d{1,3}(?:[.,]\d{3})*\d{0,3})",
                              line, re.IGNORECASE)
                if m: results["Plaq"] = m.group(1); break
                if i + 1 < len(lines):
                    m_next = re.search(NUM_PATTERN, lines[i + 1])
                    if m_next: results["Plaq"] = m_next.group(1); break
    return results


def extract_coagulograma(lines):
    # Extrai TP, INR, TTPA.
    results = {}
    results["TP_s"] = extract_labeled_value(lines, "Tempo em segundos:", label_must_be_at_start=False,
                                            search_window_lines=0)
    inr_val = ""
    for i, line in enumerate(lines):
        if "Internacional (RNI):" in line:
            if i + 1 < len(lines):
                m_inr = re.search(NUM_PATTERN, lines[i + 1])
                if m_inr: inr_val = m_inr.group(1); break
    if not inr_val: inr_val = extract_labeled_value(lines, ["RNI:", "INR:"], label_must_be_at_start=False,
                                                    search_window_lines=1)
    results["INR"] = inr_val

    ttpa_idx = next((i for i, l in enumerate(lines) if (
                "tempo de tromboplastina parcial ativado" in l.lower() or "ttpa" in l.lower()) and "tempo de protrombina" not in l.lower()),
                    -1)
    if ttpa_idx != -1:
        search_ttpa = lines[ttpa_idx:]
        results["TTPA_s"] = extract_labeled_value(search_ttpa, "Tempo em segundos", label_must_be_at_start=False,
                                                  search_window_lines=1)
        results["TTPA_R"] = extract_labeled_value(search_ttpa, "Relação:", label_must_be_at_start=False,
                                                  search_window_lines=1)
    return results


def extract_funcao_renal_e_eletrólitos(lines):
    # Extrai função renal e eletrólitos.
    results = {}
    results["U"] = extract_labeled_value(lines, "Ureia", label_must_be_at_start=True)
    if not results["U"]: results["U"] = extract_labeled_value(lines, "U ", label_must_be_at_start=True)
    results["Cr"] = extract_labeled_value(lines, "Creatinina ", label_must_be_at_start=True)
    results["eGFR"] = extract_labeled_value(lines, ["eGFR", "*eGFR", "Ritmo de Filtração Glomerular"],
                                            label_must_be_at_start=True)
    for k, lbls in [("K", ["Potássio", "K "]), ("Na", ["Sódio", "Na "]), ("Mg", "Magnésio"),
                    ("P", "Fósforo"), ("CaI", "Cálcio Iônico"), ("Cl", "Cloreto"), ("Gli", ["Glicose", "Glicemia"])]:
        results[k] = extract_labeled_value(lines, lbls, label_must_be_at_start=k not in ["CaI"])
    return results


def extract_marcadores_inflamatorios_cardiacos(lines):
    # Extrai marcadores inflamatórios e cardíacos.
    results = {}
    for k, lbls, start in [("PCR", ["Proteína C Reativa", "PCR"], True), ("Lac", "Lactato", True),
                           ("Trop", "Troponina", False), ("DD", "D-Dímero", False)]:
        results[k] = extract_labeled_value(lines, lbls, label_must_be_at_start=start)
    return results


def extract_hepatograma_pancreas(lines):
    # Extrai dados do hepatograma e pâncreas.
    results = {}
    tgo_val, tgp_val = "", ""

    # Verifica se estamos numa seção que parece ser de hepatograma para evitar falsos positivos
    # Adiciona mais termos chave do hepatograma para aumentar a chance de identificar a seção correta
    hepatograma_keywords = ["bilirrubina", "fosfatase alcalina", "gama-gt", "ggt", "albumina",
                            "transaminase", "ast", "alt", "tgo", "tgp"]
    is_hepatograma_section = any(keyword in line.lower() for line in lines for keyword in hepatograma_keywords)

    # Se não for uma seção de hepatograma, não tenta extrair TGO/TGP para evitar falsos positivos
    # de laudos que só têm, por exemplo, Vancomicina.
    if not is_hepatograma_section:
        # Ainda tenta extrair outros exames do hepatograma que podem estar isolados,
        # mas TGO/TGP são mais propensos a falsos positivos se não houver contexto.
        for k, lbls in [("GGT", ["Gama-Glutamil Transferase", "GGT"]), ("FA", "Fosfatase Alcalina"),
                        ("BT", "Bilirrubina Total"), ("BD", "Bilirrubina Direta"), ("BI", "Bilirrubina Indireta"),
                        ("ALB", "Albumina"), ("AML", "Amilase"), ("LIP", "Lipase")]:
            results[k] = extract_labeled_value(lines, lbls, label_must_be_at_start=True, search_window_lines=1)
        return results

    for i, line in enumerate(lines):
        if not tgo_val and "Transaminase oxalacética - TGO" in line:
            for offset in range(1, 4):
                if i + offset < len(lines):
                    # Procura por um número seguido por U/L, começando no início da linha
                    m = re.match(r"^\s*" + NUM_PATTERN + r"\s*U/L", lines[i + offset])
                    if m: tgo_val = m.group(1); break
            if not tgo_val and i + 2 < len(lines):  # Fallback se o padrão com U/L não pegar
                m = re.search(NUM_PATTERN, lines[i + 2])
                if m: tgo_val = m.group(1)

        if not tgp_val and "Transaminase pirúvica - TGP" in line:
            for offset in range(1, 4):
                if i + offset < len(lines):
                    m = re.match(r"^\s*" + NUM_PATTERN + r"\s*U/L", lines[i + offset])
                    if m: tgp_val = m.group(1); break
            if not tgp_val and i + 2 < len(lines):
                m = re.search(NUM_PATTERN, lines[i + 2])
                if m: tgp_val = m.group(1)
        if tgo_val and tgp_val: break

    results["TGO"] = tgo_val
    results["TGP"] = tgp_val

    # Fallbacks genéricos com require_unit para maior precisão
    if not results["TGO"]: results["TGO"] = extract_labeled_value(lines, ["TGO", "AST"], label_must_be_at_start=False,
                                                                  search_window_lines=1, require_unit="U/L")
    if not results["TGP"]: results["TGP"] = extract_labeled_value(lines, ["TGP", "ALT"], label_must_be_at_start=False,
                                                                  search_window_lines=1, require_unit="U/L")

    for k, lbls in [("GGT", ["Gama-Glutamil Transferase", "GGT"]), ("FA", "Fosfatase Alcalina"),
                    ("BT", "Bilirrubina Total"), ("BD", "Bilirrubina Direta"), ("BI", "Bilirrubina Indireta"),
                    ("ALB", "Albumina"), ("AML", "Amilase"), ("LIP", "Lipase")]:
        if k not in results or not results[k]:
            results[k] = extract_labeled_value(lines, lbls, label_must_be_at_start=True, search_window_lines=1)
    return results


def extract_medicamentos(lines):
    # Extrai dosagem de medicamentos como Vancomicina.
    results = {}
    results["Vanco"] = extract_labeled_value(lines, "Vancomicina", label_must_be_at_start=False, search_window_lines=0,
                                             require_unit="µg/mL")
    return results


def extract_gasometria(lines):
    # Extrai dados da gasometria.
    results, exam_prefix, gas_idx = {}, "", -1
    for i, line in enumerate(lines):
        l_line = line.lower()
        if "gasometria venosa" in l_line:
            exam_prefix, gas_idx = "GV_", i; break
        elif "gasometria arterial" in l_line:
            exam_prefix, gas_idx = "GA_", i; break
    if gas_idx == -1: return results
    gas_map = {"ph": "pH_gas", "pco2": "pCO2_gas", "hco3": "HCO3_gas", "bicarbonato": "HCO3_gas",
               "excesso de bases": "BE_gas",
               "be": "BE_gas", "po2": "pO2_gas", "saturação de o2": "SatO2_gas", "sato2": "SatO2_gas",
               "lactato": "Lac_gas",
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
    # Extrai resultados de sorologias.
    results = {}
    tests = [("Anti HIV 1/2", "HIV"), ("Anti-HAV (IgM)", "HAV_IgM"), ("HBsAg", "HBsAg"), ("Anti-HBs", "AntiHBs"),
             ("Anti-HBc Total", "AntiHBc_Total"), ("Anti-HCV", "HCV"), ("VDRL", "VDRL")]
    for i, line in enumerate(lines):
        l_line = line.lower()
        for srch_k, dict_k in tests:
            if srch_k.lower() in l_line:
                res_txt = ""
                for k_rng in range(i, min(i + 3, len(lines))):
                    s_line = lines[k_rng].lower()
                    if any(t in s_line for t in ["não reagente", "nao reagente", "negativo"]):
                        res_txt = "(-)"; break
                    elif any(t in s_line for t in ["reagente", "positivo"]):
                        res_txt = "(+)"; break
                    elif srch_k.lower() in s_line:
                        m = re.search(r"(\d+[:/]\d+)", lines[k_rng])
                        if m: res_txt = f"({m.group(1)})"; break
                if res_txt: results[dict_k] = res_txt; break
    return results


def extract_urina_tipo_i(lines):
    # Extrai dados da Urina Tipo I.
    results, found = {}, False
    for i, line in enumerate(lines):
        l_line = line.lower()
        if any(t in l_line for t in ["urina tipo i", "eas", "sumário de urina"]): found = True
        if not found: continue
        if "assinado eletronicamente" in l_line or ("método:" in l_line and "urina tipo i" not in l_line):
            if found: break
        if "nitrito" in l_line: results["U1_Nit"] = "(+)" if "positivo" in l_line else "(-)"
        for k, lbls, terms in [("U1_Leuco", ["leucócitos"],
                                {"numerosos": "Num", "inumeros": "Num", "raros": "Raros", "campos cobertos": "Cob"}),
                               ("U1_Hem", ["hemácias", "eritrócitos"],
                                {"numerosas": "Num", "inumeras": "Num", "raras": "Raras", "campos cobertos": "Cob"})]:
            if any(lbl in l_line for lbl in lbls):
                search_text = line.split(lbls[0])[-1] if lbls[0] in line else line
                m = re.search(NUM_PATTERN, search_text)
                if m and clean_number_format(m.group(1)).isdigit():
                    results[k] = clean_number_format(m.group(1));
                    break
                for term, abbr in terms.items():
                    if term in l_line: results[k] = abbr; break
                if k in results: break
    return results


def extract_culturas(lines):
    # Extrai dados de culturas (urocultura, hemocultura).
    found_cultures = []
    processed_indices = set()
    germe_regex = r"([A-Z][a-z]+\s(?:cf\.\s)?[A-Z]?[a-z]+)"

    current_culture_block_lines = []
    block_start_index = -1

    for i, line_content in enumerate(lines):
        l_line = line_content.lower()
        is_new_culture_header = "cultura de urina" in l_line or \
                                "urocultura" in l_line or \
                                "hemocultura" in l_line

        if is_new_culture_header and block_start_index != -1:
            # Processar o bloco anterior
            if current_culture_block_lines:
                culture_data = process_single_culture_block(current_culture_block_lines, lines, block_start_index,
                                                            germe_regex)
                if culture_data: found_cultures.append(culture_data)
            current_culture_block_lines = []  # Reset for new culture
            block_start_index = i

        if is_new_culture_header and block_start_index == -1:  # Primeira cultura encontrada
            block_start_index = i

        if block_start_index != -1:  # Se estamos dentro de um bloco de cultura potencial
            current_culture_block_lines.append(line_content)
            processed_indices.add(i)  # Marca como processada para não re-iniciar aqui

    # Processar o último bloco de cultura encontrado após o loop
    if current_culture_block_lines and block_start_index != -1:
        culture_data = process_single_culture_block(current_culture_block_lines, lines, block_start_index, germe_regex)
        if culture_data: found_cultures.append(culture_data)

    return found_cultures


def process_single_culture_block(block_lines, all_lines, original_start_idx, germe_regex):
    # Processa um bloco de linhas identificado como uma única cultura.
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

    if not culture_type_label: return None  # Não é um bloco de cultura válido
    current_culture_data["Tipo"] = culture_type_label.strip()

    result_text_found = "(-)"  # Default to negative
    for r_line in block_lines:
        lc_r_line = r_line.lower()
        if lc_r_line.startswith("resultado:") or "resultado da cultura:" in lc_r_line:
            res_text = re.sub(r"(?i)(resultado:|resultado da cultura:)", "", r_line, count=1).strip()
            germe_match = re.search(germe_regex, res_text)
            if germe_match:
                result_text_found = f"{germe_match.group(1).strip()} (+)"
            elif any(neg in res_text.lower() for neg in
                     ["negativo", "negativa", "não houve crescimento", "ausência de crescimento"]):
                result_text_found = "(-)"
            elif res_text:  # Se tem texto e não é explicitamente negativo nem germe
                result_text_clean = res_text.replace("Negativo", "").strip()  # Tenta limpar "Negativo" do final
                if result_text_clean: result_text_found = f"{result_text_clean} (+)"
                # else: result_text_found permanece "(-)" se ficou vazio
            break  # Encontrou a linha de resultado
    current_culture_data["Resultado"] = result_text_found

    antibiogram_results, antibiogram_start_idx_in_block = {"S": [], "I": [], "R": []}, -1
    for k, abg_line in enumerate(block_lines):
        if any(term in abg_line.lower() for term in ["antibiograma", "tsa", "teste de sensibilidade"]):
            antibiogram_start_idx_in_block = k;
            break
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


# --- Função Principal de Análise ---
def parse_lab_report(text):
    # Pré-processamento do texto para padronizar termos.
    subs = [("ur[eé]ia", "Ureia"), ("pot[aá]ssio", "Potássio"), ("s[oó]dio", "Sódio"),
            ("c[aá]lcio i[oô]nico", "Cálcio Iônico"), ("magn[eé]sio", "Magnésio"),
            ("Creatinina(?!\s*Kinase|\s*quinase)", "Creatinina ")]
    for p, r in subs: text = re.sub(f"(?i){p}", r, text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    all_res = {"datetime": extract_datetime_info(lines)}
    # Lista de funções extratoras para iterar.
    for ext in [extract_hemograma_completo, extract_coagulograma, extract_funcao_renal_e_eletrólitos,
                extract_marcadores_inflamatorios_cardiacos, extract_hepatograma_pancreas,
                extract_medicamentos, extract_gasometria, extract_sorologias, extract_urina_tipo_i]:
        all_res.update(ext(lines))
    all_res["culturas_list"] = extract_culturas(lines)  # Culturas retorna uma lista.

    # Dicionário para organizar a saída por seções.
    out_sections = {s: [] for s in ["HEADER", "HEMOGRAMA", "COAGULOGRAMA", "FUNCAO_RENAL_ELETRÓLITOS_GLI",
                                    "MARCADORES_INFLAM_CARD", "HEPATOGRAMA_PANCREAS", "MEDICAMENTOS", "GASOMETRIA",
                                    "URINA_I", "SOROLOGIAS", "CULTURAS", "OUTROS"]}

    # Montagem das seções de saída.
    if all_res.get("datetime"): out_sections["HEADER"].append(all_res["datetime"])

    # Hemograma
    for k, lbl in [("Hb", "Hb"), ("Ht", "Ht"), ("VCM", "VCM"), ("HCM", "HCM"), ("CHCM", "CHCM"), ("RDW", "RDW")]:
        if all_res.get(k): out_sections["HEMOGRAMA"].append(format_value_with_alert(lbl, all_res[k], k))
    l_str = format_value_with_alert("Leuco", all_res.get("Leuco", ""), "Leuco") if all_res.get("Leuco") else ""
    if l_str and all_res.get("Leuco_Diff") and all_res["Leuco_Diff"] != "()": l_str += f" {all_res['Leuco_Diff']}"
    if l_str: out_sections["HEMOGRAMA"].append(l_str)
    if all_res.get("Plaq"): out_sections["HEMOGRAMA"].append(format_value_with_alert("Plaq", all_res["Plaq"], "Plaq"))

    # Coagulograma
    tp_raw, inr_raw = all_res.get("TP_s", ""), all_res.get("INR", "")
    tp_fmt = format_value_with_alert("TP", tp_raw, "TP_s").replace("TP ", "") if tp_raw else ""
    inr_fmt = format_value_with_alert("INR", inr_raw, "INR").replace("INR ", "") if inr_raw else ""
    coag_p = []
    if tp_fmt:
        tp_inr_s = f"TP {tp_fmt}"
        if inr_fmt: tp_inr_s += f" (INR {inr_fmt})"
        coag_p.append(tp_inr_s)
    ttpa_s_raw, ttpa_r_raw = all_res.get("TTPA_s", ""), all_res.get("TTPA_R", "")
    ttpa_s_fmt = format_value_with_alert("TTPA", ttpa_s_raw, "TTPA_s").replace("TTPA ", "") if ttpa_s_raw else ""
    ttpa_r_fmt = format_value_with_alert("R", ttpa_r_raw, "TTPA_R").replace("R ", "") if ttpa_r_raw else ""
    if ttpa_s_fmt:
        ttpa_s = f"TTPA {ttpa_s_fmt}"
        if ttpa_r_fmt: ttpa_s += f" (R {ttpa_r_fmt})"
        coag_p.append(ttpa_s)
    if coag_p: out_sections["COAGULOGRAMA"].append(" // ".join(coag_p))

    # Função Renal, Eletrólitos, Glicemia
    if all_res.get("U"): out_sections["FUNCAO_RENAL_ELETRÓLITOS_GLI"].append(
        format_value_with_alert("Ureia", all_res["U"], "U"))
    cr_raw, egfr_raw = all_res.get("Cr", ""), all_res.get("eGFR", "")
    cr_fmt = format_value_with_alert("Cr", cr_raw, "Cr").replace("Cr ", "") if cr_raw else ""
    egfr_fmt = format_value_with_alert("eGFR", egfr_raw, "eGFR").replace("eGFR ", "") if egfr_raw else ""
    cr_egfr_s = f"Cr {cr_fmt}" if cr_fmt else ""
    if egfr_fmt: cr_egfr_s = (cr_egfr_s + f" (eGFR {egfr_fmt})") if cr_egfr_s else f"eGFR {egfr_fmt}"
    if cr_egfr_s: out_sections["FUNCAO_RENAL_ELETRÓLITOS_GLI"].append(cr_egfr_s)

    for k, lbl in [("Na", "Na"), ("K", "K"), ("Cl", "Cl"), ("Mg", "Mg"), ("CaI", "CaI"), ("P", "P"), ("Gli", "Gli")]:
        if all_res.get(k): out_sections["FUNCAO_RENAL_ELETRÓLITOS_GLI"].append(
            format_value_with_alert(lbl, all_res[k], k))
    try:  # AGap
        na, cl = convert_to_float(clean_number_format(all_res.get("Na", ""))), convert_to_float(
            clean_number_format(all_res.get("Cl", "")))
        hco3_s = next((all_res.get(k) for k in [f"{p}HCO3_gas" for p in ["GA_", "GV_", ""]] if all_res.get(k)), None)
        hco3 = convert_to_float(clean_number_format(hco3_s if hco3_s else ""))
        if na and cl and hco3: out_sections["FUNCAO_RENAL_ELETRÓLITOS_GLI"].append(f"AGap {(na - (cl + hco3)):.1f}")
    except:
        pass

    # Marcadores Inflamatórios e Cardíacos
    for k, lbl in [("PCR", "PCR"), ("Lac", "Lactato"), ("Trop", "Trop"), ("DD", "D-Dímero")]:
        if all_res.get(k): out_sections["MARCADORES_INFLAM_CARD"].append(format_value_with_alert(lbl, all_res[k], k))

    # Medicamentos
    if all_res.get("Vanco"): out_sections["MEDICAMENTOS"].append(
        format_value_with_alert("Vanco", all_res["Vanco"], "Vanco"))

    # Hepatograma e Pâncreas
    for k, lbl in [("TGO", "TGO"), ("TGP", "TGP"), ("GGT", "GGT"), ("FA", "FA")]:
        if all_res.get(k): out_sections["HEPATOGRAMA_PANCREAS"].append(format_value_with_alert(lbl, all_res[k], k))
    bili_p = [format_value_with_alert(lbl, all_res[k], k) for k, lbl in [("BT", "BT"), ("BD", "BD"), ("BI", "BI")] if
              all_res.get(k)]
    if bili_p: out_sections["HEPATOGRAMA_PANCREAS"].append(" ".join(bili_p))
    for k, lbl in [("ALB", "ALB"), ("AML", "AML"), ("LIP", "LIP")]:
        if all_res.get(k): out_sections["HEPATOGRAMA_PANCREAS"].append(format_value_with_alert(lbl, all_res[k], k))

    # Gasometria com prefixo GA_/GV_
    gas_pfx = next((p for p in ["GA_", "GV_"] if any(k.startswith(p) for k in all_res)), "")
    if gas_pfx:
        gas_order = ["pH_gas", "pCO2_gas", "pO2_gas", "HCO3_gas", "BE_gas", "SatO2_gas", "Lac_gas", "cCO2_gas"]
        for k_sfx in gas_order:
            full_key = gas_pfx + k_sfx
            if all_res.get(full_key):
                display_label = gas_pfx + k_sfx.replace("_gas", "")
                out_sections["GASOMETRIA"].append(format_value_with_alert(display_label, all_res[full_key], k_sfx))

    # Urina I
    for k, lbl in [("U1_Nit", "Nit"), ("U1_Leuco", "Leuco Ur"), ("U1_Hem", "Hem Ur")]:
        if all_res.get(k): out_sections["URINA_I"].append(f"{lbl} {all_res[k]}")

    # Sorologias
    soro_map = {"HIV": "Anti HIV 1/2", "HAV_IgM": "Anti-HAV IgM", "HBsAg": "HBsAg", "AntiHBs": "Anti-HBs",
                "AntiHBc_Total": "Anti-HBc Total", "HCV": "Anti-HCV", "VDRL": "VDRL"}
    for k, lbl in soro_map.items():
        if all_res.get(k): out_sections["SOROLOGIAS"].append(f"{lbl} {all_res[k]}")

    # Culturas
    if all_res.get("culturas_list"):
        for cult_info in all_res["culturas_list"]:
            c_str = f"{cult_info.get('Tipo', '')} {cult_info.get('Resultado', '')}"
            abg = cult_info.get("Antibiograma", {})
            abg_p = [f"{s[0]}: {', '.join(abg[s[0]])}" for s in ["S", "I", "R"] if abg.get(s[0])]
            if abg_p: c_str += " / " + " | ".join(abg_p)
            out_sections["CULTURAS"].append(c_str.strip())

    # Ordem final das seções na string de saída.
    section_order = ["HEADER", "HEMOGRAMA", "COAGULOGRAMA", "FUNCAO_RENAL_ELETRÓLITOS_GLI",
                     "MARCADORES_INFLAM_CARD", "MEDICAMENTOS", "HEPATOGRAMA_PANCREAS",
                     "GASOMETRIA", "URINA_I", "SOROLOGIAS", "CULTURAS", "OUTROS"]
    final_out = [" // ".join(out_sections[s_k]) for s_k in section_order if out_sections[s_k]]
    return " // ".join(filter(None, final_out)) + (" //" if any(final_out) else "")


# --- Interface Streamlit ---
st.set_page_config(page_title="ClipDoc", layout="wide")
st.title("🧪 ClipDoc")

st.markdown("""
Cole o texto do exame laboratorial no campo abaixo.
A formatação da saída busca ser concisa para prontuários. Valores alterados são marcados com `*` e críticos com `(!)`.
""")

if "input_text_area_content" not in st.session_state: st.session_state.input_text_area_content = ""
if "saida" not in st.session_state: st.session_state["saida"] = ""
if "show_about" not in st.session_state: st.session_state["show_about"] = False
if "show_compatible_exams_detailed" not in st.session_state: st.session_state["show_compatible_exams_detailed"] = False

col1, col2 = st.columns(2)
with col1:
    st.subheader("Entrada do Exame:")
    st.session_state.input_text_area_content = st.text_area(
        "Cole o texto do exame aqui:",
        value=st.session_state.input_text_area_content,
        key="entrada_widget",
        height=350,
        label_visibility="collapsed"
    )
    action_cols = st.columns(4)
    if action_cols[0].button("🔍 Analisar Exame", use_container_width=True, type="primary"):
        current_input = st.session_state.entrada_widget
        if current_input:
            with st.spinner("Analisando..."):
                st.session_state["saida"] = parse_lab_report(current_input)
            st.session_state.input_text_area_content = ""
            st.success("Análise concluída!")
            st.rerun()
        else:
            st.error("Por favor, insira o texto do exame.")
    if action_cols[1].button("ℹ️ Sobre", use_container_width=True):
        st.session_state["show_about"] = not st.session_state["show_about"]
        st.session_state["show_compatible_exams_detailed"] = False
    if action_cols[2].button("📋 Exames Compatíveis", use_container_width=True):
        st.session_state["show_compatible_exams_detailed"] = not st.session_state["show_compatible_exams_detailed"]
        st.session_state["show_about"] = False
    if action_cols[3].button("✨ Limpar Tudo", use_container_width=True):
        st.session_state["saida"] = ""
        st.session_state.input_text_area_content = ""
        st.rerun()
with col2:
    st.subheader("Saída Formatada:")
    st.text_area("Resultados formatados:", value=st.session_state.get("saida", ""), height=350,
                 key="saida_text_main_display", label_visibility="collapsed", disabled=True)
    if st.session_state.get("saida"):
        # Código HTML/JS para o botão de copiar.
        # As chaves {} do JavaScript precisam ser escapadas com {{}} em f-strings.
        components.html(
            f"""
            <textarea id="cClip" style="opacity:0;position:absolute;left:-9999px;top:-9999px;">{st.session_state['saida'].replace("'", "&apos;").replace('"', "&quot;")}</textarea>
            <button 
                onclick="
                    var t = document.getElementById('cClip');
                    t.select();
                    t.setSelectionRange(0, 99999);
                    try {{ 
                        var s = document.execCommand('copy');
                        var m = document.createElement('div');
                        m.textContent = s ? 'Resultados copiados!' : 'Falha ao copiar.';
                        m.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);padding:10px 20px;background-color:' + (s ? '#28a745' : '#dc3545') + ';color:white;border-radius:5px;z-index:1000;';
                        document.body.appendChild(m);
                        setTimeout(function() {{ 
                            document.body.removeChild(m);
                        }}, 2000); 
                    }} catch(e) {{ 
                        alert('Não foi possível copiar.');
                    }}
                " 
                style="padding:10px 15px;background-color:#007bff;color:white;border:none;border-radius:5px;cursor:pointer;width:100%;margin-top:10px;"
            >
            📋 Copiar Resultados
            </button>
            """,
            height=65
        )

if st.session_state["show_about"]:
    st.info(
        """
        **Autor do Código Original:** Charles Ribas
        - Medicina (2016 - 2021) - Universidade de São Paulo
        - Letras - Tradução (2009 - 2012) - Universidade Nova de Lisboa

        **Aprimoramentos e Refatoração:** Modelo de IA Gemini
        **Objetivo:** Facilitar a extração e formatação de dados de exames laboratoriais para agilizar o trabalho de profissionais de saúde.
        """
    )

if st.session_state["show_compatible_exams_detailed"]:
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

st.markdown("---")
st.caption(
    "Este aplicativo é uma ferramenta de auxílio e não substitui a análise crítica e o julgamento clínico profissional. Verifique sempre os resultados e a formatação final antes de usar em prontuários.")
