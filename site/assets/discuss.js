/* MarketsOnDeck share bar.
   Injects no-sign-in share buttons (X, Facebook, Threads, copy link)
   into <div id="discuss"> on article pages. Pure progressive enhancement:
   if this file fails to load, the page is unchanged. */
(function () {
  var host = document.getElementById('discuss');
  if (!host) return;

  var url = location.href.split('#')[0];
  var title = document.title.replace(/\s*[|\u2014-]\s*MarketsOnDeck.*$/i, '').trim();

  /* ---- share bar ---- */
  var bar = document.createElement('div');
  bar.className = 'discuss-share';
  var links = [
    { label: 'Post on X', href: 'https://x.com/intent/post?text=' + encodeURIComponent(title) + '&url=' + encodeURIComponent(url) + '&hashtags=MarketsOnDeck' },
    { label: 'Share on Facebook', href: 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url) },
    { label: 'Share on Threads', href: 'https://www.threads.net/intent/post?text=' + encodeURIComponent(title + ' ' + url) }
  ];
  bar.appendChild(document.createTextNode('Share: '));
  links.forEach(function (l) {
    var a = document.createElement('a');
    a.href = l.href; a.target = '_blank'; a.rel = 'noopener';
    a.className = 'discuss-share-btn'; a.textContent = l.label;
    bar.appendChild(a);
  });
  var copy = document.createElement('button');
  copy.type = 'button'; copy.className = 'discuss-share-btn'; copy.textContent = 'Copy link';
  copy.addEventListener('click', function () {
    function done() { copy.textContent = 'Copied'; setTimeout(function(){ copy.textContent = 'Copy link'; }, 2000); }
    if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(url).then(done, done); } else { done(); }
  });
  bar.appendChild(copy);
  host.appendChild(bar);

})();
