// API du Drive Universitaire : /api/...
import {
  json, ErreurHttp, ANNEES, FILIERES, normId, propre, genererMdp, aleatoire, hacherMdp, verifierMdp, dateFr, ficheDocument, DEPOT,
} from "../../lib/outils.js";
import {
  base, initialiser, lireSite, ecrireReglage, lireReglage, noter, creerSauvegarde, sauvegardeAutoSiBesoin,
  instantane, restaurer, verifierFormat,
} from "../../lib/base.js";
import { ouvrirSession, fermerSession, exigerConnexion, verifierEssais, essaiRate, essaiReussi } from "../../lib/auth.js";
import { testerJeton, envoyerBlob, commit, etatPublication } from "../../lib/github.js";

const TAILLE_MAX = 25 * 1024 * 1024;   // limite Cloudflare Pages par fichier

async function corps(request) {
  try { return await request.json(); } catch (e) { throw new ErreurHttp(400, "Requête illisible."); }
}

const utilisateurPublic = u => ({
  id: u.id, nom: u.nom, role: u.role, matieres: typeof u.matieres === "string" ? JSON.parse(u.matieres || "[]") : (u.matieres || []),
  cree: u.cree, actif: !!u.hash, derniere_connexion: u.derniere_connexion || null,
});

function verifierMatieres(liste) {
  return (Array.isArray(liste) ? liste : []).filter(m => m && ANNEES.includes(m.annee) && FILIERES.includes(m.filiere) && propre(m.matiere))
    .map(m => ({ annee: m.annee, filiere: m.filiere, matiere: propre(m.matiere) }));
}

async function nouveauMotDePasse(env, id) {
  const mdp = genererMdp(), sel = aleatoire(16);
  await base(env).batch([
    base(env).prepare("UPDATE utilisateurs SET hash = ?, sel = ?, modifie = ? WHERE id = ?").bind(await hacherMdp(mdp, sel), sel, Date.now(), id),
    base(env).prepare("DELETE FROM sessions WHERE utilisateur = ?").bind(id),
  ]);
  return mdp;
}

// ── Routes ──
const routes = [];
const route = (methode, motif, role, action) => routes.push({ methode, motif: new RegExp("^" + motif + "$"), role, action });

// État de la base (visible sans connexion)
route("GET", "/etat", null, async ({ env }) => {
  const admin = await base(env).prepare("SELECT COUNT(*) AS n FROM utilisateurs WHERE role = 'admin' AND hash IS NOT NULL").first();
  return { base: true, installe: admin.n > 0, depot: `${DEPOT.owner}/${DEPOT.repo}` };
});

// Première installation : création du compte propriétaire (preuve = jeton GitHub du dépôt)
route("POST", "/installer", null, async ({ env, request, ip }) => {
  const d = await corps(request);
  const admin = await base(env).prepare("SELECT COUNT(*) AS n FROM utilisateurs WHERE role = 'admin' AND hash IS NOT NULL").first();
  if (admin.n > 0) throw new ErreurHttp(409, "Le site est déjà installé. Connecte-toi normalement.");
  await verifierEssais(env, ["ip:" + ip]);
  const id = normId(d.id), nom = propre(d.nom), mdp = String(d.mdp || ""), jeton = String(d.token || "").trim();
  if (!id || !nom) throw new ErreurHttp(400, "Indique ton nom et ton identifiant.");
  if (mdp.length < 8) throw new ErreurHttp(400, "Le mot de passe doit faire au moins 8 caractères.");
  try { await testerJeton(jeton); } catch (e) { await essaiRate(env, ["ip:" + ip]); throw e; }
  const sel = aleatoire(16);
  await base(env).batch([
    base(env).prepare(`INSERT INTO utilisateurs (id, nom, role, matieres, hash, sel, cree, modifie) VALUES (?, ?, 'admin', '[]', ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET nom = excluded.nom, role = 'admin', hash = excluded.hash, sel = excluded.sel, modifie = excluded.modifie`)
      .bind(id, nom, await hacherMdp(mdp, sel), sel, dateFr(), Date.now()),
    base(env).prepare("INSERT INTO reglages (cle, valeur, modifie) VALUES ('github_token', ?, ?) ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur, modifie = excluded.modifie")
      .bind(JSON.stringify(jeton), Date.now()),
  ]);
  await noter(env, nom, "installation", "Compte propriétaire créé et site relié à GitHub");
  await creerSauvegarde(env, nom, "auto", "Première sauvegarde après installation");
  return { ok: true, cookie: await ouvrirSession(env, id, true) };
});

