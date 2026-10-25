// Page d'accueil dynamique : les documents et les réglages viennent de la base à chaque visite.
// Si la base n'est pas disponible, la version statique générée par maj.py est servie telle quelle.
import { initialiser, lireSite, base } from "../lib/base.js";
import { lireAsset } from "../lib/outils.js";

const DEBUT = { DATA: "/*DATA*/", CFG: "/*CFG*/" };
const FIN = { DATA: "/*/DATA*/", CFG: "/*/CFG*/" };

const pourScript = obj => JSON.stringify(obj).replace(/</g, "\\u003c");

function remplacer(html, nom, valeur) {
  const a = html.indexOf(DEBUT[nom]), b = html.indexOf(FIN[nom]);
  if (a < 0 || b < a) return null;
  return html.slice(0, a + DEBUT[nom].length) + valeur + html.slice(b);
}

function extraire(html, nom) {
  const a = html.indexOf(DEBUT[nom]), b = html.indexOf(FIN[nom]);
  if (a < 0 || b < a) return null;
  try { return JSON.parse(html.slice(a + DEBUT[nom].length, b)); } catch (e) { return null; }
}

function page(html, statut = 200) {
  return new Response(html, { status: statut, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache" } });
}

async function accueil(context) {
  const { env, request } = context;
  const origine = new URL(request.url).origin;
  await initialiser(env, origine);
  const site = await lireSite(env);

  if (site.maintenance) {
    const r = await lireAsset(env, origine, "/maintenance.html");
    if (r) return page((await r.text()).replaceAll("__SIGNATURE__", site.signature || "Farhan&Co"), 503);
  }

  const modele = await lireAsset(env, origine, "/index-complet.html");
  if (!modele) return null;
  let html = await modele.text();
  const cfgStatique = extraire(html, "CFG");
  if (!cfgStatique) return null;

  const docs = await base(env).prepare("SELECT path, filiere, annee, matiere, titre_defaut, n, e, t, s, d FROM documents ORDER BY annee, filiere, matiere, path").all();
  const data = {};
  let derniere = 0;
  for (const x of docs.results) {
    const m = ((data[x.annee] ||= {})[x.filiere] ||= {})[x.matiere] ||= {
      titre: site.noms_matieres[`${x.filiere}/${x.annee}/${x.matiere}`] || x.titre_defaut || x.matiere, docs: [],
    };
    m.docs.push({ n: x.n, e: x.e, p: x.path, t: x.t, s: x.s, d: x.d });
    if (x.d > derniere) derniere = x.d;
  }
  const maj = new Date((derniere || Date.now() / 1000) * 1000);
  const cfg = {
    ...cfgStatique,
    nouveauJours: site.nouveau_jours || 14,
    message: site.message || "",
    surprise: site.surprise.actif ? { nom: site.surprise.nom, titre: site.surprise.titre, message: site.surprise.message } : null,
    signature: site.signature || cfgStatique.signature,
    maj: maj.toLocaleString("fr-FR", { timeZone: "Africa/Djibouti", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" }).replace(" ", " à "),
    annee: new Date().getFullYear(),
    motDePasse: !!site.mot_de_passe.actif,
    login: site.mot_de_passe.actif ? site.mot_de_passe.login : "",
    mdp: site.mot_de_passe.actif ? site.mot_de_passe.mdp : "",
  };
  html = remplacer(html, "DATA", pourScript(data));
  html = html && remplacer(html, "CFG", pourScript(cfg));
  return html ? page(html) : null;
}

export async function onRequest(context) {
  const chemin = new URL(context.request.url).pathname;
  if ((chemin === "/" || chemin === "/index.html" || chemin === "/index") && context.request.method === "GET") {
    try {
      const r = await accueil(context);
      if (r) return r;
    } catch (e) {
      console.error("Accueil dynamique indisponible :", e && e.message);
    }
  }
  // Fichiers internes : pas besoin de les exposer
  if (chemin === "/index-complet.html" || chemin === "/index-complet") return context.env.ASSETS.fetch(new Request(new URL("/", context.request.url)));
  return context.next();
}
