"""SoundCloud Downloader – interface moderne (CustomTkinter) + yt-dlp.

Fonctions : analyse d'un lien, liste des sons avec pochette, sélection,
qualité MP3, aperçu audio, progression par son, annulation, historique,
thème sombre / clair.
"""
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import imageio_ffmpeg
import yt_dlp
from PIL import Image, ImageDraw, ImageTk

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
try:  # l'aperçu audio est optionnel
    import pygame

    HAS_PYGAME = True
except Exception:  # pragma: no cover
    pygame = None
    HAS_PYGAME = False

# --------------------------------------------------------------------------- #
#  Constantes
# --------------------------------------------------------------------------- #
APP_NAME = "SoundCloud Downloader"
ORANGE = "#ff5500"
ORANGE_HOVER = "#d94800"
BG = ("#f3f3f5", "#101012")
CARD = ("#ffffff", "#1a1a1e")
ROW = ("#f1f1f4", "#232328")
MUTED = ("#6b6b75", "#9b9ba5")
TEXT = ("#16161a", "#f2f2f4")
GREEN = "#2fbf71"
RED = "#e5484d"

QUALITIES = {
    "320 kbps": "320",
    "256 kbps": "256",
    "192 kbps": "192",
    "128 kbps": "128",
    "Meilleure (VBR)": "0",
}
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".soundcloud_downloader.json")
DEFAULT_CFG = {
    "dest_dir": os.path.expanduser("~/Desktop/Musiques_SoundCloud"),
    "quality": "320 kbps",
    "theme": "dark",
    "skip_existing": True,
    "history": [],
}
THUMB = 52


def resource_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def load_config():
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def fmt_duration(sec):
    if not sec:
        return ""
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def trunc(text, n):
    return text if len(text) <= n else text[: n - 1] + "…"


def no_window_flags():
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def rounded(img, radius):
    img = img.convert("RGBA")
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.size[0] - 1, img.size[1] - 1), radius=radius, fill=255)
    img.putalpha(mask)
    return img


