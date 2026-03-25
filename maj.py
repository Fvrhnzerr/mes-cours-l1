import os
import subprocess
import datetime
import json

# ==========================================
# 🔄 0. SYNCHRONISATION AUTOMATIQUE
# ==========================================
print("🔄 Vérification du Cloud (récupération des fichiers de l'iPad)...")
try:
    subprocess.run(["git", "checkout", "main"], check=True, capture_output=True)
    subprocess.run(["git", "stash"], check=True, capture_output=True)
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "stash", "pop"], capture_output=True)
    print("✅ Mac parfaitement synchronisé avec le Cloud !")
except subprocess.CalledProcessError as e:
    print(f"⚠️ Impossible de synchroniser : {e.stderr.strip() or 'Conflit mineur'}. On continue !")

# ==========================================
# ⚙️ 1. PARAMÈTRES GÉNÉRAUX ET INTERRUPTEURS
# ==========================================
NOM_UTILISATEUR          = "Fvrhnzerr"
NOM_SIGNATURE_NORMAL     = "Farhan Abdoul-Mougni Farhan"
NOM_SIGNATURE_MAINTENANCE = "Farhan&Co"
NOM_REPO                 = "mes-cours-l1"

# 🛑 LE BOUTON MAINTENANCE
MODE_MAINTENANCE = False

# 🔓 LE BOUTON MOT DE PASSE
MOT_DE_PASSE_ACTIF = False

# 🔐 IDENTIFIANTS
LOGIN_REQUIS = os.environ.get("DRIVE_LOGIN") or "L1GI"
MDP_REQUIS   = os.environ.get("DRIVE_MDP") or "IAD2026"

# ==========================================
# 📁 2. CONFIGURATION DES DOSSIERS
# ==========================================
noms_filieres = {
    "GI":  "💻 Génie Informatique",
    "MRT": "📡 Maintenance Réseau Telecom",
    "GE":  "📊 Gestion des Entreprises"
}

noms_annees = {
    "L1": "Licence 1",
    "L2": "Licence 2",
    "L3": "Licence 3"
}

noms_matieres_base = {
    "algebre_lineaire":             "📐 Algèbre Linéaire",
    "algebre lineaire":             "📐 Algèbre Linéaire",
    "algebre":                      "📐 Algèbre Linéaire",
    "algo_avancee":                 "🧬 Algorithme Avancée",
    "algo avancee":                 "🧬 Algorithme Avancée",
    "algorithme_avance":            "🧬 Algorithme Avancée",
    "algo":                         "🧬 Algorithmique",
    "system_exploitation":          "💻 Système d'Exploitation",
    "systeme_exploitation":         "💻 Système d'Exploitation",
    "web":                          "🌐 Développement Web",
    "dev_web":                      "🌐 Développement Web",
    "system_logique":               "🔢 Système Logique",
    "systeme_logique":              "🔢 Système Logique",
    "cisco":                        "📡 CISCO",
    "francais":                     "📚 Français",
    "français":                     "📚 Français",
    "reseau":                       "🌐 Réseau",
    "réseau":                       "🌐 Réseau",
    "tec1":                         "📝 TEC1",
    "anglais":                      "🇬🇧 Anglais",
    "architecture des ordinateurs": "🖥️ Architecture des Ordinateurs",
    "architecture_ordinateurs":     "🖥️ Architecture des Ordinateurs",
    "analyse-math":                 "📊 Analyse & Mathématiques",
    "analyse_math":                 "📊 Analyse & Mathématiques",
    "analyse math":                 "📊 Analyse & Mathématiques",
    "base de données":              "🗄️ Base de Données",
    "base_de_donnees":              "🗄️ Base de Données",
    "base_donnees":                 "🗄️ Base de Données",
}

def get_nom_matiere(matiere):
    key = matiere.lower().strip()
    return noms_matieres_base.get(key) or "📚 " + matiere.replace("_", " ").capitalize()

extensions_valides = (
    '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',
    '.txt', '.png', '.jpg', '.jpeg', '.zip', '.rar',
    '.c', '.cpp', '.py', '.java', '.html', '.css', '.js', '.heic'
)

