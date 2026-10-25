// Outils communs aux fonctions du serveur (Cloudflare Pages Functions).

export const DEPOT = { owner: "Fvrhnzerr", repo: "mes-cours-l1", branch: "main" };

export const ANNEES = ["L1", "L2", "L3"];
export const FILIERES = ["GI", "MRT", "GE"];
export const TYPES = ["Cours", "TD", "TP", "Sujets"];

export const EXTENSIONS = ["pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "c", "cpp", "h", "py", "java", "html", "css", "js", "sql", "png", "jpg", "jpeg", "gif", "webp", "zip"];
const MOTS_SUJET = ["sujet", "revision", "entrainement", "examen", "annale", "partiel"];

// Noms affichés par défaut (mêmes règles que maj.py)
const NOMS_MATIERES = {
  algo_avancee: "Algorithmique avancée", algo: "Algorithmique", algorithmique: "Algorithmique",
  web: "Développement Web", francais: "Français", system_exploitation: "Système d'exploitation",
  systeme_exploitation: "Système d'exploitation", system_logique: "Systèmes logiques",
  systeme_logique: "Systèmes logiques", cisco: "CISCO", algebre_lineaire: "Algèbre linéaire",
  statisque: "Statistique", statistique: "Statistique",
};

export class ErreurHttp extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

export function json(data, status = 200, entetes = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...entetes },
  });
}

export function normCle(texte) {
  return String(texte).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim().replace(/[\s-]+/g, "_");
}

export function normId(texte) {
  return String(texte || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim().replace(/[^a-z0-9._-]/g, "");
}

export function propre(texte) {
  return String(texte || "").normalize("NFC").replace(/[\/\\]/g, "-").replace(/\s+/g, " ").trim();
}

export function nomMatiere(dossier) {
  const connu = NOMS_MATIERES[normCle(dossier)];
  if (connu) return connu;
  const t = String(dossier).replace(/_/g, " ").trim();
  return t.slice(0, 1).toUpperCase() + t.slice(1);
}

function mot(cle, texte) {
  return new RegExp(`(^|[^a-z])${cle}([^a-z]|$)`).test(texte);
}

// Classe un fichier : cours / td / tp / sujet (le dossier le plus proche décide)
export function categorie(sousDossiers, fichier) {
  for (const brut of [...sousDossiers].reverse()) {
    const d = normCle(brut);
    if (MOTS_SUJET.some(k => d.includes(k))) return "sujet";
    if (mot("td", d)) return "td";
    if (mot("tp", d)) return "tp";
    if (d.includes("cours") || d.startsWith("chap")) return "cours";
  }
  const f = normCle(fichier.replace(/\.[^.]+$/, ""));
  if (mot("td", f)) return "td";
  if (mot("tp", f)) return "tp";
  return "cours";
}

// Fiche d'un document à partir de son chemin cours/FILIERE/ANNEE/MATIERE/.../fichier.ext
export function ficheDocument(chemin, taille, date, extra = {}) {
  const p = chemin.normalize("NFC").split("/");
  if (p.length < 5 || p[0] !== "cours") return null;
  const [, filiere, annee, matiere, ...reste] = p;
  const fichier = reste.pop();
  const point = fichier.lastIndexOf(".");
  const base = point > 0 ? fichier.slice(0, point) : fichier;
  const e = point > 0 ? fichier.slice(point + 1).toLowerCase() : "";
  return {
    path: p.join("/"), filiere, annee, matiere, titre_defaut: nomMatiere(matiere),
    n: base.replace(/_/g, " ").trim(), e, t: categorie(reste, fichier), s: taille || 0, d: date || Math.floor(Date.now() / 1000),
    ...extra,
  };
}

// ── Cryptographie ──
const enc = new TextEncoder();
export const b64 = buf => { let t = ""; new Uint8Array(buf).forEach(c => (t += String.fromCharCode(c))); return btoa(t); };
export const hex = buf => [...new Uint8Array(buf)].map(x => x.toString(16).padStart(2, "0")).join("");

export function aleatoire(octets = 32) {
  return hex(crypto.getRandomValues(new Uint8Array(octets)));
}

export async function sha256(texte) {
  return hex(await crypto.subtle.digest("SHA-256", enc.encode(texte)));
}

export const ITERATIONS = 20000;
export async function hacherMdp(mdp, sel, iterations = ITERATIONS) {
  const cle = await crypto.subtle.importKey("raw", enc.encode(mdp), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", salt: enc.encode(sel), iterations, hash: "SHA-256" }, cle, 256);
  return `pbkdf2$${iterations}$${b64(bits)}`;
}

export async function verifierMdp(mdp, sel, stocke) {
  if (!stocke || !sel) return false;
  const [, it] = stocke.split("$");
  const calcule = await hacherMdp(mdp, sel, +it || ITERATIONS);
  if (calcule.length !== stocke.length) return false;
  let diff = 0;
  for (let i = 0; i < calcule.length; i++) diff |= calcule.charCodeAt(i) ^ stocke.charCodeAt(i);
  return diff === 0;
}

export function genererMdp() {
  const A = "abcdefghjkmnpqrstuvwxyz23456789", r = crypto.getRandomValues(new Uint32Array(12));
  let m = "";
  r.forEach((x, i) => { if (i && i % 4 === 0) m += "-"; m += A[x % A.length]; });
  return m;
}

export function dateFr(ts = Date.now()) {
  return new Date(ts).toLocaleDateString("fr-FR", { timeZone: "Africa/Djibouti" });
}

// Lit un fichier statique publié avec le site (suit les redirections .html → sans extension)
export async function lireAsset(env, origine, chemin) {
  if (!env.ASSETS) return null;
  let url = new URL(chemin, origine).toString();
  for (let i = 0; i < 3; i++) {
    const r = await env.ASSETS.fetch(new Request(url, { redirect: "manual" }));
    if (r.status >= 300 && r.status < 400 && r.headers.get("Location")) { url = new URL(r.headers.get("Location"), url).toString(); continue; }
    return r.ok ? r : null;
  }
  return null;
}
