// Flechas entre cajas: flecha(desde, lado, hasta, lado, opciones).
// Lados: "n", "s", "e", "w", con desplazamiento opcional "e:0.3" (fraccion del borde).
// Opciones: punteada, doble, color, puntos (codos [x,y] intermedios absolutos).
const NS = "http://www.w3.org/2000/svg";
const svg = document.createElementNS(NS, "svg");
svg.id = "flechas";
document.getElementById("lienzo").appendChild(svg);

function marcador(color) {
  const id = "m" + color.replace("#", "");
  if (document.getElementById(id)) return id;
  let defs = svg.querySelector("defs");
  if (!defs) { defs = document.createElementNS(NS, "defs"); svg.appendChild(defs); }
  const m = document.createElementNS(NS, "marker");
  m.setAttribute("id", id); m.setAttribute("viewBox", "0 0 10 10");
  m.setAttribute("refX", "9"); m.setAttribute("refY", "5");
  m.setAttribute("markerWidth", "8"); m.setAttribute("markerHeight", "8");
  m.setAttribute("orient", "auto-start-reverse");
  const p = document.createElementNS(NS, "path");
  p.setAttribute("d", "M0,0 L10,5 L0,10 z"); p.setAttribute("fill", color);
  m.appendChild(p); defs.appendChild(m);
  return id;
}

function punto(id, lado) {
  const el = document.getElementById(id);
  const base = document.getElementById("lienzo").getBoundingClientRect();
  const r = el.getBoundingClientRect();
  const [l, f] = lado.split(":");
  const t = f === undefined ? 0.5 : parseFloat(f);
  const x0 = r.left - base.left, y0 = r.top - base.top;
  return {
    n: [x0 + r.width * t, y0], s: [x0 + r.width * t, y0 + r.height],
    w: [x0, y0 + r.height * t], e: [x0 + r.width, y0 + r.height * t],
  }[l];
}

function flecha(a, la, b, lb, o = {}) {
  const color = o.color || "#3e4c59";
  const p1 = punto(a, la), p2 = punto(b, lb);
  const pts = [p1, ...(o.puntos || []), p2];
  const path = document.createElementNS(NS, "path");
  path.setAttribute("d", "M" + pts.map((p) => p.join(",")).join(" L"));
  path.setAttribute("fill", "none"); path.setAttribute("stroke", color);
  path.setAttribute("stroke-width", o.grosor || 2.2);
  if (o.punteada) path.setAttribute("stroke-dasharray", "7 5");
  const m = marcador(color);
  path.setAttribute("marker-end", `url(#${m})`);
  if (o.doble) path.setAttribute("marker-start", `url(#${m})`);
  svg.appendChild(path);
}

function ajustarLienzo() {
  const l = document.getElementById("lienzo");
  svg.setAttribute("width", l.scrollWidth); svg.setAttribute("height", l.scrollHeight);
}
