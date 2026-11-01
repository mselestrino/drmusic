from __future__ import annotations

import os
import queue
import shutil
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import yt_dlp


APP_NAME = "DrMusic"
DEFAULT_FOLDER = Path.home() / "Music"


class DrMusicApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("DrMusic — Music Downloader")
        self.root.geometry("900x650")
        self.root.minsize(760, 540)
        self.root.configure(bg="#101318")

        self.events: queue.Queue[tuple] = queue.Queue()
        self.entries: list[dict] = []
        self.is_playlist = False
        self.busy = False

        self.destination = tk.StringVar(value=str(DEFAULT_FOLDER))
        self.url = tk.StringVar()
        self.format_choice = tk.StringVar(value="MP3")
        self.quality = tk.StringVar(value="192")
        self.status = tk.StringVar(value="Cole um link de vídeo ou playlist para começar.")

        self._style()
        self._build()
        self.root.after(120, self._poll_events)

    def _style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#191f28", foreground="#edf2f7",
                        fieldbackground="#191f28", rowheight=30, borderwidth=0)
        style.configure("Treeview.Heading", background="#252d39", foreground="#ffffff",
                        font=("Segoe UI", 9, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", "#285c4b")],
                  foreground=[("selected", "#ffffff")])
        style.configure("TCombobox", fieldbackground="#202733", background="#202733",
                        foreground="#ffffff", arrowcolor="#ffffff")
        style.configure("Horizontal.TProgressbar", troughcolor="#252d39",
                        background="#39c58a", bordercolor="#252d39")

    def _build(self) -> None:
        outer = tk.Frame(self.root, bg="#101318", padx=24, pady=20)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg="#101318")
        header.pack(fill="x", pady=(0, 18))
        tk.Label(header, text="♫  DrMusic", bg="#101318", fg="#ffffff",
                 font=("Segoe UI", 23, "bold")).pack(anchor="w")
        tk.Label(header, text="Seu gerenciador de downloads de áudio",
                 bg="#101318", fg="#9aa6b2", font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))

        tk.Label(outer, text="LINK DO VÍDEO OU PLAYLIST", bg="#101318", fg="#c7d0da",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        url_row = tk.Frame(outer, bg="#101318")
        url_row.pack(fill="x", pady=(7, 15))
        self.url_entry = tk.Entry(url_row, textvariable=self.url, bg="#202733", fg="#ffffff",
                                  insertbackground="#ffffff", relief="flat", font=("Segoe UI", 10))
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 9))
        self.load_button = self._button(url_row, "Carregar", self.load_url)
        self.load_button.pack(side="right")

        tk.Label(outer, text="CONTEÚDO ENCONTRADO  •  Selecione os itens que deseja baixar",
                 bg="#101318", fg="#c7d0da", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        list_frame = tk.Frame(outer, bg="#101318")
        list_frame.pack(fill="both", expand=True, pady=(7, 14))

        columns = ("number", "title", "duration")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings",
                                 selectmode="extended")
        self.tree.heading("number", text="#")
        self.tree.heading("title", text="TÍTULO")
        self.tree.heading("duration", text="DURAÇÃO")
        self.tree.column("number", width=55, anchor="center", stretch=False)
        self.tree.column("title", width=600, anchor="w")
        self.tree.column("duration", width=100, anchor="center", stretch=False)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        selection_row = tk.Frame(outer, bg="#101318")
        selection_row.pack(fill="x", pady=(0, 14))
        self._link_button(selection_row, "Selecionar todos", self.select_all).pack(side="left")
        self._link_button(selection_row, "Limpar seleção", self.clear_selection).pack(side="left", padx=15)

        options = tk.Frame(outer, bg="#171d26", padx=14, pady=12)
        options.pack(fill="x", pady=(0, 14))
        tk.Label(options, text="PASTA DE DESTINO", bg="#171d26", fg="#c7d0da",
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w")
        tk.Entry(options, textvariable=self.destination, bg="#202733", fg="#ffffff",
                 insertbackground="#ffffff", relief="flat").grid(row=1, column=0, sticky="ew", ipady=7, pady=(5, 0))
        self._button(options, "Procurar", self.choose_folder).grid(row=1, column=1, padx=(8, 18), pady=(5, 0))
        tk.Label(options, text="FORMATO", bg="#171d26", fg="#c7d0da",
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=2, sticky="w")
        ttk.Combobox(options, textvariable=self.format_choice, values=("MP3", "Áudio original"),
                     state="readonly", width=15).grid(row=1, column=2, padx=(0, 14), pady=(5, 0), ipady=3)
        tk.Label(options, text="QUALIDADE MP3", bg="#171d26", fg="#c7d0da",
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=3, sticky="w")
        ttk.Combobox(options, textvariable=self.quality, values=("128", "192", "256", "320"),
                     state="readonly", width=8).grid(row=1, column=3, pady=(5, 0), ipady=3)
        options.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(outer, mode="determinate", maximum=100,
                                        style="Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(0, 7))
        tk.Label(outer, textvariable=self.status, bg="#101318", fg="#9aa6b2",
                 font=("Segoe UI", 9)).pack(anchor="w")
        self.download_button = self._button(outer, "BAIXAR SELECIONADOS", self.download_selected,
                                            primary=True)
        self.download_button.pack(fill="x", pady=(12, 0))

        tk.Label(outer, text="Baixe somente conteúdos que você tem direito ou autorização para baixar.",
                 bg="#101318", fg="#778391", font=("Segoe UI", 8)).pack(anchor="center", pady=(10, 0))

    def _button(self, parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command,
                         bg="#27a875" if primary else "#2a3542",
                         fg="#ffffff", activebackground="#218b62" if primary else "#39485a",
                         activeforeground="#ffffff", relief="flat", bd=0,
                         padx=16, pady=9, cursor="hand2",
                         font=("Segoe UI", 9, "bold"))

    def _link_button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg="#101318", fg="#68d6a5",
                         activebackground="#101318", activeforeground="#ffffff",
                         relief="flat", bd=0, cursor="hand2", font=("Segoe UI", 9))

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.load_button.configure(state=state)
        self.download_button.configure(state=state)

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.destination.get() or str(DEFAULT_FOLDER))
        if folder:
            self.destination.set(folder)

    def load_url(self) -> None:
        url = self.url.get().strip()
        if not url:
            messagebox.showinfo(APP_NAME, "Cole primeiro o link de um vídeo ou playlist.")
            return
        if self.busy:
            return
        self._set_busy(True)
        self.status.set("Consultando o link…")
        threading.Thread(target=self._load_worker, args=(url,), daemon=True).start()

    def _load_worker(self, url: str) -> None:
        try:
            opts = {"extract_flat": "in_playlist", "quiet": True, "no_warnings": True,
                    "skip_download": True, "ignoreerrors": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info:
                raise RuntimeError("Não foi possível ler esse link.")
            entries = info.get("entries")
            if entries is not None:
                cleaned = [e for e in entries if e]
                self.events.put(("loaded", cleaned, True, info.get("title", "Playlist")))
            else:
                self.events.put(("loaded", [info], False, info.get("title", "Vídeo")))
        except Exception as exc:
            self.events.put(("error", f"Falha ao carregar o link: {exc}"))

    def _format_duration(self, seconds) -> str:
        if not seconds:
            return "--:--"
        seconds = int(seconds)
        return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}" if seconds >= 3600 else f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _show_entries(self, entries: list[dict]) -> None:
        self.tree.delete(*self.tree.get_children())
        for index, item in enumerate(entries, start=1):
            self.tree.insert("", "end", iid=str(index - 1),
                             values=(index, item.get("title") or item.get("id") or "Sem título",
                                     self._format_duration(item.get("duration"))))
        if entries:
            self.tree.selection_set(*[str(i) for i in range(len(entries))])

    def select_all(self) -> None:
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(*children)

    def clear_selection(self) -> None:
        self.tree.selection_remove(self.tree.selection())

    def download_selected(self) -> None:
        if self.busy:
            return
        selected = self.tree.selection()
        if not selected or not self.entries:
            messagebox.showinfo(APP_NAME, "Carregue um link e selecione pelo menos um item.")
            return
        folder = Path(self.destination.get()).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Não foi possível usar a pasta escolhida: {exc}")
            return

        indices = [int(item) + 1 for item in selected]
        self._set_busy(True)
        self.progress.configure(value=0)
        self.status.set(f"Preparando {len(indices)} download(s)…")
        url = self.url.get().strip()
        threading.Thread(target=self._download_worker,
                         args=(url, indices, str(folder), self.is_playlist,
                               self.format_choice.get(), self.quality.get()),
                         daemon=True).start()

    def _download_worker(self, url: str, indices: list[int], folder: str,
                         is_playlist: bool, output_format: str, quality: str) -> None:
        try:
            if getattr(sys, "frozen", False):
                ffmpeg_dir = Path(sys.executable).resolve().parent
                ffmpeg_exe = ffmpeg_dir / "ffmpeg.exe"
                ffprobe_exe = ffmpeg_dir / "ffprobe.exe"
                if not ffmpeg_exe.is_file() or not ffprobe_exe.is_file():
                    raise RuntimeError("Os arquivos do FFmpeg não foram encontrados junto ao DrMusic. Reinstale o aplicativo.")
            else:
                ffmpeg_path = shutil.which("ffmpeg")
                if not ffmpeg_path:
                    raise RuntimeError("FFmpeg não encontrado. Instale o FFmpeg para executar a versão de desenvolvimento.")
                ffmpeg_dir = Path(ffmpeg_path).resolve().parent
            def progress_hook(data):
                if data.get("status") == "downloading":
                    total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                    done = data.get("downloaded_bytes", 0)
                    percent = (done / total * 100) if total else 0
                    self.events.put(("progress", percent, data.get("filename", "")))
                elif data.get("status") == "finished":
                    self.events.put(("progress", 100, "Convertendo / finalizando…"))

            opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(folder, "%(title).180B.%(ext)s"),
                "noplaylist": not is_playlist,
                "ignoreerrors": False,
                "nooverwrites": True,
                "progress_hooks": [progress_hook],
                "quiet": True,
                "ffmpeg_location": str(ffmpeg_dir),
            }
            if is_playlist:
                opts["playlist_items"] = ",".join(str(i) for i in indices)
            if output_format == "MP3":
                opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality,
                }]
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.events.put(("done", "Downloads concluídos. Confira a pasta escolhida."))
        except Exception as exc:
            self.events.put(("error", f"Erro durante o download: {exc}"))

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "loaded":
                    self.entries, self.is_playlist, title = event[1], event[2], event[3]
                    self._show_entries(self.entries)
                    self.status.set(f"{title} — {len(self.entries)} item(ns) encontrado(s).")
                    self._set_busy(False)
                elif kind == "progress":
                    self.progress.configure(value=event[1])
                    self.status.set(f"Baixando… {event[1]:.1f}%")
                elif kind == "done":
                    self.progress.configure(value=100)
                    self.status.set(event[1])
                    self._set_busy(False)
                    messagebox.showinfo(APP_NAME, event[1])
                elif kind == "error":
                    self.status.set("Ocorreu um erro.")
                    self._set_busy(False)
                    messagebox.showerror(APP_NAME, event[1])
        except queue.Empty:
            pass
        self.root.after(120, self._poll_events)


def main() -> None:
    root = tk.Tk()
    DrMusicApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
