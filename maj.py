#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Drive Universitaire — générateur du site (v2 · design académique)

Ce script est lancé automatiquement par GitHub (.github/workflows/site.yml)
à chaque fois qu'un fichier est ajouté ou modifié dans le dépôt.
Il génère index.html ; GitHub publie ensuite le site.

Pour tester sur ton ordinateur :  python3 maj.py   puis ouvrir index.html

Organisation des dossiers (inchangée) :
    cours/<FILIERE>/<ANNEE>/<Matière>/<Cours|TD|TP|Sujets...>/<fichiers>
    ex : cours/GI/L2/Base de données/TD/TD1.pdf
"""
import os
import re
import sys
import json
import datetime
import subprocess
import unicodedata

# ==========================================
# ⚙️ 1. PARAMÈTRES ET INTERRUPTEURS
# ==========================================
NOM_SIGNATURE_NORMAL      = "Farhan Abdoul-Mougni Farhan"
NOM_SIGNATURE_MAINTENANCE = "Farhan&Co"

# 🛑 Maintenance (True = site fermé avec panneau / False = ouvert)
MODE_MAINTENANCE = False

# 🔓 Mot de passe (True = code requis / False = accès direct)
#    ⚠️ Protection basique : les identifiants restent lisibles dans le code de la page.
MOT_DE_PASSE_ACTIF = False
LOGIN_REQUIS = os.environ.get("DRIVE_LOGIN") or "L1GI"
MDP_REQUIS   = os.environ.get("DRIVE_MDP") or "IAD2026"

# 📣 Bandeau sous l'en-tête ("" = pas de bandeau)
#    ex : "☀️ Plus que deux mois avant l'été !"  ou  "🌙 Ramadan Mubarak !"
MESSAGE_SPECIAL = ""

# 🆕 Un fichier est marqué « Nouveau » pendant ce nombre de jours après son ajout
NOUVEAU_JOURS = 14

GOOGLE_ANALYTICS_ID = "G-PWQN6WBSV4"
DOSSIER_COURS = "cours"

# ==========================================
# 📁 2. NOMS AFFICHÉS
# ==========================================
FILIERES = {
    "GI":  "Génie Informatique",
    "MRT": "Maintenance Réseau Télécom",
    "GE":  "Gestion des Entreprises",
}

# Clés « normalisées » : minuscules, sans accents, espaces/tirets → _
# Si une matière n'est pas listée, son nom de dossier est utilisé tel quel.
NOMS_MATIERES = {
    "algebre_lineaire":             "Algèbre linéaire",
    "algebre":                      "Algèbre linéaire",
    "algo_avancee":                 "Algorithmique avancée",
    "algorithme_avance":            "Algorithmique avancée",
    "algo":                         "Algorithmique",
    "system_exploitation":          "Système d'exploitation",
    "systeme_exploitation":         "Système d'exploitation",
    "web":                          "Développement Web",
    "dev_web":                      "Développement Web",
    "system_logique":               "Systèmes logiques",
    "systeme_logique":              "Systèmes logiques",
    "cisco":                        "CISCO",
    "francais":                     "Français",
    "reseau":                       "Réseau",
    "tec1":                         "TEC1",
    "tec2":                         "TEC2",
    "anglais":                      "Anglais",
    "architecture_des_ordinateurs": "Architecture des ordinateurs",
    "architecture_ordinateurs":     "Architecture des ordinateurs",
    "analyse_math":                 "Analyse mathématique",
    "base_de_donnees":              "Base de données",
    "base_donnees":                 "Base de données",
    "statisque":                    "Statistique",
    "statistique":                  "Statistique",
    "mercatique":                   "Mercatique",
}

EXTENSIONS_VALIDES = (
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
    ".txt", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".zip", ".rar",
    ".c", ".cpp", ".h", ".py", ".java", ".html", ".css", ".js", ".sql",
)

# Un dossier dont le nom contient un de ces mots → « Sujets d'entraînement »
MOTS_SUJET = ("sujet", "revision", "entrainement", "examen", "annale", "partiel")


def norm(texte):
    """minuscules, sans accents, espaces/tirets → _"""
    t = unicodedata.normalize("NFD", texte)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[\s\-]+", "_", t.lower().strip())


def nom_matiere(dossier):
    return NOMS_MATIERES.get(norm(dossier)) or dossier.replace("_", " ").strip()[:1].upper() + dossier.replace("_", " ").strip()[1:]


def mot(cle, texte):
    """True si `cle` apparaît comme mot isolé (td, tp...) dans `texte` normalisé."""
    return re.search(rf"(^|[^a-z]){cle}([^a-z]|$)", texte) is not None


def categorie(sous_dossiers, fichier):
    """Classe un fichier : cours / td / tp / sujet. Le dossier le plus proche décide."""
    for d in reversed([norm(x) for x in sous_dossiers]):
        if any(k in d for k in MOTS_SUJET):
            return "sujet"
        if mot("td", d):
            return "td"
        if mot("tp", d):
            return "tp"
        if "cours" in d or d.startswith("chap"):
            return "cours"
    f = norm(os.path.splitext(fichier)[0])
    if mot("td", f):
        return "td"
    if mot("tp", f):
        return "tp"
    return "cours"


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def dates_ajout_git():
    """Date d'ajout de chaque fichier d'après l'historique git (pour le badge « Nouveau »)."""
    dates = {}
    try:
        r = git("-c", "core.quotepath=off", "log", "--diff-filter=A",
                "--format=@%ct", "--name-only", "--", DOSSIER_COURS)
    except FileNotFoundError:
        return dates
    if r.returncode != 0:
        return dates
    ts = None
    for ligne in r.stdout.splitlines():
        if ligne.startswith("@"):
            ts = int(ligne[1:])
        elif ligne and ts:
            dates.setdefault(unicodedata.normalize("NFC", ligne), ts)
    return dates


