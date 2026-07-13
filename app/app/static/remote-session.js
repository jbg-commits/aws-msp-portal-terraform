(function () {
  var elapsedEl = document.getElementById("rs-elapsed");
  if (elapsedEl) {
    var started = new Date(elapsedEl.dataset.started).getTime();
    var tick = function () {
      var s = Math.max(0, Math.floor((Date.now() - started) / 1000));
      var hh = String(Math.floor(s / 3600)).padStart(2, "0");
      var mm = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
      var ss = String(s % 60).padStart(2, "0");
      elapsedEl.textContent = hh + ":" + mm + ":" + ss;
    };
    tick();
    setInterval(tick, 1000);
  }

  var graceEl = document.getElementById("rs-grace");
  if (graceEl) {
    var disconnected = new Date(graceEl.dataset.disconnected).getTime();
    var tickGrace = function () {
      var remaining = Math.ceil((disconnected + 30000 - Date.now()) / 1000);
      if (remaining <= 0) {
        location.reload();
        return;
      }
      graceEl.textContent = remaining;
    };
    tickGrace();
    setInterval(tickGrace, 1000);
  }
})();