route("POST", "/connexion", null, async ({ env, request, ip }) => {
  const d = await corps(request);
  const id = normId(d.id), mdp = String(d.mdp || "");
  const cles = ["ip:" + ip, "id:" + id];
  await verifierEssais(env, cles);
  const u = id && await base(env).prepare("SELECT id, hash, sel FROM utilisateurs WHERE id = ?").bind(id).first();
  if (u && !u.hash) throw new ErreurHttp(403, "Ce compte n'a pas encore de mot de passe. Demande à l'administrateur de t'en créer un.");
  if (!u || !(await verifierMdp(mdp, u.sel, u.hash))) {
    await essaiRate(env, cles);
    await new Promise(r => setTimeout(r, 600));
    throw new ErreurHttp(401, "Identifiant ou mot de passe incorrect.");
  }
  await essaiReussi(env, cles);
  return { ok: true, cookie: await ouvrirSession(env, u.id, !!d.memoriser) };
});

route("POST", "/deconnexion", null, async ({ env, request }) => ({ ok: true, cookie: await fermerSession(env, request) }));

route("GET", "/moi", "connecte", async ({ env, moi }) => {
  if (moi.role === "admin") await sauvegardeAutoSiBesoin(env, moi.nom);
  const github = !!(await lireReglage(env, "github_token", null));
  return { ...moi, github };
});

route("POST", "/moi/mdp", "connecte", async ({ env, request, moi }) => {
  const d = await corps(request);
  const nouveau = String(d.nouveau || "");
  if (nouveau.length < 8) throw new ErreurHttp(400, "8 caractères minimum.");
  const sel = aleatoire(16);
  await base(env).prepare("UPDATE utilisateurs SET hash = ?, sel = ?, modifie = ? WHERE id = ?").bind(await hacherMdp(nouveau, sel), sel, Date.now(), moi.id).run();
  await noter(env, moi.nom, "mot de passe", "A changé son mot de passe");
  return { ok: true };
});

// ── Documents ──
route("GET", "/documents", "connecte", async ({ env }) => {
  const r = await base(env).prepare("SELECT path, filiere, annee, matiere, titre_defaut, n, e, t, s, d, source, par FROM documents ORDER BY annee, filiere, matiere, path").all();
  return { documents: r.results, site: { noms_matieres: (await lireSite(env)).noms_matieres } };
});

// Étape 1 : envoi d'un fichier (corps {content, encoding:"base64"} transmis tel quel à GitHub)
route("POST", "/fichiers/blob", "connecte", async ({ env, request }) => {
  const taille = +request.headers.get("Content-Length") || 0;
  if (taille > TAILLE_MAX * 1.4 + 1000) throw new ErreurHttp(413, "Fichier trop lourd (25 Mo maximum).");
  return { sha: await envoyerBlob(env, await request.arrayBuffer()) };
});

// Étape 2 : publication (un commit pour tous les fichiers) + ajout immédiat dans la base
route("POST", "/fichiers/publier", "connecte", async ({ env, request, moi }) => {
  const d = await corps(request);
  const annee = d.annee, filiere = d.filiere, matiere = propre(d.matiere), type = d.type;
  if (!ANNEES.includes(annee) || !FILIERES.includes(filiere) || !matiere) throw new ErreurHttp(400, "Choisis l'année, la filière et la matière.");
  const dossierType = propre(d.dossier || type);
  if (!dossierType) throw new ErreurHttp(400, "Type de document manquant.");
  const fichiers = (Array.isArray(d.fichiers) ? d.fichiers : []).map(f => ({ nom: propre(f.nom), sha: String(f.sha || ""), taille: +f.taille || 0 }))
    .filter(f => f.nom && /^[0-9a-f]{40}$/.test(f.sha));
  if (!fichiers.length) throw new ErreurHttp(400, "Aucun fichier à publier.");
  const dossier = `cours/${filiere}/${annee}/${matiere}/${dossierType}`;
  const entrees = fichiers.map(f => ({ path: `${dossier}/${f.nom}`, sha: f.sha }));
  const noms = fichiers.map(f => f.nom);
  await commit(env, entrees, `📚 Ajout ${noms.length > 1 ? noms.length + " fichiers" : noms[0]} — ${annee} ${filiere} ${matiere} (${type}) — par ${moi.nom}`, moi);
  const existant = await base(env).prepare("SELECT titre_defaut FROM documents WHERE annee = ? AND filiere = ? AND matiere = ? LIMIT 1").bind(annee, filiere, matiere).first();
  const maintenant = Math.floor(Date.now() / 1000);
  const ops = fichiers.map(f => {
    const x = ficheDocument(`${dossier}/${f.nom}`, f.taille, maintenant);
    return base(env).prepare(`INSERT INTO documents (path, filiere, annee, matiere, titre_defaut, n, e, t, s, d, source, par)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'admin', ?)
      ON CONFLICT(path) DO UPDATE SET s = excluded.s, d = excluded.d, source = 'admin', par = excluded.par`)
      .bind(x.path, x.filiere, x.annee, x.matiere, (existant && existant.titre_defaut) || x.titre_defaut, x.n, x.e, x.t, x.s, x.d, moi.nom);
  });
  await base(env).batch(ops);
  await noter(env, moi.nom, "ajout", `${noms.join(", ")} → ${annee} ${filiere} ${matiere} (${type})`);
  return { ok: true, dossier };
});

