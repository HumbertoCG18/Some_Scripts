#!/usr/bin/env python3
"""
GUI da Biblioteca Astral Downloader.

Recursos:
  - escolher a pasta de destino
  - filtrar por tradição
  - barra de progresso
  - pausar / continuar / cancelar
  - log em tempo real

Roda sobre o núcleo em fetcher.py. Sem dependências extras (Tkinter é stdlib).

Iniciar:
  python gui.py
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import fetcher


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Biblioteca Astral — Downloader")
        root.geometry("760x560")
        root.minsize(640, 480)

        self.events: queue.Queue = queue.Queue()
        self.books: list[dict] = []
        self.dl: fetcher.Downloader | None = None

        self.out_var = tk.StringVar(value=str(fetcher.OUT_DIR_DEFAULT))
        self.trad_var = tk.StringVar(value="Todas as tradições")
        self.workers_var = tk.IntVar(value=4)
        self.delay_var = tk.DoubleVar(value=0.0)
        self.night_var = tk.BooleanVar(value=False)
        self.cooldown_var = tk.DoubleVar(value=30.0)
        self.status_var = tk.StringVar(value="Carregando catálogo...")
        self._cancel_event = threading.Event()
        self.loop_mode = False

        self._build_ui()
        self._set_state("loading")
        self._load_catalog_async(refresh=False)
        self.root.after(100, self._drain)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}
        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        # Pasta de destino
        ttk.Label(frm, text="Pasta de destino:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.out_var).grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(frm, text="Procurar...", command=self._pick_folder).grid(row=0, column=2, **pad)

        # Tradição
        ttk.Label(frm, text="Tradição:").grid(row=1, column=0, sticky="w", **pad)
        self.trad_combo = ttk.Combobox(frm, textvariable=self.trad_var, state="readonly")
        self.trad_combo.grid(row=1, column=1, sticky="ew", **pad)
        ttk.Button(frm, text="Atualizar catálogo",
                   command=lambda: self._load_catalog_async(refresh=True)).grid(row=1, column=2, **pad)

        # Threads + delay
        opts = ttk.Frame(frm)
        opts.grid(row=2, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(opts, text="Simultâneos:").pack(side="left")
        ttk.Spinbox(opts, from_=1, to=16, textvariable=self.workers_var, width=5).pack(side="left", padx=(4, 14))
        ttk.Label(opts, text="Delay (s):").pack(side="left")
        ttk.Spinbox(opts, from_=0, to=10, increment=0.5, textvariable=self.delay_var, width=5).pack(side="left", padx=4)

        # Modo noturno
        night = ttk.Frame(frm)
        night.grid(row=3, column=0, columnspan=3, sticky="w", **pad)
        self.night_chk = ttk.Checkbutton(
            night, text="Modo noturno (repete até concluir, contorna quota)",
            variable=self.night_var, command=self._on_night_toggle)
        self.night_chk.pack(side="left")
        ttk.Label(night, text="  cooldown (min):").pack(side="left")
        self.cooldown_spin = ttk.Spinbox(night, from_=1, to=180, textvariable=self.cooldown_var, width=5)
        self.cooldown_spin.pack(side="left", padx=4)

        # Botões de ação
        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 4))
        self.btn_start = ttk.Button(btns, text="Iniciar", command=self._start)
        self.btn_pause = ttk.Button(btns, text="Pausar", command=self._toggle_pause)
        self.btn_cancel = ttk.Button(btns, text="Cancelar", command=self._cancel)
        self.btn_start.pack(side="left", padx=4)
        self.btn_pause.pack(side="left", padx=4)
        self.btn_cancel.pack(side="left", padx=4)

        # Barra de progresso
        self.progress = ttk.Progressbar(frm, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Label(frm, textvariable=self.status_var).grid(
            row=6, column=0, columnspan=3, sticky="w", **pad)

        # Log
        logfrm = ttk.Frame(frm)
        logfrm.grid(row=7, column=0, columnspan=3, sticky="nsew", **pad)
        frm.rowconfigure(7, weight=1)
        logfrm.rowconfigure(0, weight=1)
        logfrm.columnconfigure(0, weight=1)
        self.log = tk.Text(logfrm, height=12, wrap="none", state="disabled",
                           font=("Consolas", 9))
        self.log.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(logfrm, orient="vertical", command=self.log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=sb.set)

    # --------------------------------------------------------------- estado
    def _set_state(self, state: str) -> None:
        """state: loading | idle | running | paused | done"""
        cfg = {
            "loading": (("disabled", "disabled", "disabled"), True),
            "idle":    (("normal", "disabled", "disabled"), False),
            "running": (("disabled", "normal", "normal"), False),
            "paused":  (("disabled", "normal", "normal"), False),
            "done":    (("normal", "disabled", "disabled"), False),
        }
        (s, p, c), combo_lock = cfg[state]
        self.btn_start["state"] = s
        self.btn_pause["state"] = p
        self.btn_cancel["state"] = c
        self.btn_pause["text"] = "Continuar" if state == "paused" else "Pausar"
        self.trad_combo["state"] = "disabled" if (combo_lock or state in ("running", "paused")) else "readonly"
        self.state = state

    def _log(self, msg: str) -> None:
        self.log["state"] = "normal"
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log["state"] = "disabled"

    # ----------------------------------------------------------- catálogo
    def _load_catalog_async(self, refresh: bool) -> None:
        self._set_state("loading")
        self.status_var.set("Atualizando catálogo..." if refresh else "Carregando catálogo...")

        def work():
            try:
                books = fetcher.load_catalog(refresh=refresh, log=lambda m: self.events.put(("log", m)))
                self.events.put(("catalog", books))
            except Exception as e:
                self.events.put(("error", f"Falha ao carregar catálogo: {e}"))

        threading.Thread(target=work, daemon=True).start()

    def _on_catalog(self, books: list[dict]) -> None:
        self.books = books
        counts = fetcher.tradition_counts(books)
        values = [f"Todas as tradições ({len(books)})"]
        values += [f"{t} ({n})" for t, n in counts.items()]
        self.trad_combo["values"] = values
        self.trad_var.set(values[0])
        self.status_var.set(f"Pronto — {len(books)} livros no catálogo.")
        self._set_state("idle")

    def _selected_tradition(self) -> str:
        v = self.trad_var.get()
        if v.startswith("Todas as tradições"):
            return ""
        return v.rsplit(" (", 1)[0]  # remove " (N)"

    # ------------------------------------------------------------ ações
    def _pick_folder(self) -> None:
        d = filedialog.askdirectory(initialdir=self.out_var.get() or ".")
        if d:
            self.out_var.set(d)

    def _on_night_toggle(self) -> None:
        # sugere um delay seguro ao ligar o modo noturno
        if self.night_var.get() and self.delay_var.get() == 0.0:
            self.delay_var.set(1.0)

    def _start(self) -> None:
        if not self.books:
            messagebox.showwarning("Aguarde", "Catálogo ainda não carregado.")
            return
        out = Path(self.out_var.get().strip() or str(fetcher.OUT_DIR_DEFAULT))
        trad = self._selected_tradition()
        books = fetcher.select_books(self.books, tradition=trad)
        if not books:
            messagebox.showinfo("Nada a baixar", "Nenhum livro nesse filtro.")
            return

        self._cancel_event.clear()
        self.dl = None
        self.progress["maximum"] = len(books)
        self.progress["value"] = 0
        workers = int(self.workers_var.get())
        delay = float(self.delay_var.get())

        if self.night_var.get():
            self.loop_mode = True
            cooldown = float(self.cooldown_var.get())
            self._log(f"\n=== Modo noturno: {len(books)} livros -> {out} "
                      f"(workers={workers}, delay~{delay}s, cooldown={cooldown:.0f}min) ===")

            def work():
                summary = fetcher.run_until_done(
                    books, out, workers=workers, delay=delay, cooldown_min=cooldown,
                    on_event=lambda e: self.events.put(("dl", e)),
                    on_status=lambda m: self.events.put(("status", m)),
                    cancel_event=self._cancel_event,
                    register=lambda dl: setattr(self, "dl", dl),
                )
                self.events.put(("loop_done", summary))

            threading.Thread(target=work, daemon=True).start()
        else:
            self.loop_mode = False
            targets = fetcher.build_targets(books, out)
            self._log(f"\n=== Iniciando: {len(books)} livros -> {out} "
                      f"(workers={workers}, delay~{delay}s) ===")
            self.dl = fetcher.Downloader(
                books, targets, workers=workers, delay=delay,
                on_event=lambda e: self.events.put(("dl", e)),
            )
            self.dl.start()
        self._set_state("running")

    def _toggle_pause(self) -> None:
        if not self.dl:
            return
        if self.dl.is_paused():
            self.dl.resume()
            self._set_state("running")
            self.status_var.set("Retomado.")
        else:
            self.dl.pause()
            self._set_state("paused")
            self.status_var.set("Pausado (downloads em andamento terminam).")

    def _cancel(self) -> None:
        if not (self.dl or self.loop_mode):
            return
        if messagebox.askyesno("Cancelar", "Cancelar o download?"):
            self._cancel_event.set()
            if self.dl:
                self.dl.cancel()
            self.status_var.set("Cancelando... (aguardando arquivos em andamento)")
            self._set_state("running")  # mantém botões até 'finished'/'loop_done'

    # ---------------------------------------------------------- eventos
    def _drain(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "status":
                    self.status_var.set(payload)
                    self._log(f"  · {payload}")
                elif kind == "catalog":
                    self._on_catalog(payload)
                elif kind == "error":
                    self.status_var.set("Erro.")
                    self._set_state("idle")
                    messagebox.showerror("Erro", payload)
                elif kind == "dl":
                    self._on_dl_event(payload)
                elif kind == "loop_done":
                    self._on_loop_done(payload)
        except queue.Empty:
            pass
        self.root.after(100, self._drain)

    def _on_dl_event(self, e: dict) -> None:
        if e["type"] == "progress":
            self.progress["maximum"] = e["total"]
            self.progress["value"] = e["done"]
            retry = e.get("retry", 0)
            self.status_var.set(
                f"{e['done']}/{e['total']}  —  {e['ok']} baixados, "
                f"{e['skip']} já existiam, {e['fail']} falhas, {retry} p/ retentar"
            )
            tag = {"ok": "OK  ", "skip": "SKIP", "fail": "FAIL", "retry": "WAIT"}[e["status"]]
            line = f"[{e['done']}/{e['total']}] {tag} {e['name'][:60]}"
            if e["status"] in ("fail", "retry"):
                line += f"  -> {e['detail'][:80]}"
            self._log(line)
        elif e["type"] == "finished":
            retry = e.get("retry", 0)
            self._log(f"--- passada: {e['ok']} ok / {e['skip']} skip / "
                      f"{e['fail']} permanentes / {retry} p/ retentar ---")
            if not self.loop_mode:  # modo simples termina aqui
                verb = "Cancelado" if e["cancelled"] else "Concluído"
                self.status_var.set(
                    f"{verb}: {e['ok']} baixados, {e['skip']} já existiam, {e['fail']} falhas."
                )
                self.dl = None
                self._set_state("done")

    def _on_loop_done(self, s: dict) -> None:
        self.loop_mode = False
        self.dl = None
        self.status_var.set(
            f"Fim: {s['baixados']} no disco, {s['faltando']} faltando "
            f"({s['permanentes']} permanentes)."
        )
        self._log(f"=== FIM DO MODO NOTURNO: {s['baixados']} baixados, "
                  f"{s['faltando']} faltando ===")
        self._set_state("done")


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")  # tema nativo no Windows
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
