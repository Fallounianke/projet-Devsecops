CINERANK posters — 100 movies

The ZIP does NOT contain 100 real posters: network access to image hosts was unavailable when this archive was created.
Run this on your Linux server (internet required):
  cd /home/master/projet_Devsecops/app/public/posters
  python3 -m pip install --user Pillow
  python3 download_posters.py

The downloader attempts 10 known poster CDN URLs and Wikipedia thumbnails for remaining films. Wikipedia images are NOT necessarily theatrical posters; review images and permissions before publication. Missing items are listed in download-report.json. Add any verified image as 001.webp, 002.webp ... 100.webp.

The included index.html uses a local image when present, falling back to existing remote lookup when missing. No Kubernetes configuration changes needed.