KEYWORDS_SUJET = [
    "sujet entrainement", "sujet entraînement",
    "sujet_entrainement", "sujet_entraînement",
    "sujet révision", "sujet revision",
    "sujet_révision", "sujet_revision",
    "sujets", "sujet", "révision", "revision",
    "entrainement", "entraînement",
]

def est_dossier_sujet(chemin):
    nom = os.path.basename(chemin).lower().strip()
    for kw in KEYWORDS_SUJET:
        if kw in nom: return True
    return False

# ==========================================
# 🌴 3. MESSAGE SPÉCIAL ÉTÉ
# ==========================================
AFFICHER_MESSAGE_ETE = True
decor_css = "body::after { content: '🌴'; position: fixed; top: 20px; right: 20px; font-size: 2.5rem; opacity: 0.8; pointer-events: none; z-index: 1000; }" if AFFICHER_MESSAGE_ETE else ""

# ==========================================
# 🎓 5. GÉNÉRATION DU SITE NORMAL
# ==========================================
maintenant = datetime.datetime.now()
date_maj = maintenant.strftime("%d/%m/%Y à %H:%M")

dossier_principal = "cours"
total_fichiers = 0
data = {}

if os.path.exists(dossier_principal):
    for filiere in sorted(os.listdir(dossier_principal)):
        if filiere.startswith('.'): continue
        chemin_filiere = os.path.join(dossier_principal, filiere)
        if not os.path.isdir(chemin_filiere): continue

        for annee in sorted(os.listdir(chemin_filiere)):
            if annee.startswith('.'): continue
            chemin_annee = os.path.join(chemin_filiere, annee)
            if not os.path.isdir(chemin_annee): continue

            for matiere in sorted(os.listdir(chemin_annee)):
                if matiere.startswith('.'): continue
                chemin_matiere = os.path.join(chemin_annee, matiere)
                if not os.path.isdir(chemin_matiere): continue

                fichiers_cours, fichiers_td, fichiers_tp, fichiers_sujets = "", "", "", ""

                for racine, dirs, fichiers in os.walk(chemin_matiere):
                    for fichier in sorted(fichiers):
                        if not fichier.lower().endswith(extensions_valides): continue
                        total_fichiers += 1

                        chemin_fichier_complet = os.path.join(racine, fichier)
                        chemin_web = chemin_fichier_complet.replace("\\", "/")
                        parent_lower = racine.lower()
                        nom_affichable = fichier.replace("_", " ")

                        taille_bytes = os.path.getsize(chemin_fichier_complet)
                        taille_str = f"{taille_bytes / 1024:.1f} Ko" if taille_bytes < 1024 * 1024 else f"{taille_bytes / (1024 * 1024):.1f} Mo"
                        span_taille = f"<span class='file-size'>{taille_str}</span>"
                        lien = f'<a href="{chemin_web}" target="_blank" class="file-link">'

                        if est_dossier_sujet(racine): fichiers_sujets += f'{lien}<span class="tag tag-sujet">SUJET</span> 📄 {nom_affichable} {span_taille}</a>\n'
                        elif "td" in parent_lower or "td" in fichier.lower(): fichiers_td += f'{lien}<span class="tag tag-td">TD</span> 📝 {nom_affichable} {span_taille}</a>\n'
                        elif "tp" in parent_lower or "tp" in fichier.lower(): fichiers_tp += f'{lien}<span class="tag tag-tp">TP</span> ⚙️ {nom_affichable} {span_taille}</a>\n'
                        else: fichiers_cours += f'{lien}<span class="tag tag-cours">COURS</span> 📖 {nom_affichable} {span_taille}</a>\n'

                titre = get_nom_matiere(matiere)

                if annee not in data: data[annee] = {}
                if filiere not in data[annee]: data[annee][filiere] = {}
                data[annee][filiere][matiere] = {
                    "titre":  titre,
                    "cours":  fichiers_cours,
                    "td":     fichiers_td,
                    "tp":     fichiers_tp,
                    "sujets": fichiers_sujets,
                }

