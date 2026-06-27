# Fetcher — Biblioteca Astral

Baixa em massa os PDFs do acervo da [Biblioteca Astral](https://biblioteca-astral-tawny.vercel.app/)
(acesso comprado pelo usuário), onde cada livro é um arquivo público no Google Drive.

Tem **GUI** (`src/gui.py`) e **CLI** (`src/fetcher.py`).

## Estrutura

```
Biblioteca Astral.exe   executável pronto (versionado na raiz)
Instalar.bat            instala + cria atalho na Área de Trabalho
Desinstalar.bat         remove o programa (mantém os livros baixados)
src/                    fetcher.py (núcleo + CLI), gui.py (Tkinter), main.py (instância única)
assets/                 book.ico (ícone, usado só na compilação)
scripts/                make_icon.py (gera o ícone), build.ps1 (recompila o .exe)
```

## Instalação para quem não tem Python (usuário final)

1. Baixe a pasta do projeto (ou só estes 3: `Biblioteca Astral.exe`,
   `Instalar.bat`, `Desinstalar.bat` — mantenha-os juntos).
2. Dê dois cliques em **`Instalar.bat`**.
   - Se aparecer "Windows protegeu o computador": **Mais informações → Executar assim mesmo**
     (aviso normal para apps sem assinatura paga).
3. Pronto: atalho **Biblioteca Astral** na Área de Trabalho. Não precisa de Python.

Para remover: dois cliques em **`Desinstalar.bat`** (ou em "Adicionar ou remover programas").
Os livros já baixados (Documentos\Biblioteca Astral) **não** são apagados.

## Como funciona

1. A rota `/estante` devolve um payload RSC (público) com o catálogo inteiro:
   cada livro é `{id, name, tradition, subpath}`, onde `id` é o ID do arquivo no Google Drive.
2. Os PDFs são baixados direto do Drive
   (`https://drive.usercontent.google.com/download?id=<id>&export=download`),
   organizados em pastas `downloads/<tradição>/<subpasta>/`.

Sem login: catálogo e arquivos são públicos.

## Instalação

```bash
pip install -r requirements.txt
```

(única dependência: `requests`)

## GUI

```bash
python src/main.py        # (ou: python src/gui.py)
```

- escolher a pasta de destino (botão **Procurar...**)
- filtrar por tradição
- barra de progresso + log em tempo real
- **Pausar / Continuar / Cancelar**
- **Atualizar catálogo**
- **Modo noturno**: repete passadas com cooldown até baixar tudo (contorna a quota)
- **Delay**: pausa com jitter entre downloads (ritmo educado anti-quota)

## Rodar a noite inteira sem bater quota

O Google Drive limita downloads anônimos por arquivo/IP ("muitos acessos recentes").
Não dá pra **eliminar** o limite, mas o **modo noturno** faz o acervo inteiro
completar sozinho:

- baixa em ritmo educado (poucos workers + `delay` com jitter) → dispara menos o limite;
- o que bater quota entra numa fila e é re-tentado após um **cooldown**;
- a janela de quota do Drive reseta com o tempo, então deixando rodar a noite tudo converge;
- falhas permanentes (sem permissão / removidos) são marcadas e não travam o loop.

Na GUI: marque **Modo noturno**, ajuste o cooldown e clique **Iniciar**.

Pela CLI:

```bash
python src/fetcher.py --loop                          # noturno, padrões seguros
python src/fetcher.py --loop --cooldown 45 --workers 3 --delay 1.5
```

## CLI

```bash
python src/fetcher.py                      # baixa todos os ~2304 livros
python src/fetcher.py --loop               # modo noturno: repete até concluir
python src/fetcher.py --limit 5            # teste rápido (5 livros)
python src/fetcher.py --tradition Wicca    # só uma tradição (substring)
python src/fetcher.py --workers 6          # nº de downloads simultâneos (padrão 4)
python src/fetcher.py --delay 1.5          # pausa entre downloads (anti-quota)
python src/fetcher.py --cooldown 45        # min de espera entre passadas (com --loop)
python src/fetcher.py --list-traditions    # lista tradições e contagens
python src/fetcher.py --refresh-catalog    # rebaixa o catálogo do site
python src/fetcher.py --retry-failed       # reprocessa só o que falhou
python src/fetcher.py --out D:/Livros      # pasta de saída custom
```

## Recursos

- **Retomada**: arquivos já baixados são pulados — pode interromper e rodar de novo.
- **Pausar/Cancelar**: pausar age entre arquivos (os downloads em andamento terminam);
  cancelar interrompe inclusive no meio de um arquivo.
- **Retentativas**: 3 tentativas por arquivo com backoff.
- **Falhas registradas**: IDs que falharam vão para `failed.json`; use `--retry-failed`.
- **Nomes seguros**: caracteres inválidos no Windows são saneados; nomes duplicados na
  mesma pasta ganham sufixo do ID.
- **Cache do catálogo**: salvo em `catalog.json`.
- **Instância única**: abrir o app uma 2ª vez foca a janela já aberta e avisa
  "o programa já está aberto" (mutex nomeado do Windows).
- **Arquivos grandes** (>100 MB): a página de confirmação de "vírus" do Drive é tratada.

## Recompilar o executável (.exe)

```powershell
pip install pyinstaller pillow requests
.\scripts\build.ps1
```

Regera `Biblioteca Astral.exe` na raiz (com o ícone). `Instalar.bat` e `Desinstalar.bat`
não mudam — continuam funcionando ao lado do exe.

## Arquivos

| arquivo | papel |
|---|---|
| `src/fetcher.py` | núcleo (catálogo, download, `Downloader`) + CLI |
| `src/gui.py` | interface Tkinter |
| `src/main.py` | entrada (instância única) |
| `scripts/build.ps1` | gera o `.exe` e a pasta `release/` |
| `scripts/make_icon.py` | gera `assets/book.ico` |
| `catalog.json` / `failed.json` | cache / falhas (gerados, na raiz) |
| `downloads/` | PDFs baixados (gerado) |
