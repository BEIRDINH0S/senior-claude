/*
 * Calque d'annotations injecté dans la page avant la capture.
 * Les annotations sont ancrées sur des éléments réels (sélecteurs CSS) :
 * elles tombent au pixel près, quelle que soit la mise en page.
 *
 * Ce fichier n'est pas exécuté tel quel : capture.py le combine avec la
 * spécification de la capture (window.__DOC_SPEC__) et l'envoie par
 * `agent-browser eval`. L'expression renvoie un objet JSON :
 *   { ok, missing: [sélecteurs introuvables], box: {x, y, w, h}, dpr }
 * box = zone englobant les éléments annotés (+ marge), élargie au conteneur
 * spec.crop_to s'il est donné, en px CSS du document. Si spec.crop est vrai,
 * un élément transparent #__doc_crop__ matérialise cette zone pour la capture.
 */
(function (spec) {
  var ID = "__doc_annot__";
  var old = document.getElementById(ID);
  if (old) old.remove();
  document.querySelectorAll("[data-doc-annot-blur]").forEach(function (el) {
    el.style.filter = el.getAttribute("data-doc-annot-blur");
    el.removeAttribute("data-doc-annot-blur");
  });
  if (spec.clear) return { ok: true, cleared: true };

  var st = Object.assign({
    color: "#E5484D",        // une seule couleur d'annotation dans toute la doc
    width: 3,                // épaisseur des cadres (px CSS)
    radius: 6,
    badge: 26,               // diamètre des pastilles numérotées
    font: "600 14px -apple-system, Segoe UI, Roboto, sans-serif",
    padding: 6,              // marge entre l'élément et son cadre
    crop_margin: 48          // marge autour de la zone recadrée
  }, spec.style || {});

  var layer = document.createElement("div");
  layer.id = ID;
  layer.setAttribute("aria-hidden", "true");
  // Le calque a la taille du document : une note peut ainsi prendre sa largeur naturelle sans passer à la ligne.
  layer.style.cssText = "position:absolute;left:0;top:0;width:" + document.documentElement.scrollWidth + "px;height:0;" +
    "z-index:2147483647;pointer-events:none;";
  document.body.appendChild(layer);

  var missing = [];
  var boxes = [];
  var sx = window.scrollX, sy = window.scrollY;

  function find(sel) {
    var el = document.querySelector(sel);
    if (!el) { missing.push(sel); return null; }
    return el;
  }
  function rectOf(el) {
    var r = el.getBoundingClientRect();
    return { x: r.left + sx, y: r.top + sy, w: r.width, h: r.height };
  }
  function add(tag, css, text) {
    var n = document.createElement(tag);
    n.style.cssText = "position:absolute;box-sizing:border-box;" + css;
    if (text != null) n.textContent = text;
    layer.appendChild(n);
    return n;
  }
  // --- Évitement des collisions -------------------------------------------
  var frames = [];   // cadres déjà posés (px document)
  var placed = [];   // pastilles et notes déjà posées
  function inter(a, b) { return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h; }
  function hitsContent(r) {
    // Vrai si la zone recouvre du contenu de la page (texte, champ, bouton, image), hors calque.
    var pts = [];
    [0.08, 0.5, 0.92].forEach(function (fx) {
      [0.12, 0.5, 0.88].forEach(function (fy) { pts.push([r.x + r.w * fx, r.y + r.h * fy]); });
    });
    for (var i = 0; i < pts.length; i++) {
      var vx = pts[i][0] - window.scrollX, vy = pts[i][1] - window.scrollY;
      if (vx < 0 || vy < 0 || vx >= window.innerWidth || vy >= window.innerHeight) continue;
      var els = document.elementsFromPoint(vx, vy);
      for (var j = 0; j < els.length; j++) {
        var e = els[j];
        if (layer.contains(e)) continue;
        if (/^(BUTTON|INPUT|SELECT|TEXTAREA|A|IMG|SVG|LABEL|CANVAS|VIDEO)$/i.test(e.tagName)) return true;
        for (var k = 0; k < e.childNodes.length; k++) {
          var c = e.childNodes[k];
          if (c.nodeType === 3 && c.textContent.trim()) {
            var range = document.createRange(); range.selectNodeContents(c);
            var rr = range.getBoundingClientRect();
            if (vx >= rr.left && vx <= rr.right && vy >= rr.top && vy <= rr.bottom) return true;
          }
        }
        break;   // premier élément non-calque : un conteneur sans texte à cet endroit, c'est libre
      }
    }
    return false;
  }
  function inside(r) { return r.x >= 0 && r.y >= 0 && r.x + r.w <= document.documentElement.scrollWidth; }
  function clearOfAnnotations(r, own) {
    // Tolérance : un cadre n'est qu'un trait, effleurer son bord de quelques pixels ne gêne pas la lecture.
    var t = 6;
    for (var i = 0; i < frames.length; i++) {
      var f = frames[i];
      if (f !== own && inter(r, { x: f.x + t, y: f.y + t, w: f.w - 2 * t, h: f.h - 2 * t })) return false;
    }
    for (var j = 0; j < placed.length; j++) if (inter(r, placed[j])) return false;
    return true;
  }
  function gap(a, b) {
    var dx = Math.max(0, b.x - (a.x + a.w), a.x - (b.x + b.w));
    var dy = Math.max(0, b.y - (a.y + a.h), a.y - (b.y + b.h));
    return Math.sqrt(dx * dx + dy * dy);
  }
  function unambiguous(r, own) {
    // Une pastille ou une note doit être nettement plus près de son cadre que de tout autre.
    if (!own) return true;
    var g = gap(r, own);
    for (var i = 0; i < frames.length; i++) if (frames[i] !== own && gap(r, frames[i]) <= 3 * g + 16) return false;
    return true;
  }
  function choose(cands, own) {
    // Paliers : libre de tout > ne chevauche aucune annotation > au moins dans l'image.
    var tiers = [
      function (r) { return inside(r) && clearOfAnnotations(r, own) && unambiguous(r, own) && !hitsContent(r); },
      function (r) { return inside(r) && clearOfAnnotations(r, own) && unambiguous(r, own); },
      function (r) { return inside(r) && clearOfAnnotations(r, own); },
      function (r) { return inside(r); }
    ];
    for (var t = 0; t < tiers.length; t++)
      for (var i = 0; i < cands.length; i++) if (tiers[t](cands[i])) return cands[i];
    return cands[cands.length - 1];
  }

  function badge(fr, label, pos) {
    var d = st.badge, g = 8;
    var c = {
      left: { x: fr.x - d - g, y: fr.y + fr.h / 2 - d / 2 },
      "top-left": { x: fr.x - d / 2, y: fr.y - d / 2 - 2 },
      top: { x: fr.x + 10, y: fr.y - d - g },
      right: { x: fr.x + fr.w + g, y: fr.y + fr.h / 2 - d / 2 },
      inside: { x: fr.x + 6, y: fr.y + 6 }
    };
    var order = pos ? [pos] : ["left", "top-left", "top", "right", "inside"];
    var r = choose(order.map(function (k) { return { x: c[k].x, y: c[k].y, w: d, h: d }; }), fr);
    if (pos === "inside" || (!pos && r === undefined)) r = { x: c.inside.x, y: c.inside.y, w: d, h: d };
    var x = r.x + d / 2, y = r.y + d / 2;
    placed.push(r);
    add("div", "left:" + (x - d / 2) + "px;top:" + (y - d / 2) + "px;width:" + d + "px;height:" + d + "px;" +
      "border-radius:50%;background:" + st.color + ";color:#fff;font:" + st.font + ";" +
      "display:flex;align-items:center;justify-content:center;box-shadow:0 1px 4px rgba(0,0,0,.35);", String(label));
    boxes.push({ x: x - d / 2, y: y - d / 2, w: d, h: d });
  }
  function note(r, text, side) {
    // Note courte placée à côté de l'élément, du côté où il y a de la place.
    var n = add("div", "max-width:260px;padding:6px 10px;border-radius:6px;background:" + st.color + ";color:#fff;" +
      "font:" + st.font + ";line-height:1.3;box-shadow:0 1px 4px rgba(0,0,0,.35);", text);
    n.style.whiteSpace = "nowrap";
    var nw = n.offsetWidth, nh = n.offsetHeight, gap = 12;
    var pos = {
      right: { x: r.x + r.w + gap, y: r.y + r.h / 2 - nh / 2 },
      left: { x: r.x - gap - nw, y: r.y + r.h / 2 - nh / 2 },
      top: { x: r.x, y: r.y - gap - nh },
      bottom: { x: r.x, y: r.y + r.h + gap }
    };
    var order = side ? [side] : ["right", "bottom", "top", "left"];
    var c = choose(order.map(function (k) { return { x: pos[k].x, y: pos[k].y, w: nw, h: nh }; }), r);
    n.style.left = c.x + "px"; n.style.top = c.y + "px";
    placed.push(c);
    boxes.push(c);
  }

  var svg = null, later = [];
  function arrow(r, it) {
    // Note placée à distance (side + distance), reliée à l'élément par une flèche.
    var side = it.side || "right", dist = it.distance || 90;
    var n = add("div", "white-space:nowrap;padding:6px 10px;border-radius:6px;background:" + st.color + ";color:#fff;" +
      "font:" + st.font + ";box-shadow:0 1px 4px rgba(0,0,0,.35);", it.note || "");
    var nw = n.offsetWidth, nh = n.offsetHeight, cx = r.x + r.w / 2, cy = r.y + r.h / 2, x, y, ax, ay, tx, ty;
    if (side === "right") { x = r.x + r.w + dist; y = cy - nh / 2; ax = x; ay = cy; tx = r.x + r.w + 4; ty = cy; }
    else if (side === "left") { x = r.x - dist - nw; y = cy - nh / 2; ax = x + nw; ay = cy; tx = r.x - 4; ty = cy; }
    else if (side === "top") { x = cx - nw / 2; y = r.y - dist - nh; ax = cx; ay = y + nh; tx = cx; ty = r.y - 4; }
    else { x = cx - nw / 2; y = r.y + r.h + dist; ax = cx; ay = y; tx = cx; ty = r.y + r.h + 4; }
    n.style.left = x + "px"; n.style.top = y + "px";
    boxes.push({ x: x, y: y, w: nw, h: nh });
    placed.push({ x: x, y: y, w: nw, h: nh });
    if (!svg) {
      var NS = "http://www.w3.org/2000/svg";
      svg = document.createElementNS(NS, "svg");
      svg.setAttribute("width", document.documentElement.scrollWidth);
      svg.setAttribute("height", document.documentElement.scrollHeight);
      svg.style.cssText = "position:absolute;left:0;top:0;overflow:visible;";
      svg.innerHTML = '<defs><marker id="__doc_arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">' +
        '<path d="M0,0 L10,5 L0,10 z" fill="' + st.color + '"/></marker></defs>';
      layer.appendChild(svg);
    }
    var line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", ax); line.setAttribute("y1", ay); line.setAttribute("x2", tx); line.setAttribute("y2", ty);
    line.setAttribute("stroke", st.color); line.setAttribute("stroke-width", st.width);
    line.setAttribute("marker-end", "url(#__doc_arrow)");
    svg.appendChild(line);
  }

  (spec.items || []).forEach(function (it) {
    if (it.type === "blur") {
      // Données personnelles ou sensibles : toutes les correspondances sont floutées dans la page elle-même.
      var all = document.querySelectorAll(it.selector);
      if (!all.length) { missing.push(it.selector); return; }
      all.forEach(function (b) {
        b.setAttribute("data-doc-annot-blur", b.style.filter || "");
        b.style.filter = "blur(" + (it.strength || 6) + "px)";
      });
      return;
    }
    var el = find(it.selector);
    if (!el) return;
    if (it.scroll !== false && it === spec.items[0]) {
      el.scrollIntoView({ block: "center", inline: "nearest" });
      sx = window.scrollX; sy = window.scrollY;
    }
    var r = rectOf(el), p = st.padding;
    var fr = { x: r.x - p, y: r.y - p, w: r.w + 2 * p, h: r.h + 2 * p };

    if (it.type === "spotlight") {
      // Assombrit tout sauf l'élément : attire l'œil sans ajouter de texte.
      add("div", "left:" + fr.x + "px;top:" + fr.y + "px;width:" + fr.w + "px;height:" + fr.h + "px;" +
        "border-radius:" + st.radius + "px;box-shadow:0 0 0 99999px rgba(0,0,0,.45);");
    } else if (it.type === "arrow" && it.frame === false) {
      // flèche seule, sans cadre autour de la cible
    } else {
      // "box" (défaut) et "arrow" : cadre autour de l'élément
      add("div", "left:" + fr.x + "px;top:" + fr.y + "px;width:" + fr.w + "px;height:" + fr.h + "px;" +
        "border:" + st.width + "px solid " + st.color + ";border-radius:" + st.radius + "px;");
    }
    boxes.push(fr);
    if (!(it.type === "arrow" && it.frame === false) && it.type !== "spotlight") frames.push(fr);
    later.push({ it: it, fr: fr });
  });
  // Deuxième passe : pastilles et notes, une fois tous les cadres connus (évitement des collisions).
  // Pastille : à gauche du cadre de préférence ; sinon coin, dessus, droite, intérieur.
  later.forEach(function (o) {
    if (o.it.label != null) badge(o.fr, o.it.label, o.it.badge);
    if (o.it.type === "arrow") arrow(o.fr, o.it);
    else if (o.it.note) note(o.fr, o.it.note, o.it.side);
  });

  var box = null;
  var cropEl = spec.crop_to ? find(spec.crop_to) : null;
  if (cropEl) {
    // Recadrage sur un conteneur (formulaire, carte, panneau), élargi si une annotation en dépasse.
    boxes.push(rectOf(cropEl));
    st.crop_margin = st.crop_to_margin != null ? st.crop_to_margin : 16;
  }
  if (boxes.length) {
    var x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
    boxes.forEach(function (b) {
      x1 = Math.min(x1, b.x); y1 = Math.min(y1, b.y);
      x2 = Math.max(x2, b.x + b.w); y2 = Math.max(y2, b.y + b.h);
    });
    var m = st.crop_margin;
    box = { x: Math.max(0, x1 - m), y: Math.max(0, y1 - m), w: (x2 - x1) + 2 * m, h: (y2 - y1) + 2 * m,
            scrollX: window.scrollX, scrollY: window.scrollY,
            viewportW: window.innerWidth, viewportH: window.innerHeight };
  }
  if (spec.crop && box) {
    // Zone de recadrage matérialisée par un élément transparent : capture.py demande à Chrome
    // de capturer cet élément (screenshot "#__doc_crop__"), sans retraitement d'image.
    var w = Math.min(box.w, document.documentElement.scrollWidth - box.x);
    add("div", "left:" + box.x + "px;top:" + box.y + "px;width:" + w + "px;height:" + box.h + "px;").id = "__doc_crop__";
  }
  return { ok: missing.length === 0, missing: missing, box: box, dpr: window.devicePixelRatio || 1 };
})(window.__DOC_SPEC__ || {})
