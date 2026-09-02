"""Câblage CLI du générateur — FIGÉ.

Ce module ne contient aucune logique : il définit les **signatures** que chaque lot doit
implémenter, et l'ordre dans lequel elles sont appelées. C'est le contrat d'interface
entre les lots — le modifier reviendrait à changer le contrat de tous les autres.

    python3 -m sitegen.build --packs-dir ../optcgsim-deckpacks-data/packs --out dist
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_PACKS_DIR = "../optcgsim-deckpacks-data/packs"
DEFAULT_BASE_URL = "http://localhost:8000"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sitegen.build",
                                 description="Génère le site bibliothèque de deckpacks.")
    ap.add_argument("--packs-dir", default=DEFAULT_PACKS_DIR,
                    help=f"dossier des packs scrapés (défaut : {DEFAULT_PACKS_DIR})")
    ap.add_argument("--out", default="dist", help="dossier de sortie (défaut : dist)")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                    help="URL publique, utilisée dans les commandes d'import affichées")
    ap.add_argument("--card-link-base", default="", metavar="GABARIT",
                    help="gabarit d'URL contenant {id} : lie chaque identifiant de carte "
                         "(ex. https://onepiece.limitlesstcg.com/cards/{id}). Absent = "
                         "IDs nus, comportement par défaut")
    args = ap.parse_args(argv)

    # Imports locaux : le CLI doit pouvoir afficher --help même si un lot n'est pas encore
    # implémenté (les boucles de développement s'exécutent sur un arbre incomplet).
    from . import packs, parse, render

    # Lot A — corpus d'entrée -> modèle. Doit lever sur un pack illisible.
    try:
        site = parse.load_site(Path(args.packs_dir))
    except (OSError, ValueError) as e:
        print(f"erreur : corpus illisible ({e})", file=sys.stderr)
        return 1

    out = Path(args.out)

    # Lot C — les deckpack.json dérivés (tournois, leaders, méta, decks isolés).
    written = packs.write_packs(site, out)
    # Lot B — les pages HTML + la feuille de style.
    # Le lien par carte est opt-in (cf. SPEC § « Lien par carte »). On ne transmet le
    # paramètre que s'il est demandé : le chemin par défaut reste ainsi appelable sur un
    # `render.write_pages` qui ne le connaît pas encore, pour qu'un lot en cours
    # d'implémentation ne casse pas le build — ni le portillon transversal — de tout le
    # monde. Une fois le lot F terminé, la branche vide et la branche pleine sont
    # équivalentes ; garder la condition ne coûte rien et documente que le défaut est nu.
    lien = {"card_link_base": args.card_link_base} if args.card_link_base else {}
    written += render.write_pages(site, out, base_url=args.base_url.rstrip("/"), **lien)

    archetypes = site.leaders()
    print(f"{len(site.tournaments)} tournoi(s), "
          f"{sum(len(t.decks) for t in site.tournaments)} deck(s), "
          f"{len(archetypes)} archétype(s) -> {len(written)} fichier(s) dans {out}")
    for w in site.warnings:
        print(f"  ⚠ [{w.scope}] {w.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
