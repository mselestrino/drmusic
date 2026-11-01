from __future__ import annotations

import os
import queue
import shutil
import sys
import threading
import tkinter as tk
from io import BytesIO
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.request import Request, urlopen

from PIL import Image, ImageTk
import yt_dlp

APP_NAME = "DrMusic"
DEFAULT_FOLDER = Path.home() / "Music"
BG = "#090b0e"
SIDEBAR = "#0c0f13"
PANEL = "#101317"
PANEL_ALT = "#15191e"
BORDER = "#242a31"
TEXT = "#f2f4f6"
MUTED = "#9299a2"
GREEN = "#00c99a"
BLUE = "#1768e8"


class DrMusicApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("DrMusic")
        self.root.geometry("1280x880")
        self.root.minsize(1050, 740)
        self.root.configure(bg=BG)
        self.events: queue.Queue[tuple] = queue.Queue()
        self.entries: list[dict] = []
        self.is_playlist = False
        self.busy = False
        self.preview_image = None
        self.thumbnail_token = 0
        self.queue_items: list[dict] = []
        self.destination = tk.StringVar(value=str(DEFAULT_FOLDER))
        self.url = tk.StringVar()
        self.format_choice = tk.StringVar(value="MP3")
        self.quality = tk.StringVar(value="192")
        self.status = tk.StringVar(value="Cole um link para começar.")
        self.preview_title = tk.StringVar(value="Nenhum conteúdo carregado")
        self.preview_meta = tk.StringVar(value="A miniatura e os detalhes aparecerão aqui.")
        self.queue_count = tk.StringVar(value="0/0")
        self._style()
        self._build()
        self.root.after(100, self._poll_events)

    def _style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL, foreground=TEXT,
                        fieldbackground=PANEL, rowheight=38, borderwidth=0,
                        font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=PANEL_ALT, foreground=MUTED,
                        font=("Segoe UI", 8, "bold"), relief="flat", padding=9)
        style.map("Treeview", background=[("selected", "#153d37")],
                  foreground=[("selected", TEXT)])
        style.configure("Horizontal.TProgressbar", troughcolor=PANEL_ALT,
                        background=GREEN, bordercolor=PANEL_ALT, lightcolor=GREEN,
                        darkcolor=GREEN)

    def label(self, parent, text, color=TEXT, size=10, bold=False, bg=None, **kw):
        opts = dict(bg=bg or parent.cget("bg"), fg=color,
                    font=("Segoe UI", size, "bold" if bold else "normal"))
        if isinstance(text, tk.Variable):
            opts["textvariable"] = text
        else:
            opts["text"] = text
        opts.update(kw)
        return tk.Label(parent, **opts)

    def button(self, parent, text, command, primary=False, **kw):
        return tk.Button(parent, text=text, command=command,
                         bg=GREEN if primary else PANEL_ALT,
                         fg="#06130f" if primary else TEXT,
                         activebackground="#00ad85" if primary else "#252b33",
                         activeforeground=TEXT, relief="flat", bd=0,
                         padx=14, pady=9, cursor="hand2",
                         font=("Segoe UI", 9, "bold"), **kw)

    def _build(self):
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=12, pady=12)
        self.sidebar = tk.Frame(shell, bg=SIDEBAR, width=190,
                                highlightthickness=1, highlightbackground=BORDER)
        self.sidebar.pack(side="left", fill="y", padx=(0, 12))
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg=SIDEBAR)
        brand.pack(fill="x", padx=17, pady=(20, 30))
        tk.Label(brand, text="⚡", bg=SIDEBAR, fg=GREEN,
                 font=("Segoe UI Emoji", 23)).pack(side="left", padx=(0, 9))
        self.label(brand, "DrMusic", GREEN, 16, True, bg=SIDEBAR).pack(side="left")
        nav = [
            ("▣", "YouTube", True), ("◎", "Universal", False),
            ("▧", "Gallery", False), ("▣", "Channels", False),
            ("✧", "AI Summary", False), ("⚒", "Processing", False),
            ("▤", "Subtitles", False), ("♧", "Metadata", False),
            ("⇩", "Library", False), ("▤", "Logs", False),
            ("⚙", "Settings", False)
        ]
        for glyph, name, active in nav:
            row = tk.Frame(self.sidebar, bg="#102a2a" if active else SIDEBAR)
            row.pack(fill="x", padx=9, pady=3)
            if active:
                tk.Frame(row, bg=GREEN, width=3, height=35).pack(side="left", fill="y")
            tk.Label(row, text=glyph, bg=row.cget("bg"),
                     fg=GREEN if active else MUTED,
                     font=("Segoe UI", 13), width=3).pack(side="left", padx=(7, 2), pady=7)
            self.label(row, name, GREEN if active else "#b0b5bc", 9,
                       bg=row.cget("bg")).pack(side="left")
        tk.Frame(self.sidebar, bg=SIDEBAR).pack(fill="both", expand=True)
        self.button(self.sidebar, "☼  Tema escuro", self.toggle_theme).pack(fill="x", padx=13, pady=(8, 4))
        self.label(self.sidebar, "  ‹  Recolher menu", MUTED, 9, bg=SIDEBAR).pack(anchor="w", padx=16, pady=12)

        self.main = tk.Frame(shell, bg=BG, highlightthickness=1, highlightbackground=BORDER)
        self.main.pack(side="left", fill="both", expand=True)
        top = tk.Frame(self.main, bg=BG)
        top.pack(fill="x", padx=24, pady=(18, 16))
        self.label(top, "YouTube", TEXT, 14, bg=BG).pack(side="left")
        self.label(top, "◉", MUTED, 14, bg=BG).pack(side="right")

        body = tk.Frame(self.main, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 18))
        modebar = tk.Frame(body, bg=BG)
        modebar.pack(fill="x", pady=(0, 10))
        self.button(modebar, "↗  Link único", lambda: self.set_mode(False)).pack(side="left")
        self.button(modebar, "☷  Playlist", lambda: self.set_mode(True)).pack(side="left", padx=5)
        self.label(modebar, "Colar link e adicionar à fila", MUTED, 9, bg=BG).pack(side="right")

        urlrow = tk.Frame(body, bg=PANEL, padx=12, pady=10,
                          highlightthickness=1, highlightbackground=BORDER)
        urlrow.pack(fill="x", pady=(0, 12))
        self.label(urlrow, "↗", MUTED, 15, bg=PANEL).pack(side="left", padx=(2, 10))
        self.url_entry = tk.Entry(urlrow, textvariable=self.url, bg=PANEL, fg=TEXT,
                                  insertbackground=TEXT, relief="flat", bd=0,
                                  font=("Segoe UI", 10))
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.url_entry.bind("<Return>", lambda _e: self.load_url())
        self.button(urlrow, "＋  Adicionar", self.load_url, primary=True).pack(side="right", padx=(10, 0))

        preview = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        preview.pack(fill="x", pady=(0, 13))
        info = tk.Frame(preview, bg=PANEL, padx=14, pady=13)
        info.pack(fill="x")
        self.thumb = tk.Label(info, text="♫", bg=PANEL_ALT, fg="#64717e",
                              font=("Segoe UI", 32, "bold"), width=13, height=5)
        self.thumb.pack(side="left", padx=(0, 15))
        details = tk.Frame(info, bg=PANEL)
        details.pack(side="left", fill="both", expand=True)
        self.label(details, self.preview_title, TEXT, 11, True, bg=PANEL,
                   wraplength=650, justify="left").pack(anchor="w", pady=(3, 8))
        self.label(details, self.preview_meta, MUTED, 9, bg=PANEL).pack(anchor="w")
        self.label(details, "Prévia do item selecionado", "#7d8792", 8, bg=PANEL).pack(anchor="w", pady=(10, 0))
        self.label(info, "×", MUTED, 16, bg=PANEL).pack(side="right", anchor="n")

        formats = tk.Frame(preview, bg="#14171b", padx=14, pady=11)
        formats.pack(fill="x")
        self.label(formats, "FORMATO DE ÁUDIO", MUTED, 8, True, bg="#14171b").pack(anchor="w", pady=(0, 8))
        fmtrow = tk.Frame(formats, bg="#14171b")
        fmtrow.pack(fill="x")
        self.button(fmtrow, "♫  MP3", lambda: self.format_choice.set("MP3")).pack(side="left", padx=(0, 7))
        self.button(fmtrow, "♫  Original", lambda: self.format_choice.set("Áudio original")).pack(side="left")

        controls = tk.Frame(body, bg=BG)
        controls.pack(fill="x", pady=(0, 12))
        self.label(controls, "QUALIDADE", MUTED, 8, True, bg=BG).pack(side="left", padx=(2, 8))
        self.quality_box = ttk.Combobox(controls, textvariable=self.quality,
                                        values=("128", "192", "256", "320"),
                                        state="readonly", width=8)
        self.quality_box.pack(side="left")
        self.label(controls, "kbps", MUTED, 8, bg=BG).pack(side="left", padx=(5, 14))
        self.button(controls, "▣  Pasta", self.choose_folder).pack(side="left")
        self.label(controls, self.destination, MUTED, 8, bg=BG,
                   width=32, anchor="w").pack(side="left", padx=9)
        self.button(controls, "Selecionar todos", self.select_all).pack(side="right")
        self.button(controls, "Limpar seleção", self.clear_selection).pack(side="right", padx=6)

        queuehead = tk.Frame(body, bg=BG)
        queuehead.pack(fill="x", pady=(1, 8))
        self.label(queuehead, "Fila de downloads", TEXT, 11, True, bg=BG).pack(side="left")
        self.label(queuehead, self.queue_count, MUTED, 8, bg=BG).pack(side="left", padx=9)
        self.label(queuehead, self.status, MUTED, 8, bg=BG).pack(side="right")

        table = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        table.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table, columns=("num", "title", "duration", "state"),
                                 show="headings", selectmode="extended")
        for col, title, width in (("num", "#", 42), ("title", "VÍDEO / ÁUDIO", 450),
                                  ("duration", "DURAÇÃO", 90), ("state", "STATUS", 110)):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w" if col == "title" else "center",
                             stretch=(col == "title"))
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        bottom = tk.Frame(body, bg=BG)
        bottom.pack(fill="x", pady=(12, 0))
        self.progress = ttk.Progressbar(bottom, mode="determinate", maximum=100)
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.download_button = self.button(bottom, "▷  Iniciar download", self.download_selected, primary=True)
        self.download_button.pack(side="left", ipadx=25)
        self.button(bottom, "⌫", self.remove_selected).pack(side="left", padx=(8, 0))

    def set_mode(self, playlist: bool):
        self.is_playlist = playlist
        self.status.set("Modo playlist" if playlist else "Modo link único")

    def toggle_theme(self):
        messagebox.showinfo(APP_NAME, "O DrMusic está usando o tema escuro desta interface.")

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.destination.get() or str(DEFAULT_FOLDER))
        if folder:
            self.destination.set(folder)

    def load_url(self):
        url = self.url.get().strip()
        if not url:
            messagebox.showinfo(APP_NAME, "Cole um link antes de adicionar.")
            return
        if self.busy:
            return
        self._set_busy(True)
        self.status.set("Consultando link…")
        self.preview_title.set("Buscando conteúdo…")
        self._set_thumbnail(None)
        threading.Thread(target=self._load_worker, args=(url,), daemon=True).start()

    def _load_worker(self, url):
        try:
            opts = {"extract_flat": "in_playlist", "quiet": True, "no_warnings": True,
                    "skip_download": True, "ignoreerrors": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info:
                raise RuntimeError("Não foi possível ler esse link.")
            entries = info.get("entries")
            if entries is not None:
                self.events.put(("loaded", [e for e in entries if e], True, info.get("title", "Playlist")))
            else:
                self.events.put(("loaded", [info], False, info.get("title", "Vídeo")))
        except Exception as exc:
            self.events.put(("error", f"Falha ao carregar: {exc}"))

    def _thumb_url(self, item):
        thumbs = [t for t in (item.get("thumbnails") or []) if t.get("url")]
        return thumbs[-1]["url"] if thumbs else item.get("thumbnail")

    def _on_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        index = int(selected[0])
        if index >= len(self.entries):
            return
        item = self.entries[index]
        self.preview_title.set(item.get("title") or "Sem título")
        self.preview_meta.set(f"{self._duration(item.get('duration'))}   •   Item selecionado")
        self._set_thumbnail(None)
        self.thumbnail_token += 1
        token = self.thumbnail_token
        url = self._thumb_url(item)
        if url:
            threading.Thread(target=self._thumbnail_worker, args=(url, token), daemon=True).start()

    def _thumbnail_worker(self, url, token):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=12) as response:
                data = response.read(5 * 1024 * 1024)
            self.events.put(("thumbnail", data, token))
        except Exception:
            self.events.put(("thumbnail_missing", token))

    def _set_thumbnail(self, data):
        if not data:
            self.preview_image = None
            self.thumb.configure(image="", text="♫")
            return
        try:
            img = Image.open(BytesIO(data)).convert("RGB")
            img.thumbnail((180, 105), Image.Resampling.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(img)
            self.thumb.configure(image=self.preview_image, text="")
        except Exception:
            self.thumb.configure(image="", text="♫")

    def _duration(self, seconds):
        if not seconds:
            return "--:--"
        seconds = int(seconds)
        return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}" if seconds >= 3600 else f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _show_entries(self):
        self.tree.delete(*self.tree.get_children())
        self.queue_items = []
        for i, item in enumerate(self.entries):
            title = item.get("title") or item.get("id") or "Sem título"
            self.tree.insert("", "end", iid=str(i),
                             values=(i + 1, title, self._duration(item.get("duration")), "Pendente"))
            self.queue_items.append(item)
        if self.entries:
            self.tree.selection_set("0")
            self.tree.focus("0")
        self.queue_count.set(f"0/{len(self.entries)}")

    def select_all(self):
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(*children)

    def clear_selection(self):
        self.tree.selection_remove(self.tree.selection())

    def remove_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        remove = {int(x) for x in selected}
        self.entries = [item for i, item in enumerate(self.entries) if i not in remove]
        self._show_entries()

    def _set_busy(self, busy):
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.download_button.configure(state=state)

    def download_selected(self):
        if self.busy:
            return
        selected = self.tree.selection()
        if not selected or not self.entries:
            messagebox.showinfo(APP_NAME, "Adicione um link e selecione pelo menos um item.")
            return
        folder = Path(self.destination.get()).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Não foi possível usar a pasta: {exc}")
            return
        indices = [self.entries[int(x)].get("_drmusic_playlist_index", int(x) + 1) for x in selected]
        self._set_busy(True)
        self.progress.configure(value=0)
        self.status.set(f"Preparando {len(indices)} item(ns)…")
        threading.Thread(target=self._download_worker,
                         args=(self.url.get().strip(), indices, str(folder), self.is_playlist,
                               self.format_choice.get(), self.quality.get()), daemon=True).start()

    def _download_worker(self, url, indices, folder, is_playlist, output_format, quality):
        try:
            if getattr(sys, "frozen", False):
                ffmpeg_dir = Path(sys.executable).resolve().parent
                if not (ffmpeg_dir / "ffmpeg.exe").is_file() or not (ffmpeg_dir / "ffprobe.exe").is_file():
                    raise RuntimeError("FFmpeg não foi encontrado. Reinstale o aplicativo.")
            else:
                path = shutil.which("ffmpeg")
                if not path:
                    raise RuntimeError("FFmpeg não encontrado na versão de desenvolvimento.")
                ffmpeg_dir = Path(path).resolve().parent

            def hook(data):
                if data.get("status") == "downloading":
                    total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                    done = data.get("downloaded_bytes", 0)
                    pct = done / total * 100 if total else 0
                    self.events.put(("progress", pct))
                elif data.get("status") == "finished":
                    self.events.put(("progress", 100))

            opts = {"format": "bestaudio/best",
                    "outtmpl": os.path.join(folder, "%(title).180B.%(ext)s"),
                    "noplaylist": not is_playlist, "ignoreerrors": False,
                    "nooverwrites": True, "progress_hooks": [hook], "quiet": True,
                    "ffmpeg_location": str(ffmpeg_dir)}
            if is_playlist:
                opts["playlist_items"] = ",".join(str(i) for i in indices)
            if output_format == "MP3":
                opts["postprocessors"] = [{"key": "FFmpegExtractAudio",
                                           "preferredcodec": "mp3",
                                           "preferredquality": quality}]
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.events.put(("done", "Downloads concluídos. Confira a pasta escolhida."))
        except Exception as exc:
            self.events.put(("error", f"Erro durante o download: {exc}"))

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "loaded":
                    self.entries, self.is_playlist = event[1], event[2]
                    for original_index, entry in enumerate(self.entries, start=1):
                        entry["_drmusic_playlist_index"] = original_index
                    self._show_entries()
                    self.status.set(f"{event[3]} carregado.")
                    self._set_busy(False)
                elif kind == "thumbnail" and event[2] == self.thumbnail_token:
                    self._set_thumbnail(event[1])
                elif kind == "thumbnail_missing" and event[1] == self.thumbnail_token:
                    self._set_thumbnail(None)
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
        self.root.after(100, self._poll_events)


def main():
    root = tk.Tk()
    DrMusicApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