maintenant = datetime.datetime.now()
date_maj = maintenant.strftime("%d/%m/%Y à %H:%M")

# ==========================================
# 🚧 4. PAGE DE MAINTENANCE
# ==========================================
PAGE_MAINTENANCE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>En maintenance · Drive Universitaire</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,600;1,500&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root { --bg:#f6f1e7; --paper:#fffdf8; --ink:#1c2738; --soft:#5b6475; --line:#e3dac8; --gold:#a8834a; --accent:#7b1e2b; }
  @media (prefers-color-scheme: dark) { :root { --bg:#11151d; --paper:#181e29; --ink:#ebe4d4; --soft:#9aa2b1; --line:#2a3242; --gold:#c9a46a; --accent:#d9939a; } }
  body { margin:0; min-height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:16px; box-sizing:border-box;
         background:var(--bg); color:var(--ink); font-family:'Source Sans 3', system-ui, sans-serif; text-align:center; }
  .box { background:var(--paper); border:1px solid var(--line); border-top:3px double var(--gold); border-radius:6px; padding:40px 28px; max-width:520px; width:100%; }
  .fleuron { color:var(--gold); font-family:'Cormorant Garamond', serif; font-size:1.6rem; }
  h1 { font-family:'Cormorant Garamond', Georgia, serif; font-weight:600; font-size:2.4rem; margin:6px 0 10px; }
  p { color:var(--soft); margin:4px 0; }
  footer { margin-top:28px; color:var(--soft); font-size:.9rem; }
  footer b { font-family:'Cormorant Garamond', serif; font-size:1.15rem; color:var(--ink); }
</style>
</head>
<body>
  <div class="box">
    <div class="fleuron">❦</div>
    <h1>En maintenance</h1>
    <p>Le Drive Universitaire est en cours de mise à jour.</p>
    <p><i>Revenez dans quelques minutes.</i></p>
  </div>
  <footer>Par <b>__SIGNATURE__</b></footer>
</body>
</html>"""

# ==========================================
# 🎓 5. PAGE PRINCIPALE (le contenu est injecté à la place des __MARQUEURS__)
# ==========================================
PAGE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Drive Universitaire</title>
<meta name="description" content="Cours, travaux dirigés, travaux pratiques et sujets — GI · MRT · GE">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&family=Source+Sans+3:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#f6f1e7; --paper:#fffdf8; --hover:#fbf6ea; --ink:#1c2738; --ink-soft:#5f6879; --line:#e4dbc9;
  --navy:#1f2f4a; --navy-ink:#f3ecdc; --navy-soft:#c9c0ad; --accent:#7b1e2b; --gold:#a8834a; --gold-light:#d8b878; --gold-soft:#f1e7d3;
  --new:#2f6b4f; --c-cours:#a8834a; --c-td:#2f6b4f; --c-tp:#2c4f7c; --c-sujet:#7b1e2b;
  --shadow:0 1px 2px rgba(28,39,56,.05), 0 6px 20px rgba(28,39,56,.05);
  --serif:'Cormorant Garamond', Georgia, 'Times New Roman', serif;
  --sans:'Source Sans 3', system-ui, -apple-system, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg:#11151d; --paper:#181e29; --hover:#1d2431; --ink:#ebe4d4; --ink-soft:#9aa2b1; --line:#2a3242;
    --navy:#0b1018; --navy-ink:#efe7d6; --navy-soft:#a9a291; --accent:#df9aa1; --gold:#c9a46a; --gold-light:#d8b878; --gold-soft:#262117;
    --new:#7fc4a0; --c-cours:#c9a46a; --c-td:#7fc4a0; --c-tp:#93b3e0; --c-sujet:#df9aa1;
    --shadow:0 1px 2px rgba(0,0,0,.3);
  }
}
* { box-sizing:border-box; }
html { -webkit-text-size-adjust:100%; }
body { margin:0; background:var(--bg); color:var(--ink); font-family:var(--sans); font-size:16px; line-height:1.55; }
body.no-scroll { overflow:hidden; }
button { font:inherit; color:inherit; }
svg { display:block; }

/* ── En-tête ── */
.masthead { background:var(--navy); color:var(--navy-ink); border-bottom:4px double var(--gold); }
.masthead-inner { max-width:1100px; margin:0 auto; padding:30px 16px 26px; }
.eyebrow { font-size:.72rem; letter-spacing:.24em; text-transform:uppercase; color:var(--gold-light); }
.title { font-family:var(--serif); font-weight:600; font-size:clamp(2.3rem,7vw,3.5rem); line-height:1.02; margin:8px 0 6px; cursor:pointer; display:inline-block; }
.subtitle { font-family:var(--serif); font-style:italic; font-size:1.18rem; color:var(--navy-soft); margin:0; }
.search { position:relative; max-width:580px; margin-top:22px; }
.search input { width:100%; padding:13px 44px 13px 46px; border-radius:4px; border:1px solid rgba(255,255,255,.18);
  background:rgba(255,255,255,.07); color:var(--navy-ink); font-size:1rem; font-family:var(--sans); outline:none; transition:border-color .2s, background .2s; -webkit-appearance:none; }
.search input::placeholder { color:var(--navy-soft); }
.search input:focus { border-color:var(--gold-light); background:rgba(255,255,255,.11); }
.search .s-icon { position:absolute; left:16px; top:50%; transform:translateY(-50%); color:var(--gold-light); pointer-events:none; }
.search .s-clear { position:absolute; right:8px; top:50%; transform:translateY(-50%); background:none; border:0; color:var(--navy-soft); cursor:pointer; padding:8px; display:none; }
.search.has-text .s-clear { display:block; }
.banner { background:var(--gold-soft); color:var(--ink); text-align:center; padding:10px 16px; font-family:var(--serif); font-style:italic; font-size:1.1rem; border-bottom:1px solid var(--line); }

/* ── Contenu ── */
main { max-width:1100px; margin:0 auto; padding:26px 16px 40px; min-height:50vh; }
.crumbs { display:flex; flex-wrap:wrap; align-items:center; gap:8px; font-size:.78rem; letter-spacing:.12em; text-transform:uppercase; color:var(--ink-soft); margin-bottom:22px; }
.crumbs a { color:var(--accent); text-decoration:none; font-weight:600; }
.crumbs a:hover { text-decoration:underline; text-underline-offset:3px; }
.crumbs .sep { color:var(--gold); }
.back { margin-left:auto; background:none; border:1px solid var(--line); border-radius:4px; padding:5px 12px; cursor:pointer; font-size:.78rem; letter-spacing:.1em; text-transform:uppercase; color:var(--ink-soft); }
.back:hover { border-color:var(--gold); color:var(--accent); }

.section + .section { margin-top:40px; }
.section-head { display:flex; align-items:center; gap:16px; margin:0 0 18px; }
.section-head h2 { font-family:var(--serif); font-weight:600; font-size:1.75rem; margin:0; line-height:1.2; }
.section-head::after { content:""; flex:1; height:1px; background:var(--line); }

.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:16px; }
.card { position:relative; display:flex; gap:16px; align-items:flex-start; background:var(--paper); border:1px solid var(--line); border-radius:6px;
  padding:20px 44px 20px 20px; cursor:pointer; box-shadow:var(--shadow); transition:border-color .2s, transform .2s; }
.card:hover { border-color:var(--gold); transform:translateY(-2px); }
.card:focus-visible, .doc-main:focus-visible, .icon-btn:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.card-body { flex:1; min-width:0; }
.card-kicker { display:block; font-size:.68rem; letter-spacing:.18em; text-transform:uppercase; color:var(--accent); margin-bottom:2px; }
.card-title { display:block; font-family:var(--serif); font-size:1.38rem; font-weight:600; line-height:1.18; overflow-wrap:anywhere; }
.card-meta { display:block; font-size:.88rem; color:var(--ink-soft); margin-top:5px; }
.card .badge-new { margin-top:10px; }
.card-annee { flex-direction:column; gap:6px; padding:26px 24px; min-height:190px; }
.roman { font-family:var(--serif); font-size:3.6rem; line-height:.9; font-weight:600; color:var(--gold); }
.card.vide { box-shadow:none; }
.card.vide .roman { color:var(--line); }
.seal { flex:none; width:54px; height:54px; border-radius:50%; display:grid; place-items:center; font-family:var(--serif); font-weight:600; font-size:1.3rem;
  color:var(--accent); background:var(--paper); border:1px solid var(--gold); box-shadow:inset 0 0 0 3px var(--paper), inset 0 0 0 4px var(--gold-soft); }
.star { position:absolute; top:8px; right:8px; background:none; border:0; cursor:pointer; color:var(--line); padding:6px; border-radius:50%; }
.star:hover { color:var(--gold); }
.star.on { color:var(--gold); }
.badge-new { display:inline-block; font-size:.64rem; font-weight:600; letter-spacing:.14em; text-transform:uppercase; color:var(--new); border:1px solid currentColor; border-radius:3px; padding:1px 6px; white-space:nowrap; }

/* ── Page matière ── */
.page-head { position:relative; display:flex; gap:22px; align-items:center; background:var(--paper); border:1px solid var(--line); border-top:3px double var(--gold); border-radius:6px; padding:26px; margin-bottom:30px; }
.page-head .seal { width:72px; height:72px; font-size:1.7rem; }
.page-head h2 { font-family:var(--serif); font-weight:600; font-size:clamp(1.8rem,5vw,2.5rem); line-height:1.08; margin:2px 0 6px; overflow-wrap:anywhere; }
.pin-btn { display:inline-flex; align-items:center; gap:7px; margin-top:12px; background:none; border:1px solid var(--line); border-radius:4px; padding:6px 12px; cursor:pointer; font-size:.85rem; color:var(--ink-soft); }
.pin-btn:hover { border-color:var(--gold); color:var(--accent); }
.pin-btn.on { color:var(--gold); border-color:var(--gold); }
.chips { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:26px; }
.chip { text-decoration:none; font-size:.85rem; border:1px solid var(--line); background:var(--paper); border-radius:999px; padding:5px 14px; color:var(--ink); }
.chip:hover { border-color:var(--gold); }
.chip b { color:var(--ink-soft); font-weight:500; margin-left:4px; }
.doc-section { margin-bottom:30px; scroll-margin-top:16px; }
.doc-section h3 { display:flex; align-items:center; gap:10px; font-family:var(--serif); font-weight:600; font-size:1.4rem; margin:0 0 10px; }
.doc-section h3 .dot { width:9px; height:9px; transform:rotate(45deg); flex:none; }
.doc-section h3 small { font-family:var(--sans); font-size:.8rem; color:var(--ink-soft); font-weight:400; }

.docs { background:var(--paper); border:1px solid var(--line); border-radius:6px; overflow:hidden; }
.doc { display:flex; align-items:center; gap:14px; padding:12px 14px; border-top:1px solid var(--line); }
.doc:first-child { border-top:0; }
.doc:hover { background:var(--hover); }
.ext { flex:none; width:46px; text-align:center; font-size:.64rem; font-weight:600; letter-spacing:.08em; padding:4px 0; border-radius:3px; border:1px solid currentColor; color:var(--ink-soft); }
.ext-pdf { color:var(--c-sujet); } .ext-doc { color:var(--c-tp); } .ext-ppt { color:var(--c-cours); } .ext-xls, .ext-img { color:var(--c-td); }
.doc-main { flex:1; min-width:0; background:none; border:0; text-align:left; cursor:pointer; padding:2px 0; }
.doc-name { display:block; font-weight:500; overflow-wrap:anywhere; }
.doc-main:hover .doc-name { color:var(--accent); text-decoration:underline; text-underline-offset:3px; text-decoration-color:var(--gold); }
.doc-meta { display:block; font-size:.8rem; color:var(--ink-soft); margin-top:1px; }
.icon-btn { flex:none; width:38px; height:38px; display:grid; place-items:center; border-radius:50%; border:1px solid var(--line); color:var(--ink-soft); background:var(--paper); cursor:pointer; text-decoration:none; }
.icon-btn:hover { color:var(--accent); border-color:var(--gold); }
.empty { text-align:center; padding:56px 16px; color:var(--ink-soft); font-family:var(--serif); font-style:italic; font-size:1.25rem; }
.result-count { color:var(--ink-soft); font-family:var(--serif); font-style:italic; font-size:1.1rem; margin:-6px 0 18px; }
@media (max-width:560px) {
  .doc { gap:10px; padding:12px; }
  .ext { width:40px; }
  .page-head { padding:20px; gap:16px; }
  .page-head .seal { width:56px; height:56px; font-size:1.35rem; }
}

/* ── Aperçu ── */
.modal { position:fixed; inset:0; background:rgba(12,16,24,.62); display:none; align-items:center; justify-content:center; padding:24px; z-index:50; }
.modal.open { display:flex; }
.modal-panel { background:var(--paper); width:min(1040px,100%); height:min(90vh,100%); border-radius:8px; display:flex; flex-direction:column; overflow:hidden; box-shadow:0 24px 70px rgba(0,0,0,.4); }
.modal-head { display:flex; align-items:center; gap:10px; padding:10px 12px 10px 18px; border-bottom:1px solid var(--line); }
.modal-title { flex:1; min-width:0; }
.modal-title b { display:block; font-family:var(--serif); font-size:1.2rem; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.modal-title span { display:block; font-size:.78rem; color:var(--ink-soft); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.modal-body { flex:1; min-height:0; background:var(--bg); }
.modal-body iframe { width:100%; height:100%; border:0; background:#fff; }
.img-wrap { height:100%; overflow:auto; display:grid; place-items:center; padding:16px; }
.img-wrap img { max-width:100%; max-height:100%; object-fit:contain; }
.code { margin:0; height:100%; overflow:auto; padding:18px; font-size:.85rem; line-height:1.5; white-space:pre; color:var(--ink); }
.no-preview { height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; gap:16px; padding:24px; color:var(--ink-soft); font-family:var(--serif); font-style:italic; font-size:1.2rem; }
.btn { display:inline-flex; align-items:center; gap:8px; padding:9px 18px; border-radius:4px; border:1px solid var(--accent); background:var(--accent); color:var(--paper); text-decoration:none; font-family:var(--sans); font-style:normal; font-size:.95rem; font-weight:500; cursor:pointer; }
@media (max-width:640px) { .modal { padding:0; } .modal-panel { height:100%; border-radius:0; } }

/* ── Pied de page ── */
footer { border-top:1px solid var(--line); padding:30px 16px 44px; text-align:center; color:var(--ink-soft); font-size:.88rem; }
.fleuron { font-family:var(--serif); color:var(--gold); font-size:1.5rem; line-height:1; }
.sign { font-family:var(--serif); font-size:1.25rem; color:var(--ink); font-weight:600; }
.copyright { max-width:520px; margin:14px auto 0; font-size:.78rem; opacity:.85; }

/* ── Connexion ── */
#login { position:fixed; inset:0; background:var(--bg); display:none; align-items:center; justify-content:center; z-index:100; padding:16px; }
.login-box { background:var(--paper); border:1px solid var(--line); border-top:3px double var(--gold); border-radius:6px; padding:36px 28px; width:100%; max-width:360px; text-align:center; }
.login-box h2 { font-family:var(--serif); font-weight:600; font-size:2rem; margin:4px 0 4px; }
.login-box p { color:var(--ink-soft); margin:0 0 22px; font-size:.92rem; }
.login-box input { width:100%; padding:12px; margin-bottom:12px; border:1px solid var(--line); border-radius:4px; background:var(--bg); color:var(--ink); font-size:1rem; outline:none; }
.login-box input:focus { border-color:var(--gold); }
.login-box .btn { width:100%; justify-content:center; }
#login-error { color:var(--accent); font-size:.88rem; margin:14px 0 0; display:none; }
</style>
__ANALYTICS__
</head>
<body>

<div id="login">
  <form class="login-box" id="login-form" autocomplete="off">
    <div class="fleuron">❦</div>
    <h2>Accès privé</h2>
    <p>Entrez vos identifiants pour consulter le Drive.</p>
    <input type="text" id="username" placeholder="Identifiant">
    <input type="password" id="password" placeholder="Mot de passe">
    <button class="btn" type="submit">Se connecter</button>
    <p id="login-error">Identifiant ou mot de passe incorrect.</p>
  </form>
</div>

<header class="masthead">
  <div class="masthead-inner">
    <div class="eyebrow">Bibliothèque numérique · GI · MRT · GE</div>
    <h1 class="title" id="home-link">Drive Universitaire</h1>
    <p class="subtitle" id="stats"></p>
    <div class="search" id="search">
      <svg class="s-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input type="search" id="q" placeholder="Rechercher un document, une matière…" autocomplete="off" aria-label="Rechercher">
      <button class="s-clear" id="q-clear" aria-label="Effacer"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg></button>
    </div>
  </div>
</header>
<div id="banner-slot"></div>

<main id="view"></main>

<footer>
  <div class="fleuron">❦</div>
  <p>Dernière mise à jour le <b id="maj"></b></p>
  <p>Conçu par <span class="sign" id="signature"></span></p>
  <p class="copyright">© <span id="annee-copy"></span> <span id="signature-copy"></span> — Tous droits réservés.<br>Toute reproduction, copie ou redistribution de ce code est interdite sans autorisation écrite.</p>
</footer>

<div class="modal" id="modal" aria-hidden="true">
  <div class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="modal-name">
    <div class="modal-head">
      <div class="modal-title"><b id="modal-name"></b><span id="modal-ctx"></span></div>
      <a class="icon-btn" id="modal-open" target="_blank" rel="noopener" title="Ouvrir dans un nouvel onglet"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg></a>
      <a class="icon-btn" id="modal-dl" download title="Télécharger"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg></a>
      <button class="icon-btn" id="modal-close" title="Fermer"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg></button>
    </div>
    <div class="modal-body" id="modal-body"></div>
  </div>
</div>

<script>
const DATA = __DATA__;
const CFG  = __CONFIG__;

const FILIERES = CFG.filieres;
const ANNEES = [["L1","I","Licence 1"], ["L2","II","Licence 2"], ["L3","III","Licence 3"]];
const TYPES = [["cours","Cours"], ["td","Travaux dirigés"], ["tp","Travaux pratiques"], ["sujet","Sujets d’entraînement"]];
const COURT = { cours:"cours", td:"TD", tp:"TP", sujet:"sujets" };
const OFFICE = ["doc","docx","ppt","pptx","xls","xlsx"];
const IMAGES = ["png","jpg","jpeg","gif","webp"];
const TEXTE  = ["txt","c","cpp","h","py","java","html","css","js","sql"];
const ICON = {
  star: '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/></svg>',
  dl:   '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg>'
};

const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
const norm = s => String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const plur = (n, mot, pl) => n + " " + (n > 1 ? (pl || mot + "s") : mot);
const isNew = d => d && (Date.now() - d * 1000) < CFG.nouveauJours * 864e5;
const url = p => p.split("/").map(encodeURIComponent).join("/");
const href = (...p) => "#/" + p.map(encodeURIComponent).join("/");
const taille = b => b < 1048576 ? (b / 1024).toFixed(0) + " Ko" : (b / 1048576).toFixed(1).replace(".", ",") + " Mo";
const dateFr = d => new Date(d * 1000).toLocaleDateString("fr-FR", { day:"numeric", month:"short", year:"numeric" });
const nomAnnee = a => (ANNEES.find(x => x[0] === a) || [a, "", a])[2];

// ── Index de tous les documents ──
const ALL = [];
for (const [a, fs] of Object.entries(DATA))
  for (const [f, ms] of Object.entries(fs))
    for (const [m, info] of Object.entries(ms))
      info.docs.forEach(d => { Object.assign(d, { a, f, m, titre: info.titre, i: ALL.length }); ALL.push(d); });

const docsDe = (a, f, m) => ALL.filter(d => d.a === a && (!f || d.f === f) && (!m || d.m === m));
const nbNew = docs => docs.filter(d => isNew(d.d)).length;
const badgeNew = n => n ? `<span class="badge-new">${n === true ? "Nouveau" : plur(n, "nouveau", "nouveaux")}</span>` : "";

// ── Favoris (mémorisés dans ce navigateur) ──
const FAV_KEY = "drive-favoris";
function getFavs() { try { return JSON.parse(localStorage.getItem(FAV_KEY)) || []; } catch (e) { return []; } }
function setFavs(v) { try { localStorage.setItem(FAV_KEY, JSON.stringify(v)); } catch (e) {} }
function toggleFav(id) { const f = getFavs(); setFavs(f.includes(id) ? f.filter(x => x !== id) : [...f, id]); render(); }

function initiales(t) {
  const mots = t.replace(/[’']/g, " ").split(/\s+/).filter(w => w && !/^(de|des|du|la|le|les|l|d|à|a|et|aux|en)$/i.test(w));
  if (mots.length === 1) return mots[0].slice(0, 2).replace(/^./, c => c.toUpperCase());
  return mots.slice(0, 2).map(w => w[0].toUpperCase()).join("");
}

// ── Composants ──
function crumbs(items) {
  if (!items.length) return "";
  const parts = [`<a href="#/">Accueil</a>`].concat(items.map(([label, h]) => h ? `<a href="${h}">${esc(label)}</a>` : `<span>${esc(label)}</span>`));
  return `<nav class="crumbs">${parts.join('<span class="sep">›</span>')}<button class="back" data-back>← Retour</button></nav>`;
}
const section = (titre, contenu) => `<section class="section"><div class="section-head"><h2>${titre}</h2></div>${contenu}</section>`;

function carteMatiere(a, f, m, avecContexte) {
  const info = DATA[a][f][m], docs = docsDe(a, f, m), id = [a, f, m].join("/");
  const fav = getFavs().includes(id);
  const resume = TYPES.map(([t]) => [t, docs.filter(d => d.t === t).length]).filter(x => x[1]).map(([t, n]) => n + " " + (t === "sujet" && n === 1 ? "sujet" : COURT[t])).join(" · ") || "Aucun document";
  return `<div class="card" role="link" tabindex="0" data-go="${href(a, f, m)}">
    <span class="seal">${esc(initiales(info.titre))}</span>
    <span class="card-body">
      ${avecContexte ? `<span class="card-kicker">${esc(a)} · ${esc(f)}</span>` : ""}
      <span class="card-title">${esc(info.titre)}</span>
      <span class="card-meta">${resume}</span>
      ${badgeNew(nbNew(docs))}
    </span>
    <button class="star ${fav ? "on" : ""}" data-fav="${esc(id)}" title="${fav ? "Retirer des favoris" : "Épingler"}" aria-label="Épingler">${ICON.star}</button>
  </div>`;
}

function ligneDoc(d, avecContexte) {
  const e = (d.e || "").toLowerCase();
  const cls = e === "pdf" ? "pdf" : e.startsWith("doc") ? "doc" : e.startsWith("ppt") ? "ppt" : e.startsWith("xls") ? "xls" : IMAGES.includes(e) || e === "heic" ? "img" : "autre";
  const ctx = avecContexte ? `${d.a} · ${d.f} · ${d.titre} · ${COURT[d.t]} · ` : "";
  return `<div class="doc">
    <span class="ext ext-${cls}">${esc(e.toUpperCase() || "—")}</span>
    <button class="doc-main" data-preview="${d.i}">
      <span class="doc-name">${esc(d.n)}</span>
      <span class="doc-meta">${esc(ctx)}${taille(d.s)} · ajouté le ${dateFr(d.d)}</span>
    </button>
    ${isNew(d.d) ? badgeNew(true) : ""}
    <a class="icon-btn" href="${url(d.p)}" download title="Télécharger" aria-label="Télécharger">${ICON.dl}</a>
  </div>`;
}

// ── Écrans ──
function vueAccueil() {
  const favs = getFavs().map(id => id.split("/")).filter(([a, f, m]) => DATA[a] && DATA[a][f] && DATA[a][f][m]);
  let html = favs.length ? section("Mes matières épinglées", `<div class="grid">${favs.map(([a, f, m]) => carteMatiere(a, f, m, true)).join("")}</div>`) : "";
  html += section("Choisissez une année", `<div class="grid">${ANNEES.map(([a, rom, label]) => {
    const docs = docsDe(a), nm = Object.values(DATA[a] || {}).reduce((s, ms) => s + Object.keys(ms).length, 0);
    return `<div class="card card-annee ${docs.length ? "" : "vide"}" role="link" tabindex="0" data-go="${href(a)}">
      <span class="roman">${rom}</span>
      <span class="card-title">${label}</span>
      <span class="card-meta">${docs.length ? plur(nm, "matière") + " · " + plur(docs.length, "document") : "Bientôt disponible"}</span>
      ${badgeNew(nbNew(docs))}
    </div>`;
  }).join("")}</div>`);
  return html;
}

function vueFilieres(a) {
  return crumbs([[nomAnnee(a)]]) + section(`${nomAnnee(a)} · <i>choisissez une filière</i>`, `<div class="grid">${Object.entries(FILIERES).map(([f, nom]) => {
    const nm = Object.keys((DATA[a] || {})[f] || {}).length, docs = docsDe(a, f);
    return `<div class="card ${docs.length ? "" : "vide"}" role="link" tabindex="0" data-go="${href(a, f)}">
      <span class="seal">${esc(f)}</span>
      <span class="card-body">
        <span class="card-title">${esc(nom)}</span>
        <span class="card-meta">${nm ? plur(nm, "matière") + " · " + plur(docs.length, "document") : "Aucun document pour l’instant"}</span>
        ${badgeNew(nbNew(docs))}
      </span>
    </div>`;
  }).join("")}</div>`);
}

function vueMatieres(a, f) {
  const ms = Object.keys((DATA[a] || {})[f] || {}).sort((x, y) => DATA[a][f][x].titre.localeCompare(DATA[a][f][y].titre, "fr"));
  const contenu = ms.length ? `<div class="grid">${ms.map(m => carteMatiere(a, f, m)).join("")}</div>`
                            : `<div class="empty">Aucune matière n’a encore été déposée ici.</div>`;
  return crumbs([[nomAnnee(a), href(a)], [FILIERES[f] || f]]) + section(esc(FILIERES[f] || f), contenu);
}

function vueMatiere(a, f, m) {
  const info = DATA[a][f][m], docs = docsDe(a, f, m), id = [a, f, m].join("/"), fav = getFavs().includes(id);
  const groupes = TYPES.map(([t, label]) => [t, label, docs.filter(d => d.t === t)]).filter(g => g[2].length);
  let html = crumbs([[nomAnnee(a), href(a)], [f, href(a, f)], [info.titre]]);
  html += `<div class="page-head">
    <span class="seal">${esc(initiales(info.titre))}</span>
    <div>
      <span class="card-kicker">${esc(nomAnnee(a))} · ${esc(FILIERES[f] || f)}</span>
      <h2>${esc(info.titre)}</h2>
      <span class="card-meta">${plur(docs.length, "document")}${nbNew(docs) ? " · " + plur(nbNew(docs), "nouveau", "nouveaux") : ""}</span>
      <button class="pin-btn ${fav ? "on" : ""}" data-fav="${esc(id)}">${ICON.star} ${fav ? "Épinglée" : "Épingler cette matière"}</button>
    </div>
  </div>`;
  if (!groupes.length) return html + `<div class="empty">Aucun document pour l’instant.</div>`;
  if (groupes.length > 1) html += `<div class="chips">${groupes.map(([t, label, g]) => `<a class="chip" href="#" data-scroll="sec-${t}">${label}<b>${g.length}</b></a>`).join("")}</div>`;
  html += groupes.map(([t, label, g]) => `<section class="doc-section" id="sec-${t}">
    <h3><span class="dot" style="background:var(--c-${t})"></span>${label} <small>${g.length}</small></h3>
    <div class="docs">${g.map(d => ligneDoc(d)).join("")}</div>
  </section>`).join("");
  return html;
}

function vueRecherche(q) {
  const mots = norm(q).split(/\s+/).filter(Boolean);
  const res = ALL.filter(d => { const h = norm([d.n, d.e, d.titre, d.a, d.f, COURT[d.t], FILIERES[d.f]].join(" ")); return mots.every(w => h.includes(w)); });
  let html = section(`Résultats pour « ${esc(q)} »`, "");
  html = html.replace("</section>", `<p class="result-count">${res.length ? plur(res.length, "document trouvé", "documents trouvés") : ""}</p>` +
    (res.length ? `<div class="docs">${res.slice(0, 200).map(d => ligneDoc(d, true)).join("")}</div>` : `<div class="empty">Aucun document trouvé. Essayez un autre mot-clé.</div>`) + "</section>");
  return html;
}

// ── Routeur (#/L2/GI/Matière) ──
const segments = () => location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(s => { try { return decodeURIComponent(s); } catch (e) { return s; } });
function render() {
  const q = $("#q").value.trim();
  $("#search").classList.toggle("has-text", !!q);
  const [a, f, m] = segments();
  let html;
  if (q.length >= 2) html = vueRecherche(q);
  else if (a && f && m && DATA[a] && DATA[a][f] && DATA[a][f][m]) html = vueMatiere(a, f, m);
  else if (a && f && FILIERES[f]) html = vueMatieres(a, f);
  else if (a && ANNEES.some(x => x[0] === a)) html = vueFilieres(a);
  else html = vueAccueil();
  $("#view").innerHTML = html;
}

window.addEventListener("hashchange", () => { $("#q").value = ""; render(); window.scrollTo(0, 0); });
$("#q").addEventListener("input", render);
$("#q-clear").addEventListener("click", () => { $("#q").value = ""; render(); $("#q").focus(); });
$("#home-link").addEventListener("click", () => { $("#q").value = ""; location.hash = "#/"; render(); });

document.addEventListener("click", e => {
  const fav = e.target.closest("[data-fav]");
  if (fav) { e.preventDefault(); e.stopPropagation(); toggleFav(fav.dataset.fav); return; }
  const pv = e.target.closest("[data-preview]");
  if (pv) { ouvrirApercu(+pv.dataset.preview); return; }
  const sc = e.target.closest("[data-scroll]");
  if (sc) { e.preventDefault(); const el = document.getElementById(sc.dataset.scroll); if (el) el.scrollIntoView({ behavior: "smooth" }); return; }
  if (e.target.closest("[data-back]")) { const s = segments(); location.hash = s.length > 1 ? href(...s.slice(0, -1)) : "#/"; return; }
  const go = e.target.closest("[data-go]");
  if (go) location.hash = go.dataset.go;
});
document.addEventListener("keydown", e => {
  if (e.key === "Escape") fermerApercu();
  if (e.key === "Enter" && e.target.matches && e.target.matches("[data-go]")) location.hash = e.target.dataset.go;
});

// ── Aperçu des documents ──
function ouvrirApercu(i) {
  const d = ALL[i]; if (!d) return;
  const u = url(d.p), e = (d.e || "").toLowerCase(), enLigne = location.protocol.startsWith("http");
  const indispo = msg => `<div class="no-preview">${msg}<a class="btn" href="${u}" download>${ICON.dl} Télécharger le fichier</a></div>`;
  let body;
  if (e === "pdf") body = `<iframe src="${u}" title="${esc(d.n)}"></iframe>`;
  else if (IMAGES.includes(e)) body = `<div class="img-wrap"><img src="${u}" alt="${esc(d.n)}"></div>`;
  else if (OFFICE.includes(e)) body = enLigne
    ? `<iframe src="https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(new URL(u, location.href).href)}" title="${esc(d.n)}"></iframe>`
    : indispo("L’aperçu des fichiers Word, PowerPoint et Excel fonctionne une fois le site en ligne.");
  else if (TEXTE.includes(e)) {
    body = `<pre class="code">Chargement…</pre>`;
    fetch(u).then(r => r.ok ? r.text() : Promise.reject()).then(t => { const p = $("#modal-body pre"); if (p) p.textContent = t; })
      .catch(() => { $("#modal-body").innerHTML = indispo("Impossible d’afficher ce fichier."); });
  } else body = indispo("Aperçu indisponible pour ce format.");
  $("#modal-name").textContent = d.n + (e ? "." + e : "");
  $("#modal-ctx").textContent = `${nomAnnee(d.a)} · ${FILIERES[d.f] || d.f} · ${d.titre} · ${taille(d.s)}`;
  $("#modal-open").href = u; $("#modal-dl").href = u;
  $("#modal-body").innerHTML = body;
  $("#modal").classList.add("open"); $("#modal").setAttribute("aria-hidden", "false");
  document.body.classList.add("no-scroll");
}
function fermerApercu() {
  if (!$("#modal").classList.contains("open")) return;
  $("#modal").classList.remove("open"); $("#modal").setAttribute("aria-hidden", "true");
  $("#modal-body").innerHTML = ""; document.body.classList.remove("no-scroll");
}
$("#modal-close").addEventListener("click", fermerApercu);
$("#modal").addEventListener("click", e => { if (e.target.id === "modal") fermerApercu(); });

// ── Textes fixes ──
const nbMat = Object.values(DATA).reduce((s, fs) => s + Object.values(fs).reduce((t, ms) => t + Object.keys(ms).length, 0), 0);
$("#stats").textContent = `${plur(ALL.length, "document")} · ${plur(nbMat, "matière")}`;
$("#maj").textContent = CFG.maj;
$("#signature").textContent = CFG.signature;
$("#signature-copy").textContent = CFG.signature;
$("#annee-copy").textContent = CFG.annee;
if (CFG.message) $("#banner-slot").innerHTML = `<div class="banner">${esc(CFG.message)}</div>`;

// ── Connexion (protection basique) ──
function afficherSite() { $("#login").style.display = "none"; }
let autorise = false; try { autorise = sessionStorage.getItem("driveAutorise") === "oui"; } catch (e) {}
if (CFG.motDePasse && !autorise) $("#login").style.display = "flex";
$("#login-form").addEventListener("submit", e => {
  e.preventDefault();
  if ($("#username").value === CFG.login && $("#password").value === CFG.mdp) {
    try { sessionStorage.setItem("driveAutorise", "oui"); } catch (err) {}
    afficherSite();
  } else $("#login-error").style.display = "block";
});

render();
</script>
</body>
</html>"""

ANALYTICS = f"""<script async src="https://www.googletagmanager.com/gtag/js?id={GOOGLE_ANALYTICS_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GOOGLE_ANALYTICS_ID}');
</script>""" if GOOGLE_ANALYTICS_ID else ""


def pour_script(obj):
    """JSON sûr à insérer dans une balise <script>."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


# ==========================================
# 🔍 6. SCAN DU DOSSIER cours/
# ==========================================
total_fichiers = 0
if MODE_MAINTENANCE:
    html_complet = PAGE_MAINTENANCE.replace("__SIGNATURE__", NOM_SIGNATURE_MAINTENANCE)
else:
    dates = dates_ajout_git()
    data = {}

    if os.path.isdir(DOSSIER_COURS):
        for filiere in sorted(os.listdir(DOSSIER_COURS)):
            chemin_filiere = os.path.join(DOSSIER_COURS, filiere)
            if filiere.startswith(".") or not os.path.isdir(chemin_filiere):
                continue
            for annee in sorted(os.listdir(chemin_filiere)):
                chemin_annee = os.path.join(chemin_filiere, annee)
                if annee.startswith(".") or not os.path.isdir(chemin_annee):
                    continue
                for matiere in sorted(os.listdir(chemin_annee)):
                    chemin_matiere = os.path.join(chemin_annee, matiere)
                    if matiere.startswith(".") or not os.path.isdir(chemin_matiere):
                        continue

                    docs = []
                    for racine, dossiers, fichiers in os.walk(chemin_matiere):
                        dossiers[:] = sorted(d for d in dossiers if not d.startswith("."))
                        rel = os.path.relpath(racine, chemin_matiere)
                        sous_dossiers = [] if rel == "." else rel.split(os.sep)
                        for fichier in sorted(fichiers):
                            if fichier.startswith((".", "~$")) or not fichier.lower().endswith(EXTENSIONS_VALIDES):
                                continue
                            chemin = os.path.join(racine, fichier).replace("\\", "/")
                            base, ext = os.path.splitext(fichier)
                            docs.append({
                                "n": base.replace("_", " ").strip(),
                                "e": ext[1:].lower(),
                                "p": chemin,
                                "t": categorie(sous_dossiers, fichier),
                                "s": os.path.getsize(chemin),
                                "d": dates.get(unicodedata.normalize("NFC", chemin)) or int(os.path.getmtime(chemin)),
                            })
                    total_fichiers += len(docs)
                    data.setdefault(annee, {}).setdefault(filiere, {})[matiere] = {
                        "titre": nom_matiere(matiere),
                        "docs": docs,
                    }

    config = {
        "filieres": FILIERES,
        "nouveauJours": NOUVEAU_JOURS,
        "message": MESSAGE_SPECIAL,
        "signature": NOM_SIGNATURE_NORMAL,
        "maj": date_maj,
        "annee": maintenant.year,
        "motDePasse": MOT_DE_PASSE_ACTIF,
        "login": LOGIN_REQUIS if MOT_DE_PASSE_ACTIF else "",
        "mdp": MDP_REQUIS if MOT_DE_PASSE_ACTIF else "",
    }
    html_complet = (PAGE
                    .replace("__ANALYTICS__", ANALYTICS)
                    .replace("__DATA__", pour_script(data))
                    .replace("__CONFIG__", pour_script(config)))

# ==========================================
# 💾 7. ÉCRITURE DU SITE
# ==========================================
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_complet)
print(f"✅ index.html généré ({total_fichiers} fichiers indexés).")
