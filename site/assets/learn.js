(function(){
var $=function(i){return document.getElementById(i)};
var fmt=function(n){var s=Math.abs(n).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});return (n<0?'-$':'$')+s};
// glossary search
var q=$('glq');if(q){var items=[].slice.call(document.querySelectorAll('#gllist .gl-item')),c=$('glcount');
function f(){var v=q.value.trim().toLowerCase(),n=0;items.forEach(function(e){var t=e.textContent.toLowerCase(),show=!v||t.indexOf(v)>-1;e.hidden=!show;if(show)n++});c.textContent=v?(n+' of '+items.length+' terms'):items.length+' terms. Type to filter.'}
q.addEventListener('input',f);f()}
// position size
if($('ps-out')){var ids=['ps-acct','ps-risk','ps-entry','ps-stop'];
function ps(){var a=+$('ps-acct').value,r=+$('ps-risk').value,e=+$('ps-entry').value,s=+$('ps-stop').value,o=$('ps-out');
if(!(a>0&&r>0&&e>0&&s>0)){o.innerHTML='<p class="calc-warn">Enter positive numbers in every field.</p>';return}
var rps=Math.abs(e-s);if(rps===0){o.innerHTML='<p class="calc-warn">Entry and stop can\'t be the same price.</p>';return}
var dollars=a*r/100,sh=Math.floor(dollars/rps),val=sh*e,long=e>s;
o.innerHTML='<div><dt>Dollars at risk</dt><dd>'+fmt(dollars)+'</dd></div><div><dt>Risk per share</dt><dd>'+fmt(rps)+'</dd></div><div><dt>Shares</dt><dd>'+sh.toLocaleString()+'</dd></div><div><dt>Position value</dt><dd>'+fmt(val)+'</dd></div><div><dt>% of account</dt><dd>'+(val/a*100).toFixed(1)+'%</dd></div><div><dt>Direction</dt><dd>'+(long?'Long':'Short')+'</dd></div>'+(val>a?'<p class="calc-warn">This position is bigger than your account. It would need margin.</p>':'')}
ids.forEach(function(i){$(i).addEventListener('input',ps)});ps()}
// options P/L
if($('op-out')){var oi=['op-type','op-side','op-strike','op-prem','op-qty','op-px'];
function pl(px,t,sd,k,p,q){var intr=t==='call'?Math.max(px-k,0):Math.max(k-px,0);var v=(sd==='long'?intr-p:p-intr)*100*q;return v}
function op(){var t=$('op-type').value,sd=$('op-side').value,k=+$('op-strike').value,p=+$('op-prem').value,q=Math.max(1,Math.floor(+$('op-qty').value||1)),px=+$('op-px').value,o=$('op-out');
if(!(k>0&&p>=0&&px>=0)){o.innerHTML='<p class="calc-warn">Enter a strike, premium and stock price.</p>';return}
var v=pl(px,t,sd,k,p,q),be=t==='call'?k+p:k-p,cost=p*100*q,mx,ml;
if(sd==='long'){ml=cost;mx=t==='call'?'Unlimited':fmt((k-p)*100*q)}else{mx=cost;ml=t==='call'?'Unlimited':fmt((k-p)*100*q)}
o.innerHTML='<div><dt>Profit / loss</dt><dd class="'+(v>=0?'pos':'neg')+'">'+fmt(v)+'</dd></div><div><dt>Breakeven</dt><dd>'+fmt(be).replace('-','')+'</dd></div><div><dt>'+(sd==='long'?'Premium paid':'Premium received')+'</dt><dd>'+fmt(cost)+'</dd></div><div><dt>Max profit</dt><dd>'+(typeof mx==='string'?mx:fmt(mx))+'</dd></div><div><dt>Max loss</dt><dd>'+(typeof ml==='string'?ml:fmt(ml))+'</dd></div>';
var tb=document.querySelector('#op-table tbody'),rows='';for(var i=-5;i<=5;i++){var s=Math.max(0,k*(1+i*0.05)),r=pl(s,t,sd,k,p,q);rows+='<tr><td>'+fmt(s).replace('-','')+'</td><td class="'+(r>=0?'pos':'neg')+'">'+fmt(r)+'</td></tr>'}tb.innerHTML=rows}
oi.forEach(function(i){$(i).addEventListener('input',op)});op()}
})();

