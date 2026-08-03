#!/usr/bin/env python3
"""Contrôles structurels sur `dist/` — FIGÉ. Appelé par verify.sh (étapes 3 à 5).

Ne teste pas les lots isolément (c'est le rôle de pytest) mais leur **cohérence
mutuelle** : le rendu et les packs doivent couvrir exactement le corpus qu'a produit le
parsing, sans page orpheline ni pack manquant.

    python3 orchestration/check_dist.py <dist> <packs-dir> <base-url>
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT.parent / "optcgsim-deckpacks" / "scripts" / "validate.py"

sys.path.insert(0, str(ROOT))

_MOTIFS_INTERDITS = ("<script", "@import", "cdn.", "fonts.google", "googletagmanager",
                     "google-analytics", "doubleclick")


def expected_paths(site) -> set[str]:
    """L'ensemble EXACT attendu dans dist/, dérivé du corpus (cf. spec § carte des URLs)."""
    out = {"index.html", "style.css", "meta/index.html", "meta/deckpack.json"}
    for t in site.tournaments:
        out.add(f"tournois/{t.slug}/index.html")
        out.add(f"tournois/{t.slug}/deckpack.json")
        for d in t.decks:
            out.add(f"tournois/{t.slug}/decks/{d.slug}.json")
    for aslug in site.leaders():
        out.add(f"leaders/{aslug}/index.html")
        out.add(f"leaders/{aslug}/deckpack.json")
    return out


def check_url_map(dist: Path, site) -> list[str]:
    actual = {p.relative_to(dist).as_posix() for p in dist.rglob("*") if p.is_file()}
    expected = expected_paths(site)
    errs = []
    for missing in sorted(expected - actual):
        errs.append(f"chemin manquant : {missing}")
    for extra in sorted(actual - expected):
        errs.append(f"chemin hors contrat : {extra}")
    return errs


# Ressources qu'un navigateur va chercher TOUT SEUL en affichant la page. C'est cela qui
# ferait fuiter l'IP du visiteur vers un tiers — pas un lien qu'il choisit de cliquer.
_SUBRESOURCE_RE = re.compile(
    r"""(?:src|srcset|data-src)\s*=\s*["']([^"']+)"""      # img, script, iframe, video…
    r"""|<link[^>]+href\s*=\s*["']([^"']+)"""              # feuilles, icônes, preload
    r"""|@import\s+(?:url\()?["']?([^"')\s;]+)"""          # @import CSS
    r"""|url\(\s*["']?([^"')]+)""",                        # url() CSS
    re.IGNORECASE,
)


def check_no_outbound(dist: Path, base_url: str) -> list[str]:
    """Invariant : une page produite ne déclenche aucune requête vers un tiers.

    Distinction essentielle, et c'est l'erreur que ce contrôle faisait au départ : une
    sous-ressource (`src`, `<link>`, `@import`, `url()`) est récupérée automatiquement à
    l'affichage et expose l'IP du visiteur à un tiers — un `<a href>` externe, non : il
    n'est suivi que si le visiteur clique, et c'est précisément le mécanisme d'attribution
    de la source (cf. AGENTS.md). Une URL en texte brut ne déclenche rien du tout.
    """
    errs = []
    for p in sorted(dist.rglob("*")):
        if p.suffix not in {".html", ".css"}:
            continue
        text = p.read_text(encoding="utf-8")
        rel = p.relative_to(dist).as_posix()

        for groups in _SUBRESOURCE_RE.findall(text):
            url = next((g for g in groups if g), "")
            if url.lower().startswith(("http://", "https://")) \
                    and not url.startswith(base_url):
                errs.append(f"{rel} : sous-ressource externe {url}")
        for motif in _MOTIFS_INTERDITS:
            if motif in text.lower():
                errs.append(f"{rel} : motif interdit « {motif} »")

        # Un lien externe est autorisé, mais ne doit pas fuiter le référent ni offrir
        # gratuitement du poids SEO à la source qu'on cite.
        for href in re.findall(r"""<a\s[^>]*href\s*=\s*["'](https?://[^"']+)["'][^>]*>""",
                               text, re.IGNORECASE):
            if href.startswith(base_url):
                continue
            balise = re.search(
                r"""<a\s[^>]*href\s*=\s*["']""" + re.escape(href) + r"""["'][^>]*>""",
                text, re.IGNORECASE)
            if balise and "noreferrer" not in balise.group(0).lower():
                errs.append(f"{rel} : lien externe sans rel=noreferrer -> {href}")
    return errs


def check_no_card_names(dist: Path) -> list[str]:
    """Invariant zéro-copyright : on n'affiche que des IDs.

    Heuristique volontairement grossière — on ne peut pas prouver l'absence de nom de
    carte, mais on peut détecter le cas réaliste : un champ importé d'une base de cartes.
    """
    errs = []
    for p in sorted(dist.rglob("*.json")):
        raw = p.read_text(encoding="utf-8")
        for champ in ('"card_name"', '"cardName"', '"effect"', '"ability"', '"image"',
                      '"image_url"', '"art"'):
            if champ in raw:
                errs.append(f"{p.relative_to(dist).as_posix()} : champ interdit {champ}")
    return errs


