/* Draws a LangGraph-style diagram from a small JSON description.
   Markup:
     <figure class="flow" data-w="640" data-h="200">
       <script type="application/json">{
         "nodes": [{"id":"reason","label":"reason","sub":"LLM","x":160,"y":90,"kind":"llm"}],
         "edges": [{"from":"reason","to":"act","label":"tool calls?","bend":-30,"hot":true,"dash":false}]
       }</script>
       <figcaption>…</figcaption>
     </figure>
   kinds: llm (calls a model), guard, human, end (START/END), ghost (optional), or omitted (plain code).
   Colours come from the theme tokens in course.css, so diagrams follow light and dark. */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var uid = 0;

  function make(tag, attrs, parent) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  // Point where a ray from the box centre towards (tx, ty) leaves the box.
  function boxExit(n, tx, ty) {
    var dx = tx - n.x, dy = ty - n.y;
    if (dx === 0 && dy === 0) return { x: n.x, y: n.y };
    var hw = n.w / 2 + 3, hh = n.h / 2 + 3;
    var t = Math.min(dx ? hw / Math.abs(dx) : Infinity, dy ? hh / Math.abs(dy) : Infinity);
    return { x: n.x + dx * t, y: n.y + dy * t };
  }

  document.querySelectorAll("figure.flow").forEach(function (fig) {
    var spec;
    try { spec = JSON.parse(fig.querySelector('script[type="application/json"]').textContent); }
    catch (e) { return; }
    var W = +fig.dataset.w || 640, H = +fig.dataset.h || 220;
    var id = "flow" + (++uid);

    var wrap = document.createElement("div");
    wrap.className = "flow-scroll";
    var svg = make("svg", { viewBox: "0 0 " + W + " " + H, role: "img" });
    var cap = fig.querySelector("figcaption");
    svg.setAttribute("aria-label", cap ? cap.textContent : "Graph diagram");
    wrap.appendChild(svg);
    fig.insertBefore(wrap, fig.firstChild);

    var defs = make("defs", {}, svg);
    ["", "hot"].forEach(function (v) {
      var m = make("marker", {
        id: id + "-arrow" + v, viewBox: "0 0 10 10", refX: "9", refY: "5",
        markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse"
      }, defs);
      make("path", { d: "M0,0 L10,5 L0,10 z", "class": "flow-arrow" + (v ? " hot" : "") }, m);
    });

    var nodes = {};
    spec.nodes.forEach(function (n) {
      var label = n.label || n.id;
      n.w = n.w || Math.max(64, label.length * 7.6 + 26);
      n.h = n.h || (n.sub ? 44 : 34);
      nodes[n.id] = n;
    });

    var edgeLayer = make("g", {}, svg);
    var labelLayer = make("g", {}, svg);
    var nodeLayer = make("g", {}, svg);

    spec.edges.forEach(function (e) {
      var a = nodes[e.from], b = nodes[e.to];
      if (!a || !b) return;
      var bend = e.bend || 0;
      var mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      var dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1;
      var cx = mx + (-dy / len) * bend, cy = my + (dx / len) * bend;
      var p1 = boxExit(a, bend ? cx : b.x, bend ? cy : b.y);
      var p2 = boxExit(b, bend ? cx : a.x, bend ? cy : a.y);
      var d = bend
        ? "M" + p1.x + "," + p1.y + " Q" + cx + "," + cy + " " + p2.x + "," + p2.y
        : "M" + p1.x + "," + p1.y + " L" + p2.x + "," + p2.y;
      make("path", {
        d: d,
        "class": "flow-edge" + (e.dash ? " dash" : "") + (e.hot ? " hot" : ""),
        "marker-end": "url(#" + id + "-arrow" + (e.hot ? "hot" : "") + ")"
      }, edgeLayer);
      if (e.label) {
        // label sits on the curve's midpoint (t = 0.5)
        var lx = bend ? 0.25 * p1.x + 0.5 * cx + 0.25 * p2.x : (p1.x + p2.x) / 2;
        var ly = bend ? 0.25 * p1.y + 0.5 * cy + 0.25 * p2.y : (p1.y + p2.y) / 2;
        if (e.lx) lx += e.lx;
        if (e.ly) ly += e.ly;
        var g = make("g", { "class": "flow-label" }, labelLayer);
        var tw = e.label.length * 5.9 + 10;
        make("rect", { x: lx - tw / 2, y: ly - 8, width: tw, height: 16, rx: 3 }, g);
        var t = make("text", { x: lx, y: ly + 3.5, "text-anchor": "middle" }, g);
        t.textContent = e.label;
      }
    });

    spec.nodes.forEach(function (n) {
      var g = make("g", { "class": "flow-node" + (n.kind ? " " + n.kind : "") }, nodeLayer);
      var rx = n.kind === "end" ? n.h / 2 : 5;
      make("rect", { x: n.x - n.w / 2, y: n.y - n.h / 2, width: n.w, height: n.h, rx: rx }, g);
      var t = make("text", { x: n.x, y: n.sub ? n.y - 2 : n.y + 4, "text-anchor": "middle" }, g);
      t.textContent = n.label || n.id;
      if (n.sub) {
        var s = make("text", { x: n.x, y: n.y + 13, "text-anchor": "middle", "class": "sub" }, g);
        s.textContent = n.sub;
      }
      if (n.stack) { // a stack of identical workers, drawn as offset outlines behind
        for (var i = 1; i <= 2; i++) {
          var r = make("rect", {
            x: n.x - n.w / 2 + i * 4, y: n.y - n.h / 2 - i * 4, width: n.w, height: n.h, rx: rx,
            "class": "flow-stack"
          });
          g.insertBefore(r, g.firstChild);
          r.style.fill = "var(--surface)";
          r.style.stroke = "var(--rule)";
        }
      }
    });
  });
})();
