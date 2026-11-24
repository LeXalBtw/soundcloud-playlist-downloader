# SoundCloud Downloader

Télécharge des sons ou des playlists SoundCloud en MP3 avec une interface moderne.

## Lancer
```
pip install -r requirements.txt
python make_logo.py   # (re)génère le logo dans assets/
python main.py
```

## Fonctions
- Analyse d'un lien (son, playlist, profil) avec pochettes, titres, artistes et durées
- Sélection des sons (cases, tout cocher / décocher, recherche)
- Qualité MP3 : 128 / 192 / 256 / 320 kbps ou VBR
- Aperçu audio de 30 s (▶)
- Progression par son + globale, annulation, récapitulatif des erreurs
- Dossier de destination mémorisé, historique, thème sombre / clair
- Raccourcis : Entrée (analyser), Ctrl/Cmd+A (tout cocher), Ctrl/Cmd+F (recherche), Ctrl/Cmd+Entrée (télécharger), Échap (annuler)

## Créer l'app (.app / .exe)
Onglet Actions → « Build app » → Run workflow. Les fichiers sont dans les artefacts.
