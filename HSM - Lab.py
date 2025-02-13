import keyboard
import PySimpleGUI as sg
##############################
sg.theme('LightBlue3')
##############################
icon40 = b'iVBORw0KGgoAAAANSUhEUgAAAB4AAAAeCAYAAAA7MK6iAAAABmJLR0QA/wD/AP+gvaeTAAABU0lEQVRIiWNkIAOkVfV7M/xnmMnAwPD/PyND2uy2wu2kmsFCjsUM/xlm/GdiCmP8w8DEyPRvGQMDgxypRjCiCxydGXr+799/BujiSx7bwNksDH+///nH6vaP6S8jO+O/7b//M3PD5GJkj2BYwsTEeN4mY40RshiGj//+/WdgrKOMoXnJYwT7HwMzBzPz793MDAwMf/4zsSOrw6b37JW7huhiZAX1PwYGRob/zBzk6CXKYi7bTjhb5foqhjsPnuE1TFVBmoHLtgDO/3a4nDyLkUFpWhixSokCTFQ1bShYTFLiOuHiwsDAwMBgsWcPinhlz1wUfntJMnUtxgWIsYgsi2E+Reej+5zqFhMCNAtqmM9w+ZScoB4aqRpXnA6pVD24gxo9KAkBqgU1OUFJCIwGNdkGkQpG62MUgK/NRCkYPD5mYmI8j60dTAlgZmI6R03zhiYAAKgbZeNdVka9AAAAAElFTkSuQmCC'
icon80 = b'iVBORw0KGgoAAAANSUhEUgAAAFAAAABQCAYAAACOEfKtAAAABmJLR0QA/wD/AP+gvaeTAAAEU0lEQVR4nO2cXWwUVRTH/3dm1+2yXaBLU7AfgqU2sVZjTIEYm6ZoYnyqLxYV0icSNKjEGh+oIm6a+PFgiNqY+JEmJkpI7BsvPklNlQcgJgRMmzRYE9pikQUWF+ouuzPXh+1Ca2fbO5yZndn2/N56P+ae/nJuzpk2GQHfIcUr73y2B1Luk8ATAACB3wD51dcf9h4DhPQ4wAUIrwOYT3f3D3pV0/RRAC9azUvgWPJCXc/Q0C6jxKEVRfM6gPlUbZ0+hLvychI4KYGTAHIAIICXY02X+jwL0ALfZGBv75HwrQrxN4BKACkpxTPffPzmGQB49d0j201T/FSYux26UfNtPJ72Mt4CvsnA2fu0bcgLAgQ+L8gDgC8/eOu0EBiY+zEayKzd5kGIlgTsLP51sCsq08EDUshWQOh29k6lqzaM/VPXXGw+Y940ktkIAEBI8eeiBVL8AeTrRyw4+9178feLnv/w2unx+orrV+3EB0gD0M5rodsD7XuPp1R3KQscjncGjHTwhBBou5ebb5g6LmfWK66WzwIYnD9iQj5XODWZjWxeanezOVNvO0AIAPIlMxN4fjje+dTO+M85lV3KAvWNsR2QaLMfmH0ksGtf36cTOUMfAAA9kDsgJF4oxdmA2K5vjO1Avngti7JAIbVaOXeFGhs2oWpdxFZY+l9h/KJ0qSTmsuFgQM8dvDNkg8aGTXj8/nW29ly/cQsTkzMA8r+r6j7fFJG7+KYxUMKHAssLFkiEBRKx1QcuhRZ9AMH6jqLzleGrwNmzTh23JJWNnQht2VB0Pjs1AjN10ZGzHBMoQuuhVz9adH5rJI01P45h9t+MU0daEglXoOmRJ6GHQ0XX5K6cAxwSWLIrHAlXYH9PFxpqa6BpzldaTRNoqK3B/p4urFlCntM4loEqPLSlDode313KI12HiwgRFkiEBRJhgURYIBEWSIQFEilpH1hgvL8f10ZGFozFOjrQfPiw0v6jx0/g9/HFf/W34qO399qOzw6cgUQ8yUAqm2trvA7hDmUpsL2tFe1eBzEHX2EirmfgeH//orHU6KjlmNVa1cLiFa4L/H+1LUY2kVBe6yf4ChMpyyLCfeAKwvUMjHUs/kdTanQU2URiwViwuhrRlhalZ66qPtCqilq9ykVbWpQrLveBKwgWSIQFEmGBRDzpA6mvZ9wHriDK8k1kVfWBbsB94AqCBRJhgURYIBHXi0jfJ4PLL3IR7gN9jusZ2Nr8oNtHeIrrAvd0Pe32EZ7CV5gICyTCAomwQCLcBxLhDCTCfSAR7gOJ8BUmwgKJsEAiLJAICyTCAok41sbITBJG4rxTj3MVmUk69izHBJqpi8iMfe/U48oGvsJEWCARFkiEBRJRLiJSmJcg8x/MmZicASZdi8lzDE1Mqa5VzkDj8rVTgDx9byGVFafkzJUzyy/LY+sbTMNfdFfqwngDwGN2P0Lrf6QB4Jwh9YGdrw3d9DoahmEYZhXwH9lzHz2UZvOtAAAAAElFTkSuQmCC'
sg.set_global_icon(icon=icon80)
#################################################
import re
import pyperclip

