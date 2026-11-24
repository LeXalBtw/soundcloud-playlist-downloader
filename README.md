# SoundCloud Downloader

Desktop app to grab tracks, playlists, or full profiles from SoundCloud as tagged MP3s. Paste a link, pick the tracks you want, and download.

## Download

Grab the latest build for your OS from the **[Releases page](https://github.com/LeXalBtw/soundcloud/releases/latest)**:

* **Windows** — Download `SoundCloud-Downloader-windows.zip`, extract it, and run the `.exe`.
  *(If Windows SmartScreen pops up: click **More info** → **Run anyway**.)*
* **macOS** — Download `SoundCloud-Downloader-mac.zip`, extract it, then right-click `SoundCloud Downloader.app` → **Open**.
  *(On newer macOS versions, you may need to allow it under **System Settings → Privacy & Security → Open Anyway**. If macOS says the app is damaged, run `xattr -cr "SoundCloud Downloader.app"` in Terminal.)*

## Features

* **Track browser** — Fetches cover art, artist names, titles, and durations before downloading.
* **Filtering & selection** — Search within large playlists and pick individual tracks instead of downloading everything.
* **30-second preview** — Built-in audio preview (`▶`) to check tracks before saving them.
* **Audio quality** — Export to MP3 at 128, 192, 256, or 320 kbps, or VBR, with embedded cover art and metadata.
* **Queue & history** — Per-track progress, cancel button, download history, and light/dark themes.

### Keyboard shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Enter` | Fetch link |
| `Ctrl/Cmd + A` | Select all tracks |
| `Ctrl/Cmd + F` | Focus search bar |
| `Ctrl/Cmd + Enter` | Start download |
| `Esc` | Cancel / clear |

## Run from source

Requires Python 3.10+.

```bash
git clone [https://github.com/LeXalBtw/soundcloud.git](https://github.com/LeXalBtw/soundcloud.git)
cd soundcloud
pip install -r requirements.txt
python main.py
