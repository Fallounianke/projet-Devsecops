#!/usr/bin/env python3

import io
import json
import pathlib
import time
import urllib.parse
import urllib.request
import urllib.error
from difflib import SequenceMatcher

from PIL import Image, UnidentifiedImageError


# ==========================================
# CONFIGURATION
# ==========================================

ROOT = pathlib.Path(__file__).resolve().parent

CAT = json.loads(
    (ROOT / "catalogue.json").read_text(encoding="utf-8")
)

DELAY = 3

# Protection contre les images trop volumineuses
MAX_DOWNLOAD_BYTES = 15 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000

# Chemins d'affiches TMDB
KNOWN = {
    "The Godfather": "3bhkrj58Vtu7enYsRolD1fZdja1",
    "The Shawshank Redemption": "9cqNxx0GxF0bflZmeSMuL5tnGzr",
    "The Dark Knight": "qJ2tW6WMUDux911r6m7haRef0WH",
    "Pulp Fiction": "d5iIlFn5s0ImszYzBPb8JPIfbXD",
    "Schindler's List": "sF1U4EUQS8YHUYjNl3pMGNIQyr0",
    "Forrest Gump": "arw2vcBveWOVZr6pxd9XTd1TdQa",
    "Inception": "oYuLEt3zVCKq57qu2F8dT7NIa6f",
    "Interstellar": "gEU2QniE6E77NI6lCU6MxlNBvIx",
    "The Matrix": "f89U3ADr1oiB1s9GkdPOEpXUk5H",
    "Psycho": "yz4QVqPx3h1hD1DfqqQkCq3rmxW",

    # Deux affiches manquantes — chemins à vérifier
    "Se7en": "6yoghtyTpznpBik8EngEmJskVUO",
    "Star Wars: The Empire Strikes Back": "nNAeTmF4CtdSgMDplXTDPOpYzsX",
}


# ==========================================
# HTTP
# ==========================================

class RateLimitError(Exception):
    pass


def get(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "CineRankEducational/1.0 "
                "(personal educational movie catalogue)"
            ),
            "Accept": "application/json,image/*",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:

            content_length = response.headers.get("Content-Length")

            if (
                content_length
                and int(content_length) > MAX_DOWNLOAD_BYTES
            ):
                raise ValueError("Fichier trop volumineux")

            data = response.read(MAX_DOWNLOAD_BYTES + 1)

            if len(data) > MAX_DOWNLOAD_BYTES:
                raise ValueError("Téléchargement trop volumineux")

            return data

    except urllib.error.HTTPError as error:

        if error.code == 429:
            retry_after = error.headers.get(
                "Retry-After",
                "non précisé"
            )

            raise RateLimitError(
                f"HTTP 429 - Too Many Requests. "
                f"Retry-After: {retry_after}"
            )

        raise


# ==========================================
# RECHERCHE IMDb
# ==========================================

def normalize(text):
    return "".join(
        char.lower()
        for char in text
        if char.isalnum()
    )


def find_imdb_poster(title, year):
    query = urllib.parse.quote(title)
    first = urllib.parse.quote(title[0].lower())

    url = (
        f"https://v2.sg.media-imdb.com/suggestion/"
        f"{first}/{query}.json"
    )

    data = json.loads(get(url))
    candidates = data.get("d", [])

    best_url = None
    best_score = 0

    for movie in candidates:

        candidate_title = movie.get("l", "")
        candidate_year = movie.get("y")

        image = movie.get("i", {})

        image_url = (
            image.get("imageUrl")
            if isinstance(image, dict)
            else None
        )

        if not image_url:
            continue

        similarity = SequenceMatcher(
            None,
            normalize(title),
            normalize(candidate_title)
        ).ratio()

        if similarity < 0.90:
            continue

        if candidate_year is not None:
            try:
                if abs(int(candidate_year) - int(year)) > 1:
                    continue
            except (TypeError, ValueError):
                continue

        if similarity > best_score:
            best_score = similarity
            best_url = image_url

    return best_url


# ==========================================
# TRAITEMENT IMAGE
# ==========================================

def download_poster(url, destination):

    data = get(url)

    with Image.open(io.BytesIO(data)) as source:

        width, height = source.size

        if width * height > MAX_IMAGE_PIXELS:
            raise ValueError(
                f"Image trop grande : {width}x{height}"
            )

        if width < 120 or height < 120:
            raise ValueError("Image trop petite")

        if width > height * 1.2:
            raise ValueError(
                "Image horizontale, probablement pas une affiche"
            )

        source.load()
        image = source.convert("RGB")

    image.thumbnail((420, 630))

    temporary = destination.with_suffix(".tmp.webp")

    image.save(
        temporary,
        "WEBP",
        quality=80,
        method=5
    )

    temporary.replace(destination)


# ==========================================
# RAPPORT
# ==========================================

def report_results(stopped=False):

    saved = [
        item["title"]
        for item in CAT
        if (ROOT / item["filename"]).is_file()
    ]

    missing = [
        item["title"]
        for item in CAT
        if not (ROOT / item["filename"]).is_file()
    ]

    report = {
        "total": len(CAT),
        "downloaded": len(saved),
        "missing_count": len(missing),
        "stopped_by_rate_limit": stopped,
        "saved": saved,
        "missing": missing,
    }

    (ROOT / "download-report.json").write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print("\n=======================================")
    print(f"Total movies: {len(CAT)}")
    print(f"Downloaded: {len(saved)}")
    print(f"Missing: {len(missing)}")
    print("=======================================")


# ==========================================
# MAIN
# ==========================================

def main():

    print("\n🎬 CINERANK - POSTER DOWNLOADER")
    print("Sources : TMDB + IMDb")
    print("=" * 45)

    stopped = False

    try:

        for item in CAT:

            rank = item["rank"]
            title = item["title"]
            year = item["year"]

            destination = ROOT / item["filename"]

            # Ne jamais écraser une affiche existante
            if destination.is_file():

                print(f"SKIP {rank:03} {title}")
                continue

            try:

                poster_path = KNOWN.get(title)

                if poster_path:

                    url = (
                        "https://image.tmdb.org/t/p/w500/"
                        + poster_path
                        + ".jpg"
                    )

                    source = "TMDB"

                else:

                    url = find_imdb_poster(title, year)
                    source = "IMDb"

                if not url:

                    print(
                        f"MISSING {rank:03} {title}: "
                        "aucune affiche trouvée"
                    )

                    continue

                download_poster(url, destination)

                print(
                    f"OK {rank:03} {title} [{source}]"
                )

            except RateLimitError as error:

                print(
                    f"STOP {rank:03} {title}: {error}"
                )

                stopped = True
                break

            except (
                urllib.error.HTTPError,
                urllib.error.URLError,
                ValueError,
                UnidentifiedImageError,
                OSError,
                json.JSONDecodeError,
            ) as error:

                print(
                    f"MISSING {rank:03} {title}: {error}"
                )

            finally:
                time.sleep(DELAY)

    except KeyboardInterrupt:
        print("\nTéléchargement interrompu.")

    finally:
        report_results(stopped)


if __name__ == "__main__":
    main()