# Universal numeric patterns:
# For hematology/chemistry values: 1 to 6 digits, optionally with a comma/dot and 1 to 3 decimals.
num_pattern = r"(\d{1,6}(?:[,.]\d{1,3})?)"
# For gasometry values (allows an optional negative sign):
gas_num_pattern = r"(-?\d{1,6}(?:[,.]\d{1,3})?)"


def extract_value_in(lines, label):
    """
    Searches for 'label' (case-insensitive) in the list of lines and returns the first numeric value found,
    checking the current line and up to the next 3 lines.
    """
    for i, line in enumerate(lines):
        if label.lower() in line.lower():
            m = re.search(num_pattern, line)
            if m:
                return m.group(1)
            for j in range(i + 1, min(i + 4, len(lines))):
                m = re.search(num_pattern, lines[j])
                if m:
                    return m.group(1)
    return ""


def extract_serology_result(full_text, key):
    """
    Searches full_text for a block starting with 'key' (case-insensitive) and captures up to 200 characters.
    If "não reagente" is found, returns "(-)"; if "reagente" is found (and "não reagente" is not present),
    returns "(+)".
    """
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
    """
    Searches for a line starting with 'label' (case-insensitive) and returns the first numeric value found,
    or from one of the next 3 lines.
    """
    for i, line in enumerate(lines):
        if line.lower().startswith(label.lower()):
            m = re.search(num_pattern, line)
            if m:
                return m.group(1)
            for j in range(i + 1, min(i + 4, len(lines))):
                m = re.search(num_pattern, lines[j])
                if m:
                    return m.group(1)
    return ""