def make_placeholder(size=THUMB * 2):
    """Icône de son orange (barres d'égaliseur) quand il n'y a pas de pochette."""
    img = Image.new("RGBA", (size, size), ORANGE)
    d = ImageDraw.Draw(img)
    heights = [0.25, 0.5, 0.75, 0.4, 0.6]
    bw, gap = size * 0.09, size * 0.06
    total = len(heights) * bw + (len(heights) - 1) * gap
    x0 = (size - total) / 2
    for i, h in enumerate(heights):
        x = x0 + i * (bw + gap)
        hh = size * h * 0.6
        d.rounded_rectangle((x, size / 2 - hh / 2, x + bw, size / 2 + hh / 2), radius=bw / 2, fill="white")
    return rounded(img, size // 5)


def pick_thumb(e):
    ths = e.get("thumbnails") or []
    for pref in ("large", "badge", "t67x67"):
        for t in ths:
            if t.get("id") == pref and t.get("url"):
                return t["url"]
    sized = [t for t in ths if t.get("url") and t.get("width")]
    if sized:
        return min(sized, key=lambda t: abs(t["width"] - 120))["url"]
    urls = [t["url"] for t in ths if t.get("url")]
    return urls[0] if urls else e.get("thumbnail")


@dataclass
class Track:
    url: str
    title: str
    artist: str
    duration: int
    thumb_url: str


# --------------------------------------------------------------------------- #
#  Ligne de la liste
# --------------------------------------------------------------------------- #
class TrackRow(ctk.CTkFrame):
    def __init__(self, master, app, idx, track):
        super().__init__(master, fg_color=ROW, corner_radius=12)
        self.app, self.idx, self.track = app, idx, track
        self.visible = True
        self.search_text = f"{track.title} {track.artist}".lower()
        self.columnconfigure(2, weight=1)

        self.var = tk.BooleanVar(value=True)
        self.check = ctk.CTkCheckBox(
            self, text="", variable=self.var, width=24, checkbox_width=22, checkbox_height=22,
            corner_radius=6, fg_color=ORANGE, hover_color=ORANGE_HOVER, command=app.update_counter,
        )
        self.check.grid(row=0, column=0, padx=(12, 4), pady=8)

        self.thumb = ctk.CTkLabel(self, text="", image=app.placeholder_img, width=THUMB, height=THUMB)
        self.thumb.grid(row=0, column=1, padx=6, pady=8)

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.grid(row=0, column=2, sticky="ew", padx=4)
        self.title_lbl = ctk.CTkLabel(
            info, text="♪  " + trunc(track.title, 70), anchor="w", text_color=TEXT,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.title_lbl.pack(fill="x")
        sub = " · ".join(x for x in (track.artist, fmt_duration(track.duration)) if x)
        self.sub_lbl = ctk.CTkLabel(info, text=sub, anchor="w", text_color=MUTED, font=ctk.CTkFont(size=12))
        self.sub_lbl.pack(fill="x")
        for w in (self.title_lbl, self.sub_lbl):
            w.bind("<Button-1>", lambda _e: self.check.toggle())

        self.play_btn = ctk.CTkButton(
            self, text="▶", width=36, height=36, corner_radius=18, fg_color="transparent",
            border_width=2, border_color=ORANGE, text_color=ORANGE, hover_color=("#ffe3d6", "#3a2418"),
            command=lambda: app.toggle_preview(self.idx),
        )
        self.play_btn.grid(row=0, column=3, padx=6)

        status = ctk.CTkFrame(self, fg_color="transparent", width=120)
        status.grid(row=0, column=4, padx=(4, 12))
        self.status_lbl = ctk.CTkLabel(status, text="", width=120, anchor="e", font=ctk.CTkFont(size=12), text_color=MUTED)
        self.status_lbl.pack()
        self.bar = ctk.CTkProgressBar(status, width=110, height=6, progress_color=ORANGE)
        self.bar.set(0)

    # -- API -------------------------------------------------------------- #
    def is_selected(self):
        return self.var.get()

    def set_thumb(self, image):
        self.thumb.configure(image=image)

    def set_status(self, text, color=None):
        self.status_lbl.configure(text=text, text_color=color or MUTED)

    def set_progress(self, frac):
        if frac is None:
            self.bar.pack_forget()
            return
        if not self.bar.winfo_ismapped():
            self.bar.pack(pady=(2, 0))
        self.bar.set(max(0.0, min(1.0, frac)))

    def set_play(self, text):
        self.play_btn.configure(text=text)


# --------------------------------------------------------------------------- #
#  Application
# --------------------------------------------------------------------------- #
class App(ctk.CTk):
    def __init__(self):
        self.cfg = load_config()
        ctk.set_appearance_mode(self.cfg["theme"])
        super().__init__()
        self.title(APP_NAME)
        self.geometry("900x780")
        self.minsize(760, 640)
        self.configure(fg_color=BG)
        self._set_icon()

        self.q = queue.Queue()
        self.rows = []
        self.tracks = []
        self.folder_name = "SoundCloud"
        self.gen = 0
        self.busy = False
        self.cancel_evt = threading.Event()
        self.pool = ThreadPoolExecutor(max_workers=4)
        self.pending = []
        self.results = {}
        self.job_total = 0
        self.job_done = 0
        self.job_ids = []
        self.tmpdir = tempfile.mkdtemp(prefix="scdl_")
        self.preview_idx = None
        self.preview_token = 0
        self.mixer_ready = False
        self.placeholder_img = ctk.CTkImage(make_placeholder(), size=(THUMB, THUMB))

        self._build_ui()
        self._bind_keys()
        self.after(100, self._poll)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ UI #
    def _set_icon(self):
        try:
            png = Image.open(resource_path("assets/logo.png")).resize((256, 256), Image.LANCZOS)
            self._icon_photo = ImageTk.PhotoImage(png)
            self.iconphoto(True, self._icon_photo)
            if sys.platform.startswith("win"):
                ico = resource_path("assets/icon.ico")
                self.after(250, lambda: self.iconbitmap(ico))
        except Exception:
            pass

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # En-tête avec logo
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        head.columnconfigure(1, weight=1)
        try:
            logo = Image.open(resource_path("assets/logo.png"))
            self.logo_img = ctk.CTkImage(logo, size=(52, 52))
            ctk.CTkLabel(head, text="", image=self.logo_img).grid(row=0, column=0, rowspan=2, padx=(0, 14))
        except Exception:
            pass
        ctk.CTkLabel(head, text=APP_NAME, anchor="w", text_color=TEXT, font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=1, sticky="sw")
        ctk.CTkLabel(head, text="Colle un lien de playlist ou de son, choisis, télécharge.", anchor="w", text_color=MUTED).grid(row=1, column=1, sticky="nw")
        self.theme_switch = ctk.CTkSwitch(
            head, text="Mode clair", progress_color=ORANGE, command=self._toggle_theme, text_color=MUTED,
        )
        if self.cfg["theme"] == "light":
            self.theme_switch.select()
        self.theme_switch.grid(row=0, column=2, rowspan=2, padx=(10, 0))

        # Carte : lien + options
        top = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16)
        top.grid(row=1, column=0, sticky="ew", padx=20, pady=6)
        top.columnconfigure(0, weight=1)
        self.url_entry = ctk.CTkEntry(
            top, height=42, corner_radius=10, border_width=1,
            placeholder_text="https://soundcloud.com/…", font=ctk.CTkFont(size=14),
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(16, 8), pady=(16, 8))
        self.url_entry.focus()
        self.btn_analyze = ctk.CTkButton(
            top, text="Analyser", height=42, width=120, corner_radius=10, fg_color=ORANGE,
            hover_color=ORANGE_HOVER, font=ctk.CTkFont(size=14, weight="bold"), command=self.start_analyze,
        )
        self.btn_analyze.grid(row=0, column=1, padx=(0, 16), pady=(16, 8))

        opts = ctk.CTkFrame(top, fg_color="transparent")
        opts.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14))
        ctk.CTkLabel(opts, text="Qualité MP3", text_color=MUTED).pack(side="left")
        self.quality_menu = ctk.CTkOptionMenu(
            opts, values=list(QUALITIES), width=160, fg_color=ROW, button_color=ORANGE,
            button_hover_color=ORANGE_HOVER, text_color=TEXT, dropdown_text_color=TEXT,
            command=lambda _v: self._save_prefs(),
        )
        self.quality_menu.set(self.cfg["quality"] if self.cfg["quality"] in QUALITIES else "320 kbps")
        self.quality_menu.pack(side="left", padx=(8, 18))
        ctk.CTkButton(
            opts, text="Dossier…", width=90, fg_color=ROW, hover_color=("#e4e4e8", "#2e2e35"),
            text_color=TEXT, command=self.choose_dir,
        ).pack(side="left")
        self.dir_lbl = ctk.CTkLabel(opts, text=self._dir_text(), text_color=MUTED, anchor="w")
        self.dir_lbl.pack(side="left", padx=8)
        self.skip_var = tk.BooleanVar(value=bool(self.cfg["skip_existing"]))
        ctk.CTkCheckBox(
            opts, text="Ignorer les sons déjà présents", variable=self.skip_var, fg_color=ORANGE,
            hover_color=ORANGE_HOVER, text_color=MUTED, command=self._save_prefs,
        ).pack(side="right")

        # Carte : liste des sons
        mid = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16)
        mid.grid(row=2, column=0, sticky="nsew", padx=20, pady=6)
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(1, weight=1)
        bar = ctk.CTkFrame(mid, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.apply_filter())
        self.search_entry = ctk.CTkEntry(bar, width=230, height=34, placeholder_text="Rechercher un titre…", textvariable=self.search_var)
        self.search_entry.pack(side="left")
        for txt, val in (("Tout cocher", True), ("Tout décocher", False)):
            ctk.CTkButton(
                bar, text=txt, width=105, height=34, fg_color=ROW, hover_color=("#e4e4e8", "#2e2e35"),
                text_color=TEXT, command=lambda v=val: self.set_all(v),
            ).pack(side="left", padx=(8, 0))
        self.counter_lbl = ctk.CTkLabel(bar, text="0 / 0 sélectionnés", text_color=MUTED)
        self.counter_lbl.pack(side="right")

        self.list_frame = ctk.CTkScrollableFrame(mid, fg_color="transparent")
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 8))
        self.list_frame.columnconfigure(0, weight=1)
        self.empty_lbl = ctk.CTkLabel(
            self.list_frame, text="\n♪\n\nAnalyse un lien pour afficher les sons ici.", text_color=MUTED,
            font=ctk.CTkFont(size=14),
        )
        self.empty_lbl.grid(row=0, column=0, pady=60)

        # Bas : progression + actions
        bottom = ctk.CTkFrame(self, fg_color=CARD, corner_radius=16)
        bottom.grid(row=3, column=0, sticky="ew", padx=20, pady=(6, 18))
        bottom.columnconfigure(0, weight=1)
        self.global_bar = ctk.CTkProgressBar(bottom, height=10, progress_color=ORANGE)
        self.global_bar.set(0)
        self.global_bar.grid(row=0, column=0, columnspan=5, sticky="ew", padx=16, pady=(14, 6))
        self.status_lbl = ctk.CTkLabel(bottom, text="Prêt", text_color=MUTED, anchor="w")
        self.status_lbl.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
        grey = dict(fg_color=ROW, hover_color=("#e4e4e8", "#2e2e35"), text_color=TEXT, height=38)
        ctk.CTkButton(bottom, text="Historique", width=100, command=self.show_history, **grey).grid(row=1, column=1, padx=4, pady=(0, 14))
        ctk.CTkButton(bottom, text="Ouvrir le dossier", width=130, command=self.open_dest, **grey).grid(row=1, column=2, padx=4, pady=(0, 14))
        self.btn_cancel = ctk.CTkButton(bottom, text="Annuler", width=100, state="disabled", command=self.cancel, **grey)
        self.btn_cancel.grid(row=1, column=3, padx=4, pady=(0, 14))
        self.btn_download = ctk.CTkButton(
            bottom, text="Télécharger", width=170, height=38, state="disabled", fg_color=ORANGE,
            hover_color=ORANGE_HOVER, font=ctk.CTkFont(size=14, weight="bold"), command=self.start_download,
        )
        self.btn_download.grid(row=1, column=4, padx=(4, 16), pady=(0, 14))

    def _bind_keys(self):
        mod = "Command" if sys.platform == "darwin" else "Control"
        self.url_entry.bind("<Return>", lambda _e: self.start_analyze())
        self.bind_all(f"<{mod}-a>", self._kb_select_all)
        self.bind_all(f"<{mod}-f>", lambda _e: self.search_entry.focus_set())
        self.bind_all(f"<{mod}-Return>", lambda _e: self.start_download())
        self.bind_all("<Escape>", lambda _e: self.cancel())

    def _kb_select_all(self, _e):
        if isinstance(self.focus_get(), (tk.Entry, tk.Text)):
            return None
        self.set_all(True)
        return "break"

    # ------------------------------------------------------------- Prefs #
    def _dir_text(self):
        return trunc(self.cfg["dest_dir"], 38)

    def _save_prefs(self):
        self.cfg["quality"] = self.quality_menu.get()
        self.cfg["skip_existing"] = bool(self.skip_var.get())
        save_config(self.cfg)

    def _toggle_theme(self):
        theme = "light" if self.theme_switch.get() else "dark"
        ctk.set_appearance_mode(theme)
        self.cfg["theme"] = theme
        save_config(self.cfg)

    def choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.cfg["dest_dir"], title="Dossier de destination")
        if d:
            self.cfg["dest_dir"] = d
            self.dir_lbl.configure(text=self._dir_text())
            save_config(self.cfg)

    def open_dest(self, path=None):
        path = path or self.cfg["dest_dir"]
        os.makedirs(path, exist_ok=True)
        os.system(f'open "{path}"')

    # ----------------------------------------------------------- Analyse #
    def set_status(self, text, color=None):
        self.status_lbl.configure(text=text, text_color=color or MUTED)

    def _set_busy(self, busy):
        self.busy = busy
        self.btn_analyze.configure(state="disabled" if busy else "normal")
        self.btn_cancel.configure(state="normal" if busy else "disabled")
        self.update_counter()

    def start_analyze(self):
        if self.busy:
            return
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Lien manquant", "Colle un lien SoundCloud d'abord !")
            return
        self.stop_preview()
        self.gen += 1
        self.job_total = 0
        self._clear_rows()
        self._set_busy(True)
        self.btn_cancel.configure(state="disabled")
        self.global_bar.configure(mode="indeterminate")
        self.global_bar.start()
        self.set_status("Analyse du lien…", ORANGE)
        threading.Thread(target=self._analyze_worker, args=(url, self.gen), daemon=True).start()

    def _analyze_worker(self, url, gen):
        opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "skip_download": True}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info:
                raise RuntimeError("Aucun résultat pour ce lien.")
            tracks = []
            if info.get("entries") is not None:
                folder = info.get("title") or info.get("uploader") or "SoundCloud"
                for e in info["entries"]:
                    if not e:
                        continue
                    u = e.get("webpage_url") or e.get("url")
                    if not u:
                        continue
                    title = e.get("title") or u.rstrip("/").split("/")[-1].replace("-", " ")
                    tracks.append(Track(u, title, e.get("uploader") or e.get("channel") or "", e.get("duration"), pick_thumb(e)))
            else:
                folder = info.get("uploader") or "SoundCloud"
                u = info.get("webpage_url") or url
                tracks.append(Track(u, info.get("title") or "Sans titre", info.get("uploader") or "", info.get("duration"), pick_thumb(info)))
            if not tracks:
                raise RuntimeError("Aucun son trouvé dans ce lien.")
            self.q.put(("tracks", gen, folder, tracks))
        except Exception as e:
            self.q.put(("analyze_error", gen, str(e)))

    def _clear_rows(self):
        for r in self.rows:
            r.destroy()
        self.rows.clear()
        self.tracks.clear()
        self.pending.clear()
        self.global_bar.set(0)
        self.update_counter()

    def _build_rows_chunk(self, gen):
        if gen != self.gen:
            return
        for _ in range(12):
            if not self.pending:
                break
            idx, tr = self.pending.pop(0)
            row = TrackRow(self.list_frame, self, idx, tr)
            row.grid(row=idx + 1, column=0, sticky="ew", padx=4, pady=3)
            self.rows.append(row)
            if tr.thumb_url:
                self.pool.submit(self._thumb_worker, gen, idx, tr.thumb_url)
        self.apply_filter()
        self.update_counter()
        if self.pending:
            self.after(15, self._build_rows_chunk, gen)
        else:
            self.set_status(f"{len(self.tracks)} son(s) trouvé(s) – coche ceux que tu veux.", GREEN)

    def _thumb_worker(self, gen, idx, url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                img = Image.open(BytesIO(r.read())).convert("RGB")
            w, h = img.size
            s = min(w, h)
            img = img.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s)).resize((THUMB * 2, THUMB * 2), Image.LANCZOS)
            self.q.put(("thumb", gen, idx, rounded(img, THUMB * 2 // 5)))
        except Exception:
            pass

    # ------------------------------------------------- Sélection / filtre #
    def apply_filter(self):
        q = self.search_var.get().strip().lower()
        for r in self.rows:
            show = q in r.search_text
            if show and not r.visible:
                r.grid()
            elif not show and r.visible:
                r.grid_remove()
            r.visible = show

    def set_all(self, value):
        for r in self.rows:
            if r.visible:
                r.var.set(value)
        self.update_counter()

    def update_counter(self):
        total = len(self.tracks)
        sel = sum(1 for r in self.rows if r.is_selected())
        self.counter_lbl.configure(text=f"{sel} / {total} sélectionnés")
        ok = sel > 0 and not self.busy
        self.btn_download.configure(
            state="normal" if ok else "disabled", text=f"Télécharger ({sel})" if sel else "Télécharger"
        )

    # ------------------------------------------------------ Téléchargement #
    def start_download(self):
        if self.busy:
            return
        jobs = [(r.idx, r.track) for r in self.rows if r.is_selected()]
        if not jobs:
            return
        self.stop_preview()
        os.makedirs(self.cfg["dest_dir"], exist_ok=True)
        self._save_prefs()
        self.cancel_evt.clear()
        self.results = {}
        self.job_ids = [i for i, _ in jobs]
        self.job_total, self.job_done = len(jobs), 0
        for r in self.rows:
            r.set_progress(None)
            r.set_status("En attente" if r.is_selected() else "")
        self.global_bar.stop()
        self.global_bar.configure(mode="determinate")
        self.global_bar.set(0)
        self._set_busy(True)
        self.set_status(f"Téléchargement de {len(jobs)} son(s)…", ORANGE)
        quality = QUALITIES[self.quality_menu.get()]
        threading.Thread(
            target=self._download_worker,
            args=(jobs, self.cfg["dest_dir"], quality, bool(self.skip_var.get()), self.folder_name),
            daemon=True,
        ).start()

    def _download_worker(self, jobs, dest, quality, skip, folder):
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        safe_folder = yt_dlp.utils.sanitize_filename(folder).replace("%", "%%")
        for idx, tr in jobs:
            if self.cancel_evt.is_set():
                self.q.put(("state", idx, "cancelled", ""))
                continue
            self.q.put(("state", idx, "run", ""))

            def on_dl(d, idx=idx):
                if self.cancel_evt.is_set():
                    raise yt_dlp.utils.DownloadCancelled()
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    if total:
                        frac = d.get("downloaded_bytes", 0) / total
                    elif d.get("fragment_count"):
                        frac = d.get("fragment_index", 0) / d["fragment_count"]
                    else:
                        return
                    self.q.put(("progress", idx, 0.85 * frac, f"Téléchargement {int(frac * 100)}%"))

            def on_pp(d, idx=idx):
                if d.get("status") == "started":
                    self.q.put(("progress", idx, 0.92, "Conversion MP3…"))

            opts = {
                "format": "bestaudio/best",
                "ffmpeg_location": ffmpeg,
                "outtmpl": os.path.join(dest.replace("%", "%%"), safe_folder, "%(title)s.%(ext)s"),
                "writethumbnail": True,
                "postprocessors": [
                    {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": quality},
                    {"key": "FFmpegMetadata"},
                    {"key": "EmbedThumbnail"},
                ],
                "progress_hooks": [on_dl],
                "postprocessor_hooks": [on_pp],
                "quiet": True,
                "no_warnings": True,
            }
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    if skip:
                        info = ydl.extract_info(tr.url, download=False)
                        target = os.path.splitext(ydl.prepare_filename(info))[0] + ".mp3"
                        if os.path.exists(target):
                            self.q.put(("state", idx, "skipped", ""))
                            continue
                    ydl.download([tr.url])
                self.q.put(("state", idx, "done", ""))
            except Exception as e:
                if self.cancel_evt.is_set():
                    self.q.put(("state", idx, "cancelled", ""))
                else:
                    msg = str(e).replace("ERROR: ", "").strip().splitlines()[0] if str(e).strip() else "Erreur inconnue"
                    self.q.put(("state", idx, "error", msg))
        self.q.put(("finished",))

    def cancel(self):
        if self.busy and self.job_total:
            self.cancel_evt.set()
            self.set_status("Annulation…", RED)

    def _handle_state(self, idx, state, msg):
        row = next((r for r in self.rows if r.idx == idx), None)
        if state == "run":
            if row:
                row.set_status("Démarrage…", ORANGE)
                row.set_progress(0.02)
            return
        self.results[idx] = (state, msg)
        self.job_done += 1
        if row:
            labels = {
                "done": ("✓ Terminé", GREEN),
                "skipped": ("Déjà présent", MUTED),
                "cancelled": ("Annulé", MUTED),
                "error": ("✗ Erreur", RED),
            }
            text, color = labels[state]
            row.set_status(text, color)
            row.set_progress(1.0 if state in ("done", "skipped") else None)
        self.global_bar.set(self.job_done / max(1, self.job_total))

    def _handle_finished(self):
        done = [i for i, (s, _) in self.results.items() if s == "done"]
        errs = [(i, m) for i, (s, m) in self.results.items() if s == "error"]
        skipped = [i for i, (s, _) in self.results.items() if s == "skipped"]
        cancelled = self.cancel_evt.is_set()
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        by_idx = {r.idx: r.track for r in self.rows}
        for i in done:
            self.cfg["history"].insert(0, {"t": now, "title": by_idx[i].title, "folder": self.folder_name, "path": os.path.join(self.cfg["dest_dir"], self.folder_name)})
        self.cfg["history"] = self.cfg["history"][:300]
        save_config(self.cfg)
        self._set_busy(False)
        summary = f"{len(done)} réussi(s)"
        if skipped:
            summary += f", {len(skipped)} ignoré(s)"
        if errs:
            summary += f", {len(errs)} échec(s)"
        if cancelled:
            summary = "Annulé – " + summary
        self.set_status(summary, RED if errs else GREEN)
        if errs:
            detail = "\n".join(f"• {trunc(by_idx[i].title, 50)} : {trunc(m, 80)}" for i, m in errs[:10])
            messagebox.showwarning("Terminé avec des erreurs", f"{summary}\n\n{detail}")
        elif done and not cancelled:
            messagebox.showinfo("C'est prêt !", f"{summary}\n\nDossier : {self.cfg['dest_dir']}")
        if done and not cancelled:
            self.open_dest(os.path.join(self.cfg["dest_dir"], self.folder_name))

    # ------------------------------------------------------------ Aperçu #
    def toggle_preview(self, idx):
        if self.preview_idx == idx:
            self.stop_preview()
            return
        if not HAS_PYGAME:
            messagebox.showinfo("Aperçu indisponible", "Installe pygame-ce pour activer l'aperçu :\n\npip install pygame-ce")
            return
        self.stop_preview()
        row = next((r for r in self.rows if r.idx == idx), None)
        if not row:
            return
        self.preview_token += 1
        self.preview_idx = idx
        row.set_play("…")
        threading.Thread(target=self._preview_worker, args=(self.preview_token, idx, row.track.url), daemon=True).start()

    def _preview_worker(self, token, idx, url):
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "format": "bestaudio/best"}) as ydl:
                info = ydl.extract_info(url, download=False)
            stream = info.get("url") or info["requested_formats"][0]["url"]
            out = os.path.join(self.tmpdir, f"preview_{token}.wav")
            cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-t", "30", "-i", stream,
                   "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", out]
            subprocess.run(cmd, check=True, timeout=90, creationflags=no_window_flags(), capture_output=True)
            self.q.put(("preview_ready", token, idx, out))
        except Exception as e:
            self.q.put(("preview_error", token, idx, str(e)))

    def stop_preview(self):
        self.preview_token += 1
        if self.mixer_ready:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except Exception:
                pass
        if self.preview_idx is not None:
            row = next((r for r in self.rows if r.idx == self.preview_idx), None)
            if row:
                row.set_play("▶")
        self.preview_idx = None

    # --------------------------------------------------------- Historique #
    def show_history(self):
        win = ctk.CTkToplevel(self)
        win.title("Historique")
        win.geometry("640x520")
        win.configure(fg_color=BG)
        win.after(100, win.lift)
        win.columnconfigure(0, weight=1)
        win.rowconfigure(0, weight=1)
        frame = ctk.CTkScrollableFrame(win, fg_color=CARD, corner_radius=14)
        frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 8))
        frame.columnconfigure(0, weight=1)
        hist = self.cfg.get("history", [])
        if not hist:
            ctk.CTkLabel(frame, text="Aucun téléchargement pour l'instant.", text_color=MUTED).grid(pady=40)
        for i, h in enumerate(hist):
            row = ctk.CTkFrame(frame, fg_color=ROW, corner_radius=10)
            row.grid(row=i, column=0, sticky="ew", pady=3, padx=4)
            row.columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text="♪  " + trunc(h["title"], 58), anchor="w", text_color=TEXT, font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 0))
            ctk.CTkLabel(row, text=f"{h['t']} · {h['folder']}", anchor="w", text_color=MUTED, font=ctk.CTkFont(size=12)).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))
            ctk.CTkButton(row, text="Ouvrir", width=70, fg_color=ORANGE, hover_color=ORANGE_HOVER, command=lambda p=h.get("path"): self.open_dest(p)).grid(row=0, column=1, rowspan=2, padx=10)

        def clear():
            self.cfg["history"] = []
            save_config(self.cfg)
            win.destroy()

        ctk.CTkButton(win, text="Vider l'historique", fg_color=ROW, hover_color=("#e4e4e8", "#2e2e35"), text_color=TEXT, command=clear).grid(row=1, column=0, pady=(0, 16))

    # --------------------------------------------------- Boucle d'événements #
    def _poll(self):
        try:
            while True:
                ev = self.q.get_nowait()
                kind = ev[0]
                if kind == "tracks":
                    _, gen, folder, tracks = ev
                    if gen != self.gen:
                        continue
                    self.global_bar.stop()
                    self.global_bar.configure(mode="determinate")
                    self.global_bar.set(0)
                    self.empty_lbl.grid_remove()
                    self.folder_name = folder
                    self.tracks = tracks
                    self.pending = list(enumerate(tracks))
                    self._set_busy(False)
                    self._build_rows_chunk(gen)
                elif kind == "analyze_error":
                    _, gen, msg = ev
                    if gen != self.gen:
                        continue
                    self.global_bar.stop()
                    self.global_bar.configure(mode="determinate")
                    self.global_bar.set(0)
                    self._set_busy(False)
                    self.empty_lbl.grid()
                    self.set_status("Impossible d'analyser ce lien", RED)
                    messagebox.showerror("Erreur", f"Impossible d'analyser ce lien.\n\nDétail : {msg}")
                elif kind == "thumb":
                    _, gen, idx, pil = ev
                    if gen == self.gen:
                        row = next((r for r in self.rows if r.idx == idx), None)
                        if row:
                            row.set_thumb(ctk.CTkImage(pil, size=(THUMB, THUMB)))
                elif kind == "progress":
                    _, idx, frac, text = ev
                    row = next((r for r in self.rows if r.idx == idx), None)
                    if row:
                        row.set_progress(frac)
                        row.set_status(text, ORANGE)
                    self.global_bar.set((self.job_done + frac) / max(1, self.job_total))
                elif kind == "state":
                    self._handle_state(ev[1], ev[2], ev[3])
                elif kind == "finished":
                    self._handle_finished()
                elif kind == "preview_ready":
                    _, token, idx, path = ev
                    if token != self.preview_token:
                        continue
                    try:
                        if not self.mixer_ready:
                            pygame.mixer.init()
                            self.mixer_ready = True
                        pygame.mixer.music.load(path)
                        pygame.mixer.music.play()
                        row = next((r for r in self.rows if r.idx == idx), None)
                        if row:
                            row.set_play("■")
                    except Exception as e:
                        self.stop_preview()
                        self.set_status(f"Aperçu impossible : {trunc(str(e), 60)}", RED)
                elif kind == "preview_error":
                    _, token, idx, msg = ev
                    if token == self.preview_token:
                        self.stop_preview()
                        self.set_status("Aperçu impossible pour ce son", RED)
        except queue.Empty:
            pass
        if self.preview_idx is not None and self.mixer_ready:
            try:
                row = next((r for r in self.rows if r.idx == self.preview_idx), None)
                if row and row.play_btn.cget("text") == "■" and not pygame.mixer.music.get_busy():
                    self.stop_preview()
            except Exception:
                pass
        self.after(100, self._poll)

    def _on_close(self):
        self.cancel_evt.set()
        self.stop_preview()
        try:
            if self.mixer_ready:
                pygame.mixer.quit()
        except Exception:
            pass
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
