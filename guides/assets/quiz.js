/* Retrieval-practice quiz.
   Markup:
     <div class="quiz"><script type="application/json">
       {"questions":[{"q":"…","options":["…","…","…"],"answer":1,"why":"…"}]}
     </script></div>
   One click per question; feedback is immediate. Options in a question are
   written to the same length so their shape gives nothing away. */
(function () {
  "use strict";

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  document.querySelectorAll(".quiz").forEach(function (root, qi) {
    var data;
    try {
      data = JSON.parse(root.querySelector('script[type="application/json"]').textContent);
    } catch (e) {
      root.appendChild(el("p", "small", "This quiz could not load."));
      return;
    }

    var score = el("p", "quiz-score");
    var answered = 0, correct = 0;

    function updateScore() {
      score.innerHTML = "";
      if (answered === 0) {
        score.textContent = data.questions.length + " questions. Answer from memory before you scroll back up.";
        return;
      }
      var s = el("span");
      s.innerHTML = "<strong>" + correct + "</strong> of " + answered + " right" +
        (answered === data.questions.length ? " · all answered" : "");
      score.appendChild(s);
      if (answered === data.questions.length) {
        var again = el("button", "quiz-reset", "Try again");
        again.type = "button";
        again.addEventListener("click", reset);
        score.appendChild(again);
      }
    }

    var blocks = [];

    function build() {
      data.questions.forEach(function (q, i) {
        var fs = el("fieldset", "quiz-q");
        var lg = el("legend");
        lg.appendChild(el("span", "qn", (i + 1) + "."));
        lg.appendChild(document.createTextNode(q.q));
        fs.appendChild(lg);
        var opts = el("div", "quiz-opts");
        var why = el("p", "quiz-why");
        why.hidden = true;
        why.setAttribute("aria-live", "polite");

        q.options.forEach(function (text, oi) {
          var lab = el("label", "quiz-opt");
          var input = document.createElement("input");
          input.type = "radio";
          input.name = "quiz" + qi + "-q" + i;
          input.id = "quiz" + qi + "-q" + i + "-o" + oi;
          input.value = String(oi);
          lab.appendChild(input);
          lab.appendChild(el("span", null, text));
          opts.appendChild(lab);

          input.addEventListener("change", function () {
            if (fs.classList.contains("answered")) return;
            fs.classList.add("answered");
            var ok = oi === q.answer;
            answered += 1;
            if (ok) correct += 1;
            opts.querySelectorAll("input").forEach(function (inp) { inp.disabled = true; });
            lab.classList.add(ok ? "right" : "wrong");
            if (!ok) opts.children[q.answer].classList.add("right");
            why.innerHTML = "";
            why.appendChild(el("span", "verdict " + (ok ? "ok" : "no"), ok ? "Right. " : "Not quite. "));
            why.appendChild(document.createTextNode(q.why));
            why.hidden = false;
            updateScore();
          });
        });

        fs.appendChild(opts);
        fs.appendChild(why);
        root.appendChild(fs);
        blocks.push(fs);
      });
      root.appendChild(score);
      updateScore();
    }

    function reset() {
      blocks.forEach(function (b) { b.remove(); });
      blocks = [];
      score.remove();
      answered = 0; correct = 0;
      build();
    }

    build();
  });
})();
