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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root { --bg:#f7f8fa; --paper:#fff; --ink:#0f172a; --soft:#64748b; --line:#e5e7eb; --accent:#2563eb; --accent-soft:#eff6ff; }
  @media (prefers-color-scheme: dark) { :root { --bg:#0b0d12; --paper:#14171e; --ink:#f1f5f9; --soft:#94a3b8; --line:#232834; --accent:#60a5fa; --accent-soft:#16213a; } }
  body { margin:0; min-height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:16px; box-sizing:border-box;
         background:var(--bg); color:var(--ink); font-family:'Inter', system-ui, sans-serif; text-align:center; -webkit-font-smoothing:antialiased; }
  .box { background:var(--paper); border:1px solid var(--line); border-radius:18px; padding:40px 28px; max-width:480px; width:100%; }
  .icon { width:56px; height:56px; margin:0 auto 16px; border-radius:16px; background:var(--accent-soft); display:grid; place-items:center; font-size:1.6rem; }
  h1 { font-weight:700; font-size:1.8rem; letter-spacing:-.03em; margin:0 0 8px; }
  p { color:var(--soft); margin:4px 0; }
  footer { margin-top:24px; color:var(--soft); font-size:.85rem; }
  footer b { color:var(--ink); }
</style>
</head>
<body>
  <div class="box">
    <div class="icon">🚧</div>
    <h1>En maintenance</h1>
    <p>Le Drive Universitaire est en cours de mise à jour.</p>
    <p>Revenez dans quelques minutes.</p>
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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#f7f8fa; --paper:#ffffff; --hover:#f8fafc; --ink:#0f172a; --ink-soft:#64748b; --line:#e5e7eb; --line-strong:#d1d5db;
  --accent:#2563eb; --accent-ink:#ffffff; --accent-soft:#eff6ff; --accent-line:#bfdbfe;
  --new:#15803d; --new-soft:#dcfce7;
  --c-cours:#2563eb; --c-td:#16a34a; --c-tp:#d97706; --c-sujet:#9333ea;
  --s-cours:#eff6ff; --s-td:#f0fdf4; --s-tp:#fffbeb; --s-sujet:#faf5ff;
  --shadow:0 1px 2px rgba(15,23,42,.04); --shadow-hover:0 8px 24px rgba(15,23,42,.08);
  --radius:14px;
  --font:'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg:#0b0d12; --paper:#14171e; --hover:#191d26; --ink:#f1f5f9; --ink-soft:#94a3b8; --line:#232834; --line-strong:#323949;
    --accent:#60a5fa; --accent-ink:#0b0d12; --accent-soft:#16213a; --accent-line:#1e3a8a;
    --new:#4ade80; --new-soft:#12301f;
    --c-cours:#60a5fa; --c-td:#4ade80; --c-tp:#fbbf24; --c-sujet:#c084fc;
    --s-cours:#16213a; --s-td:#12291c; --s-tp:#2d2410; --s-sujet:#261a35;
    --shadow:none; --shadow-hover:0 8px 24px rgba(0,0,0,.35);
  }
}
* { box-sizing:border-box; }
html { -webkit-text-size-adjust:100%; }
body { margin:0; background:var(--bg); color:var(--ink); font-family:var(--font); font-size:15px; line-height:1.55; -webkit-font-smoothing:antialiased; }
body.no-scroll { overflow:hidden; }
button { font:inherit; color:inherit; }
svg { display:block; }

/* ── En-tête ── */
.masthead { background:var(--paper); border-bottom:1px solid var(--line); }
.masthead-inner { max-width:1100px; margin:0 auto; padding:28px 16px 24px; }
.eyebrow { display:flex; width:fit-content; align-items:center; gap:6px; font-size:.75rem; font-weight:600; color:var(--accent); background:var(--accent-soft); border-radius:999px; padding:4px 10px; }
.title { font-weight:700; font-size:clamp(1.9rem,6vw,2.6rem); letter-spacing:-.03em; line-height:1.1; margin:12px 0 4px; cursor:pointer; display:inline-block; }
.subtitle { font-size:.95rem; color:var(--ink-soft); margin:0; }
.search { position:relative; max-width:600px; margin-top:20px; }
.search input { width:100%; padding:12px 44px; border-radius:12px; border:1px solid var(--line); background:var(--bg); color:var(--ink);
  font-size:1rem; font-family:var(--font); outline:none; transition:border-color .15s, box-shadow .15s, background .15s; -webkit-appearance:none; }
.search input::placeholder { color:var(--ink-soft); }
.search input:focus { border-color:var(--accent); background:var(--paper); box-shadow:0 0 0 4px var(--accent-soft); }
.search .s-icon { position:absolute; left:15px; top:50%; transform:translateY(-50%); color:var(--ink-soft); pointer-events:none; }
.search .s-clear { position:absolute; right:6px; top:50%; transform:translateY(-50%); background:none; border:0; color:var(--ink-soft); cursor:pointer; padding:8px; display:none; border-radius:8px; }
.search .s-clear:hover { background:var(--hover); }
.search.has-text .s-clear { display:block; }
.banner { background:var(--accent-soft); color:var(--accent); text-align:center; padding:10px 16px; font-weight:500; font-size:.92rem; border-bottom:1px solid var(--accent-line); }

/* ── Contenu ── */
main { max-width:1100px; margin:0 auto; padding:28px 16px 48px; min-height:50vh; }
.crumbs { display:flex; flex-wrap:wrap; align-items:center; gap:6px; font-size:.88rem; color:var(--ink-soft); margin-bottom:22px; }
.crumbs a { color:var(--ink-soft); text-decoration:none; padding:2px 6px; border-radius:6px; }
.crumbs a:hover { color:var(--accent); background:var(--accent-soft); }
.crumbs > span:not(.sep) { color:var(--ink); font-weight:600; padding:2px 6px; }
.crumbs .sep { color:var(--line-strong); }
.back { margin-left:auto; background:var(--paper); border:1px solid var(--line); border-radius:10px; padding:6px 12px; cursor:pointer; font-size:.85rem; font-weight:500; color:var(--ink); }
.back:hover { border-color:var(--accent); color:var(--accent); }

.section + .section { margin-top:40px; }
.section-head { margin:0 0 16px; }
.section-head h2 { font-weight:700; font-size:1.3rem; letter-spacing:-.02em; margin:0; line-height:1.3; }
.section-head h2 i { font-style:normal; color:var(--ink-soft); font-weight:500; }

.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:14px; }
.card { position:relative; display:flex; gap:14px; align-items:flex-start; background:var(--paper); border:1px solid var(--line); border-radius:var(--radius);
  padding:18px 44px 18px 18px; cursor:pointer; box-shadow:var(--shadow); transition:border-color .15s, box-shadow .15s, transform .15s; }
