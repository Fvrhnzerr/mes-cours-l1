// Base de données D1 : création des tables, réglages, journal, index des documents, sauvegardes.
import { ErreurHttp, lireAsset, ficheDocument, dateFr, normId } from "./outils.js";

const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS reglages (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL, modifie INTEGER)`,
  `CREATE TABLE IF NOT EXISTS utilisateurs (
     id TEXT PRIMARY KEY, nom TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'prof', matieres TEXT NOT NULL DEFAULT '[]',
     hash TEXT, sel TEXT, cree TEXT, modifie INTEGER, derniere_connexion INTEGER)`,
  `CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, utilisateur TEXT NOT NULL, expire INTEGER NOT NULL, cree INTEGER NOT NULL)`,
  `CREATE TABLE IF NOT EXISTS documents (
     path TEXT PRIMARY KEY, filiere TEXT NOT NULL, annee TEXT NOT NULL, matiere TEXT NOT NULL, titre_defaut TEXT,
     n TEXT NOT NULL, e TEXT, t TEXT, s INTEGER, d INTEGER, source TEXT DEFAULT 'depot', par TEXT)`,
  `CREATE INDEX IF NOT EXISTS documents_matiere ON documents (annee, filiere, matiere)`,
  `CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY AUTOINCREMENT, quand INTEGER NOT NULL, qui TEXT, action TEXT NOT NULL, details TEXT)`,
  `CREATE TABLE IF NOT EXISTS sauvegardes (
     id INTEGER PRIMARY KEY AUTOINCREMENT, quand INTEGER NOT NULL, qui TEXT, type TEXT NOT NULL, note TEXT, taille INTEGER, contenu TEXT NOT NULL)`,
  `CREATE TABLE IF NOT EXISTS tentatives (cle TEXT PRIMARY KEY, n INTEGER NOT NULL, depuis INTEGER NOT NULL)`,
];

export const REGLAGES_DEFAUT = {
  maintenance: false, message: "", nouveau_jours: 14, signature: "",
  mot_de_passe: { actif: false, login: "", mdp: "" },
  surprise: { actif: false, nom: "", titre: "", message: "" },
  noms_matieres: {},
};

let pret = false;   // une fois par instance du serveur

export function base(env) {
  if (!env.DB) throw new ErreurHttp(503, "La base de données n'est pas encore branchée au site.");
  return env.DB;
}

export async function initialiser(env, origine) {
  const db = base(env);
  if (!pret) {
    await db.batch(SCHEMA.map(s => db.prepare(s)));
    // Première mise en route : reprise des réglages et des comptes de l'ancienne version
    const deja = await db.prepare("SELECT 1 FROM reglages WHERE cle = 'site'").first();
    if (!deja) await importerAncienneVersion(env, origine);
    pret = true;
  }
  await synchroniserDocuments(env, origine);
}

async function importerAncienneVersion(env, origine) {
  const db = base(env);
  let site = { ...REGLAGES_DEFAUT };
  try { const r = await lireAsset(env, origine, "/site-config.json"); if (r) site = { ...site, ...(await r.json()) }; } catch (e) {}
  const ops = [db.prepare("INSERT OR IGNORE INTO reglages (cle, valeur, modifie) VALUES ('site', ?, ?)").bind(JSON.stringify(site), Date.now())];
  try {
    const r = await lireAsset(env, origine, "/admin-users.json");
    const anciens = r ? (await r.json()).users || [] : [];
    for (const u of anciens) {
      const id = normId(u.id);
      if (!id) continue;
      // Le mot de passe n'est pas récupérable : un administrateur devra en créer un nouveau.
      ops.push(db.prepare("INSERT OR IGNORE INTO utilisateurs (id, nom, role, matieres, cree, modifie) VALUES (?, ?, ?, ?, ?, ?)")
        .bind(id, u.nom || id, u.role === "admin" ? "admin" : "prof", JSON.stringify(u.matieres || []), u.cree || dateFr(), Date.now()));
    }
  } catch (e) {}
  ops.push(db.prepare("INSERT INTO journal (quand, qui, action, details) VALUES (?, 'système', 'installation', 'Base créée, réglages et comptes repris de l’ancienne version')").bind(Date.now()));
  await db.batch(ops);
}

// L'index docs-index.json est généré par maj.py à chaque publication.
// S'il a changé depuis la dernière fois, la table documents est remise à jour.
export async function synchroniserDocuments(env, origine) {
  const db = base(env);
  let index;
  try {
    const r = await lireAsset(env, origine, "/docs-index.json");
    if (!r) return;
    index = await r.json();
  } catch (e) { return; }
  if (!index || !index.version || !Array.isArray(index.docs)) return;
  const vu = await db.prepare("SELECT valeur FROM reglages WHERE cle = 'index_version'").first();
  if (vu && vu.valeur === String(index.version)) return;

  const ops = [
    // on garde les fichiers envoyés depuis l'admin après la génération de l'index (ils seront dans le prochain)
    db.prepare("DELETE FROM documents WHERE NOT (source = 'admin' AND d > ?)").bind(Math.floor((index.genere || 0))),
  ];
  for (const x of index.docs) {
    const f = ficheDocument(x.p, x.s, x.d);
    if (!f) continue;
    ops.push(db.prepare(`INSERT INTO documents (path, filiere, annee, matiere, titre_defaut, n, e, t, s, d, source, par)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'depot', NULL)
      ON CONFLICT(path) DO UPDATE SET titre_defaut = excluded.titre_defaut, n = excluded.n, e = excluded.e, t = excluded.t, s = excluded.s, d = MIN(documents.d, excluded.d), source = 'depot'`)
      .bind(f.path, f.filiere, f.annee, f.matiere, x.titre || f.titre_defaut, x.n || f.n, x.e || f.e, x.t || f.t, f.s, f.d));
  }
  ops.push(db.prepare("INSERT INTO reglages (cle, valeur, modifie) VALUES ('index_version', ?, ?) ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur, modifie = excluded.modifie")
    .bind(String(index.version), Date.now()));
  // D1 limite la taille d'un lot : on découpe
  for (let i = 0; i < ops.length; i += 80) await db.batch(ops.slice(i, i + 80));
}

// ── Réglages ──
export async function lireReglage(env, cle, defaut = null) {
  const r = await base(env).prepare("SELECT valeur FROM reglages WHERE cle = ?").bind(cle).first();
  if (!r) return defaut;
  try { return JSON.parse(r.valeur); } catch (e) { return r.valeur; }
}

export async function ecrireReglage(env, cle, valeur) {
  await base(env).prepare("INSERT INTO reglages (cle, valeur, modifie) VALUES (?, ?, ?) ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur, modifie = excluded.modifie")
    .bind(cle, JSON.stringify(valeur), Date.now()).run();
}

export async function lireSite(env) {
  const c = (await lireReglage(env, "site", {})) || {};
  return {
    ...REGLAGES_DEFAUT, ...c,
    mot_de_passe: { ...REGLAGES_DEFAUT.mot_de_passe, ...(c.mot_de_passe || {}) },
    surprise: { ...REGLAGES_DEFAUT.surprise, ...(c.surprise || {}) },
    noms_matieres: { ...(c.noms_matieres || {}) },
  };
}

export async function noter(env, qui, action, details = "") {
  try {
    await base(env).prepare("INSERT INTO journal (quand, qui, action, details) VALUES (?, ?, ?, ?)").bind(Date.now(), qui || "", action, details).run();
  } catch (e) {}
}

// ── Sauvegardes ──
const SECRETS = ["github_token"];

export async function instantane(env) {
  const db = base(env);
  const [reglages, utilisateurs, documents, journal] = await db.batch([
    db.prepare("SELECT cle, valeur, modifie FROM reglages"),
    db.prepare("SELECT id, nom, role, matieres, hash, sel, cree, modifie, derniere_connexion FROM utilisateurs ORDER BY id"),
    db.prepare("SELECT path, filiere, annee, matiere, titre_defaut, n, e, t, s, d, source, par FROM documents ORDER BY path"),
    db.prepare("SELECT quand, qui, action, details FROM journal ORDER BY id DESC LIMIT 500"),
  ]);
  return {
    format: "drive-universitaire-sauvegarde", version: 1, cree: new Date().toISOString(),
    reglages: reglages.results.filter(r => !SECRETS.includes(r.cle)),
    utilisateurs: utilisateurs.results,
    documents: documents.results,
    journal: journal.results.reverse(),
  };
}

export async function creerSauvegarde(env, qui, type, note = "") {
  const contenu = JSON.stringify(await instantane(env));
  const r = await base(env).prepare("INSERT INTO sauvegardes (quand, qui, type, note, taille, contenu) VALUES (?, ?, ?, ?, ?, ?) RETURNING id")
    .bind(Date.now(), qui || "", type, note, contenu.length, contenu).first();
  // On garde les 30 dernières sauvegardes automatiques ; les manuelles restent jusqu'à suppression.
  await base(env).prepare(`DELETE FROM sauvegardes WHERE type != 'manuelle' AND id NOT IN
    (SELECT id FROM sauvegardes WHERE type != 'manuelle' ORDER BY id DESC LIMIT 30)`).run();
  return { id: r.id, taille: contenu.length };
}

// Une sauvegarde automatique par jour, déclenchée par l'activité des administrateurs.
export async function sauvegardeAutoSiBesoin(env, qui) {
  const derniere = await base(env).prepare("SELECT quand FROM sauvegardes WHERE type = 'auto' ORDER BY id DESC LIMIT 1").first();
  if (derniere && Date.now() - derniere.quand < 24 * 3600 * 1000) return null;
  return creerSauvegarde(env, qui, "auto", "Sauvegarde automatique du jour");
}

export function verifierFormat(s) {
  if (!s || s.format !== "drive-universitaire-sauvegarde" || !Array.isArray(s.utilisateurs) || !Array.isArray(s.reglages) || !Array.isArray(s.documents))
    throw new ErreurHttp(400, "Ce fichier n'est pas une sauvegarde du Drive Universitaire.");
}

export async function restaurer(env, s, qui) {
  verifierFormat(s);
  const db = base(env);
  const ops = [
    db.prepare("DELETE FROM utilisateurs"),
    db.prepare("DELETE FROM documents"),
    db.prepare(`DELETE FROM reglages WHERE cle NOT IN (${SECRETS.map(() => "?").join(",")}, 'index_version')`).bind(...SECRETS),
  ];
  for (const r of s.reglages) {
    if (SECRETS.includes(r.cle) || r.cle === "index_version") continue;
    ops.push(db.prepare("INSERT INTO reglages (cle, valeur, modifie) VALUES (?, ?, ?)").bind(r.cle, String(r.valeur), r.modifie || Date.now()));
  }
  for (const u of s.utilisateurs) {
    ops.push(db.prepare("INSERT INTO utilisateurs (id, nom, role, matieres, hash, sel, cree, modifie, derniere_connexion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
      .bind(u.id, u.nom, u.role === "admin" ? "admin" : "prof", typeof u.matieres === "string" ? u.matieres : JSON.stringify(u.matieres || []),
        u.hash || null, u.sel || null, u.cree || null, u.modifie || Date.now(), u.derniere_connexion || null));
  }
  for (const d of s.documents) {
    ops.push(db.prepare("INSERT INTO documents (path, filiere, annee, matiere, titre_defaut, n, e, t, s, d, source, par) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
      .bind(d.path, d.filiere, d.annee, d.matiere, d.titre_defaut || null, d.n, d.e || "", d.t || "cours", d.s || 0, d.d || 0, d.source || "depot", d.par || null));
  }
  // les sessions restent valides seulement pour les comptes qui existent encore
  ops.push(db.prepare("DELETE FROM sessions WHERE utilisateur NOT IN (SELECT id FROM utilisateurs)"));
  for (let i = 0; i < ops.length; i += 80) await db.batch(ops.slice(i, i + 80));
  // l'index des documents sera relu à la prochaine visite pour rester fidèle aux fichiers réellement en ligne
  await db.prepare("DELETE FROM reglages WHERE cle = 'index_version'").run();
  const quand = s.cree ? new Date(s.cree).toLocaleString("fr-FR", { timeZone: "Africa/Djibouti" }) : "?";
  await noter(env, qui, "restauration", `Sauvegarde du ${quand} restaurée`);
}