route("POST", "/fichiers/supprimer", "connecte", async ({ env, request, moi }) => {
  const d = await corps(request);
  const chemins = (Array.isArray(d.chemins) ? d.chemins : [d.chemin]).map(c => String(c || "").normalize("NFC")).filter(c => c.startsWith("cours/") && !c.includes(".."));
  if (!chemins.length) throw new ErreurHttp(400, "Aucun fichier indiqué.");
  await commit(env, chemins.map(p => ({ path: p, sha: null })), `🗑 Suppression ${chemins.length > 1 ? chemins.length + " fichiers" : chemins[0].split("/").pop()} — par ${moi.nom}`, moi);
  await base(env).batch(chemins.map(p => base(env).prepare("DELETE FROM documents WHERE path = ?").bind(p)));
  await noter(env, moi.nom, "suppression", chemins.map(c => c.split("/").pop()).join(", "));
  return { ok: true };
});

// ── Matières (admin) ──
route("POST", "/matieres/nom", "admin", async ({ env, request, moi }) => {
  const d = await corps(request);
  const cle = String(d.cle || ""), nom = propre(d.nom);
  if (cle.split("/").length !== 3) throw new ErreurHttp(400, "Matière inconnue.");
  const site = await lireSite(env);
  if (!nom || nom === d.defaut) delete site.noms_matieres[cle]; else site.noms_matieres[cle] = nom;
  await ecrireReglage(env, "site", site);
  await noter(env, moi.nom, "matière renommée", `${cle} → ${nom || d.defaut}`);
  return { ok: true, noms_matieres: site.noms_matieres };
});

route("POST", "/matieres/supprimer", "admin", async ({ env, request, moi }) => {
  const d = await corps(request);
  const [filiere, annee, matiere] = String(d.cle || "").split("/");
  const docs = await base(env).prepare("SELECT path FROM documents WHERE filiere = ? AND annee = ? AND matiere = ?").bind(filiere, annee, matiere).all();
  if (!docs.results.length) throw new ErreurHttp(404, "Cette matière n'a aucun fichier.");
  await creerSauvegarde(env, moi.nom, "avant-suppression", `Avant suppression de la matière ${matiere}`);
  await commit(env, docs.results.map(x => ({ path: x.path, sha: null })), `🗑 Suppression de la matière ${matiere} (${annee} ${filiere}) — par ${moi.nom}`, moi);
  await base(env).prepare("DELETE FROM documents WHERE filiere = ? AND annee = ? AND matiere = ?").bind(filiere, annee, matiere).run();
  await noter(env, moi.nom, "matière supprimée", `${matiere} (${annee} ${filiere}), ${docs.results.length} fichier(s)`);
  return { ok: true };
});

// ── Réglages (admin) ──
route("GET", "/reglages", "admin", async ({ env }) => ({ site: await lireSite(env), github: !!(await lireReglage(env, "github_token", null)), publication: await etatPublication(env) }));

