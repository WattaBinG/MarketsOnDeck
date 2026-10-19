/* Cashtag auto-links: $NVDA -> Yahoo Finance quote page (graceful, no dependency).
   Static text only: skips links, scripts, styles, code, inputs, and dynamically
   rendered areas (ticker tape, wire). Money amounts ($50, $1.2B) are ignored. */
(function () {
  var PATTERN = /\$([A-Z]{1,5})(?![A-Za-z])/g;
  var SKIP = { A: 1, SCRIPT: 1, STYLE: 1, CODE: 1, PRE: 1, TEXTAREA: 1, INPUT: 1, SELECT: 1, BUTTON: 1 };
  var COMMON_WORDS = { A: 1, I: 1, AM: 1, PM: 1, ET: 1, US: 1, UK: 1, TV: 1,  IT: 1, IS: 1, AT: 1, TO: 1, DO: 1, GO: 1, UP: 1, IPO: 1, ETF: 1, CEO: 1, CFO: 1, GDP: 1, CPI: 1, PPI: 1, FOMC: 1, SEC: 1, FDA: 1, Fed: 1 };

  function linkify(node) {
    var text = node.nodeValue;
    PATTERN.lastIndex = 0;
    if (!PATTERN.test(text)) return;
    PATTERN.lastIndex = 0;
    var frag = document.createDocumentFragment();
    var last = 0, m;
    while ((m = PATTERN.exec(text))) {
      var ticker = m[1];
      if (COMMON_WORDS[ticker]) continue;
      if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
      var a = document.createElement('a');
      a.className = 'cashtag';
      a.href = 'https://finance.yahoo.com/quote/' + encodeURIComponent(ticker);
      a.target = '_blank';
      a.rel = 'noopener';
      a.title = ticker + ' chart (Yahoo Finance)';
      a.textContent = '$' + ticker;
      frag.appendChild(a);
      last = m.index + m[0].length;
    }
    if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
    node.parentNode.replaceChild(frag, node);
  }

  function walk(root) {
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        var p = n.parentNode;
        if (!p || SKIP[p.tagName]) return NodeFilter.FILTER_REJECT;
        if (!n.nodeValue || n.nodeValue.indexOf('$') === -1) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var nodes = [];
    var n;
    while ((n = walker.nextNode())) nodes.push(n);
    nodes.forEach(linkify);
  }

  function init() {
    var root = document.querySelector('main') || document.body;
    walk(root);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
