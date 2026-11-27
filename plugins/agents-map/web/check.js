// Not a module, on purpose: if one of the page's modules fails to load, none of them
// runs and the page would stay blank without a word. This says so.
window.addEventListener('load', function () {
  setTimeout(function () {
    if (window.agents_map) return;
    var note = document.createElement('div');
    note.id = 'empty';
    note.textContent = 'The map did not load completely. Reload the page; if that does not help, restart python3 agents_map.py.';
    document.getElementById('stage').appendChild(note);
  }, 1500);
});
