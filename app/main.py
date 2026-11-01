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
BG = "#0b1017"
PANEL = "#121a24"
PANEL_2 = "#182331"
BORDER = "#263445"
TEXT = "#f3f6fa"
MUTED = "#91a0b2"
ACCENT = "#36c98f"
ACCENT_HOVER = "#29ad79"


class DrMusicApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("DrMusic")
        self.root.geometry("1040x760")
        self.root.minsize(860, 650)
        self.root.configure(bg=BG)

        self.events: queue.Queue[tuple] = queue.Queue()
        self.entries: list[dict] = []
        self.is_playlist = False
        self.busy = False
        self.preview_image = None
        self.thumbnail_token = 0

        self.destination = tk.StringVar(value=str(DEFAULT_FOLDER))
        self.url = tk.StringVar()
        self.format_choice = tk.StringVar(value="MP3")
        self.quality = tk.StringVar(value="192")
        self.status = tk.StringVar(value="Cole um link para carregar o conteúdo.")
        self.item_count = tk.StringVar(value="Nenhum conteúdo carregado")
        self.preview_title = tk.StringVar(value="Prévia do conteúdo")
        self.preview_meta = tk.StringVar(value="A miniatura aparecerá aqui")

        self._style()
        self._build()
        self.root.after(100, self._poll_events)

    def _style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL, foreground=TEXT,
                        fieldbackground=PANEL, rowheight=34, borderwidth=0,
                        font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=PANEL_2, foreground=MUTED,
                        font=("Segoe UI", 8, "bold"), relief="flat", padding=(10, 9))
        style.map("Treeview", background=[("selected", "#214b3e")],
                  foreground=[("selected", "#ffffff")])
        style.configure("TCombobox", fieldbackground=PANEL_2, background=PANEL_2,
                        foreground=TEXT, arrowcolor=TEXT, bordercolor=BORDER,
                        padding=7)
        style.map("TCombobox", fieldbackground=[("readonly", PANEL_2)],
                  foreground=[("readonly", TEXT)])
        style.configure("Horizontal.TProgressbar", troughcolor=PANEL_2,
                        background=ACCENT, bordercolor=PANEL_2, lightcolor=ACCENT,
                        darkcolor=ACCENT)

    def _label(self, parent, text, color=MUTED, size=9, bold=False, **kwargs):
        return tk.Label(parent, text=text, bg=kwargs.pop("bg", PANEL), fg=color,
                        font=("Segoe UI", size, "bold" if bold else "normal"),
                        **kwargs)

    def _button(self, parent, text, command, primary=False, **kwargs):
        bg = ACCENT if primary else PANEL_2
        fg = "#07130e" if primary else TEXT
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                         activebackground=ACCENT_HOVER if primary else "#26374a",
                         activeforeground=fg, relief="flat", bd=0,
                         padx=15, pady=9, cursor="hand2",
                         font=("Segoe UI", 9, "bold"), **kwargs)

    def _build(self) -> None:
        page = tk.Frame(self.root, bg=BG, padx=26, pady=22)
        page.pack(fill="both", expand=True)

        header = tk.Frame(page, bg=BG)
        header.pack(fill="x", pady=(0, 20))
        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left")
        tk.Label(brand, text="♫", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 25, "bold")).pack(side="left", padx=(0, 10))
        title_area = tk.Frame(brand, bg=BG)
        title_area.pack(side="left")
        self._label(title_area, "DrMusic", TEXT, 21, True, bg=BG).pack(anchor="w")
        self._label(title_area, "Áudio do seu jeito.", MUTED, 9, bg=BG).pack(anchor="w")
        self._label(header, "WINDOWS DESKTOP", "#6e8196", 8, True, bg=BG).pack(side="right", pady=10)

        link_card = tk.Frame(page, bg=PANEL, padx=16, pady=15,
                             highlightthickness=1, highlightbackground=BORDER)
        link_card.pack(fill="x", pady=(0, 16))
        self._label(link_card, "LINK DO VÍDEO OU PLAYLIST", TEXT, 8, True).pack(anchor="w")
        url_row = tk.Frame(link_card, bg=PANEL)
        url_row.pack(fill="x", pady=(9, 0))
        self.url_entry = tk.Entry(url_row, textvariable=self.url, bg=PANEL_2, fg=TEXT,
                                  insertbackground=TEXT, selectbackground="#285b49",
                                  relief="flat", bd=0, font=("Segoe UI", 10))
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=11, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda _event: self.load_url())
        self.load_button = self._button(url_row, "Carregar link", self.load_url)
        self.load_button.pack(side="right")

        content = tk.Frame(page, bg=BG)
        content.pack(fill="both", expand=True)

        preview = tk.Frame(content, bg=PANEL, width=280, padx=14, pady=14,
                           highlightthickness=1, highlightbackground=BORDER)
        preview.pack(side="left", fill="y", padx=(0, 15))
        preview.pack_propagate(False)
        self._label(preview, "PRÉVIA", TEXT, 8, True).pack(anchor="w", pady=(0, 12))
        self.thumb = tk.Label(preview, text="♫", bg=PANEL_2, fg="#52677d",
                              font=("Segoe UI", 38, "bold"), width=18, height=7)
        self.thumb.pack(fill="x")
        self._label(preview, self.preview_title, TEXT, 11, True,
                    wraplength=245, justify="left").pack(anchor="w", pady=(14, 5))
        self._label(preview, self.preview_meta, MUTED, 9,
                    wraplength=245, justify="left").pack(anchor="w")
        tk.Frame(preview, bg=BORDER, height=1).pack(fill="x", pady=16)
        self._label(preview, "SALVAR EM", TEXT, 8, True).pack(anchor="w")
        dest_row = tk.Frame(preview, bg=PANEL)
        dest_row.pack(fill="x", pady=(8, 0))
        self.dest_entry = tk.Entry(dest_row, textvariable=self.destination, bg=PANEL_2,
                                   fg=TEXT, insertbackground=TEXT, relief="flat", bd=0,
                                   font=("Segoe UI", 8))
        self.dest_entry.pack(fill="x", ipady=9)
        self._button(preview, "Escolher pasta", self.choose_folder).pack(fill="x", pady=(8, 0))

        right = tk.Frame(content, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        list_header = tk.Frame(right, bg=BG)
        list_header.pack(fill="x", pady=(0, 9))
        self._label(list_header, "CONTEÚDO", TEXT, 10, True, bg=BG).pack(side="left")
        self._label(list_header, self.item_count, MUTED, 8, bg=BG).pack(side="right")

        list_card = tk.Frame(right, bg=PANEL, highlightthickness=1,
                              highlightbackground=BORDER)
        list_card.pack(fill="both", expand=True)
        columns = ("number", "title", "duration")
        self.tree = ttk.Treeview(list_card, columns=columns, show="headings",
                                 selectmode="extended")
        self.tree.heading("number", text="#")
        self.tree.heading("title", text="TÍTULO")
        self.tree.heading("duration", text="TEMPO")
        self.tree.column("number", width=42, anchor="center", stretch=False)
        self.tree.column("title", width=380, anchor="w")
        self.tree.column("duration", width=72, anchor="center", stretch=False)
        scrollbar = ttk.Scrollbar(list_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        scrollbar.pack(side="right", fill="y", pady=5, padx=(0, 5))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        selection = tk.Frame(right, bg=BG)
        selection.pack(fill="x", pady=(8, 14))
        self._link_button(selection, "Selecionar todos", self.select_all).pack(side="left")
        self._link_button(selection, "Limpar", self.clear_selection).pack(side="left", padx=12)

        settings = tk.Frame(right, bg=PANEL, padx=13, pady=12,
                            highlightthickness=1, highlightbackground=BORDER)
        settings.pack(fill="x", pady=(0, 12))
        self._label(settings, "FORMATO", TEXT, 8, True).grid(row=0, column=0, sticky="w")
        self._label(settings, "QUALIDADE", TEXT, 8, True).grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Combobox(settings, textvariable=self.format_choice,
                     values=("MP3", "Áudio original"), state="readonly",
                     width=17).grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.quality_box = ttk.Combobox(settings, textvariable=self.quality,
                                        values=("128", "192", "256", "320"),
                                        state="readonly", width=10)
        self.quality_box.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=(6, 0))
        settings.columnconfigure(0, weight=2)
        settings.columnconfigure(1, weight=1)
        self.format_choice.trace_add("write", self._toggle_quality)

        footer = tk.Frame(page, bg=BG)
        footer.pack(fill="x", pady=(15, 0))
        self.progress = ttk.Progressbar(footer, mode="determinate", maximum=100,
                                        style="Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(0, 9))
        self._label(footer, self.status, MUTED, 9, bg=BG).pack(anchor="w")
        self.download_button = self._button(footer, "Baixar selecionados", self.download_selected,
                                            primary=True)
        self.download_button.pack(fill="x", pady=(10, 0))
        self._label(footer, "Use apenas conteúdos que você tem autorização para baixar.",
                    "#657487", 8, bg=BG).pack(anchor="center", pady=(9, 0))

    def _link_button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, bg=BG, fg=ACCENT,
                         activebackground=BG, activeforeground=TEXT, relief="flat",
                         bd=0, cursor="hand2", font=("Segoe UI", 9))

    def _toggle_quality(self, *_):
        self.quality_box.configure(state="readonly" if self.format_choice.get() == "MP3" else "disabled")

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
        self.item_count.set("Carregando…")
        self.preview_title.set("Buscando conteúdo…")
        self.preview_meta.set("A miniatura será exibida quando estiver disponível.")
        self._set_thumbnail(None)
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

    def _thumbnail_url(self, item: dict) -> str | None:
        thumbs = item.get("thumbnails") or []
        candidates = [t for t in thumbs if t.get("url")]
        if candidates:
            return candidates[-1]["url"]
        return item.get("thumbnail")

    def _on_select(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected or not self.entries:
            return
        index = int(selected[0])
        if index >= len(self.entries):
            return
        item = self.entries[index]
        self.preview_title.set(item.get("title") or "Sem título")
        duration = self._format_duration(item.get("duration"))
        self.preview_meta.set(f"{duration}  •  Miniatura do item selecionado")
        self._set_thumbnail(None)
        thumb_url = self._thumbnail_url(item)
        self.thumbnail_token += 1
        token = self.thumbnail_token
        if thumb_url:
            threading.Thread(target=self._thumbnail_worker,
                             args=(thumb_url, token), daemon=True).start()

    def _thumbnail_worker(self, url: str, token: int) -> None:
        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0 DrMusic"})
            with urlopen(request, timeout=12) as response:
                data = response.read(5 * 1024 * 1024)
            self.events.put(("thumbnail", data, token))
        except Exception:
            self.events.put(("thumbnail_missing", token))

    def _set_thumbnail(self, data: bytes | None) -> None:
        if not data:
            self.preview_image = None
            self.thumb.configure(image="", text="♫", bg=PANEL_2, fg="#52677d")
            return
        try:
            image = Image.open(BytesIO(data)).convert("RGB")
            image.thumbnail((250, 145), Image.Resampling.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(image)
            self.thumb.configure(image=self.preview_image, text="", bg=PANEL_2)
        except Exception:
            self.preview_image = None
            self.thumb.configure(image="", text="♫", bg=PANEL_2, fg="#52677d")

    def _format_duration(self, seconds) -> str:
        if not seconds:
            return "--:--"
        seconds = int(seconds)
        if seconds >= 3600:
            return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _show_entries(self, entries: list[dict]) -> None:
        self.tree.delete(*self.tree.get_children())
        for index, item in enumerate(entries, start=1):
            self.tree.insert("", "end", iid=str(index - 1),
                             values=(index, item.get("title") or item.get("id") or "Sem título",
                                     self._format_duration(item.get("duration"))))
        if entries:
            self.tree.selection_set("0")
            self.tree.focus("0")
        else:
            self.preview_title.set("Nenhum item encontrado")
            self.preview_meta.set("Verifique o link e tente novamente.")

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
        threading.Thread(target=self._download_worker,
                         args=(self.url.get().strip(), indices, str(folder), self.is_playlist,
                               self.format_choice.get(), self.quality.get()),
                         daemon=True).start()

    def _download_worker(self, url: str, indices: list[int], folder: str,
                         is_playlist: bool, output_format: str, quality: str) -> None:
        try:
            if getattr(sys, "frozen", False):
                ffmpeg_dir = Path(sys.executable).resolve().parent
                if not (ffmpeg_dir / "ffmpeg.exe").is_file() or not (ffmpeg_dir / "ffprobe.exe").is_file():
                    raise RuntimeError("FFmpeg não foi encontrado junto ao DrMusic. Reinstale o aplicativo.")
            else:
                ffmpeg_path = shutil.which("ffmpeg")
                if not ffmpeg_path:
                    raise RuntimeError("FFmpeg não encontrado na versão de desenvolvimento.")
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
                    self.item_count.set(f"{len(self.entries)} item(ns)")
                    self.status.set(f"{title} carregado.")
                    self._set_busy(False)
                elif kind == "thumbnail":
                    if event[2] == self.thumbnail_token:
                        self._set_thumbnail(event[1])
                elif kind == "thumbnail_missing":
                    if event[1] == self.thumbnail_token:
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
                    self.item_count.set("Não foi possível carregar")
                    self._set_busy(False)
                    messagebox.showerror(APP_NAME, event[1])
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)


def main() -> None:
    root = tk.Tk()
    DrMusicApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