def parse_lab_report_chrome(text):
    # Preprocess: Replace any occurrence of "Uréia" (or "Ureia") with "U"
    text = re.sub(r"(?i)ur[eé]ia", "U", text)

    # Split text into nonempty, stripped lines.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    full_text = " ".join(lines).lower()  # For serology searches

    # --- Extract Date and Time ---
    datetime_out = ""
    for line in lines:
        if line.startswith("Data de Coleta/Recebimento:"):
            m = re.search(r"(\d{2}/\d{2})/\d{4},\s*Hora Aproximada:\s*(\d{2}:\d{2})", line, re.IGNORECASE)
            if m:
                datetime_out = f"{m.group(1)} {m.group(2).replace(':', 'h')}"
            break

    # --- Extract Red Series (Série Vermelha) ---
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
        red_index = next(i for i, l in enumerate(lines) if "Série Vermelha" in l)
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
    hb_value = red_values.get("Hb", "")
    ht_value = red_values.get("Ht", "")
    vcm_value = red_values.get("VCM", "")
    hcm_value = red_values.get("HCM", "")
    chcm_value = red_values.get("CHCM", "")
    rdw_value = red_values.get("RDW", "")

    # --- Extract White Series (Série Branca) ---
    leuco_abs = ""
    for line in lines:
        if line.lower().startswith("leucócitos"):
            parts = re.split(r"\s+", line)
            if len(parts) >= 3:
                leuco_abs = parts[2]
            break
    # Differential percentages: Metamielócitos, Bastonetes, Segmentados (or Neutrófilos), Linfócitos.
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

    # --- Extract Platelets ---
    plaq_value = ""
    for line in lines:
        if "contagem de plaquetas" in line.lower() and re.search(r"\d", line):
            m = re.search(r"Contagem de Plaquetas\s+" + num_pattern, line, re.IGNORECASE)
            if m:
                plaq_value = m.group(1)
            break

    # --- Extract PCR ---
    pcr_value = ""
    for line in lines:
        if line.lower().startswith("proteína c reativa"):
            m = re.search(r"Prote[ií]na C Reativa\s+" + num_pattern, line, re.IGNORECASE)
            if m:
                pcr_value = m.group(1)
            break

    # --- Extract U (from replaced Ureia) ---
    u_value = ""
    for line in lines:
        if line.startswith("U ") and re.search(r"\d", line):
            m = re.search(r"U\s+" + num_pattern, line, re.IGNORECASE)
            if m:
                u_value = m.group(1)
            break

    # --- Extract Creatinina and eGFR ---
    cr_value = ""
    for line in lines:
        if line.lower().startswith("creatinina") and "mg/dl" in line.lower():
            m = re.search(r"Creatinina\s+" + num_pattern, line, re.IGNORECASE)
            if m:
                cr_value = m.group(1)
            break
    egfr_value = ""
    for line in lines:
        if line.lower().startswith("*egfr") or line.lower().startswith("egfr"):
            m = re.search(r"\*?eGFR\s+" + num_pattern, line, re.IGNORECASE)
            if m:
                egfr_value = m.group(1)
            break
    creat_field = ""
    if cr_value or egfr_value:
        if cr_value:
            creat_field = "Cr " + cr_value
        if egfr_value:
            creat_field += " eGFR " + egfr_value

    # --- Extract Potássio ---
    k_value = ""
    for line in lines:
        if line.lower().startswith("potássio") or line.lower().startswith("potassio"):
            m = re.search(r"Pot[aá]ssio\s+" + num_pattern, line, re.IGNORECASE)
            if m:
                k_value = m.group(1)
            break

    # --- Extract Sódio ---
    na_value = ""
    for line in lines:
        if line.lower().startswith("sódio") or line.lower().startswith("sodio"):
            m = re.search(r"S[oó]dio\s+" + num_pattern, line, re.IGNORECASE)
            if m:
                na_value = m.group(1)
            break

    # --- Extract Coagulation Exams and Magnesium ---
    tp_value = extract_value_in(lines, "Tempo de Protrombina")
    inr_value = extract_value_in(lines, "RNI:")
    ttpa_value = extract_value_in(lines, "Tempo de Tromboplastina Parcial Ativado")
    r_value = extract_value_in(lines, "Relação:")
    mg_value = extract_value_in(lines, "Magnésio")

    # --- Extract new chemistry exams: Fósforo (P) and Cálcio Iônico (CaI) ---
    p_value = extract_value_in(lines, "Fósforo")
    cai_value = ""
    for line in lines:
        if re.search(r"c[áa]lcio iônico", line, re.IGNORECASE):
            m = re.search(num_pattern, line)
            if m:
                cai_value = m.group(1)
            break

    # --- Build the Base Output (Hematology/Chemistry + Coagulation + Chemistry) ---
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
    # Coagulation block:
    if tp_value:
        base_fields.append("TP " + tp_value)
    if inr_value:
        base_fields.append("INR " + inr_value)
    if ttpa_value:
        base_fields.append("TTPA " + ttpa_value)
    if r_value:
        base_fields.append("R " + r_value)
    # Remaining chemistry block:
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

    # --- Extract New Exams (Liver Tests, plus Amilase and Lipase) ---
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

    # --- Extract Gasometry Exam (Venous or Arterial) ---
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
        for line in lines[gas_index + 1:]:
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

    # --- Extract Serologies ---
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

    # --- Build Final Output ---
    # Join non-empty blocks with " // " and add a trailing separator.
    blocks = [base_output, new_exams_output, gas_output, sero_output]
    final_output = " // ".join(block for block in blocks if block) + " //"
    return final_output


