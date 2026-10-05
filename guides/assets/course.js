/* Shared behaviour for every guide page:
   1. a Copy button on each code block (skip with <pre data-nocopy>)
   2. tick-off boxes on <ol class="steps"> items, remembered per page in this browser
   3. a progress line in any element with class="progress"
   Works from file:// and from a web server; storage is optional. */
(function () {
  "use strict";

  // ---- 1. copy buttons --------------------------------------------------------
  function textOf(pre) {
    // Leave out shell prompts and comment lines so the copied text runs as-is.
    var clone = pre.cloneNode(true);
    clone.querySelectorAll(".p, .copy-btn").forEach(function (n) { n.remove(); });
    return clone.textContent.replace(/\n+$/, "");
  }

  document.querySelectorAll("pre:not([data-nocopy])").forEach(function (pre) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy-btn";
    btn.textContent = "Copy";
    btn.setAttribute("aria-label", "Copy this code");
    btn.addEventListener("click", function () {
      var text = textOf(pre);
      function done() {
        btn.textContent = "Copied";
        btn.classList.add("copied");
        setTimeout(function () { btn.textContent = "Copy"; btn.classList.remove("copied"); }, 1600);
      }
      function fallback() {
        var range = document.createRange();
        range.selectNodeContents(pre.querySelector("code") || pre);
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        btn.textContent = "Press ⌘C";
      }
      try {
        navigator.clipboard.writeText(text).then(done, fallback);
      } catch (e) {
        fallback();
      }
    });
    pre.appendChild(btn);
  });

  // ---- 2. step tick-off -------------------------------------------------------
  var key = "lab-guides:" + location.pathname.split("/").slice(-2).join("/");
  var saved = {};
  try { saved = JSON.parse(localStorage.getItem(key) || "{}"); } catch (e) { saved = {}; }

  function save() {
    try { localStorage.setItem(key, JSON.stringify(saved)); } catch (e) { /* storage blocked: fine */ }
  }

  var items = [];
  document.querySelectorAll("ol.steps").forEach(function (ol, listIndex) {
    Array.prototype.forEach.call(ol.children, function (li, i) {
      if (li.tagName !== "LI") return;
      var id = "s" + listIndex + "-" + i;
      var title = li.querySelector(".step-title");
      if (!title) return;
      var label = document.createElement("label");
      label.className = "step-check";
      var box = document.createElement("input");
      box.type = "checkbox";
      box.id = "chk-" + id;
      box.checked = !!saved[id];
      label.appendChild(box);
      label.appendChild(document.createTextNode("Done"));
      title.appendChild(label);
      li.classList.toggle("done", box.checked);
      box.addEventListener("change", function () {
        saved[id] = box.checked;
        li.classList.toggle("done", box.checked);
        save();
        render();
      });
      items.push(box);
    });
  });

  // ---- 3. progress ------------------------------------------------------------
  function render() {
    var n = items.filter(function (b) { return b.checked; }).length;
    document.querySelectorAll(".progress").forEach(function (el) {
      el.innerHTML = items.length
        ? "<strong>" + n + "</strong> of " + items.length + " steps done"
        : "";
    });
  }
  render();
})();