cartes_html = ""
for annee, filieres in data.items():
    for filiere, matieres in filieres.items():
        for matiere, info in matieres.items():
            cartes_html += f'<div class="card" data-filiere="{filiere}" data-annee="{annee}">'
            cartes_html += f'<div class="card-badge">{filiere} - {annee}</div>'
            cartes_html += f'<h2>{info["titre"]}</h2><div class="file-list">'

            if not info["cours"] and not info["td"] and not info["tp"] and not info["sujets"]:
                cartes_html += '<p style="font-size:0.8rem;font-style:italic;opacity:0.7;">Aucun fichier.</p>'
            else:
                if info["cours"]: cartes_html += f'<details class="sub-section"><summary class="sub-title">📖 Cours</summary><div class="folder-content">{info["cours"]}</div></details>'
                if info["td"]: cartes_html += f'<details class="sub-section"><summary class="sub-title">📝 Travaux Dirigés</summary><div class="folder-content">{info["td"]}</div></details>'
                if info["tp"]: cartes_html += f'<details class="sub-section"><summary class="sub-title">⚙️ Travaux Pratiques</summary><div class="folder-content">{info["tp"]}</div></details>'
                if info["sujets"]: cartes_html += f'<details class="sub-section"><summary class="sub-title">📄 Sujets d\'entraînement</summary><div class="folder-content">{info["sujets"]}</div></details>'
            cartes_html += '</div></div>'

annee_labels = {"L1": ("📘", "Licence 1"), "L2": ("📗", "Licence 2"), "L3": ("📕", "Licence 3")}
ecran_annees_html = '<div class="nav-grid">'
for annee in ["L1", "L2", "L3"]:
    emoji, label = annee_labels.get(annee, ("📚", annee))
    nb = sum(len(mats) for mats in data.get(annee, {}).values())
    ecran_annees_html += f'<div class="nav-card" onclick="goFiliere(\'{annee}\')"><div class="nav-card-icon">{emoji}</div><div class="nav-card-title">{label}</div><div class="nav-card-sub">{"Aucun document" if nb == 0 else f"{nb} matière(s)"}</div></div>'
ecran_annees_html += '</div>'

filiere_labels = {"GI":  ["💻", "Génie Informatique", "GI"], "MRT": ["📡", "Maintenance Réseau Telecom", "MRT"], "GE":  ["📊", "Gestion des Entreprises", "GE"]}

data_json           = json.dumps(data, ensure_ascii=False)
filiere_labels_json = json.dumps(filiere_labels, ensure_ascii=False)

display_login = "flex" if MOT_DE_PASSE_ACTIF else "none"
display_main  = "none" if MOT_DE_PASSE_ACTIF else "block"
message_ete_html  = '<div class="special-message">☀️ Plus que deux mois avant l\'été ! 🌴</div>' if AFFICHER_MESSAGE_ETE else ''

