# SoundCloud Downloader

Colle un lien SoundCloud (son, playlist, profil), coche les sons que tu veux, télécharge en MP3.

## ⬇️ Download

**[→ Latest release (Windows + Mac)](https://github.com/LeXalBtw/soundcloud/releases/latest)**

Pick the file that matches your computer:

| Your computer | Download |
| --- | --- |
| **Windows** | `SoundCloud-Downloader-windows.zip` |
| **Mac with Apple Silicon** (M1, M2, M3, M4 — 2020 and later) | `SoundCloud-Downloader-mac-apple-silicon.zip` |
| **Mac with an Intel chip** (2019 and earlier) | `SoundCloud-Downloader-mac-intel.zip` |

**Not sure which Mac you have?** Click the Apple menu  → **About This Mac**. If you see *Chip: Apple M…* → download **Apple Silicon**. If you see *Processor: Intel…* → download **Intel**.

**Windows:** unzip, then run `SoundCloud Downloader.exe`. If SmartScreen blocks it, click *More info* → *Run anyway*.

**Mac:** unzip, then right-click the app → *Open*. If macOS says the app is "damaged", run this in Terminal:
```
xattr -cr "SoundCloud Downloader.app"
```

## Fonctions
- Pochettes, titres, artistes, durées
- Sélection des sons + recherche
- MP3 128 / 192 / 256 / 320 kbps ou VBR
- Aperçu de 30 s (▶)
- Progression par son, annulation, historique, thème sombre / clair
- Raccourcis : Entrée (analyser), Ctrl/Cmd+A, Ctrl/Cmd+F, Ctrl/Cmd+Entrée, Échap

## Lancer depuis le code
```
pip install -r requirements.txt
python main.py
```
