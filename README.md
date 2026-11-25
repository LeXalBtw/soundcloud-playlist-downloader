# SoundCloud Downloader

Application de bureau pour télécharger des sons, playlists ou profils SoundCloud au format MP3 avec leurs pochettes et métadonnées. Colle un lien, sélectionne tes morceaux et lance le téléchargement.

## Télécharger

**[Accéder à la dernière version (Windows et macOS)](https://github.com/LeXalBtw/soundcloud/releases/latest)**

Choisis l'archive correspondant à ton ordinateur :

| Système | Fichier à télécharger |
| :--- | :--- |
| **Windows** | `SoundCloud-Downloader-windows.zip` |
| **Mac Apple Silicon** (puces M1, M2, M3, M4 — 2020 et après) | `SoundCloud-Downloader-mac-apple-silicon.zip` |
| **Mac Intel** (2019 et avant) | `SoundCloud-Downloader-mac-intel.zip` |

> **Tu ne sais pas quel Mac tu as ?**
> Clique sur le menu **Pomme ()** tout en haut à gauche de l'écran → **À propos de ce Mac**.
> - S'il est écrit *Puce : Apple M…* → télécharge la version **Apple Silicon**.
> - S'il est écrit *Processeur : Intel…* → télécharge la version **Intel**.

### Installation et premier lancement

* **Sur Windows :**
  1. Décompresse le fichier `.zip` et lance `SoundCloud Downloader.exe`.
  2. Si Windows SmartScreen bloque l'ouverture : clique sur **Informations complémentaires** → **Exécuter quand même**.

* **Sur macOS :**
  1. Décompresse le fichier `.zip` puis glisse `SoundCloud Downloader` dans ton dossier **Applications** (ou sur le Bureau).
  2. Au premier lancement, si macOS bloque l'application : clique sur **OK**, ouvre **Réglages Système → Confidentialité et sécurité**, descends tout en bas et clique sur **Ouvrir quand même** (ou fais **Clic droit → Ouvrir** sur l'icône).
  3. Si macOS affiche que l'application est « endommagée », ouvre le **Terminal** et exécute :
     ```bash
     xattr -cr "SoundCloud Downloader.app"
     ```

## Fonctionnalités

* **Aperçu complet :** récupération automatique des pochettes, titres, artistes et durées avant téléchargement.
* **Tri et sélection :** barre de recherche instantanée dans les grandes playlists et sélection morceau par morceau.
* **Écoute rapide :** aperçu audio de 30 secondes (`▶`) directement dans la liste pour vérifier un son.
* **Qualité au choix :** export MP3 en 128, 192, 256, 320 kbps ou VBR, avec pochette et tags intégrés.
* **Suivi et confort :** barre de progression individuelle par titre, bouton d'annulation, historique des téléchargements et thème clair ou sombre.

### Raccourcis clavier

| Raccourci | Action |
| :--- | :--- |
| `Entrée` | Analyser le lien collé |
| `Ctrl + A` / `Cmd + A` | Tout sélectionner |
| `Ctrl + F` / `Cmd + F` | Rechercher un titre |
| `Ctrl + Entrée` / `Cmd + Entrée` | Lancer le téléchargement |
| `Échap` | Annuler l'action en cours |

## Lancer depuis le code source

Nécessite Python 3.10 ou supérieur.

```bash
git clone [https://github.com/LeXalBtw/soundcloud.git](https://github.com/LeXalBtw/soundcloud.git)
cd soundcloud
pip install -r requirements.txt
python main.py
