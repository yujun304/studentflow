export function currentDocumentPath() {
  const path = window.location.pathname.replace(/\/+$/, "");
  return path || "/";
}

export function documentPathId(basePath: string) {
  const path = currentDocumentPath();
  const prefix = `${basePath}/`;
  if (!path.startsWith(prefix)) return undefined;
  const id = path.slice(prefix.length).split("/")[0];
  return id ? decodeURIComponent(id) : undefined;
}

export function nextDocumentPath() {
  const next = new URLSearchParams(window.location.search).get("next");
  return next?.startsWith("/") && !next.startsWith("//") ? next : "/";
}
