import tabula
import pandas as pd

# Função para extrair a coluna 'Nome' do PDF
def extrair_nomes_do_pdf(nome_arquivo):
    try:
        dfs = tabula.read_pdf(nome_arquivo, pages='all', encoding='utf-8')
    except Exception as e:
        print(f"Erro ao ler {nome_arquivo}: {e}")
        return pd.Series(dtype=str)
    if isinstance(dfs, list):
        df = pd.concat(dfs, ignore_index=True)
    else:
        df = dfs
    if 'Nome' in df.columns:
        nomes = df['Nome']
    else:
        colunas_possiveis = [col for col in df.columns if 'Nome' in col]
        if colunas_possiveis:
            nomes = df[colunas_possiveis[0]]
        else:
            print(f"Coluna 'Nome' não encontrada em {nome_arquivo}")
            return pd.Series(dtype=str)
    nomes = nomes.astype(str).str.strip()
    nomes = nomes.dropna()
    nomes = nomes[nomes != '']
    nomes = nomes.str.upper()
    return nomes


# Extrai os nomes dos PDFs
nomes1 = extrair_nomes_do_pdf("Tabela1.pdf")
nomes2 = extrair_nomes_do_pdf("Tabela2_Pen.pdf")

# Converte as listas de nomes em conjuntos para comparação
set1 = set(nomes1)
set2 = set(nomes2)

# Nomes na lista 1 que faltam na lista 2
faltando_na_lista2 = set1 - set2

# Nomes na lista 2 que faltam na lista 1
faltando_na_lista1 = set2 - set1

# Escreve os nomes faltantes no arquivo TXT
with open('nomes_faltantes.txt', 'w', encoding='utf-8') as f:
    f.write('Nomes no arquivo Tabela1 que faltam na Tabela2_Pen:\n')
    for nome in sorted(faltando_na_lista2):
        f.write(nome + '\n')
    f.write('\nNomes no arquivo Tabela2_Pen que faltam no arquivo Tabela1:\n')
    for nome in sorted(faltando_na_lista1):
        f.write(nome + '\n')
