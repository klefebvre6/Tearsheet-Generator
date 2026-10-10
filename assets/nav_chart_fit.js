(function () {
  var WRAP = ".tcp-nav-chart-plot-wrap, .tearsheet-nav-chart-plot-wrap";

  function fit(gd) {
    if (!gd || !window.Plotly || !gd._fullLayout) return;
    var wrap = gd.closest(WRAP);
    if (!wrap) return;
    var height = wrap.clientHeight;
    if (!height || Math.abs(gd._fullLayout.height - height) < 2) return;
    window.Plotly.relayout(gd, {height: height, autosize: false});
  }

  function watch(gd) {
    if (!gd || gd.__hcNavFit) return;
    gd.__hcNavFit = true;
    if (typeof gd.on === "function") {
      gd.on("plotly_afterplot", function () { fit(gd); });
    }
    fit(gd);
  }

  function scan() {
    document.querySelectorAll(".tcp-nav-chart-plot-wrap .js-plotly-plot, .tearsheet-nav-chart-plot-wrap .js-plotly-plot").forEach(watch);
  }

  scan();
  window.addEventListener("resize", scan);
  if (document.body) {
    new MutationObserver(scan).observe(document.body, {childList: true, subtree: true});
  }
  var tries = 0;
  var timer = window.setInterval(function () {
    scan();
    tries += 1;
    if (tries >= 24) window.clearInterval(timer);
  }, 500);
})();
