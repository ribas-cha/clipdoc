import streamlit as st
import re
import json
import streamlit.components.v1 as components

# Padrões numéricos universais:
num_pattern = r"(\d{1,6}(?:[,.]\d{1,3})?)"  # de 1 a 6 dígitos, opcionalmente com vírgula/ponto e 1 a 3 decimais
gas_num_pattern = r"(-?\d{1,6}(?:[,.]\d{1,3})?)"  # permite sinal negativo opcional

def extract_value_in(lines, label):
    for i, line in enumerate(lines):
        if label.lower() in line.lower():
            m = re.search(num_pattern, line)
            if m:
                return m.group(1)
            for j in range(i+1, min(i+4, len(lines))):
                m = re.search(num_pattern, lines[j])
                if m:
                    return m.group(1)
    return ""

def extract_serology_result(full_text, key):
    pattern = re.compile(re.escape(key) + r".{0,200}", re.IGNORECASE | re.DOTALL)
    match = pattern.search(full_text)
    if match:
        block = match.group(0).lower()
        if "não reagente" in block:
            return "(-)"
        elif "reagente" in block:
            return "(+)"
    return ""

def extract_exam(label, lines):
    for i, line in enumerate(lines):
        if line.lower().startswith(label.lower()):
            m = re.search(num_pattern, line)
            if m:
                return m.group(1)
            for j in range(i+1, min(i+4, len(lines))):
                m = re.search(num_pattern, lines[j])
                if m:
                    return m.group(1)
    return ""

def extract_urina(lines):
    """
    Procura a seção "Urina Tipo I" e extrai:
      - U1_Nit: converte “Negativo” para (-) e “Positivo” para (+)
      - U1_leuco: extrai o primeiro valor numérico da linha de “Leucócitos” e converte, por exemplo, "16.000" para "16 mil"
      - U1_hem: faz o mesmo para "Hemácias"
    """
    urina_data = {}
    start_idx = None
    for i, line in enumerate(lines):
        if line.lower().startswith("urina tipo i"):
            start_idx = i
            break
    if start_idx is None:
        return None
    for line in lines[start_idx:]:
        lower_line = line.lower()
        if "assinado eletronicamente" in lower_line:
            break
        if "nitrito" in lower_line:
            if "negativo" in lower_line:
                urina_data["Nit"] = "(-)"
            elif "positivo" in lower_line:
                urina_data["Nit"] = "(+)"
        elif lower_line.startswith("leucócitos"):
            m = re.search(num_pattern, line)
            if m:
                val = m.group(1)
                val = val.replace(".000", "").replace(",000", "")
                urina_data["leuco"] = f"{val} mil"
        elif lower_line.startswith("hemácias"):
            m = re.search(num_pattern, line)
            if m:
                val = m.group(1)
                val = val.replace(".000", "").replace(",000", "")
                urina_data["hem"] = f"{val} mil"
    return urina_data if urina_data else None

def extract_cultura(lines):
    """
    Procura uma seção que contenha "Cultura de Urina" ou "Hemocultura" e extrai:
      - O tipo: URC (para urocultura) ou HMC (para hemocultura)
      - O resultado: remove as palavras "negativo" ou "não reagente". Se o resultado ficar vazio, usa (-).
      - Dos antibióticos, captura o nome do primeiro que tiver a marcação "R" (indicando resistência).
    """
    culture_type = None
    start_idx = None
    for i, line in enumerate(lines):
        l = line.lower()
        if "cultura de urina" in l:
            culture_type = "URC"
            start_idx = i
            break
        elif "hemocultura" in l:
            culture_type = "HMC"
            start_idx = i
            break
    if culture_type is None:
        return ""
    result = ""
    for line in lines[start_idx:]:
        if line.lower().startswith("resultado:"):
            res_text = line[len("resultado:"):].strip()
            # Remove as palavras "negativo" e "não reagente"
            res_clean = re.sub(r"(?i)\b(negativo|não reagente)\b", "", res_text).strip()
            if res_clean:
                result = res_clean
            else:
                result = "(-)"
            break
    if not result:
        result = "(-)"
    resistant_antibiotics = []
    antibiogram_found = False
    for line in lines[start_idx:]:
        if "antibiograma" in line.lower():
            antibiogram_found = True
            continue
        if antibiogram_found:
            m = re.search(r"^(.+?)\s+R\b", line)
            if m:
                antibiotic = m.group(1).strip()
                resistant_antibiotics.append(antibiotic + " R")
            if not line.strip():
                break
    antibiotics_str = " / ".join(resistant_antibiotics)
    if antibiotics_str:
        output = f"{culture_type} {result} / {antibiotics_str}"
    else:
        output = f"{culture_type} {result}"
    return output