def programa():
    raw_text = pyperclip.paste()
    parsed_output = parse_lab_report_chrome(raw_text)
    print(parsed_output)
    pyperclip.copy(parsed_output)


if __name__ == "__main__":
    programa()

#######################################################

tecla = keyboard.add_hotkey("ctrl+z", programa)
if tecla:
    programa()


##############################################
def make_win1():
    layout = [
        [sg.Text("LabScribe", font=('Lato', 13, 'bold'), justification='center', size=(50, 1))],
        [sg.HSeparator()],
        [sg.Text("Pré-visualização (texto pronto para colar):", font=('Lato', 12), justification='center', size=(52,1))],
        [sg.Multiline(size=(72, 14), autoscroll=True, reroute_stdout=True, reroute_stderr=True, key='-OUTPUT-')],
        [sg.HSeparator()],
        [sg.Button("Instruções", font=('Lato', 10, 'bold')), sg.Button("Exames compatíveis", font=('Lato', 10, 'bold')),
         sg.Button("Sobre", font=('Lato', 10, 'bold')), sg.Button("Fechar", font=('Lato', 10, 'bold'))]
    ]
    window1 = sg.Window('LabScribe - v1.5.2', layout, location=(800,300), finalize=True)
    window1.bind("Instruções", on_instrucoes_clicked, window1)
    return window1

def on_instrucoes_clicked(event, values, window1):
    instructions = "Passo 1: abra este programa e um PDF de exame laboratorial. No PDF, desative o CAPS LOCK, aperte uma vez CTRL+A (selecionar tudo), pressione CTRL+C (copiar) e CTRL+Z (executar programa)."
    instructions += "\nPasso 2: após, cole o texto onde desejar com CTRL+V (colar)."
    instructions += "\nSempre que houver algum erro ao colar, repita o Passo 1 ou abra e feche o programa."
    instructions += "\nNota: ao deslogar e logar no Windows, é necessária a reabertura do programa."
    window1['-OUTPUT-'].update(instructions)

def make_win4():
    layout4 = [
        [sg.Text("- Hemograma completo, TTPa/R, TP/INR, U/CR (com eGFR)", font=('Lato', 10))],
        [sg.Text("- Barrigograma: TGO, TGP, GGT, FA, BT, BD, BI, AML, LIP, ALB", font=('Lato', 10))],
        [sg.Text("- Eletrólitos e outros: Na, K, Mg, CaI, P", font=('Lato', 10))],
        [sg.Text("- Gasometria arterial e venosa", font=('Lato', 10))],
        [sg.Text("- Perfil de ferro e reticulócitos", font=('Lato', 10))],
        [sg.Text("- Urina: Nit_U1, Leuco_U1, Hem_U1", font=('Lato', 10))],
        [sg.Text("- Infectologia: HMC, URC, TR Influenza, TR COVID, Dengue (IgG, IgM, NS-1)", font=('Lato', 10))]
    ]
    return sg.Window('Exames compatíveis', layout4, finalize=True)

def make_win6():
    layout6 = [
        [sg.Text("Versão 1.6")],
        [sg.Text("Última atualização: 11/02/2025")],
        [sg.Text("Changelog: adaptação para exames NAV DASA")],
        [sg.Text("##########################")],
        [sg.Text("Autor: Charles Ribas")],
        [sg.Text("- Letras - Tradução (2009 - 2012) - Universidade Nova de Lisboa")],
        [sg.Text("- Medicina (2016 - 2021) - Universidade de Sâo Paulo")],
        [sg.Text("##########################")]
    ]
    return sg.Window('Sobre', layout6, finalize=True)

window3, window4, window6 = make_win1(), None, None


while True:
    window, event, values = sg.read_all_windows()
    if event == sg.WIN_CLOSED or event == 'Fechar':
        window.close()
        if window == window3:
            window3 = None
        elif window == window4:
            window4 = None
        elif window == window1:
            break
    elif event == 'Exames compatíveis' and not window4:
        window4 = make_win4()
    elif event == 'Sobre' and not window6:
        window6 = make_win6()
    elif event == "Instruções":
        on_instrucoes_clicked(event, values, window3)

window.close()