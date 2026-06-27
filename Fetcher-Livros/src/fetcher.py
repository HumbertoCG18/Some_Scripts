#!/usr/bin/env python3
"""
Downloader da Biblioteca Astral (núcleo + CLI).

O usuário comprou acesso ao acervo (https://biblioteca-astral-tawny.vercel.app/).
Cada livro é um arquivo PDF público no Google Drive; o slug da página do livro
(/livro/<id>) é o próprio ID do arquivo no Drive.

Etapas:
  1. Busca o catálogo na rota /estante (payload RSC, público).
  2. Faz parse dos objetos de livro: {id, name, tradition, subpath, ...}.
  3. Baixa cada PDF do Drive, organizando em pastas por tradição/subpasta.

Este módulo expõe a API usada também pela GUI (gui.py):
  - load_catalog(refresh) / fetch_catalog()
  - build_targets(books, out_dir)
  - download_one(book, dest, retries)
  - Downloader  (pausar / continuar / cancelar, com callback de progresso)

Uso CLI:
  python fetcher.py                      # baixa tudo
  python fetcher.py --limit 5            # teste rápido (5 livros)
  python fetcher.py --tradition Wicca    # só uma tradição
  python fetcher.py --workers 4          # nº de downloads simultâneos
  python fetcher.py --refresh-catalog    # rebaixa o catálogo
  python fetcher.py --retry-failed       # só reprocessa o que falhou
  python fetcher.py --list-traditions    # lista tradições e contagens
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

# Console em UTF-8 (evita UnicodeEncodeError no Windows).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import requests  # noqa: E402

BASE_URL = "https://biblioteca-astral-tawny.vercel.app"
ESTANTE_URL = f"{BASE_URL}/estante"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Diretório base p/ dados graváveis. No .exe (PyInstaller) usa a pasta do executável;
# em script, a raiz do repositório (src/..). Downloads vão pra Documentos quando empacotado.
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    OUT_DIR_DEFAULT = Path.home() / "Documents" / "Biblioteca Astral"
else:
    APP_DIR = Path(__file__).resolve().parent.parent  # raiz do repo
    OUT_DIR_DEFAULT = APP_DIR / "downloads"

ROOT = APP_DIR
CATALOG_PATH = APP_DIR / "catalog.json"
FAILED_PATH = APP_DIR / "failed.json"

ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# caracteres invisíveis (ZWSP/ZWJ/marcas direcionais/BOM) que aparecem em alguns títulos
ZWJ = re.compile("[​-‏‪-‮⁠﻿]")


# --------------------------------------------------------------------------- #
# Catálogo
# --------------------------------------------------------------------------- #
def fetch_catalog() -> list[dict]:
    """Baixa /estante (RSC) e extrai todos os objetos de livro."""
    req = urllib.request.Request(ESTANTE_URL, headers={"RSC": "1", "User-Agent": UA})
    data = urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")

    books: dict[str, dict] = {}
    for m in re.finditer(r'\{"id":"', data):
        start = m.start()
        depth = 0
        i = start
        instr = False
        esc = False
        obj = None
        while i < len(data):
            c = data[i]
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = not instr
            elif not instr:
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        obj = data[start:i + 1]
                        break
            i += 1
        if obj is None:
            continue
        try:
            o = json.loads(obj)
        except Exception:
            continue
        # Objeto de livro tem nome e tradição; ignora nós de categoria.
        if isinstance(o, dict) and "name" in o and "tradition" in o and "id" in o:
            books[o["id"]] = {
                "id": o["id"],
                "name": o.get("name") or f"{o['id']}.pdf",
                "tradition": o.get("tradition") or "Sem tradição",
                "subpath": o.get("subpath") or "",
            }
    return list(books.values())


def load_catalog(refresh: bool = False, log: Callable[[str], None] = print) -> list[dict]:
    if CATALOG_PATH.exists() and not refresh:
        books = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        log(f"Catálogo (cache): {len(books)} livros — {CATALOG_PATH.name}")
        return books
    log("Buscando catálogo no site...")
    books = fetch_catalog()
    CATALOG_PATH.write_text(json.dumps(books, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Catálogo salvo: {len(books)} livros — {CATALOG_PATH.name}")
    return books


def tradition_counts(books: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for b in books:
        counts[b["tradition"]] = counts.get(b["tradition"], 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


# --------------------------------------------------------------------------- #
# Caminhos de saída
# --------------------------------------------------------------------------- #
def clean(part: str, maxlen: int = 120) -> str:
    part = ZWJ.sub("", part)
    part = ILLEGAL.sub("_", part)
    part = part.strip().strip(".").strip()
    if len(part) > maxlen:
        part = part[:maxlen].rstrip()
    return part or "_"


def build_targets(books: list[dict], out_dir: Path) -> dict[str, Path]:
    """Mapeia id -> caminho de destino, resolvendo nomes duplicados na mesma pasta."""
    by_folder: dict[Path, list[dict]] = {}
    for b in books:
        folder = out_dir / clean(b["tradition"])
        if b["subpath"]:
            folder = folder / clean(b["subpath"])
        by_folder.setdefault(folder, []).append(b)

    targets: dict[str, Path] = {}
    for folder, group in by_folder.items():
        base: dict[str, str] = {}
        counts: dict[str, int] = {}
        for b in group:
            name = clean(b["name"])
            if not name.lower().endswith(".pdf"):
                name += ".pdf"
            base[b["id"]] = name
            counts[name] = counts.get(name, 0) + 1
        for b in group:
            name = base[b["id"]]
            if counts[name] > 1:  # nomes iguais na mesma pasta -> sufixo do id
                name = f"{name[:-4]}-{b['id'][:8]}.pdf"
            targets[b["id"]] = folder / name
    return targets


# --------------------------------------------------------------------------- #
# Download de um arquivo (direto do Google Drive, sem gdown)
# --------------------------------------------------------------------------- #
DRIVE_DL_URL = "https://drive.usercontent.google.com/download"
_local = threading.local()


class QuotaError(RuntimeError):
    """Limite temporário de quota do Drive — não adianta repetir agora."""


def _session() -> requests.Session:
    """Uma Session por thread (pool de conexões, cookies do fluxo de confirmação)."""
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers["User-Agent"] = UA
        _local.s = s
    return s


def _drive_download(file_id: str, tmp: Path, should_stop: Callable[[], bool] | None = None) -> bool:
    """
    Baixa um arquivo público do Drive para `tmp`.
    Lida com a página de confirmação de arquivos grandes (>~100 MB).
    Retorna True em sucesso; False se cancelado. Lança em erro real.
    """
    s = _session()
    params = {"id": file_id, "export": "download"}
    r = s.get(DRIVE_DL_URL, params=params, stream=True, timeout=60)
    r.raise_for_status()

    ctype = r.headers.get("Content-Type", "")
    if "text/html" in ctype:
        html = r.content.decode("utf-8", "replace")
        form = dict(re.findall(r'name="([^"]+)"\s+value="([^"]*)"', html))
        if "confirm" in form:
            # Arquivo grande: reenvia com o token de confirmação do formulário.
            r = s.get(DRIVE_DL_URL, params=form, stream=True, timeout=60)
            r.raise_for_status()
            if "text/html" in r.headers.get("Content-Type", ""):
                raise QuotaError("Drive retornou HTML após confirmação (limite de quota)")
        elif "uc-error-caption" in html or "many users have" in html or "download file" in html:
            raise QuotaError("limite temporário de quota do Drive (muitos acessos) — reprocesse depois com --retry-failed")
        else:
            raise RuntimeError("página HTML inesperada (arquivo sem permissão pública ou removido?)")

    with open(tmp, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 16):
            if should_stop and should_stop():
                return False
            if chunk:
                f.write(chunk)
    return True


def download_one(book: dict, dest: Path, retries: int = 3,
                 should_stop: Callable[[], bool] | None = None) -> tuple[str, str, str]:
    """
    Retorna (id, status, detalhe).
    status:
      ok    -> baixado
      skip  -> já existia
      cancel-> cancelado
      retry -> falha transitória (quota do Drive, rede): vale tentar mais tarde
      fail  -> falha permanente (sem permissão / removido / vazio)
    """
    if dest.exists() and dest.stat().st_size > 0:
        return (book["id"], "skip", str(dest))

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")

    last = ""
    kind = "fail"
    for attempt in range(1, retries + 1):
        if should_stop and should_stop():
            break
        try:
            if tmp.exists():
                tmp.unlink()
            ok = _drive_download(book["id"], tmp, should_stop)
            if not ok:  # cancelado no meio
                if tmp.exists():
                    tmp.unlink()
                return (book["id"], "cancel", "")
            if tmp.stat().st_size > 0:
                tmp.replace(dest)
                return (book["id"], "ok", str(dest))
            last, kind = "arquivo vazio", "fail"
            break
        except QuotaError as e:  # quota: não recupera em segundos -> deixa pro loop
            last, kind = str(e), "retry"
            break
        except requests.RequestException as e:  # rede: transitória
            last, kind = f"{type(e).__name__}: {e}", "retry"
        except Exception as e:  # sem permissão / HTML inesperado: permanente
            last, kind = f"{type(e).__name__}: {e}", "fail"
            break
        time.sleep(min(2 ** attempt, 15))
    if tmp.exists():
        try:
            tmp.unlink()
        except Exception:
            pass
    return (book["id"], kind, last)


# --------------------------------------------------------------------------- #
# Orquestrador com pausar / continuar / cancelar
# --------------------------------------------------------------------------- #
class Downloader:
    """
    Baixa uma lista de livros com pool de threads, emitindo eventos de progresso.

    Eventos passados a on_event (dict):
      {"type":"progress", done, total, ok, skip, fail, name, status, detail}
      {"type":"finished", done, total, ok, skip, fail, cancelled}

    Controle:
      start()  -> roda em thread de fundo (para GUI)
      run()    -> roda bloqueando (para CLI)
      pause() / resume() / cancel()

    Pausar/cancelar agem entre arquivos: downloads já em andamento terminam
    (o gdown não é interrompível no meio de um arquivo).
    """

    def __init__(
        self,
        books: list[dict],
        targets: dict[str, Path],
        workers: int = 4,
        retries: int = 3,
        on_event: Callable[[dict], None] | None = None,
        delay: float = 0.0,
    ):
        self.books = books
        self.targets = targets
        self.workers = max(1, workers)
        self.retries = retries
        self.on_event = on_event or (lambda e: None)
        self.delay = max(0.0, delay)  # ritmo: pausa (com jitter) antes de cada download

        self._pause = threading.Event()
        self._pause.set()  # set = rodando; clear = pausado
        self._cancel = threading.Event()
        self._lock = threading.Lock()

        self.total = len(books)
        self.done = 0
        self.ok = 0
        self.skip = 0
        self.fail = 0          # permanentes
        self.retry = 0         # transitórias (quota/rede)
        self.permanent_ids: list[str] = []
        self.retry_ids: list[str] = []
        self._thread: threading.Thread | None = None

    # -- controle -------------------------------------------------------- #
    def start(self) -> None:
        self._thread = threading.Thread(target=self.run, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        self._pause.clear()

    def resume(self) -> None:
        self._pause.set()

    def cancel(self) -> None:
        self._cancel.set()
        self._pause.set()  # libera quem estiver esperando em pausa

    def is_paused(self) -> bool:
        return not self._pause.is_set()

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    # -- execução -------------------------------------------------------- #
    def _interruptible_sleep(self, seconds: float) -> None:
        end = time.time() + seconds
        while time.time() < end and not self._cancel.is_set():
            time.sleep(min(0.1, max(0.0, end - time.time())))

    def _worker(self, book: dict):
        if self._cancel.is_set():
            return None
        while not self._pause.is_set() and not self._cancel.is_set():
            time.sleep(0.1)
        if self._cancel.is_set():
            return None
        dest = self.targets[book["id"]]
        already = dest.exists() and dest.stat().st_size > 0
        if self.delay > 0 and not already:  # espaça só downloads reais (não skips)
            self._interruptible_sleep(random.uniform(self.delay * 0.5, self.delay * 1.5))
            if self._cancel.is_set():
                return None
        return download_one(book, dest, self.retries, should_stop=self._cancel.is_set)

    def run(self) -> None:
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            futs = {ex.submit(self._worker, b): b for b in self.books}
            for fut in as_completed(futs):
                b = futs[fut]
                try:
                    res = fut.result()
                except Exception as e:
                    res = (b["id"], "fail", f"{type(e).__name__}: {e}")
                if res is None:  # cancelado antes de começar
                    continue
                bid, status, detail = res
                if status == "cancel":  # cancelado no meio do arquivo
                    continue
                with self._lock:
                    self.done += 1
                    if status == "ok":
                        self.ok += 1
                    elif status == "skip":
                        self.skip += 1
                    elif status == "retry":
                        self.retry += 1
                        self.retry_ids.append(bid)
                    else:
                        self.fail += 1
                        self.permanent_ids.append(bid)
                self.on_event({
                    "type": "progress",
                    "done": self.done, "total": self.total,
                    "ok": self.ok, "skip": self.skip,
                    "fail": self.fail, "retry": self.retry,
                    "name": b["name"], "status": status, "detail": detail,
                })

        try:
            FAILED_PATH.write_text(
                json.dumps(self.retry_ids + self.permanent_ids, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass
        self.on_event({
            "type": "finished",
            "done": self.done, "total": self.total,
            "ok": self.ok, "skip": self.skip,
            "fail": self.fail, "retry": self.retry,
            "cancelled": self._cancel.is_set(),
        })


# --------------------------------------------------------------------------- #
# Loop "até concluir" — pensado para rodar a noite inteira sem bater quota
# --------------------------------------------------------------------------- #
def run_until_done(
    books: list[dict],
    out_dir: Path,
    *,
    workers: int = 3,
    retries: int = 3,
    delay: float = 1.0,
    cooldown_min: float = 30.0,
    max_rounds: int = 50,
    on_event: Callable[[dict], None] | None = None,
    on_status: Callable[[str], None] | None = None,
    cancel_event: threading.Event | None = None,
    register: Callable[["Downloader"], None] | None = None,
) -> dict:
    """
    Repete passadas até baixar tudo o que dá. Cada passada baixa só o que falta
    (pula o que já existe). Falhas de quota/rede entram numa fila e são tentadas
    de novo após um cooldown — a janela de quota do Drive reseta com o tempo,
    então deixando rodar a noite o acervo inteiro tende a completar.

    Arquivos com falha permanente (sem permissão / removidos) são marcados e
    deixam de ser tentados, para o loop poder terminar.
    """
    on_status = on_status or (lambda m: None)
    targets = build_targets(books, out_dir)  # nomes estáveis entre passadas
    permanent: set[str] = set()

    def still_missing(b: dict) -> bool:
        p = targets[b["id"]]
        return not (p.exists() and p.stat().st_size > 0)

    for rnd in range(1, max_rounds + 1):
        if cancel_event and cancel_event.is_set():
            break
        pending = [b for b in books if b["id"] not in permanent and still_missing(b)]
        if not pending:
            on_status(f"Tudo baixado em {rnd - 1} passada(s).")
            break

        on_status(f"Passada {rnd}/{max_rounds}: {len(pending)} livros faltando.")
        dl = Downloader(
            pending,
            {b["id"]: targets[b["id"]] for b in pending},
            workers=workers, retries=retries, on_event=on_event, delay=delay,
        )
        if register:
            register(dl)
        dl.run()
        permanent |= set(dl.permanent_ids)

        if cancel_event and cancel_event.is_set():
            on_status("Cancelado.")
            break
        if not dl.retry_ids:
            # nada mais transitório falhando; o que sobrou é permanente
            break

        if rnd < max_rounds:
            mins = cooldown_min
            on_status(f"{len(dl.retry_ids)} com quota/rede — aguardando {mins:.0f} min até a próxima passada.")
            end = time.time() + mins * 60
            while time.time() < end:
                if cancel_event and cancel_event.is_set():
                    break
                time.sleep(1)

    remaining = [b["id"] for b in books if still_missing(b)]
    summary = {
        "baixados": sum(1 for b in books if not still_missing(b)),
        "faltando": len(remaining),
        "permanentes": len(permanent),
        "restantes_ids": remaining,
    }
    on_status(
        f"Fim do loop: {summary['baixados']} no disco, "
        f"{summary['faltando']} faltando ({summary['permanentes']} permanentes)."
    )
    return summary


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def select_books(books: list[dict], tradition: str = "", limit: int = 0,
                 retry_failed: bool = False) -> list[dict]:
    if retry_failed and FAILED_PATH.exists():
        failed_ids = set(json.loads(FAILED_PATH.read_text(encoding="utf-8")))
        books = [b for b in books if b["id"] in failed_ids]
    if tradition:
        q = tradition.lower()
        books = [b for b in books if q in b["tradition"].lower()]
    if limit > 0:
        books = books[:limit]
    return books


def main() -> int:
    ap = argparse.ArgumentParser(description="Downloader da Biblioteca Astral")
    ap.add_argument("--out", type=Path, default=OUT_DIR_DEFAULT, help="pasta de saída")
    ap.add_argument("--limit", type=int, default=0, help="baixa só os N primeiros (teste)")
    ap.add_argument("--tradition", default="", help="filtra por tradição (substring)")
    ap.add_argument("--workers", type=int, default=4, help="downloads simultâneos")
    ap.add_argument("--retries", type=int, default=3, help="tentativas por arquivo")
    ap.add_argument("--delay", type=float, default=0.0,
                    help="pausa (s, com jitter) antes de cada download — ritmo educado anti-quota")
    ap.add_argument("--loop", action="store_true",
                    help="modo noturno: repete passadas até concluir, com cooldown entre elas")
    ap.add_argument("--cooldown", type=float, default=30.0,
                    help="minutos de espera entre passadas no --loop (padrão 30)")
    ap.add_argument("--max-rounds", type=int, default=50, help="máx. de passadas no --loop")
    ap.add_argument("--refresh-catalog", action="store_true", help="rebaixa o catálogo")
    ap.add_argument("--retry-failed", action="store_true", help="só reprocessa failed.json")
    ap.add_argument("--list-traditions", action="store_true", help="lista tradições e sai")
    args = ap.parse_args()

    books = load_catalog(args.refresh_catalog)

    if args.list_traditions:
        for t, n in tradition_counts(books).items():
            print(f"{n:5d}  {t}")
        print(f"\nTotal: {len(books)} livros em {len(tradition_counts(books))} tradições")
        return 0

    books = select_books(books, args.tradition, args.limit, args.retry_failed)
    if not books:
        print("Nada para baixar.")
        return 0

    def on_event(e: dict) -> None:
        if e["type"] == "progress":
            tag = {"ok": "OK  ", "skip": "SKIP", "fail": "FAIL", "retry": "WAIT"}[e["status"]]
            line = f"[{e['done']}/{e['total']}] {tag} {e['name'][:60]}"
            if e["status"] in ("fail", "retry"):
                line += f"  -> {e['detail'][:80]}"
            print(line)
        elif e["type"] == "finished":
            extra = f", {e.get('retry', 0)} p/ tentar de novo" if e.get("retry") else ""
            print(f"\nPassada: {e['ok']} baixados, {e['skip']} já existiam, "
                  f"{e['fail']} permanentes{extra}.")

    if args.loop:
        # modo noturno: workers e delay conservadores por padrão
        workers = args.workers if args.workers != 4 else 3
        delay = args.delay if args.delay > 0 else 1.0
        print(f"\nModo noturno -> {args.out}  (workers={workers}, delay~{delay}s, "
              f"cooldown={args.cooldown}min)\n")
        summary = run_until_done(
            books, args.out, workers=workers, retries=args.retries, delay=delay,
            cooldown_min=args.cooldown, max_rounds=args.max_rounds,
            on_event=on_event, on_status=lambda m: print(f"  · {m}"),
        )
        return 0 if summary["faltando"] == 0 else 1

    targets = build_targets(books, args.out)
    print(f"\nIniciando: {len(books)} livros -> {args.out}  "
          f"({args.workers} threads, delay~{args.delay}s)\n")
    dl = Downloader(books, targets, args.workers, args.retries, on_event, delay=args.delay)
    dl.run()
    if dl.fail or dl.retry:
        print(f"IDs com falha em {FAILED_PATH.name}. Reprocesse:  python fetcher.py --retry-failed")
        print("Dica: para baixar tudo sem babá, use o modo noturno:  python fetcher.py --loop")
    return 0 if (dl.fail == 0 and dl.retry == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