route("POST", "/reglages", "admin", async ({ env, request, moi }) => {
  const d = await corps(request);
  const avant = await lireSite(env);
  const s = {
    ...avant,
    maintenance: !!d.maintenance,
    message: String(d.message || "").trim().slice(0, 300),
    nouveau_jours: Math.min(365, Math.max(1, +d.nouveau_jours || 14)),
    signature: String(d.signature || "").trim().slice(0, 120),
    mot_de_passe: { actif: !!(d.mot_de_passe && d.mot_de_passe.actif), login: String((d.mot_de_passe || {}).login || "").trim(), mdp: String((d.mot_de_passe || {}).mdp || "").trim() },
    surprise: { actif: !!(d.surprise && d.surprise.actif), nom: String((d.surprise || {}).nom || "").trim(), titre: String((d.surprise || {}).titre || "").trim(), message: String((d.surprise || {}).message || "").trim() },
  };
  if (s.mot_de_passe.actif && (!s.mot_de_passe.login || !s.mot_de_passe.mdp)) throw new ErreurHttp(400, "Indique l'identifiant et le mot de passe du site.");
  await ecrireReglage(env, "site", s);
  const ch = [];
  if (avant.maintenance !== s.maintenance) ch.push(s.maintenance ? "maintenance activée" : "site rouvert");
  if (avant.mot_de_passe.actif !== s.mot_de_passe.actif) ch.push(s.mot_de_passe.actif ? "mot de passe activé" : "mot de passe désactivé");
  if (avant.surprise.actif !== s.surprise.actif) ch.push(s.surprise.actif ? "surprise activée" : "surprise désactivée");
  if (avant.message !== s.message) ch.push(s.message ? "bandeau : " + s.message : "bandeau retiré");
  await noter(env, moi.nom, "réglages", ch.join(", ") || "Réglages enregistrés");
  return { ok: true, site: s };
});

route("POST", "/github", "admin", async ({ env, request, moi }) => {
  const d = await corps(request);
  const jeton = String(d.token || "").trim();
  await testerJeton(jeton);
  await ecrireReglage(env, "github_token", jeton);
  await noter(env, moi.nom, "github", "Nouveau jeton GitHub enregistré");
  return { ok: true };
});

// ── Utilisateurs (admin) ──
route("GET", "/utilisateurs", "admin", async ({ env }) => {
  const r = await base(env).prepare("SELECT id, nom, role, matieres, cree, hash, derniere_connexion FROM utilisateurs ORDER BY role, nom").all();
  return { utilisateurs: r.results.map(utilisateurPublic) };
});

route("POST", "/utilisateurs", "admin", async ({ env, request, moi }) => {
  const d = await corps(request);
  const id = normId(d.id), nom = propre(d.nom), role = d.role === "admin" ? "admin" : "prof";
  if (!id || !nom) throw new ErreurHttp(400, "Indique le nom et l'identifiant.");
  const ex = await base(env).prepare("SELECT 1 FROM utilisateurs WHERE id = ?").bind(id).first();
  if (ex) throw new ErreurHttp(409, `L'identifiant « ${id} » existe déjà.`);
  await base(env).prepare("INSERT INTO utilisateurs (id, nom, role, matieres, cree, modifie) VALUES (?, ?, ?, ?, ?, ?)")
    .bind(id, nom, role, JSON.stringify(verifierMatieres(d.matieres)), dateFr(), Date.now()).run();
  const mdp = await nouveauMotDePasse(env, id);
  await noter(env, moi.nom, "compte créé", `${nom} (${id}, ${role})`);
  return { ok: true, id, mdp };
});

// Création en lot : [{nom, matieres:[...]}]
route("POST", "/utilisateurs/lot", "admin", async ({ env, request, moi }) => {
  const d = await corps(request);
  const comptes = Array.isArray(d.comptes) ? d.comptes : [];
  const crees = [];
  let maj = 0;
  for (const c of comptes) {
    const id = normId(c.id), nom = propre(c.nom), matieres = verifierMatieres(c.matieres);
    if (!id || !nom) continue;
    const ex = await base(env).prepare("SELECT matieres FROM utilisateurs WHERE id = ?").bind(id).first();
    if (ex) {
      const liste = JSON.parse(ex.matieres || "[]"), avant = liste.length;
      matieres.forEach(m => { if (!liste.some(x => x.matiere === m.matiere && x.annee === m.annee && x.filiere === m.filiere)) liste.push(m); });
      if (liste.length !== avant) { await base(env).prepare("UPDATE utilisateurs SET matieres = ?, modifie = ? WHERE id = ?").bind(JSON.stringify(liste), Date.now(), id).run(); maj++; }
      continue;
    }
    await base(env).prepare("INSERT INTO utilisateurs (id, nom, role, matieres, cree, modifie) VALUES (?, ?, 'prof', ?, ?, ?)")
      .bind(id, nom, JSON.stringify(matieres), dateFr(), Date.now()).run();
    crees.push({ id, nom, matieres, mdp: await nouveauMotDePasse(env, id) });
  }
  if (crees.length || maj) await noter(env, moi.nom, "comptes", `${crees.length} créé(s), ${maj} mis à jour`);
  return { ok: true, crees, maj };
});

