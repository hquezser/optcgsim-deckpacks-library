"""Contrat du LOT C — sitegen/packs.py. FIGÉ : le worker C implémente, ne modifie pas.

Interface attendue :
    packs.META_WINDOW_DAYS: int          # 60
    packs.META_MAX_DECKS: int            # 40
    packs.meta_pairs(site) -> tuple[tuple[Tournament, Deck], ...]
    packs.build_pack(name, pairs, author=...) -> dict     # manifeste deckpack v1
    packs.write_packs(site, out: Path) -> list[Path]      # renvoie les chemins écrits
"""

from __future__ import annotations

import json

import pytest

from sitegen import packs


# --- constantes de la spec -----------------------------------------------------------

def test_constantes_conformes_a_la_spec():
    assert packs.META_WINDOW_DAYS == 60
    assert packs.META_MAX_DECKS == 40


# --- build_pack ----------------------------------------------------------------------

def test_build_pack_produit_un_manifeste_v1(site):
    biel = next(t for t in site.tournaments if t.slug.endswith("bielefeld"))
    pack = packs.build_pack("Test", tuple((biel, d) for d in biel.decks))

    assert pack["schema_version"] == 1
    assert pack["name"] == "Test"
    assert len(pack["decks"]) == 3
    # Une seule source par deck, et c'est `text` (inline) : un pack autoportant s'importe
    # sans réseau, contrairement à `source_url`.
    for entry in pack["decks"]:
        assert set(entry) <= {"name", "tags", "text"}
        assert "text" in entry and entry["text"]


def test_build_pack_reexporte_le_text_verbatim(site):
    biel = next(t for t in site.tournaments if t.slug.endswith("bielefeld"))
    enel = next(d for d in biel.decks if d.placement == 1)
    pack = packs.build_pack("Test", ((biel, enel),))
    assert pack["decks"][0]["text"] == enel.text


# --- meta_pairs ----------------------------------------------------------------------

def test_meta_exclut_hors_fenetre_et_non_parses(site):
    """Fixture : réf = 2026-07-04, fenêtre 60j -> le tournoi d'avril sort.

    Restent les 2 decks parsés de Bielefeld (le 3e n'est pas parsable).
    """
    pairs = packs.meta_pairs(site)
    assert {t.slug for t, _ in pairs} == {"2026-07-04-regional-bielefeld"}
    assert [d.placement for _, d in pairs] == [1, 2]
    assert all(d.parsed for _, d in pairs)


def test_meta_vide_si_corpus_sans_date():
    from sitegen.model import Site, Tournament
    assert packs.meta_pairs(Site(tournaments=(
        Tournament("sans-date", "X", None, "", "", ()),))) == ()


# --- write_packs ---------------------------------------------------------------------

@pytest.fixture
def written(site, tmp_path):
    paths = packs.write_packs(site, tmp_path)
    return tmp_path, paths


def test_write_packs_emet_les_chemins_du_contrat(written):
    out, paths = written
    rel = {p.relative_to(out).as_posix() for p in paths}
    assert "tournois/2026-07-04-regional-bielefeld/deckpack.json" in rel
    assert "leaders/purple-enel/deckpack.json" in rel
    assert "meta/deckpack.json" in rel
    # un pack d'un seul deck par deck, y compris le non parsable
    assert "tournois/2026-07-04-regional-bielefeld/decks/01-purple-enel-luka-forjan.json" in rel
    assert ("tournois/2026-07-04-regional-bielefeld/decks/"
            "xx-nom-sans-structure-reconnaissable.json") in rel
    # tous les chemins annoncés existent réellement
    assert all(p.exists() for p in paths)


def test_write_packs_pack_leader_agrege_les_tournois(written):
    out, _ = written
    pack = json.loads((out / "leaders" / "purple-enel" / "deckpack.json").read_text())
    # Enel apparaît dans les deux tournois de la fixture.
    assert len(pack["decks"]) == 2
    assert pack["decks"][0]["name"].startswith("Purple Enel")


def test_write_packs_meta_nomme_avec_la_date_de_reference(written):
    out, _ = written
    pack = json.loads((out / "meta" / "deckpack.json").read_text())
    assert pack["name"] == "Méta 2026-07"
    assert pack["author"] == "optcgsim-deckpacks-library"
    assert len(pack["decks"]) == 2


def test_write_packs_est_deterministe(site, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    packs.write_packs(site, a)
    packs.write_packs(site, b)
    for pa in sorted(a.rglob("*.json")):
        pb = b / pa.relative_to(a)
        assert pa.read_bytes() == pb.read_bytes(), f"sortie non déterministe : {pa}"
