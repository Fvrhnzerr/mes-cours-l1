// Connexion des comptes : sessions par cookie, limitation des essais.
import { ErreurHttp, aleatoire, sha256 } from "./outils.js";
import { base } from "./base.js";

const COOKIE = "drive_session";
const JOUR = 24 * 3600 * 1000;

function lireCookie(request, nom) {
  const c = request.headers.get("Cookie") || "";
  const m = c.split(/;\s*/).find(x => x.startsWith(nom + "="));
  return m ? decodeURIComponent(m.slice(nom.length + 1)) : "";
}

export async function ouvrirSession(env, utilisateur, memoriser) {
  const jeton = aleatoire(32);
  const duree = memoriser ? 30 * JOUR : JOUR;
  await base(env).batch([
    base(env).prepare("DELETE FROM sessions WHERE expire < ?").bind(Date.now()),
    base(env).prepare("INSERT INTO sessions (id, utilisateur, expire, cree) VALUES (?, ?, ?, ?)").bind(await sha256(jeton), utilisateur, Date.now() + duree, Date.now()),
    base(env).prepare("UPDATE utilisateurs SET derniere_connexion = ? WHERE id = ?").bind(Date.now(), utilisateur),
  ]);
  const age = memoriser ? `; Max-Age=${duree / 1000}` : "";
  return `${COOKIE}=${jeton}; Path=/; HttpOnly; Secure; SameSite=Strict${age}`;
}

export async function fermerSession(env, request) {
  const jeton = lireCookie(request, COOKIE);
  if (jeton) await base(env).prepare("DELETE FROM sessions WHERE id = ?").bind(await sha256(jeton)).run();
  return `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0`;
}

export async function utilisateurConnecte(env, request) {
  const jeton = lireCookie(request, COOKIE);
  if (!jeton) return null;
  const r = await base(env).prepare(`SELECT u.id, u.nom, u.role, u.matieres FROM sessions s JOIN utilisateurs u ON u.id = s.utilisateur
    WHERE s.id = ? AND s.expire > ?`).bind(await sha256(jeton), Date.now()).first();
  if (!r) return null;
  return { id: r.id, nom: r.nom, role: r.role, matieres: JSON.parse(r.matieres || "[]") };
}

export async function exigerConnexion(env, request, role) {
  const u = await utilisateurConnecte(env, request);
  if (!u) throw new ErreurHttp(401, "Ta session a expiré. Reconnecte-toi.");
  if (role === "admin" && u.role !== "admin") throw new ErreurHttp(403, "Réservé aux administrateurs.");
  return u;
}

// 8 essais ratés en 15 minutes → blocage de 15 minutes (par compte et par adresse)
export async function verifierEssais(env, cles) {
  const db = base(env);
  for (const cle of cles) {
    const r = await db.prepare("SELECT n, depuis FROM tentatives WHERE cle = ?").bind(cle).first();
    if (r && r.n >= 8 && Date.now() - r.depuis < 15 * 60 * 1000)
      throw new ErreurHttp(429, "Trop d'essais. Réessaie dans un quart d'heure.");
  }
}

export async function essaiRate(env, cles) {
  const db = base(env);
  await db.batch(cles.map(cle => db.prepare(`INSERT INTO tentatives (cle, n, depuis) VALUES (?, 1, ?)
    ON CONFLICT(cle) DO UPDATE SET n = CASE WHEN ? - depuis > 900000 THEN 1 ELSE n + 1 END,
      depuis = CASE WHEN ? - depuis > 900000 THEN ? ELSE depuis END`).bind(cle, Date.now(), Date.now(), Date.now(), Date.now())));
}

export async function essaiReussi(env, cles) {
  const db = base(env);
  await db.batch(cles.map(cle => db.prepare("DELETE FROM tentatives WHERE cle = ?").bind(cle)));
}