def parse_lab_report_chrome(text):
    text = re.sub(r"(?i)ur[eé]ia", "U", text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    full_text = " ".join(lines).lower()

    datetime_out = ""
    for line in lines:
        if line.startswith("Data de Coleta/Recebimento:"):
            m = re.search(r"(\d{2}/\d{2})/\d{4},\s*Hora Aproximada:\s*(\d{2}:\d{2})", line, re.IGNORECASE)
            if m:
                datetime_out = f"{m.group(1)} {m.group(2).replace(':','h')}"
            break

    red_values = {}
    red_labels = {
        "Hemoglobina": "Hb",
        "Hematócrito": "Ht",
        "VCM": "VCM",
        "HCM": "HCM",
        "CHCM": "CHCM",
        "RDW": "RDW"
    }
    try:
        red_index = next(i for i, l in enumerate(lines) if "série vermelha" in l.lower())
    except StopIteration:
        red_index = None
    if red_index is not None:
        for label in red_labels:
            for line in lines[red_index:]:
                if line.lower().startswith(label.lower()):
                    rest = line[len(label):].strip()
                    m = re.search(num_pattern, rest)
                    if m:
                        red_values[red_labels[label]] = m.group(1)
                    break
    hb_value   = red_values.get("Hb", "")
    ht_value   = red_values.get("Ht", "")
    vcm_value  = red_values.get("VCM", "")
    hcm_value  = red_values.get("HCM", "")
    chcm_value = red_values.get("CHCM", "")
    rdw_value  = red_values.get("RDW", "")

    leuco_abs = ""
    for line in lines:
        if line.lower().startswith("leucócitos"):
            parts = re.split(r"\s+", line)
            if len(parts) >= 3:
                leuco_abs = parts[2]
            break
    mm_pct = extract_value_in(lines, "Metamielócitos")
    bast_pct = extract_value_in(lines, "Bastonetes")
    seg_pct = extract_value_in(lines, "Segmentados")
    if not seg_pct:
        seg_pct = extract_value_in(lines, "Neutrófilos")
    linf_pct = extract_value_in(lines, "Linfócitos")
    diff_parts = []
    if mm_pct:
        diff_parts.append(f"MM {mm_pct}%")
    if bast_pct:
        diff_parts.append(f"Bast {bast_pct}%")
    if seg_pct:
        diff_parts.append(f"Seg {seg_pct}%")
    if linf_pct:
        diff_parts.append(f"Linf {linf_pct}%")
    diff_str = f" ({', '.join(diff_parts)})" if diff_parts else ""

    plaq_value = ""
    for line in lines:
        if "contagem de plaquetas" in line.lower() and re.search(r"\d", line):
            m = re.search(r"Contagem de Plaquetas\s+" + num_pattern, line, re.IGNORECASE)
            if m:
                plaq_value = m.group(1)
            break

    pcr_value = ""
    for line in lines:
        if line.lower().startswith("proteína c reativa"):
            m = re.search(r"prote[ií]na c reativa\s+" + num_pattern, line, re.IGNORECASE)
            if m:
                pcr_value = m.group(1)
            break

    u_value = ""
    for line in lines:
        if line.startswith("U ") and re.search(r"\d", line):
            m = re.search(r"U\s+" + num_pattern, line, re.IGNORECASE)
            if m:
                u_value = m.group(1)
            break

    cr_value = ""
    for line in lines:
        if line.lower().startswith("creatinina") and "mg/dl" in line.lower():
            m = re.search(r"creatinina\s+" + num_pattern, line, re.IGNORECASE)
            if m:
                cr_value = m.group(1)
            break
    egfr_value = ""
    for line in lines:
        if line.lower().startswith("*egfr") or line.lower().startswith("egfr"):
            m = re.search(r"\*?egfr\s+" + num_pattern, line, re.IGNORECASE)
            if m:
                egfr_value = m.group(1)
            break
    creat_field = ""
    if cr_value or egfr_value:
        if cr_value:
            creat_field = "Cr " + cr_value
        if egfr_value:
            creat_field += " eGFR " + egfr_value

    k_value = ""
    for line in lines:
        if line.lower().startswith("potássio") or line.lower().startswith("potassio"):
            m = re.search(r"pot[aá]ssio\s+" + num_pattern, line, re.IGNORECASE)
            if m:
                k_value = m.group(1)
            break

    na_value = ""
    for line in lines:
        if line.lower().startswith("sódio") or line.lower().startswith("sodio"):
            m = re.search(r"s[oó]dio\s+" + num_pattern, line, re.IGNORECASE)
            if m:
                na_value = m.group(1)
            break

    tp_value = extract_value_in(lines, "Tempo de Protrombina")
    inr_value = extract_value_in(lines, "RNI")
    ttpa_value = extract_value_in(lines, "Tempo de Tromboplastina Parcial Ativado")
    r_value = extract_value_in(lines, "Relação:")
    mg_value = extract_value_in(lines, "Magnésio")

    p_value = extract_value_in(lines, "Fósforo")
    cai_value = ""
    for line in lines:
        if re.search(r"c[áa]lcio iônico", line, re.IGNORECASE):
            m = re.search(num_pattern, line)
            if m:
                cai_value = m.group(1)
            break

    base_fields = []
    if datetime_out:
        base_fields.append(datetime_out)
    if hb_value:
        base_fields.append("Hb " + hb_value)
    if ht_value:
        base_fields.append("Ht " + ht_value)
    if vcm_value:
        base_fields.append("VCM " + vcm_value)
    if hcm_value:
        base_fields.append("HCM " + hcm_value)
    if chcm_value:
        base_fields.append("CHCM " + chcm_value)
    if rdw_value:
        base_fields.append("RDW " + rdw_value)
    if leuco_abs:
        leuc_str = "Leuco " + leuco_abs
        if diff_str:
            leuc_str += diff_str
        base_fields.append(leuc_str)
    if plaq_value:
        base_fields.append("Plaq " + plaq_value)
    if pcr_value:
        base_fields.append("PCR " + pcr_value)
    if tp_value:
        base_fields.append("TP " + tp_value)
    if inr_value:
        base_fields.append("INR " + inr_value)
    if ttpa_value:
        base_fields.append("TTPA " + ttpa_value)
    if r_value:
        base_fields.append("R " + r_value)
    if u_value:
        base_fields.append("U " + u_value)
    if creat_field:
        base_fields.append(creat_field)
    if k_value:
        base_fields.append("K " + k_value)
    if na_value:
        base_fields.append("Na " + na_value)
    if mg_value:
        base_fields.append("Mg " + mg_value)
    if p_value:
        base_fields.append("P " + p_value)
    if cai_value:
        base_fields.append("CaI " + cai_value)

    base_output = " // ".join(base_fields)

    new_exams = []
    tgo_value = extract_exam("Transaminase oxalacética - TGO", lines)
    tgp_value = extract_exam("Transaminase pirúvica - TGP", lines)
    ggt_value = extract_exam("Gama-Glutamil Transferase", lines)
    aml_value = extract_exam("Amilase", lines)
    lip_value = extract_exam("Lipase", lines)
    fa_value = extract_exam("Fosfatase Alcalina", lines)
    bt_value = extract_exam("Bilirrubina Total", lines)
    bd_value = extract_exam("Bilirrubina Direta", lines)
    bi_value = extract_exam("Bilirrubina Indireta", lines)
    alb_value = extract_exam("Albumina", lines)
    if tgo_value:
        new_exams.append("TGO " + tgo_value)
    if tgp_value:
        new_exams.append("TGP " + tgp_value)
    if ggt_value:
        new_exams.append("gGT " + ggt_value)
    if aml_value:
        new_exams.append("AML " + aml_value)
    if lip_value:
        new_exams.append("LIP " + lip_value)
    if fa_value:
        new_exams.append("FA " + fa_value)
    bilirubinas = []
    if bt_value:
        bilirubinas.append("BT " + bt_value)
    if bd_value:
        bilirubinas.append("BD " + bd_value)
    if bi_value:
        bilirubinas.append("BI " + bi_value)
    if bilirubinas:
        new_exams.append(" ".join(bilirubinas))
    if alb_value:
        new_exams.append("ALB " + alb_value)

    new_exams_output = " // ".join(new_exams) if new_exams else ""

    gas_output = ""
    exam_prefix = ""
    gas_index = None
    for i, line in enumerate(lines):
        lower_line = line.lower()
        if lower_line.startswith("gasometria venosa"):
            exam_prefix = "GV_"
            gas_index = i
            break
        elif lower_line.startswith("gasometria arterial"):
            exam_prefix = "GA_"
            gas_index = i
            break
    if gas_index is not None:
        gas_labels = [
            ("ph", "pH"),
            ("pco2", "pCO2"),
            ("hco3", "HCO3"),
            ("excesso de bases", "BE"),
            ("po2", "pO2"),
            ("saturação de o2", "SatO2"),
            ("conteúdo de co2", "cCO2")
        ]
        gas_exam = {}
        for line in lines[gas_index+1:]:
            if not re.search(r"\d", line):
                continue
            lower_line = line.lower()
            for label, out_key in gas_labels:
                if lower_line.startswith(label):
                    value_text = line[len(label):].strip()
                    m = re.search(gas_num_pattern, value_text)
                    if m:
                        gas_exam[out_key] = m.group(1)
                    break
        gas_order = ["pH", "pCO2", "HCO3", "BE", "pO2", "SatO2", "cCO2"]
        gas_parts = []
        for param in gas_order:
            if param in gas_exam:
                gas_parts.append(f"{exam_prefix}{param} {gas_exam[param]}")
        gas_output = " // ".join(gas_parts) if gas_parts else ""

    serology_tests = [
        ("Anti HIV 1/2", "Anti HIV 1/2"),
        ("Anti-HAV (IgM)", "Anti-HAV (IgM)"),
        ("Anti-HAV (IgG)", "Anti-HAV (IgG)"),
        ("HBsAg", "HBsAG"),
        ("Anti-HBs", "Anti-HBs"),
        ("Anti-HBc Total", "Anti-HBc Total"),
        ("Anti-HBc IgM", "anti-HBc IgM"),
        ("Anti-HCV", "Anti-HCV")
    ]
    sero_results = []
    for key, out_label in serology_tests:
        pattern = re.compile(re.escape(key) + r".{0,200}", re.IGNORECASE | re.DOTALL)
        match = pattern.search(full_text)
        if match:
            block = match.group(0)
            if "não reagente" in block:
                sero_results.append(f"{out_label} (-)")
            elif "reagente" in block:
                sero_results.append(f"{out_label} (+)")
    sero_output = " // ".join(sero_results) if sero_results else ""

    urina_data = extract_urina(lines)
    urina_output = ""
    if urina_data:
        urina_parts = []
        if "Nit" in urina_data:
            urina_parts.append("U1_Nit " + urina_data["Nit"])
        if "leuco" in urina_data:
            urina_parts.append("U1_leuco " + urina_data["leuco"])
        if "hem" in urina_data:
            urina_parts.append("U1_hem " + urina_data["hem"])
        urina_output = " // ".join(urina_parts)

    culture_output = extract_cultura(lines)

    # Agora, junte todos os blocos em uma única linha.
    blocks = [base_output, new_exams_output, gas_output, sero_output, urina_output, culture_output]
    final_output = " // ".join(block for block in blocks if block) + " //"
    return final_output

st.set_page_config(page_title="CopiaCola", layout="centered")
st.title("CopiaCola")
st.write("Cole o texto do exame no campo abaixo e clique em 'Analisar Exame'.")

if "counter" not in st.session_state:
    st.session_state["counter"] = 0
if "saida" not in st.session_state:
    st.session_state["saida"] = ""

unique_key = f"entrada_{st.session_state['counter']}"
entrada_placeholder = st.empty()
entrada_text = entrada_placeholder.text_area("Entrada do Exame", key=unique_key, height=300)

cols = st.columns(4)
if cols[0].button("Analisar Exame"):
    if entrada_text:
        st.session_state["saida"] = parse_lab_report_chrome(entrada_text)
        st.session_state["counter"] += 1
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
        else:
            new_key = f"entrada_{st.session_state['counter']}"
            entrada_placeholder.empty()
            entrada_placeholder.text_area("Entrada do Exame", key=new_key, height=300)
    else:
        st.error("Por favor, insira o texto do exame acima.")
if cols[1].button("Sobre"):
    st.session_state["saida"] = (
        "Autor: Charles Ribas\n"
        "- Medicina (2016 - 2021) - Universidade de São Paulo\n"
        "- Letras - Tradução (2009 - 2012) - Universidade Nova de Lisboa"
    )
if cols[2].button("Exames Compatíveis"):
    st.session_state["saida"] = (
        "- HMG, TTPA/R, TP/INR, U/Cr (com eGFR);\n"
        "- Barrigograma completo;\n"
        "- Eletrólitos: Na, K, Mg, CaI, P;\n"
        "- Gasometria arterial e venosa;\n"
        "- Culturas;\n"
        "- Sorologias de hepatite e HIV"
    )

st.subheader("Saída do Exame:")
st.text_area("Saída", value=st.session_state.get("saida", ""), height=300)