def check_packs_valid(dist: Path) -> list[str]:
    """Tout deckpack.json produit passe le validateur de la spec (arbitre unique)."""
    if not VALIDATOR.is_file():
        return [f"validateur introuvable : {VALIDATOR} (dépôt spec sibling absent ?)"]

    errs: list[str] = []
    pack_dirs = [p.parent for p in dist.rglob("deckpack.json")]
    if pack_dirs:
        r = subprocess.run([sys.executable, str(VALIDATOR), *map(str, pack_dirs)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            errs.append("validateur en échec sur les packs principaux :\n"
                        + (r.stdout + r.stderr).strip())

    # Les packs de deck isolé ne s'appellent pas deckpack.json : on les met en scène.
    singles = sorted(dist.glob("tournois/*/decks/*.json"))
    if singles:
        with tempfile.TemporaryDirectory() as tmp:
            staged = []
            for i, s in enumerate(singles):
                d = Path(tmp) / f"single-{i:04d}"
                d.mkdir()
                shutil.copy(s, d / "deckpack.json")
                staged.append(str(d))
            r = subprocess.run([sys.executable, str(VALIDATOR), *staged],
                               capture_output=True, text=True)
            if r.returncode != 0:
                errs.append(f"validateur en échec sur {len(singles)} pack(s) de deck "
                            f"isolé :\n" + (r.stdout + r.stderr).strip()[:2000])
    return errs


def check_studio_resolves(dist: Path) -> list[str]:
    """Chaque deck publié doit être RÉELLEMENT importable par le studio.

    Le validateur de la spec ne contrôle que la structure du manifeste — il a laissé passer
    des decklists que le simulateur refuse (ex. `9xOP16-042`, alors que le jeu plafonne à 4
    exemplaires). Or le site ne promet qu'une chose : un import en un clic. Publier un deck
    qui n'importe pas casse précisément cette promesse, donc c'est un échec dur ici.

    Ces défauts viennent du corpus scrapé en amont, pas du rendu : le correctif appartient
    à `optcgsim-deckpacks-data`, mais il doit être VISIBLE à chaque build plutôt que
    découvert par un utilisateur.
    """
    cli_root = ROOT.parent / "optcgsim-studio"
    if not (cli_root / "studio" / "cli.py").is_file():
        return [f"studio introuvable : {cli_root} — importabilité réelle non vérifiée"]

    errs: list[str] = []
    for pack_dir in sorted(p.parent for p in dist.rglob("deckpack.json")):
        # Chemin ABSOLU obligatoire : le sous-processus tourne avec cwd = dépôt studio, un
        # chemin relatif y désignerait autre chose (ou rien). Cette erreur a produit un faux
        # vert : la CLI échouait sans émettre de ligne « ✗ », donc rien n'était détecté.
        r = subprocess.run(
            [sys.executable, "-m", "studio.cli", "decks", "validate-pack",
             str(pack_dir.resolve())],
            capture_output=True, text=True, cwd=str(cli_root))
        lignes = (r.stdout + r.stderr).splitlines()
        echecs = [ln.strip().lstrip("✗ ") for ln in lignes if ln.lstrip().startswith("✗")]
        for e in echecs:
            errs.append(f"{pack_dir.relative_to(dist).as_posix()} : {e}")

        # Un code non nul SANS ligne « ✗ » signifie que la vérification n'a pas eu lieu —
        # à distinguer absolument de « rien à signaler », sinon le contrôle se contente de
        # ne rien voir et se déclare vert.
        if r.returncode != 0 and not echecs:
            errs.append(f"{pack_dir.relative_to(dist).as_posix()} : contrôle impossible "
                        f"(code {r.returncode}) — "
                        + " / ".join(lignes[-2:] or ["aucune sortie"]))
    return errs


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    dist, packs_dir, base_url = Path(argv[0]), Path(argv[1]), argv[2].rstrip("/")
    if not dist.is_dir():
        print(f"✗ dist introuvable : {dist}")
        return 1

    from sitegen import parse
    site = parse.load_site(packs_dir)

    etapes = [
        ("packs valides (validateur de la spec)", check_packs_valid(dist)),
        ("carte des URLs conforme au contrat", check_url_map(dist, site)),
        ("aucune requête réseau sortante", check_no_outbound(dist, base_url)),
        ("aucun contenu sous copyright", check_no_card_names(dist)),
        ("importabilité réelle par le studio", check_studio_resolves(dist)),
    ]

    ko = 0
    for label, errs in etapes:
        if errs:
            ko += 1
            print(f"✗ {label} — {len(errs)} problème(s)")
            for e in errs[:25]:
                print(f"    · {e}")
            if len(errs) > 25:
                print(f"    · … et {len(errs) - 25} autre(s)")
        else:
            print(f"✓ {label}")
    return 1 if ko else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
