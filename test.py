import re
import pyperclip
import keyboard

print("***** HSM Nápoles - Lab - Versão 0.4 *****")
print("Exames compatíveis:")
print("Hb, Ht, Leuco, Neut, Linf, Plaq, TTPa, INR, VHS, U/CR, Na/K, PCR, Tropo, Nit_U1, Leuco_U1, Hem_U1")
print("Kit dor abdominal: TGO, TGP, GGT, FA, BT, BD, BI, AMILASE")
print("Gasometria arterial")
print("*********")
print("Instruções:")
print("Passo 1: abra este programa e um PDF de exame laboratorial. Aperte uma vez CTRL+A (selecionar tudo) e *duas vezes* CTRL+C (copiar).")
print("Passo 2: Após, cole o texto onde deseja com CTRL+V (colar)")
print("Nota: apertar CTRL+C diversas vezes pode gerar erros.")
print("Sempre que houver algum erro ao colar, repita desde o Passo 1")

def programa():

    b = pyperclip.paste()
    b = str(b)
    a = b.replace("   ", " ") \
        .replace("  ", " ") \
        .replace(" : ", "") \
        .replace('\r\n', "") \
        .replace("POTASSIO", "K") \
        .replace("SÓDIO", "Na") \
        .replace("Valor de Referência:Resultado:", "") \
        .replace("UREIA", "Ur") \
        .replace("CREATININA", "Cr") \
        .replace("FAELLA", "ervilha") \
        .replace("PROTEINA C REATIVA", "PCR") \
        .replace("Hemoglobina", "de Hb") \
        .replace("Hematócrito", "de Ht") \
        .replace("Leucócitos", "de Leuco") \
        .replace("Neutrófilos", "de Neut") \
        .replace("Linfócitos", "de Linf") \
        .replace("/mm³ ", "") \
        .replace("Valor de Referência:", "") \
        .replace("Resultado", "") \
        .replace("milhões", "") \
        .replace("g/dL ", "") \
        .replace("% ", "") \
        .replace("Urina", "U1") \
        .replace("CONTAGEM DE PLAQUETAS", "de Plaq") \
        .replace("Nitrito", "Nit_U1") \
        .replace("Negativo", "(-)") \
        .replace("NEGATIVO", "") \
        .replace("Leucocitos+++", "Leuco_U1+++") \
        .replace("Leucocitos++", "Leuco_U1++") \
        .replace("Leucocitos+", "Leuco_U1(+)") \
        .replace("Leucócitos+++", "Leuco_U1+++") \
        .replace("Leucócitos++", "Leuco_U1++") \
        .replace("Leucócitos+", "Leuco_U1(+)") \
        .replace("de Leuco+++", "Leuco_U1+++") \
        .replace("de Leuco++", "Leuco_U1++") \
        .replace("de Leuco+", "Leuco_U1(+)") \
        .replace("de Leuco(-)", "Leuco_U1(-)") \
        .replace("Hemacias", "Hem_U1") \
        .replace("Hemácias(", "Hem_U1(") \
        .replace("Hemacias+++", "Hem_U1+++") \
        .replace("Hemacias++", "Hem_U1++") \
        .replace("Hemacias+", "Hem_U1(+)") \
        .replace("Hemácias+++", "Hem_U1+++") \
        .replace("Hemácias++", "Hem_U1++") \
        .replace("Hemácias+", "Hem_U1(+)") \
        .replace("Troponinas", "") \
        .replace("Tempo Tromboplastina Parcial Ativada", "TTPa ") \
        .replace("INR", "INR ") \
        .replace("Nasoph", "") \
        .replace("PCR for", "") \
        .replace("SARS-CoV-2 TESTE RÁPIDO DE ANTÍGENO (COVID-19)", "TR COVID:") \
        .replace("Não reagente", "NR") \
        .replace("Reagente", "(+)") \
        .replace("FOSFATASE ALCALINA", "FA") \
        .replace("GAMA GLUTAMIL TRANSFERASE", "GGT") \
        .replace("BILIRRUBINA TOTAIS E FRAÇÕES", "ervilha ") \
        .replace("pH:", "GA_pH:") \
        .replace("pO2:", "GA_pO2:") \
        .replace("pCO2:", "GA_pCO2:") \
        .replace(" 98 %de Hb", "ervilha") \
        .replace(" g/dLde Ht", "ervilha") \
        .replace("r da de Hb", "ervilha") \
        .replace("e do de Ht", "ervilha") \
        .replace("BILIDAD", "ervilha") \
        .replace("BIANOSI", "ervilha") \
        .replace("HCO3:", "GA_HCO3:") \
        .replace("BE:", "GA_BE:") \
        .replace("Saturação O2:", "GA_SATO2:") \
        .replace("Bilirrubina Total", "BT ") \
        .replace("Bilirrubina Direta", "BD ") \
        .replace("Bilirrubina Indireta:", "BI") \
        .replace("AERÓBIA", "ERVILHA") \
        .replace("TROPONINA I DE ALTA SENSIBILIDADE", "Tropo")
    z = re.findall('K..,..\
|Na....\
|Cr..[.]..\
|Ur\s\d\d\
|PCR\s....\
|.....de.Hb\
|.....de.Ht\
|\d\d\d\d\d\sde\sLeuco\
|\d\d\d\d\sde\sLeuco\
|\d\d\d\d\sde\sNeut\
|\d\d\d\d\d\sde\sNeut\
|\d\d\d\sde\sLinf\
|\d\d\d\d\sde\sLinf\
|\d\d\d\d\d\sde\sLinf\
|\d\d\d\d\d\d\sde\sPlaq\
|\d\d\d\d\d\sde\sPlaq\
|\d\d\d\d\sde\sPlaq\
|\d\d\d\sde\sPlaq\
|\d\d\d\d\d\d\d\sde\sPlaq\
|VHS...\
|Nit_U1....\
|Leuco_U1....\
|Tropo.....\
|INR.....\
|TTPa.....\
|TR.COVID:...\
|TGO.AST.....\
|GA_pH......\
|GA_pO2.......\
|GA_pCO2......\
|GA_HCO3......\
|GA_BE......\
|TGP.ALT.....\
|GA_SATO2....\
|FA....\
|GGT....\
|BT.....\
|BD.....\
|BI.....\
|AMILASE....\
|Hem_U1....', a)
    #print(a)
    #print(z)
    x = str(z)
    print("*********")
    print("Pré-visualização:")
    print(x)
    pyperclip.copy(x)
    pyperclip.copy(x)
    print("Texto editado copiado. Agora, cole no local desejado")
    print("*********")
    print("Por Charles Ribas")
    print("Para notificação de erros: ribas.cha@gmail.com")
    print("*********")
    print("Se desejar copiar algo novamente, pressione CTRL+C. Aperte qualquer tecla e ENTER para sair. ")
    #print("Pressione qualquer botão e Enter para sair")

keyboard.add_hotkey("ctrl+c", lambda: programa())
keyboard.add_hotkey('esc', lambda: exit())
input()

#t = input()
#if t:
#    exit()