html_complet = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drive Universitaire</title>
    <style>
        :root {{
            --primary: #d4af37; --bg: #f8fafc; --card: rgba(255, 255, 255, 0.9);
            --text: #1e293b; --border: rgba(226, 232, 240, 0.8);
            --link-bg: rgba(248, 250, 252, 0.8); --link-hover: #fffbeb;
            --subtitle-bg: rgba(255, 255, 255, 0.8); --subtitle-hover: rgba(241, 245, 249, 0.9);
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{ --card: rgba(30, 41, 59, 0.9); --text: #f1f5f9; --border: rgba(51, 65, 85, 0.8); --link-bg: rgba(15, 23, 42, 0.8); --link-hover: #334155; --subtitle-bg: rgba(30, 41, 59, 0.8); --subtitle-hover: rgba(51, 65, 85, 0.9); }}
            .special-message {{ background: #0c4a6e !important; color: #38bdf8 !important; border-color: #0284c7 !important; }}
            .subtitle, footer {{ color: #e2e8f0 !important; text-shadow: 1px 1px 2px #000; }}
            .file-link {{ color: #cbd5e1 !important; }}
            .nav-card {{ background: rgba(30, 41, 59, 0.9) !important; }}
            .nav-card:hover {{ background: rgba(38, 48, 68, 0.95) !important; }}
            .breadcrumb {{ background: rgba(30, 41, 59, 0.9) !important; border-color: rgba(51, 65, 85, 0.8) !important; }}
        }}
        * {{ box-sizing: border-box; }}
        
        /* ICI C'EST LE FOND D'ÉCRAN ! */
        body {{ 
            font-family: 'Inter', system-ui, sans-serif; 
            background: url('fond.png') no-repeat center center fixed; 
            background-size: cover;
            color: var(--text); 
            padding: 0; 
            line-height: 1.5; 
            margin: 0; 
            transition: color 0.3s; 
            scroll-behavior: smooth; 
        }}
        
        {decor_css}

        #login-screen {{ position: fixed; top: 0; left: 0; width: 100%; height: 100vh; background: rgba(0,0,0,0.5); backdrop-filter: blur(5px); display: {display_login}; align-items: center; justify-content: center; z-index: 9999; }}
        .login-box {{ background: var(--card); padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); border: 1px solid var(--border); text-align: center; max-width: 350px; width: 90%; backdrop-filter: blur(10px); }}
        .login-box h2 {{ color: var(--primary); margin-top: 0; font-size: 1.8rem; margin-bottom: 5px; }}
        .login-box p {{ color: #64748b; font-size: 0.9rem; margin-bottom: 25px; }}
        .login-box input {{ width: 100%; padding: 12px; margin-bottom: 15px; border: 2px solid var(--border); border-radius: 8px; background: rgba(255,255,255,0.5); color: var(--text); outline: none; transition: 0.2s; }}
        .login-box input:focus {{ border-color: var(--primary); }}
        .login-box button {{ width: 100%; padding: 12px; background: var(--primary); color: white; border: none; border-radius: 8px; font-size: 1rem; font-weight: bold; cursor: pointer; transition: 0.2s; }}
        .login-box button:hover {{ transform: translateY(-2px); box-shadow: 0 5px 15px rgba(212,175,55,0.4); }}
        #login-error {{ color: #ef4444; font-size: 0.85rem; margin-top: 15px; display: none; font-weight: bold; }}
        .login-warning {{ font-size: 0.75rem; color: #94a3b8; margin-top: 20px; }}

        #main-content {{ display: {display_main}; padding: 20px; min-height: 100vh; }}
        header {{ text-align: center; padding: 30px; background: var(--card); border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); border-bottom: 4px solid var(--primary); max-width: 1160px; margin: 0 auto 30px auto; backdrop-filter: blur(10px); }}
        h1 {{ margin: 0; color: var(--primary); font-size: 2rem; }}
        .subtitle {{ font-size: 1.1rem; color: #1e293b; margin-top: 5px; font-weight: bold; }}
        .special-message {{ margin-top: 15px; font-size: 0.9rem; background: #e0f2fe; color: #0369a1; padding: 8px 20px; border-radius: 20px; display: inline-block; border: 1px solid #7dd3fc; font-weight: bold; }}

        .breadcrumb {{ display: none; align-items: center; gap: 8px; max-width: 1200px; margin: 0 auto 20px auto; background: var(--card); padding: 12px 20px; border-radius: 12px; border: 1px solid var(--border); flex-wrap: wrap; backdrop-filter: blur(10px); }}
        .breadcrumb.visible {{ display: flex; }}
        .bc-item {{ color: var(--text); font-size: 0.9rem; font-weight: 500; }}
        .bc-item.link {{ color: var(--primary); cursor: pointer; font-weight: 600; text-decoration: underline; text-underline-offset: 3px; }}
        .bc-item.link:hover {{ opacity: 0.75; }}
        .bc-sep {{ color: #cbd5e1; font-size: 0.8rem; }}
        .btn-retour {{ margin-left: auto; padding: 6px 16px; background: var(--primary); color: white; border: none; border-radius: 8px; font-size: 0.85rem; font-weight: bold; cursor: pointer; transition: 0.2s; }}
        .btn-retour:hover {{ transform: translateY(-1px); box-shadow: 0 3px 10px rgba(212,175,55,0.4); }}

        .screen {{ display: none; max-width: 1200px; margin: 0 auto; animation: fadeIn 0.25s ease; }}
        .screen.active {{ display: block; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .screen-title {{ font-size: 1.3rem; font-weight: 800; margin-bottom: 20px; color: var(--text); background: var(--card); display: inline-block; padding: 5px 15px; border-radius: 8px; backdrop-filter: blur(10px); }}
        .screen-title span {{ color: var(--primary); }}

        .nav-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
        .nav-card {{ background: var(--card); border: 2px solid var(--border); border-radius: 16px; padding: 30px 20px; text-align: center; cursor: pointer; transition: all 0.25s; backdrop-filter: blur(10px); }}
        .nav-card:hover {{ border-color: var(--primary); transform: translateY(-4px); box-shadow: 0 10px 25px rgba(212,175,55,0.4); }}
        .nav-card-icon {{ font-size: 3rem; margin-bottom: 12px; }}
        .nav-card-title {{ font-size: 1.1rem; font-weight: 800; color: var(--text); margin-bottom: 5px; }}
        .nav-card-sub {{ font-size: 0.85rem; color: var(--text); opacity: 0.8; }}

        .filters {{ display: flex; gap: 15px; justify-content: center; margin-bottom: 25px; flex-wrap: wrap; }}
        .search-container {{ width: 100%; max-width: 340px; }}
        input[type="text"] {{ width: 100%; padding: 10px 15px; border-radius: 25px; border: 2px solid var(--border); background: var(--card); color: var(--text); font-size: 0.95rem; outline: none; transition: 0.3s; backdrop-filter: blur(10px); }}
        input[type="text"]:focus {{ border-color: var(--primary); box-shadow: 0 0 10px rgba(212,175,55,0.3); }}

        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }}
        .card {{ background: var(--card); border-radius: 12px; padding: 20px; border: 1px solid var(--border); transition: all 0.3s; backdrop-filter: blur(10px); }}
        .card:hover {{ transform: translateY(-3px); box-shadow: 0 10px 20px rgba(0,0,0,0.3); }}
        .card-badge {{ font-size: 0.7rem; color: #fff; background: var(--primary); padding: 3px 8px; border-radius: 12px; display: inline-block; margin-bottom: 10px; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
        h2 {{ font-size: 1.1rem; margin: 0 0 15px 0; padding-bottom: 10px; border-bottom: 2px solid var(--border); display: flex; align-items: center; gap: 10px; }}

        details.sub-section {{ margin-bottom: 12px; background: var(--link-bg); border-radius: 8px; border: 1px solid var(--border); overflow: hidden; }}
        summary.sub-title {{ font-size: 0.95rem; font-weight: bold; color: var(--text); padding: 12px 15px; cursor: pointer; display: flex; align-items: center; justify-content: space-between; background: var(--subtitle-bg); transition: 0.2s; list-style: none; user-select: none; }}
        summary.sub-title::-webkit-details-marker {{ display: none; }}
        summary.sub-title:hover {{ background: var(--subtitle-hover); }}
        summary.sub-title::after {{ content: '▼'; font-size: 0.8rem; color: var(--text); opacity: 0.6; transition: transform 0.3s; }}
        details[open] summary.sub-title::after {{ transform: rotate(180deg); }}
        details[open] summary.sub-title {{ border-bottom: 1px solid var(--border); }}
        .folder-content {{ padding: 12px; display: flex; flex-direction: column; gap: 8px; }}

        .file-link {{ display: flex; align-items: center; text-decoration: none; color: var(--text); padding: 10px; background: var(--subtitle-bg); border-radius: 8px; font-size: 0.9rem; border: 1px solid var(--border); transition: all 0.2s; }}
        .file-link:hover {{ background: var(--link-hover); border-color: var(--primary); color: var(--primary) !important; transform: translateX(5px); }}
        .file-size {{ font-size: 0.75rem; opacity: 0.6; margin-left: auto; font-weight: normal; }}

        .tag {{ font-size: 0.65rem; font-weight: 800; padding: 3px 7px; border-radius: 5px; margin-right: 10px; text-transform: uppercase; }}
        .tag-cours  {{ background: rgba(245,158,11,0.2);  color: #d97706; border: 1px solid rgba(245,158,11,0.3); }}
        .tag-td     {{ background: rgba(34,197,94,0.2);   color: #16a34a; border: 1px solid rgba(34,197,94,0.3); }}
        .tag-tp     {{ background: rgba(56,189,248,0.2);  color: #0284c7; border: 1px solid rgba(56,189,248,0.3); }}
        .tag-sujet  {{ background: rgba(168,85,247,0.2);  color: #9333ea; border: 1px solid rgba(168,85,247,0.3); }}

        #no-result {{ display: none; text-align: center; padding: 60px 20px; color: var(--text); background: var(--card); border-radius: 12px; margin-top: 20px; font-size: 1.1rem; backdrop-filter: blur(10px); }}
        #no-result span {{ font-size: 3rem; display: block; margin-bottom: 15px; }}

        #backToTop {{ display: none; position: fixed; bottom: 30px; right: 30px; z-index: 99; font-size: 1.5rem; border: none; outline: none; background-color: var(--primary); color: white; cursor: pointer; border-radius: 50%; width: 50px; height: 50px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); transition: 0.3s; justify-content: center; align-items: center; opacity: 0; pointer-events: none; }}
        #backToTop.show {{ opacity: 1; pointer-events: auto; display: flex; }}
        #backToTop:hover {{ transform: translateY(-5px); box-shadow: 0 6px 15px rgba(212,175,55,0.5); }}

        footer {{ text-align: center; margin-top: 60px; padding: 30px; font-size: 0.95rem; color: #ffffff; text-shadow: 1px 1px 3px rgba(0,0,0,0.8); line-height: 1.8; }}
        .boss-name {{ color: var(--primary); font-weight: 900; font-size: 1.1rem; text-shadow: 1px 1px 3px rgba(0,0,0,0.8); }}
        .copyright {{ font-size: 0.8rem; margin-top: 10px; padding-top: 15px; line-height: 1.7; }}
    </style>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-PWQN6WBSV4"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-PWQN6WBSV4');
    </script>
</head>
<body>

<div id="login-screen">
    <div class="login-box">
        <h2>🔒 Accès Privé</h2>
        <p>Entrez vos identifiants pour accéder au Drive.</p>
        <input type="text" id="username" placeholder="Identifiant" autocomplete="off">
        <input type="password" id="password" placeholder="Mot de passe">
        <button onclick="verifierLogin()">Se connecter</button>
        <p id="login-error">❌ Identifiant ou mot de passe incorrect.</p>
        <p class="login-warning">⚠️ Protection basique — ne pas partager pour des documents confidentiels.</p>
    </div>
</div>

<div id="main-content">
    <header>
        <h1>🎓 Drive Universitaire</h1>
        <div class="subtitle">GI • MRT • GE | <b>{total_fichiers} documents</b></div>
        {message_ete_html}
    </header>

    <div class="breadcrumb" id="breadcrumb">
        <span class="bc-item link" onclick="goHome()">🏠 Accueil</span>
        <span class="bc-sep" id="sep1" style="display:none">›</span>
        <span class="bc-item" id="bc-annee"   style="display:none"></span>
        <span class="bc-sep" id="sep2" style="display:none">›</span>
        <span class="bc-item" id="bc-filiere" style="display:none"></span>
        <button class="btn-retour" onclick="goBack()">← Retour</button>
    </div>

    <div class="screen active" id="screen-annees">
        <p class="screen-title">Choisissez une <span>année</span> :</p>
        {ecran_annees_html}
    </div>

    <div class="screen" id="screen-filieres">
        <p class="screen-title">Choisissez une <span>filière</span> :</p>
        <div class="nav-grid" id="filieres-grid"></div>
    </div>

    <div class="screen" id="screen-matieres">
        <div class="filters">
            <div class="search-container">
                <input type="text" id="searchBar" placeholder="🔍 Rechercher un document...">
            </div>
        </div>
        <div class="grid" id="cards-container">
            {cartes_html}
        </div>
        <div id="no-result">
            <span>🔍</span>
            Aucun document trouvé.<br>
            <small>Essaie un autre mot-clé.</small>
        </div>
    </div>

    <button id="backToTop" title="Retour en haut">↑</button>
    <footer>
        By <span class="boss-name">{NOM_SIGNATURE_NORMAL}</span>
        <div class="copyright">
            © {maintenant.year} {NOM_SIGNATURE_NORMAL} — Tous droits réservés.<br>
        </div>
    </footer>
</div>

<script>
const DATA           = {data_json};
const FILIERE_LABELS = {filiere_labels_json};
const ALL_FILIERES   = ["GI", "MRT", "GE"];

let currentAnnee   = null;
let currentFiliere = null;
let navHistory     = [];

function verifierLogin() {{
    var user = document.getElementById("username").value;
    var pass = document.getElementById("password").value;
    if (user === "{LOGIN_REQUIS}" && pass === "{MDP_REQUIS}") {{
        sessionStorage.setItem("driveAutorise", "oui");
        afficherSite();
    }} else {{
        document.getElementById("login-error").style.display = "block";
        var box = document.querySelector(".login-box");
        box.style.transform = "translateX(10px)";
        setTimeout(() => box.style.transform = "translateX(-10px)", 100);
        setTimeout(() => box.style.transform = "translateX(0)", 200);
    }}
}}
function afficherSite() {{
    document.getElementById("login-screen").style.display = "none";
    document.getElementById("main-content").style.display = "block";
}}
if ("{MOT_DE_PASSE_ACTIF}" === "False" || sessionStorage.getItem("driveAutorise") === "oui") {{
    afficherSite();
}}
document.getElementById("password").addEventListener("keypress", e => {{
    if (e.key === "Enter") verifierLogin();
}});

function showScreen(id) {{
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    window.scrollTo({{ top: 0, behavior: 'smooth' }});
}}

function updateBreadcrumb() {{
    const bc = document.getElementById('breadcrumb');
    if (navHistory.length === 0) {{ bc.classList.remove('visible'); return; }}
    bc.classList.add('visible');

    const bcAnnee   = document.getElementById('bc-annee');
    const bcFiliere = document.getElementById('bc-filiere');

    if (currentAnnee) {{
        document.getElementById('sep1').style.display = '';
        bcAnnee.style.display = '';
        bcAnnee.textContent = currentAnnee;
        if (navHistory[navHistory.length - 1] !== 'filieres') {{
            bcAnnee.classList.add('link');
            bcAnnee.onclick = () => goFiliere(currentAnnee);
        }} else {{
            bcAnnee.classList.remove('link');
            bcAnnee.onclick = null;
        }}
    }} else {{
        document.getElementById('sep1').style.display = 'none';
        bcAnnee.style.display = 'none';
    }}

    if (currentFiliere) {{
        const lbl = FILIERE_LABELS[currentFiliere];
        document.getElementById('sep2').style.display = '';
        bcFiliere.style.display = '';
        bcFiliere.textContent = lbl ? lbl[2] + ' · ' + lbl[1] : currentFiliere;
        bcFiliere.classList.remove('link');
    }} else {{
        document.getElementById('sep2').style.display = 'none';
        bcFiliere.style.display = 'none';
    }}
}}

function goFiliere(annee) {{
    currentAnnee   = annee;
    currentFiliere = null;
    navHistory     = ['filieres'];

    const grid     = document.getElementById('filieres-grid');
    grid.innerHTML = '';
    const filieres = DATA[annee] || {{}};

    ALL_FILIERES.forEach(fil => {{
        const matieres  = filieres[fil] || {{}};
        const nb        = Object.keys(matieres).length;
        const lbl       = FILIERE_LABELS[fil];
        const emoji     = lbl ? lbl[0] : '📁';
        const nom       = lbl ? lbl[1] : fil;
        const code      = lbl ? lbl[2] : fil;
        const sousTitre = nb === 0 ? 'Aucun document' : nb + ' matière' + (nb > 1 ? 's' : '');
        grid.innerHTML += `
            <div class="nav-card" onclick="goMatieres('${{annee}}', '${{fil}}')">
                <div class="nav-card-icon">${{emoji}}</div>
                <div class="nav-card-title">${{nom}}</div>
                <div class="nav-card-sub">${{code}} • ${{sousTitre}}</div>
            </div>`;
    }});

    showScreen('screen-filieres');
    updateBreadcrumb();
}}

function goMatieres(annee, filiere) {{
    currentAnnee   = annee;
    currentFiliere = filiere;
    navHistory     = ['filieres', 'matieres'];

    let count = 0;
    document.querySelectorAll('.card').forEach(card => {{
        const show = card.dataset.filiere === filiere && card.dataset.annee === annee;
        card.style.display = show ? 'block' : 'none';
        if (show) count++;
    }});

    document.getElementById('searchBar').value = '';
    document.querySelectorAll('details').forEach(d => d.open = false);
    document.querySelectorAll('.file-link').forEach(l => l.style.display = 'flex');
    document.getElementById('no-result').style.display = count === 0 ? 'block' : 'none';

    showScreen('screen-matieres');
    updateBreadcrumb();
}}

function goBack() {{
    if (navHistory.length === 0) return;
    navHistory.pop();
    const current = navHistory[navHistory.length - 1];
    if (current === 'filieres') {{
        currentFiliere = null;
        showScreen('screen-filieres');
        updateBreadcrumb();
    }} else {{
        goHome();
    }}
}}

function goHome() {{
    currentAnnee = currentFiliere = null;
    navHistory   = [];
    showScreen('screen-annees');
    updateBreadcrumb();
}}

document.getElementById('searchBar').addEventListener('keyup', function() {{
    const term = this.value.toLowerCase().trim();
    let count  = 0;

    document.querySelectorAll('.card').forEach(card => {{
        if (card.dataset.filiere !== currentFiliere || card.dataset.annee !== currentAnnee) return;

        const links = card.querySelectorAll('.file-link');
        let hasVisible = false;

        links.forEach(link => {{
            const show = link.textContent.toLowerCase().includes(term);
            link.style.display = show ? 'flex' : 'none';
            if (show) hasVisible = true;
        }});

        card.querySelectorAll('details').forEach(d => {{
            if (term !== '') {{
                d.open = true;
            }} else {{
                d.open = false;
                d.querySelectorAll('.file-link').forEach(l => l.style.display = 'flex');
                hasVisible = true;
            }}
        }});

        const show = hasVisible || (term === '' && links.length === 0);
        card.style.display = show ? 'block' : 'none';
        if (show) count++;
    }});

    document.getElementById('no-result').style.display = count === 0 ? 'block' : 'none';
}});

const btn = document.getElementById("backToTop");
window.onscroll = () => btn.classList.toggle("show", document.documentElement.scrollTop > 300);
btn.onclick     = () => window.scrollTo({{ top: 0, behavior: 'smooth' }});
</script>
</body>
</html>"""

# ==========================================
# 💾 6. ÉCRITURE ET ENVOI GITHUB
# ==========================================
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_complet)

print("✅ index.html généré avec succès !")

try:
    subprocess.run(["git", "add", "."], check=True)

    if MODE_MAINTENANCE:
        message_commit = "🚧 Mise en maintenance du site (Avec fond personnalisé)"
    elif MOT_DE_PASSE_ACTIF:
        message_commit = f"🔒 Mise à jour du drive (accès protégé) - {date_maj}"
    else:
        message_commit = f"📚 Mise à jour du drive - {date_maj} (Avec fond personnalisé)"

    subprocess.run(["git", "commit", "-m", message_commit], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

    if MODE_MAINTENANCE:
        print("🚧 LE SITE EST FERMÉ ! (Mode maintenance actif)")
    else:
        print(f"🌍 SITE EN LIGNE ! | Mot de passe : {'✅ Activé' if MOT_DE_PASSE_ACTIF else '🔓 Désactivé'} | {total_fichiers} fichiers indexés")

except Exception as e:
    print(f"⚠️  Git : {e}")
    print("   → Fais un Cmd+S ou modifie une lettre si 'nothing to commit'")
