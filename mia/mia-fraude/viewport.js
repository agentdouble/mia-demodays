/* Keep the complete arcade inside the visible area, including short/mobile screens. */
export function lockGameViewport(screen, stage, helpPanel) {
  const wrap = screen.parentElement;
  let pending = false;
  function fit() {
    pending = false;
    const width = Math.max(320, Math.min(460, wrap.clientWidth));
    const baseHeight = width <= 420 ? 716 : 748;
    screen.style.width = `${width}px`;
    screen.style.height = `${baseHeight}px`;
    // The rules panel can need a taller virtual console; fit it without a scroll area.
    const height = helpPanel.hidden ? baseHeight : Math.max(baseHeight, helpPanel.scrollHeight);
    screen.style.height = `${height}px`;
    const availableHeight = Math.min(wrap.clientHeight, (visualViewport?.height || innerHeight) - 48);
    const scale = Math.min(1, wrap.clientWidth / width, availableHeight / height);
    screen.style.setProperty("--console-scale", String(Math.max(0.1, scale)));
  }
  function schedule() {
    if (!pending) { pending = true; requestAnimationFrame(fit); }
  }
  new ResizeObserver(schedule).observe(wrap);
  new MutationObserver(schedule).observe(stage, { childList: true });
  new MutationObserver(schedule).observe(helpPanel, { attributes: true, attributeFilter: ["hidden"] });
  visualViewport?.addEventListener("resize", schedule);
  addEventListener("resize", schedule);
  document.fonts.ready.then(schedule);

  const block = event => {
    // Keep page zoom locked, but let the magnifier and rules scroll normally.
    if (event.type === "wheel" && !event.ctrlKey && event.target.closest?.(".zoom-media, .help")) return;
    event.preventDefault();
  };
  for (const type of ["gesturestart", "gesturechange", "gestureend", "wheel"]) {
    document.addEventListener(type, block, { passive: false });
  }
  document.addEventListener("touchmove", event => {
    if (event.touches.length > 1) event.preventDefault();
  }, { passive: false });
  document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && ["+", "=", "-", "_", "0"].includes(event.key)) {
      event.preventDefault();
    }
  });
  fit();
}
