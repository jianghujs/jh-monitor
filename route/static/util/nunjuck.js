(function (global) {
  var env = null;

  function getEnv() {
    if (!env && global.nunjucks) {
      env = new nunjucks.Environment(null, { autoescape: false });
    }
    return env;
  }

  function renderString(template, data) {
    var renderer = getEnv();
    if (!renderer || !template) {
      return '';
    }
    try {
      return renderer.renderString(template, data || {});
    } catch (err) {
      console.error('[nunjucks] render failed', err);
      return '';
    }
  }

  global.JHNunjucks = {
    getEnv: getEnv,
    renderString: renderString
  };
})(window);
