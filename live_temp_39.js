
  window.Nova = window.Nova || {};
  window.Nova.render = window.Nova.render || {};

  if (
    window.NovaRender &&
    typeof window.NovaRender.renderMessages === "function"
  ) {
    window.Nova.render.renderMessages =
      window.NovaRender.renderMessages;

    console.log(
      "[Nova Render Bridge] Nova.render.renderMessages connected"
    );
  }