.card:hover { border-color:var(--accent-line); box-shadow:var(--shadow-hover); transform:translateY(-2px); }
.card:focus-visible, .doc-main:focus-visible, .icon-btn:focus-visible, .chip:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.card-body { flex:1; min-width:0; }
.card-kicker { display:block; font-size:.75rem; font-weight:600; color:var(--accent); margin-bottom:2px; }
.card-title { display:block; font-size:1.05rem; font-weight:600; letter-spacing:-.01em; line-height:1.3; overflow-wrap:anywhere; }
.card-meta { display:block; font-size:.85rem; color:var(--ink-soft); margin-top:4px; }
.card .badge-new { margin-top:10px; }
.card-annee { flex-direction:column; gap:4px; padding:22px; min-height:170px; }
.roman { display:inline-grid; place-items:center; min-width:52px; height:52px; padding:0 12px; border-radius:12px; background:var(--accent-soft); color:var(--accent); font-size:1.25rem; font-weight:700; letter-spacing:-.02em; margin-bottom:10px; }
.card.vide { opacity:.65; }
.card.vide .roman { background:var(--hover); color:var(--ink-soft); }
.seal { flex:none; width:46px; height:46px; border-radius:12px; display:grid; place-items:center; font-weight:700; font-size:.95rem; letter-spacing:-.01em;
  color:var(--accent); background:var(--accent-soft); }
