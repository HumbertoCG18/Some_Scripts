# Fetcher — Biblioteca Astral

Baixa em massa os PDFs do acervo da [Biblioteca Astral](https://biblioteca-astral-tawny.vercel.app/)
(acesso comprado pelo usuário), onde cada livro é um arquivo público no Google Drive.

Tem **GUI** (`src/gui.py`) e **CLI** (`src/fetcher.py`).

## Estrutura

```
Instalar.bat     instala Python+deps se faltar, compila o exe e cria o atalho
Desinstalar.bat  remove o programa e os artefatos (mantém os livros baixados)
src/             fetcher.py (núcleo + CLI), gui.py (Tkinter), main.py (instância única)
assets/          book.ico (ícone)
scripts/         build.ps1 (compila o exe), make_icon.py (gera o ícone)
```

O `.exe` **não** é versionado — ele é gerado pelo `Instalar.bat` na hora da instalação.

## Instalação (usuário final)

1. Baixe **a pasta inteira do projeto** (precisa do código-fonte para compilar) e
   mantenha tudo junto.
2. Dê dois cliques em **`Instalar.bat`**. Ele, automaticamente:
   - instala o **Python** via `winget` se não houver (Windows 10/11);
   - instala as dependências (`requirements.txt` + PyInstaller);
   - **compila** o `Biblioteca Astral.exe`;
   - instala em `%LOCALAPPDATA%\Programs\Biblioteca Astral` e cria o atalho na
     **Área de Trabalho**;
   - limpa os arquivos temporários de compilação.
   - Se o SmartScreen avisar, é só seguir — o app não mexe no sistema.
3. Pronto: abra pelo atalho **Biblioteca Astral**.

A primeira instalação demora alguns minutos (baixa Python/deps e compila).

Para remover: dois cliques em **`Desinstalar.bat`** (ou "Adicionar ou remover programas").
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

## Compilar o exe manualmente (opcional)

O `Instalar.bat` já faz isso sozinho. Para compilar à mão:

```powershell
pip install pyinstaller pillow requests
.\scripts\build.ps1            # ou -SkipIcon se assets\book.ico já existe
```

Gera `Biblioteca Astral.exe` na raiz.

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
