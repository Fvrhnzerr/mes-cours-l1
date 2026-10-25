// Fichiers des cours : servis par le site. Un fichier tout juste ajouté depuis l'admin
// (pas encore publié, ça prend 1 à 2 minutes) est récupéré directement sur GitHub.
import { DEPOT } from "../../lib/outils.js";

export async function onRequestGet(context) {
  const r = await context.next();
  if (r.status !== 404) return r;
  const chemin = decodeURIComponent(new URL(context.request.url).pathname).normalize("NFC");
  if (chemin.includes("..")) return r;
  const brut = `https://raw.githubusercontent.com/${DEPOT.owner}/${DEPOT.repo}/${DEPOT.branch}${chemin.split("/").map(encodeURIComponent).join("/")}`;
  const g = await fetch(brut, { cf: { cacheTtl: 60 } });
  if (!g.ok) return r;
  const h = new Headers(g.headers);
  ["content-security-policy", "x-frame-options", "access-control-allow-origin", "strict-transport-security", "x-github-request-id", "via", "x-served-by", "x-cache", "x-cache-hits", "x-timer", "x-fastly-request-id", "source-age"].forEach(x => h.delete(x));
  const ext = chemin.split(".").pop().toLowerCase();
  const types = { pdf: "application/pdf", png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", gif: "image/gif", webp: "image/webp",
    docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", pptx: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", txt: "text/plain; charset=utf-8" };
  h.set("Content-Type", types[ext] || "application/octet-stream");
  h.set("Cache-Control", "public, max-age=60");
  return new Response(g.body, { status: 200, headers: h });
}