route("POST", "/utilisateurs/([a-z0-9._-]+)/mdp", "admin", async ({ env, moi, params }) => {
  const u = await base(env).prepare("SELECT nom FROM utilisateurs WHERE id = ?").bind(params[0]).first();
  if (!u) throw new ErreurHttp(404, "Compte introuvable.");
  const mdp = await nouveauMotDePasse(env, params[0]);
  await noter(env, moi.nom, "mot de passe", `Nouveau mot de passe pour ${u.nom}`);
  return { ok: true, mdp };
});

route("POST", "/utilisateurs/([a-z0-9._-]+)/modifier", "admin", async ({ env, request, moi, params }) => {
  const d = await corps(request);
  const u = await base(env).prepare("SELECT * FROM utilisateurs WHERE id = ?").bind(params[0]).first();
  if (!u) throw new ErreurHttp(404, "Compte introuvable.");
  const role = d.role === "admin" ? "admin" : d.role === "prof" ? "prof" : u.role;
  if (u.id === moi.id && role !== "admin") throw new ErreurHttp(400, "Tu ne peux pas retirer tes propres droits d'administrateur.");
  const nom = propre(d.nom) || u.nom;
  const matieres = d.matieres ? JSON.stringify(verifierMatieres(d.matieres)) : u.matieres;
  await base(env).prepare("UPDATE utilisateurs SET nom = ?, role = ?, matieres = ?, modifie = ? WHERE id = ?").bind(nom, role, matieres, Date.now(), u.id).run();
  await noter(env, moi.nom, "compte modifié", `${nom} (${role})`);
  return { ok: true };
});

route("DELETE", "/utilisateurs/([a-z0-9._-]+)", "admin", async ({ env, moi, params }) => {
  if (params[0] === moi.id) throw new ErreurHttp(400, "Tu ne peux pas supprimer ton propre compte.");
  const u = await base(env).prepare("SELECT nom FROM utilisateurs WHERE id = ?").bind(params[0]).first();
  if (!u) throw new ErreurHttp(404, "Compte introuvable.");
  await base(env).batch([
    base(env).prepare("DELETE FROM sessions WHERE utilisateur = ?").bind(params[0]),
    base(env).prepare("DELETE FROM utilisateurs WHERE id = ?").bind(params[0]),
  ]);
  await noter(env, moi.nom, "compte supprimé", `${u.nom} (${params[0]})`);
  return { ok: true };
});

// ── Journal (admin) ──
route("GET", "/journal", "admin", async ({ env }) => {
  const r = await base(env).prepare("SELECT quand, qui, action, details FROM journal ORDER BY id DESC LIMIT 200").all();
  return { journal: r.results };
});

// ── Sauvegardes (admin) ──
route("GET", "/sauvegardes", "admin", async ({ env }) => {
  const r = await base(env).prepare("SELECT id, quand, qui, type, note, taille FROM sauvegardes ORDER BY id DESC LIMIT 100").all();
  const stats = await base(env).batch([
    base(env).prepare("SELECT COUNT(*) AS n FROM utilisateurs"),
    base(env).prepare("SELECT COUNT(*) AS n FROM documents"),
    base(env).prepare("SELECT COUNT(*) AS n FROM journal"),
  ]);
  return { sauvegardes: r.results, contenu: { utilisateurs: stats[0].results[0].n, documents: stats[1].results[0].n, journal: stats[2].results[0].n } };
});

route("POST", "/sauvegardes", "admin", async ({ env, request, moi }) => {
  const d = await corps(request);
  const r = await creerSauvegarde(env, moi.nom, "manuelle", String(d.note || "").trim().slice(0, 200) || "Sauvegarde manuelle");
  await noter(env, moi.nom, "sauvegarde", `Sauvegarde n°${r.id} créée`);
  return { ok: true, ...r };
});