.star { position:absolute; top:10px; right:10px; background:none; border:0; cursor:pointer; color:var(--line-strong); padding:6px; border-radius:8px; }
.star:hover { color:#f59e0b; background:var(--hover); }
.star.on { color:#f59e0b; }
.badge-new { display:inline-block; font-size:.72rem; font-weight:600; color:var(--new); background:var(--new-soft); border-radius:999px; padding:2px 9px; white-space:nowrap; }

/* ── Page matière ── */
.page-head { position:relative; display:flex; gap:18px; align-items:center; background:var(--paper); border:1px solid var(--line); border-radius:var(--radius); padding:24px; margin-bottom:24px; box-shadow:var(--shadow); }
.page-head .seal { width:64px; height:64px; font-size:1.3rem; border-radius:16px; }
.page-head h2 { font-weight:700; font-size:clamp(1.5rem,4.5vw,2rem); letter-spacing:-.03em; line-height:1.15; margin:2px 0 4px; overflow-wrap:anywhere; }
.pin-btn { display:inline-flex; align-items:center; gap:6px; margin-top:12px; background:var(--paper); border:1px solid var(--line); border-radius:10px; padding:6px 12px; cursor:pointer; font-size:.85rem; font-weight:500; color:var(--ink); }
.pin-btn svg { width:16px; height:16px; color:var(--line-strong); }
.pin-btn:hover { border-color:var(--accent); }
.pin-btn.on { background:#fffbeb; border-color:#fcd34d; color:#92400e; }
.pin-btn.on svg { color:#f59e0b; }
@media (prefers-color-scheme: dark) { .pin-btn.on { background:#2d2410; border-color:#78530f; color:#fcd34d; } }
.chips { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:24px; }
.chip { text-decoration:none; font-size:.85rem; font-weight:500; border:1px solid var(--line); background:var(--paper); border-radius:999px; padding:6px 14px; color:var(--ink); }
.chip:hover { border-color:var(--accent); color:var(--accent); }
.chip b { color:var(--ink-soft); font-weight:500; margin-left:4px; }
.doc-section { margin-bottom:28px; scroll-margin-top:16px; }
.doc-section h3 { display:flex; align-items:center; gap:10px; font-weight:600; font-size:1.05rem; margin:0 0 10px; }
.doc-section h3 .dot { width:10px; height:10px; border-radius:3px; flex:none; }
.doc-section h3 small { font-size:.75rem; color:var(--ink-soft); font-weight:600; background:var(--hover); border:1px solid var(--line); border-radius:999px; padding:1px 8px; }

.docs { background:var(--paper); border:1px solid var(--line); border-radius:var(--radius); overflow:hidden; box-shadow:var(--shadow); }
.doc { display:flex; align-items:center; gap:14px; padding:12px 14px; border-top:1px solid var(--line); }
.doc:first-child { border-top:0; }
.doc:hover { background:var(--hover); }
.ext { flex:none; width:44px; height:44px; display:grid; place-items:center; font-size:.66rem; font-weight:700; letter-spacing:.02em; border-radius:10px; color:var(--ink-soft); background:var(--hover); }
.ext-pdf { color:#dc2626; background:#fef2f2; } .ext-doc { color:#2563eb; background:#eff6ff; } .ext-ppt { color:#ea580c; background:#fff7ed; }
.ext-xls, .ext-img { color:#16a34a; background:#f0fdf4; }
@media (prefers-color-scheme: dark) {
  .ext-pdf { color:#f87171; background:#2c1416; } .ext-doc { color:#60a5fa; background:#16213a; } .ext-ppt { color:#fb923c; background:#2c1a10; }
  .ext-xls, .ext-img { color:#4ade80; background:#12291c; }
}
.doc-main { flex:1; min-width:0; background:none; border:0; text-align:left; cursor:pointer; padding:2px 0; }
.doc-name { display:block; font-weight:500; overflow-wrap:anywhere; }
.doc-main:hover .doc-name { color:var(--accent); }
.doc-meta { display:block; font-size:.8rem; color:var(--ink-soft); margin-top:1px; }
.icon-btn { flex:none; width:38px; height:38px; display:grid; place-items:center; border-radius:10px; border:1px solid var(--line); color:var(--ink-soft); background:var(--paper); cursor:pointer; text-decoration:none; }
.icon-btn:hover { color:var(--accent); border-color:var(--accent); background:var(--accent-soft); }
.empty { text-align:center; padding:56px 16px; color:var(--ink-soft); font-size:1rem; background:var(--paper); border:1px dashed var(--line-strong); border-radius:var(--radius); }
.result-count { color:var(--ink-soft); font-size:.9rem; margin:-8px 0 16px; }
@media (max-width:560px) {
  .doc { gap:10px; padding:12px; }
  .ext { width:40px; height:40px; }
  .page-head { padding:18px; gap:14px; }
  .page-head .seal { width:52px; height:52px; font-size:1.1rem; }
}

/* ── Aperçu ── */
.modal { position:fixed; inset:0; background:rgba(15,23,42,.55); backdrop-filter:blur(4px); -webkit-backdrop-filter:blur(4px); display:none; align-items:center; justify-content:center; padding:24px; z-index:50; }
.modal.open { display:flex; }
.modal-panel { background:var(--paper); width:min(1040px,100%); height:min(90vh,100%); border-radius:18px; display:flex; flex-direction:column; overflow:hidden; box-shadow:0 24px 70px rgba(0,0,0,.35); }
.modal-head { display:flex; align-items:center; gap:8px; padding:10px 12px 10px 18px; border-bottom:1px solid var(--line); }
.modal-title { flex:1; min-width:0; }
.modal-title b { display:block; font-size:1rem; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.modal-title span { display:block; font-size:.78rem; color:var(--ink-soft); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.modal-body { flex:1; min-height:0; background:var(--bg); }
.modal-body iframe { width:100%; height:100%; border:0; background:#fff; }
.img-wrap { height:100%; overflow:auto; display:grid; place-items:center; padding:16px; }
.img-wrap img { max-width:100%; max-height:100%; object-fit:contain; border-radius:8px; }
.code { margin:0; height:100%; overflow:auto; padding:18px; font-size:.85rem; line-height:1.5; white-space:pre; color:var(--ink); font-family:ui-monospace, 'SF Mono', Menlo, monospace; }
.no-preview { height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; gap:16px; padding:24px; color:var(--ink-soft); }
.btn { display:inline-flex; align-items:center; gap:8px; padding:10px 18px; border-radius:10px; border:0; background:var(--accent); color:var(--accent-ink); text-decoration:none; font-size:.95rem; font-weight:600; cursor:pointer; }
.btn:hover { filter:brightness(1.08); }
@media (max-width:640px) { .modal { padding:0; } .modal-panel { height:100%; border-radius:0; } }

/* ── Pied de page ── */
footer { border-top:1px solid var(--line); background:var(--paper); padding:28px 16px 40px; text-align:center; color:var(--ink-soft); font-size:.85rem; }
footer p { margin:4px 0; }
.sign { color:var(--ink); font-weight:600; }
.copyright { max-width:520px; margin:14px auto 0 !important; font-size:.75rem; opacity:.8; }

/* ── Connexion ── */
#login { position:fixed; inset:0; background:var(--bg); display:none; align-items:center; justify-content:center; z-index:100; padding:16px; }
.login-box { background:var(--paper); border:1px solid var(--line); border-radius:18px; padding:32px 26px; width:100%; max-width:360px; text-align:center; box-shadow:var(--shadow-hover); }
.login-box h2 { font-weight:700; font-size:1.5rem; letter-spacing:-.02em; margin:0 0 4px; }
.login-box p { color:var(--ink-soft); margin:0 0 20px; font-size:.9rem; }
.login-box input { width:100%; padding:12px; margin-bottom:10px; border:1px solid var(--line); border-radius:10px; background:var(--bg); color:var(--ink); font-size:1rem; outline:none; font-family:var(--font); }
.login-box input:focus { border-color:var(--accent); box-shadow:0 0 0 4px var(--accent-soft); }
.login-box .btn { width:100%; justify-content:center; }
#login-error { color:#dc2626; font-size:.88rem; margin:14px 0 0; display:none; }
</style>
__ANALYTICS__
</head>
<body>

<div id="login">
  <form class="login-box" id="login-form" autocomplete="off">
    <h2>🔒 Accès privé</h2>
    <p>Entrez vos identifiants pour consulter le Drive.</p>
    <input type="text" id="username" placeholder="Identifiant">
    <input type="password" id="password" placeholder="Mot de passe">
    <button class="btn" type="submit">Se connecter</button>
    <p id="login-error">Identifiant ou mot de passe incorrect.</p>
  </form>
</div>

<header class="masthead">
  <div class="masthead-inner">
    <div class="eyebrow">📚 GI · MRT · GE</div>
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
      <span class="roman">${a}</span>
      <span class="card-title">${label}</span>
      <span class="card-meta">${docs.length ? plur(nm, "matière") + " · " + plur(docs.length, "document") : "Bientôt disponible"}</span>
      ${badgeNew(nbNew(docs))}
    </div>`;
  }).join("")}</div>`);
  return html;
}

function vueFilieres(a) {
  return crumbs([[nomAnnee(a)]]) + section(`${nomAnnee(a)} <i>· choisissez une filière</i>`, `<div class="grid">${Object.entries(FILIERES).map(([f, nom]) => {
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
