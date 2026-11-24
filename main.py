import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import imageio_ffmpeg
import yt_dlp


class SoundCloudDownloader:

  def __init__(self, root):
    self.root = root
    self.root.title("SoundCloud Downloader")
    self.root.geometry("460x230")
    self.root.resizable(False, False)

    # Dossier de sortie sur le Bureau
    self.dest_dir = os.path.expanduser("~/Desktop/Musiques_SoundCloud")
    os.makedirs(self.dest_dir, exist_ok=True)

    # Interface
    tk.Label(
        root,
        text="Colle le lien de la playlist ou du son SoundCloud :",
        font=("Helvetica", 13),
    ).pack(pady=(20, 8))

    self.url_entry = tk.Entry(root, width=48, font=("Helvetica", 12))
    self.url_entry.pack(pady=5, ipady=4)
    self.url_entry.focus()

    self.btn_download = tk.Button(
        root,
        text="Télécharger en MP3",
        font=("Helvetica", 12, "bold"),
        command=self.start_download,
    )
    self.btn_download.pack(pady=15)

    self.progress = ttk.Progressbar(root, mode="indeterminate", length=360)
    self.progress.pack(pady=5)

    self.status_label = tk.Label(
        root, text="Prêt", font=("Helvetica", 11), fg="gray"
    )
    self.status_label.pack(pady=5)

  def start_download(self):
    url = self.url_entry.get().strip()
    if not url:
      messagebox.showwarning(
          "Lien manquant", "Colle un lien SoundCloud d'abord !"
      )
      return

    self.btn_download.config(state="disabled")
    self.progress.start(10)
    self.status_label.config(text="Téléchargement en cours...", fg="blue")

    threading.Thread(
        target=self.download_worker, args=(url,), daemon=True
    ).start()

  def download_worker(self, url):
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    ydl_opts = {
        "format": "bestaudio/best",
        "ffmpeg_location": ffmpeg_path,
        "outtmpl": os.path.join(
            self.dest_dir, "%(playlist_title,artist)s", "%(title)s.%(ext)s"
        ),
        "writethumbnail": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",
            },
            {"key": "EmbedThumbnail"},
            {"key": "FFmpegMetadata"},
        ],
        "quiet": True,
        "no_warnings": True,
    }

    try:
      with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
      self.root.after(0, self.on_success)
    except Exception as e:
      self.root.after(0, self.on_error, str(e))

  def on_success(self):
    self.progress.stop()
    self.btn_download.config(state="normal")
    self.url_entry.delete(0, tk.END)
    self.status_label.config(text="Terminé !", fg="green")
    messagebox.showinfo(
        "C'est prêt !",
        "Tous les sons sont dans le dossier Musiques_SoundCloud sur le"
        " Bureau.",
    )
    os.system(f'open "{self.dest_dir}"')

  def on_error(self, err):
    self.progress.stop()
    self.btn_download.config(state="normal")
    self.status_label.config(text="Erreur lors du téléchargement", fg="red")
    messagebox.showerror(
        "Erreur", f"Impossible de télécharger ce lien.\n\nDétail : {err}"
    )


if __name__ == "__main__":
  root = tk.Tk()
  app = SoundCloudDownloader(root)
  root.mainloop()