route("GET", "/sauvegardes/(\\d+)", "admin", async ({ env, params }) => {
  const r = await base(env).prepare("SELECT quand, contenu FROM sauvegardes WHERE id = ?").bind(+params[0]).first();
  if (!r) throw new ErreurHttp(404, "Sauvegarde introuvable.");
  const nom = `drive-universitaire-sauvegarde-${new Date(r.quand).toISOString().slice(0, 16).replace(/[T:]/g, "-")}.json`;
  return new Response(r.contenu, { headers: { "Content-Type": "application/json; charset=utf-8", "Content-Disposition": `attachment; filename="${nom}"`, "Cache-Control": "no-store" } });
});

route("DELETE", "/sauvegardes/(\\d+)", "admin", async ({ env, moi, params }) => {
  await base(env).prepare("DELETE FROM sauvegardes WHERE id = ?").bind(+params[0]).run();
  await noter(env, moi.nom, "sauvegarde", `Sauvegarde n°${params[0]} supprimée`);
  return { ok: true };
});

route("POST", "/sauvegardes/(\\d+)/restaurer", "admin", async ({ env, moi, params }) => {
  const r = await base(env).prepare("SELECT contenu FROM sauvegardes WHERE id = ?").bind(+params[0]).first();
  if (!r) throw new ErreurHttp(404, "Sauvegarde introuvable.");
  const s = JSON.parse(r.contenu);
  verifierFormat(s);
  await creerSauvegarde(env, moi.nom, "avant-restauration", `Avant restauration de la sauvegarde n°${params[0]}`);
  await restaurer(env, s, moi.nom);
  return { ok: true };
});

// Restauration depuis un fichier téléchargé auparavant
route("POST", "/restaurer", "admin", async ({ env, request, moi }) => {
  const s = await corps(request);
  verifierFormat(s);
  if (!s.utilisateurs.some(u => u.role === "admin" && u.hash)) throw new ErreurHttp(400, "Cette sauvegarde ne contient aucun administrateur : tu perdrais l'accès au site.");
  await creerSauvegarde(env, moi.nom, "avant-restauration", "Avant restauration depuis un fichier");
  await restaurer(env, s, moi.nom);
  return { ok: true };
});

// Téléchargement de l'état actuel, sans l'enregistrer
route("GET", "/export", "admin", async ({ env, moi }) => {
  const s = await instantane(env);
  await noter(env, moi.nom, "export", "Téléchargement des données");
  const nom = `drive-universitaire-${new Date().toISOString().slice(0, 16).replace(/[T:]/g, "-")}.json`;
  return new Response(JSON.stringify(s, null, 2), { headers: { "Content-Type": "application/json; charset=utf-8", "Content-Disposition": `attachment; filename="${nom}"`, "Cache-Control": "no-store" } });
});

route("GET", "/publication", "connecte", async ({ env }) => ({ publication: await etatPublication(env) }));

// ── Point d'entrée ──
export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const chemin = url.pathname.replace(/^\/api/, "") || "/";
  const methode = request.method.toUpperCase();
  const ip = request.headers.get("CF-Connecting-IP") || "inconnue";
  try {
    // Protection contre les requêtes venues d'autres sites
    if (methode !== "GET" && request.headers.get("X-Drive") !== "1") throw new ErreurHttp(403, "Requête refusée.");
    await initialiser(env, url.origin);
    for (const r of routes) {
      if (r.methode !== methode) continue;
      const m = chemin.match(r.motif);
      if (!m) continue;
      const moi = r.role ? await exigerConnexion(env, request, r.role === "admin" ? "admin" : null) : null;
      const res = await r.action({ env, request, moi, ip, params: m.slice(1).map(decodeURIComponent) });
      if (res instanceof Response) return res;
      const { cookie, ...donnees } = res || {};
      return json(donnees, 200, cookie ? { "Set-Cookie": cookie } : {});
    }
    throw new ErreurHttp(404, "Adresse inconnue.");
  } catch (e) {
    if (e instanceof ErreurHttp) return json({ erreur: e.message }, e.status);
    console.error(e);
    return json({ erreur: "Erreur du serveur : " + (e && e.message || e) }, 500);
  }
}
