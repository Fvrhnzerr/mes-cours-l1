// Accès au dépôt GitHub (où sont rangés les fichiers des cours), avec le jeton gardé dans la base.
import { DEPOT, ErreurHttp } from "./outils.js";
import { lireReglage } from "./base.js";

const API = `https://api.github.com/repos/${DEPOT.owner}/${DEPOT.repo}`;

function entetes(jeton, extra = {}) {
  return {
    "Authorization": "Bearer " + jeton,
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "drive-universitaire",
    ...extra,
  };
}

export async function jetonGithub(env) {
  const j = (await lireReglage(env, "github_token", null)) || env.GITHUB_TOKEN || null;
  if (!j) throw new ErreurHttp(409, "Le site n'est pas encore relié à GitHub. Un administrateur doit enregistrer le jeton GitHub dans l'onglet « Réglages ».");
  return j;
}

// Vérifie qu'un jeton peut écrire dans le dépôt
export async function testerJeton(jeton) {
  const r = await fetch(API, { headers: entetes(jeton) });
  if (r.status === 401) throw new ErreurHttp(400, "Ce jeton GitHub est invalide ou expiré.");
  if (r.status === 404) throw new ErreurHttp(400, `Ce jeton ne donne pas accès au dépôt ${DEPOT.repo}.`);
  if (!r.ok) throw new ErreurHttp(502, "GitHub ne répond pas (" + r.status + ").");
  const d = await r.json();
  if (d.permissions && d.permissions.push === false) throw new ErreurHttp(400, "Ce jeton ne peut pas écrire dans le dépôt (il faut Contents : Read and write).");
  return true;
}

export async function gh(env, chemin, opts = {}) {
  const jeton = await jetonGithub(env);
  const r = await fetch(API + chemin, { ...opts, headers: entetes(jeton, opts.body && !opts.brut ? { "Content-Type": "application/json" } : {}) });
  if (!r.ok) {
    let m = "";
    try { m = (await r.json()).message || ""; } catch (e) {}
    if (r.status === 401) throw new ErreurHttp(502, "Le jeton GitHub enregistré n'est plus valide. Un administrateur doit en enregistrer un nouveau (onglet Réglages).");
    if (r.status === 403) throw new ErreurHttp(502, "Le jeton GitHub n'a pas le droit d'écrire dans le dépôt.");
    const e = new ErreurHttp(r.status === 409 || r.status === 422 ? 409 : 502, m || "Erreur GitHub " + r.status);
    e.github = r.status; throw e;
  }
  return r.status === 204 ? null : r.json();
}

// Envoie le contenu d'un fichier (corps JSON {content, encoding:"base64"} tel quel, sans le relire)
export async function envoyerBlob(env, corps) {
  const jeton = await jetonGithub(env);
  const r = await fetch(API + "/git/blobs", { method: "POST", body: corps, headers: entetes(jeton, { "Content-Type": "application/json" }) });
  if (!r.ok) {
    if (r.status === 401) throw new ErreurHttp(502, "Le jeton GitHub enregistré n'est plus valide.");
    throw new ErreurHttp(502, "GitHub a refusé le fichier (" + r.status + ").");
  }
  return (await r.json()).sha;
}

// Un seul commit pour plusieurs fichiers (sha null = suppression). Réessaie si le dépôt a bougé entre-temps.
export async function commit(env, entrees, message, auteur) {
  for (let essai = 0; essai < 3; essai++) {
    try {
      const ref = await gh(env, `/git/ref/heads/${DEPOT.branch}`);
      const base = await gh(env, `/git/commits/${ref.object.sha}`);
      const arbre = await gh(env, "/git/trees", { method: "POST", body: JSON.stringify({
        base_tree: base.tree.sha,
        tree: entrees.map(e => ({ path: e.path, mode: "100644", type: "blob", sha: e.sha })),
      }) });
      const corps = { message, tree: arbre.sha, parents: [ref.object.sha] };
      if (auteur) corps.author = { name: auteur.nom || auteur.id, email: `${auteur.id}@drive-universitaire.local`, date: new Date().toISOString() };
      const c = await gh(env, "/git/commits", { method: "POST", body: JSON.stringify(corps) });
      await gh(env, `/git/refs/heads/${DEPOT.branch}`, { method: "PATCH", body: JSON.stringify({ sha: c.sha }) });
      return c.sha;
    } catch (e) {
      if (e.status !== 409 || essai === 2) throw e;
      await new Promise(r => setTimeout(r, 600 * (essai + 1)));
    }
  }
}

export async function etatPublication(env) {
  try {
    const r = await gh(env, `/actions/runs?branch=${DEPOT.branch}&per_page=1`);
    const run = r.workflow_runs && r.workflow_runs[0];
    if (!run) return null;
    return { statut: run.status, resultat: run.conclusion, quand: run.created_at, lien: run.html_url };
  } catch (e) { return null; }
}
