#!/usr/bin/env python3
"""Ponto de entrada: abre a GUI da Biblioteca Astral (instância única)."""

import sys

WINDOW_TITLE = "Biblioteca Astral — Downloader"
_MUTEX_NAME = "BibliotecaAstral_SingleInstance_v1"
_ERROR_ALREADY_EXISTS = 183


def _acquire_single_instance():
    """
    Tenta criar um mutex nomeado do Windows.
    Retorna o handle se for a 1ª instância; None se já houver outra rodando.
    O handle precisa ficar vivo enquanto o app roda (o SO libera ao encerrar).
    """
    import ctypes
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if kernel32.GetLastError() == _ERROR_ALREADY_EXISTS:
        return None
    return handle


def _focus_existing() -> None:
    """Traz a janela já aberta para frente (best-effort)."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, WINDOW_TITLE)
        if hwnd:
            user32.ShowWindow(hwnd, 9)        # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def _warn_already_running() -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Biblioteca Astral", "O programa já está aberto.")
        root.destroy()
    except Exception:
        pass


def main() -> None:
    handle = None
    if sys.platform == "win32":
        handle = _acquire_single_instance()
        if handle is None:
            _focus_existing()
            _warn_already_running()
            return

    from gui import main as gui_main
    gui_main()
    # 'handle' permanece referenciado até aqui -> mutex vivo durante todo o app.


if __name__ == "__main__":
    main()