/* ===== PR #73: quiz engine + progress (appended to learn utils) ===== */
/* MarketsOnDeck Learn — end-of-lesson quizzes + per-device progress.
   Static only: no backend, no accounts, no network calls, no tracking.
   Progress lives in this browser's localStorage under "modLearnProgress.v1".
   Everything is wrapped defensively: if JS is off or storage is blocked,
   the lessons simply read as normal articles. */
(function () {
  "use strict";

  var PASS_PCT = 60; /* friendly bar: 3/5 passes */
  var LS_KEY = "modLearnProgress.v1";

  var LESSON_TITLES = {
    "options-in-plain-english": "Options in plain English",
    "covered-calls": "Covered calls",
    "earnings-and-iv-crush": "Earnings and IV crush"
  };
  var PUBLISHED_ORDER = [
    "options-in-plain-english",
    "covered-calls",
    "earnings-and-iv-crush"
  ];
  var LESSON_URLS = {
    "options-in-plain-english": "/learn/options-in-plain-english.html",
    "covered-calls": "/learn/covered-calls.html",
    "earnings-and-iv-crush": "/learn/earnings-and-iv-crush.html"
  };
  var LESSON_NUMBERS = {
    "options-in-plain-english": 1,
    "covered-calls": 4,
    "earnings-and-iv-crush": 7
  };

  /* Quiz content is drawn strictly from each lesson's text — no invented facts. */
  var QUIZZES = {
    "options-in-plain-english": [
      {
        q: "One option contract controls how many shares of stock?",
        choices: ["10 shares", "100 shares", "1,000 shares", "It varies by broker"],
        answer: 1,
        hint: "Check the Key terms box near the top of the lesson — it's the same for every standard stock option.",
        explain: "One contract = 100 shares, always. That's why a $2.00 quote costs $200 total (1 contract × 100 shares × $2.00)."
      },
      {
        q: "You buy one $55 call for a $2.00 premium ($200 total) and the stock jumps to $62. Roughly what's your profit?",
        choices: ["About $500", "About $700", "About $1,200", "About $200"],
        answer: 0,
        hint: "The right to buy at $55 is worth $7 per share at $62 — but don't forget what you paid up front.",
        explain: "At $62, buying at $55 is worth $7/share → about $700 per contract. Minus the $200 premium you paid = roughly $500 profit."
      },
      {
        q: "What's the most a call buyer can ever lose?",
        choices: ["The premium paid", "The strike price × 100", "An unlimited amount", "Twice the premium"],
        answer: 0,
        hint: "Remember the asymmetry the lesson points out: the buyer's risk is capped, the upside isn't.",
        explain: "A buyer's risk is capped at the premium. If the option expires worthless, you lose what you paid — nothing more."
      },
      {
        q: "A put gives its holder the right to…",
        choices: [
          "Buy 100 shares at the strike price",
          "Sell 100 shares at the strike price",
          "Collect the stock's dividends",
          "Force the company to buy back shares"
        ],
        answer: 1,
        hint: "Puts are for when you think the stock will go down — which direction does that point?",
        explain: "A put is the right to sell 100 shares at the strike price. You buy puts when you're bearish — or as insurance on shares you already own."
      },
      {
        q: "You sell a call without owning the shares (a “naked” call). What's your risk?",
        choices: [
          "Capped at the premium you collected",
          "Theoretically unlimited",
          "Zero — you collected premium",
          "Limited to the strike price"
        ],
        answer: 1,
        hint: "The lesson warns beginners away from this exact trade — ask yourself why.",
        explain: "A stock can keep rising with no ceiling, so a naked call seller's losses are theoretically unlimited. The lesson files this under common mistakes for beginners."
      }
    ],

    "covered-calls": [
      {
        q: "What's the standing rule for covered calls on this account?",
        choices: [
          "Never sell a call below your cost basis",
          "Always sell at-the-money calls",
          "Never hold a call past one week",
          "Only sell puts, never calls"
        ],
        answer: 0,
        hint: "It's the section titled “the one rule that matters.”",
        explain: "Selling below your basis can turn a winning stock into a losing trade if you're assigned — the premium rarely covers the stock loss."
      },
      {
        q: "The HD example: 100 shares at a $297.03 basis, you sell the $300 call for $1.67. HD stays under $300 through expiration. What happens?",
        choices: [
          "You keep the $167 premium and your 100 shares",
          "Your shares are sold at $300",
          "You owe another $167",
          "The trade breaks even"
        ],
        answer: 0,
        hint: "What happens to an option that finishes out of the money?",
        explain: "The call expires worthless — the most common outcome, and the whole point. You keep the $167, keep your shares, and can sell another call next cycle."
      },
      {
        q: "Same trade, but HD rallies past $300 and you're assigned. What's your total gain?",
        choices: ["$167", "$297", "$464", "$300"],
        answer: 2,
        hint: "Two pieces: the stock profit (($300 − $297.03) × 100) plus the premium you already collected.",
        explain: "$297 of stock profit + the $167 premium = $464 on a two-week trade. You miss any rally beyond $300 — that's the price of the premium."
      },
      {
        q: "What do you give up when you sell a covered call?",
        choices: [
          "The premium",
          "Gains above the strike price",
          "Your dividends",
          "Downside protection"
        ],
        answer: 1,
        hint: "It's a swap: immediate income in exchange for… what?",
        explain: "A covered call swaps open-ended upside for immediate income. If the stock moons past your strike, you watch from the sidelines holding your premium."
      },
      {
        q: "The stock drops $10 a share ($1,000 on 100 shares) while your short call collected $167. How protected are you?",
        choices: [
          "Fully protected — the premium covers the drop",
          "Softened by $167, but you still feel most of the drop",
          "You profit, because the call gains value as the stock falls",
          "The drop is erased at expiration"
        ],
        answer: 1,
        hint: "The lesson is blunt about this: a covered call is an income trade, not a… what?",
        explain: "A $167 premium softens a $1,000 drop but doesn't prevent it. A covered call is an income trade on a stock you'd be happy holding — not a hedge."
      }
    ],

    "earnings-and-iv-crush": [
      {
        q: "What is IV crush?",
        choices: [
          "The collapse in implied volatility after a known event passes, making options cheaper",
          "A stock crashing the day after earnings",
          "Your broker liquidating your position",
          "Volatility spiking before a news event"
        ],
        answer: 0,
        hint: "It's in the Key terms box — what happens to option prices right after the event?",
        explain: "Once the uncertainty passes, the “uncertainty premium” evaporates. Options get cheaper instantly — even if the stock moved."
      },
      {
        q: "The straddle example: stock at $35, you pay $2.80 ($280) for the straddle. The company beats and the stock jumps 5% to $36.75. Result?",
        choices: [
          "About a $90 loss",
          "About a $90 profit",
          "Roughly break-even",
          "About a $280 profit"
        ],
        answer: 0,
        hint: "After the crush, the call holds $1.75 of intrinsic value and the put is nearly worthless — add them up.",
        explain: "You called the direction right and still lost ~$90. The straddle fell to about $1.90 ($190) from the $280 you paid — IV crush ate the rest."
      },
      {
        q: "Why did the straddle lose even though the stock jumped?",
        choices: [
          "The 5% move was smaller than the ~8% move the options had priced in",
          "Earnings beats always hurt option buyers",
          "The strike price was wrong",
          "Commissions ate the profit"
        ],
        answer: 0,
        hint: "You don't just need the stock to move — you need it to move more than…?",
        explain: "The market had priced in roughly $2.80 of expected move. A 5% jump ($1.75) wasn't enough to overcome the premium. You're betting against the expected move, not just the direction."
      },
      {
        q: "What's this account's standing rule about earnings?",
        choices: [
          "No new option entries immediately before earnings",
          "Always buy a straddle before earnings",
          "Double position size into earnings",
          "Sell all shares before every earnings report"
        ],
        answer: 0,
        hint: "It's the section titled “the standing rule on this account.”",
        explain: "Buying premium into a binary event means paying peak IV and watching it evaporate the next morning. Shares are a different story — a stock has no IV to crush."
      },
      {
        q: "High implied volatility means…",
        choices: [
          "Everyone expects a big move — direction unknown",
          "Everyone is bullish on the stock",
          "The stock is safe and stable",
          "Options are cheap right now"
        ],
        answer: 0,
        hint: "The lesson's common-mistakes section calls this exact misunderstanding out.",
        explain: "High IV means the market expects a big swing, up or down — fear and greed in both directions. And it makes every option on the chain more expensive."
      }
    ]
  };

  /* ---------- progress store ---------- */

  function loadProgress() {
    try {
      var raw = window.localStorage.getItem(LS_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      return {};
    }
  }

  function saveProgress(p) {
    try {
      window.localStorage.setItem(LS_KEY, JSON.stringify(p));
      return true;
    } catch (e) {
      return false;
    }
  }

  function recordResult(slug, score, total) {
    var p = loadProgress();
    var prev = p[slug] || { attempts: 0 };
    var passed = (score / total) * 100 >= PASS_PCT;
    var best = prev.bestScore == null ? score : Math.max(prev.bestScore, score);
    p[slug] = {
      score: score,
      total: total,
      bestScore: best,
      passed: prev.passed || passed,
      attempts: (prev.attempts || 0) + 1,
      completedAt: prev.completedAt || (passed ? new Date().toISOString() : null)
    };
    var persisted = saveProgress(p);
    return { passed: passed, persisted: persisted, best: best };
  }

  /* ---------- quiz ---------- */

  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function initQuiz() {
    var mount = document.getElementById("learn-quiz");
    if (!mount) return;
    var slug = mount.getAttribute("data-lesson");
    var questions = QUIZZES[slug];
    if (!questions || !questions.length) return;

    var state = { idx: 0, firstTryScore: 0, answered: false };

    function renderMeta() {
      return (
        '<div class="quiz-meta">' +
        questions.length + " questions &middot; wrong answers get a hint, not a penalty &middot; " +
        "your score counts your <strong>first try</strong> on each question &middot; " +
        PASS_PCT + "%+ marks the lesson complete" +
        "</div>"
      );
    }

    function renderDots() {
      var html = '<div class="quiz-dots" aria-hidden="true">';
      for (var i = 0; i < questions.length; i++) {
        var cls = "quiz-dot";
        if (i < state.idx) cls += " is-done";
        else if (i === state.idx) cls += " is-current";
        html += '<span class="' + cls + '"></span>';
      }
      return html + "</div>";
    }

    function renderQuestion() {
      var qd = questions[state.idx];
      state.answered = false;
      var html = renderMeta() + renderDots();
      html += '<p class="quiz-q">' + (state.idx + 1) + ". " + esc(qd.q) + "</p>";
      html += '<ul class="quiz-choices">';
      for (var i = 0; i < qd.choices.length; i++) {
        html +=
          '<li><button type="button" class="quiz-choice" data-i="' + i + '">' +
          esc(qd.choices[i]) +
          "</button></li>";
      }
      html += "</ul>";
      html += '<div class="quiz-feedback-slot"></div>';
      mount.innerHTML = html;

      var buttons = mount.querySelectorAll(".quiz-choice");
      for (var b = 0; b < buttons.length; b++) {
        buttons[b].addEventListener("click", onPick);
      }
    }

    function onPick(ev) {
      if (state.answered) return;
      var btn = ev.currentTarget;
      var pick = parseInt(btn.getAttribute("data-i"), 10);
      var qd = questions[state.idx];
      var slot = mount.querySelector(".quiz-feedback-slot");
      var buttons = mount.querySelectorAll(".quiz-choice");

      if (pick === qd.answer) {
        state.answered = true;
        if (!btn.getAttribute("data-tried")) state.firstTryScore++;
        btn.classList.add("is-right");
        for (var b = 0; b < buttons.length; b++) buttons[b].disabled = true;
        slot.innerHTML =
          '<div class="quiz-feedback quiz-explain" role="status"><strong>Correct.</strong>' +
          esc(qd.explain) +
          "</div>" +
          '<div class="quiz-actions">' +
          (state.idx < questions.length - 1
            ? '<button type="button" class="btn btn-primary quiz-next">Next question &rarr;</button>'
            : '<button type="button" class="btn btn-primary quiz-next">See your score &rarr;</button>') +
          "</div>";
        mount.querySelector(".quiz-next").addEventListener("click", function () {
          state.idx++;
          if (state.idx < questions.length) renderQuestion();
          else renderResult();
        });
      } else {
        btn.classList.add("is-wrong");
        btn.disabled = true;
        btn.setAttribute("data-tried", "1");
        slot.innerHTML =
          '<div class="quiz-feedback quiz-hint" role="status"><strong>Not quite — here\'s a hint:</strong>' +
          esc(qd.hint) +
          "</div>";
      }
    }

    function verdict(score, total) {
      var pct = Math.round((score / total) * 100);
      if (pct === 100)
        return "Perfect score. You didn't skim this one — that's rarer than it sounds.";
      if (pct >= 80)
        return "Strong work. One slipped past, but the hint already showed you which.";
      if (pct >= PASS_PCT)
        return "Passed — good enough to move on. Worth a re-read of the ones you missed.";
      return "Not yet. Skim the lesson once more and retake it — the hints are here to teach, not trick.";
    }

    function renderResult() {
      var total = questions.length;
      var score = state.firstTryScore;
      var res = recordResult(slug, score, total);
      var pct = Math.round((score / total) * 100);

      var html =
        '<div class="quiz-result">' +
        renderMeta() +
        '<div class="quiz-score">' + score + "/" + total + "</div>" +
        '<p class="quiz-verdict">' + esc(verdict(score, total)) + "</p>";

      if (res.persisted) {
        if (res.passed) {
          html +=
            '<p class="quiz-best">Lesson marked complete' +
            (res.best > score ? " &middot; best score " + res.best + "/" + total : "") +
            ".</p>";
        } else {
          html += '<p class="quiz-best">Progress saved on this device.</p>';
        }
      } else {
        html +=
          '<p class="quiz-best">This browser blocked saving, so progress won\'t be remembered here.</p>';
      }

      html +=
        '<div class="quiz-actions">' +
        '<button type="button" class="btn quiz-retake">Retake the quiz</button> ' +
        '<a class="btn" href="/learn/index.html">&larr; Back to all lessons</a>' +
        "</div></div>";

      mount.innerHTML = html;
      mount.querySelector(".quiz-retake").addEventListener("click", function () {
        state.idx = 0;
        state.firstTryScore = 0;
        renderQuestion();
      });
      if (mount.scrollIntoView) {
        try { mount.scrollIntoView({ block: "nearest" }); } catch (e) {}
      }
    }

    renderQuestion();
  }

  /* ---------- hub progress ---------- */

  function initHub() {
    var mount = document.getElementById("learn-progress");
    if (!mount) return;
    var p = loadProgress();

    var doneCount = 0;
    for (var i = 0; i < PUBLISHED_ORDER.length; i++) {
      var s = PUBLISHED_ORDER[i];
      if (p[s] && p[s].passed) doneCount++;
    }

    var nextSlug = null;
    for (var j = 0; j < PUBLISHED_ORDER.length; j++) {
      var s2 = PUBLISHED_ORDER[j];
      if (!(p[s2] && p[s2].passed)) { nextSlug = s2; break; }
    }

    var pct = Math.round((doneCount / PUBLISHED_ORDER.length) * 100);
    var html =
      '<div class="lp-card">' +
      "<h3>Your progress</h3>" +
      '<p class="lp-sub">' + doneCount + " of " + PUBLISHED_ORDER.length + " published lessons complete</p>" +
      '<div class="lp-bar" role="progressbar" aria-valuenow="' + pct + '" aria-valuemin="0" aria-valuemax="100" aria-label="Lessons complete">' +
      '<div class="lp-fill" style="width:' + pct + '%"></div></div>';

    if (nextSlug) {
      html +=
        '<p class="lp-continue">Continue where you left off: ' +
        '<a href="' + LESSON_URLS[nextSlug] + '">Lesson ' + LESSON_NUMBERS[nextSlug] + " — " +
        esc(LESSON_TITLES[nextSlug]) + " &rarr;</a></p>";
    } else {
      html +=
        '<p class="lp-continue"><span class="lp-done">All published lessons complete — nice work.</span> ' +
        "More lessons are on the way.</p>";
    }

    html +=
      '<p class="lp-note">Progress saves on this device — no account, no email, nothing leaves your browser.</p>' +
      "</div>";

    mount.innerHTML = html;

    /* per-row status in the lessons table */
    var rows = document.querySelectorAll("tr[data-lesson]");
    for (var r = 0; r < rows.length; r++) {
      var slug = rows[r].getAttribute("data-lesson");
      var rec = p[slug];
      if (!rec) continue;
      var cells = rows[r].querySelectorAll("td");
      var statusCell = cells[cells.length - 1];
      if (!statusCell) continue;
      var tag;
      if (rec.passed) {
        tag = ' <span class="lp-done">&middot; &#10003; ' + rec.bestScore + "/" + rec.total + "</span>";
      } else {
        tag = ' <span class="lp-partial">&middot; ' + rec.score + "/" + rec.total + " so far</span>";
      }
      statusCell.innerHTML = statusCell.innerHTML + tag;
    }
  }

  function run() {
    try { initQuiz(); } catch (e) {}
    try { initHub(); } catch (e) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
