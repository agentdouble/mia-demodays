import { api } from "./api.js";
import { lockGameViewport } from "./viewport.js";

(() => {
  const NEW_CAP = 4500, PORTFOLIO = 50000, ROUND = 6;

  const SKIN = ["#F6D0B1", "#E8B48F", "#C68A62", "#8D5A3B", "#5E3B26"];


  const $ = id => document.getElementById(id);
  const screen = $("screen"), stage = $("stage"), hud = $("hud"), timerEl = $("timer"), muteBtn = $("mute");
  const pips = Array.from({ length: ROUND }, () => $("pips").appendChild(document.createElement("i")));
  const helpPanel = $("helpPanel");
  lockGameViewport(screen, stage, helpPanel);
  $("helpClose").onclick = () => { helpPanel.hidden = true; const s = $("help"); if (s) s.focus({ preventScroll: true }); };
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fr = (n, d = 0) => new Intl.NumberFormat("fr-FR", { maximumFractionDigits: d, minimumFractionDigits: d }).format(n);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  /* ---------- Pixel art ---------- */
  function avatar(look, size = 16) {
    const c = document.createElement("canvas");
    c.width = c.height = size;
    const g = c.getContext("2d");
    const px = (x, y, col, w = 1, h = 1) => { g.fillStyle = col; g.fillRect(x, y, w, h); };
    const skin = SKIN[look.skin], hair = look.hair;
    // corps
    px(2, 12, look.shirt, 12, 4);
    px(2, 12, "rgba(0,0,0,.18)", 1, 4); px(13, 12, "rgba(0,0,0,.18)", 1, 4);
    px(6, 11, skin, 4, 2); px(7, 13, skin, 2, 1);
    // tête
    px(4, 3, skin, 8, 8);
    [[4, 3], [11, 3], [4, 10], [11, 10]].forEach(([x, y]) => g.clearRect(x, y, 1, 1));
    // cheveux
    if (look.style === "short" || look.style === "long" || look.style === "bun") {
      px(5, 2, hair, 6, 1); px(4, 3, hair, 8, 1); px(4, 4, hair, 1, 2); px(11, 4, hair, 1, 2); px(5, 4, hair, 2, 1);
    }
    if (look.style === "long") { px(3, 4, hair, 1, 8); px(12, 4, hair, 1, 8); px(4, 6, hair, 1, 6); px(11, 6, hair, 1, 6); }
    if (look.style === "bun") { px(6, 0, hair, 4, 2); }
    if (look.style === "bald") { px(4, 5, hair, 1, 3); px(11, 5, hair, 1, 3); }
    // visage
    px(6, 7, "#1A1430"); px(9, 7, "#1A1430");
    px(5, 6, "rgba(0,0,0,.25)", 2, 1); px(9, 6, "rgba(0,0,0,.25)", 2, 1);
    px(7, 9, "rgba(120,30,40,.7)", 2, 1);
    if (look.glasses) {
      g.fillStyle = "#1A1430";
      g.fillRect(5, 6, 3, 1); g.fillRect(8, 6, 3, 1); g.fillRect(5, 8, 3, 1); g.fillRect(8, 8, 3, 1);
      g.fillRect(5, 7, 1, 1); g.fillRect(10, 7, 1, 1);
    }
    return c;
  }

  const PLAYER = { skin: 1, hair: "#2A1B12", style: "short", shirt: "#FFC94A" };

  function robot() {
    const c = document.createElement("canvas");
    c.width = c.height = 16;
    const g = c.getContext("2d");
    const px = (x, y, col, w = 1, h = 1) => { g.fillStyle = col; g.fillRect(x, y, w, h); };
    px(7, 0, "#FF4D6A", 2, 1); px(7, 1, "#8C93C9", 2, 2);         // antenne
    px(3, 3, "#B9C2EE", 10, 8); px(3, 10, "#8C93C9", 10, 1);      // tête
    px(2, 5, "#8C93C9", 1, 3); px(13, 5, "#8C93C9", 1, 3);        // oreilles
    px(4, 5, "#131A40", 8, 3);                                     // visière
    px(5, 6, "#43C6F5", 2, 1); px(9, 6, "#43C6F5", 2, 1);          // yeux
    for (let x = 5; x < 11; x += 2) px(x, 9, "#131A40");           // grille
    px(6, 11, "#8C93C9", 4, 1);                                    // cou
    px(2, 12, "#33408A", 12, 4); px(6, 13, "#43C6F5", 4, 2);       // corps
    return c;
  }

  function icon(rows, palette) {
    const w = rows[0].length, h = rows.length;
    let r = "";
    rows.forEach((row, y) => [...row].forEach((ch, x) => { if (palette[ch]) r += `<rect x="${x}" y="${y}" width="1" height="1" fill="${palette[ch]}"/>`; }));
    return `<svg viewBox="0 0 ${w} ${h}" shape-rendering="crispEdges" aria-hidden="true">${r}</svg>`;
  }
  const BILL = icon([
    "........",
    "mmmmmmmm",
    "m.mmmm.m",
    "mmm..mmm",
    "mmm..mmm",
    "m.mmmm.m",
    "mmmmmmmm",
    "........"], { m: "#4BE3A0" });
  const COINS = icon([
    "..gggg..",
    ".yyyyyy.",
    "..gggg..",
    ".yyyyyy.",
    "..gggg..",
    ".yyyyyy.",
    "..gggg..",
    "........"], { g: "#C9921C", y: "#FFC94A" });
  const SOUND_ON = icon([
    "...s....", "..ss..s.", "ssss.s.s", "ssss.s.s", "ssss.s.s", "ssss.s.s", "..ss..s.", "...s...."], { s: "#8C93C9" });
  const SOUND_OFF = icon([
    "...s....", "..ss....", "ssss.s.s", "ssss..s.", "ssss..s.", "ssss.s.s", "..ss....", "...s...."], { s: "#8C93C9" });

  /* ---------- Son 8 bits ---------- */
  let ctx = null, muted = false;
  try { muted = localStorage.getItem("111bis-mute") === "1"; } catch (e) {}
  function setMuteIcon() { muteBtn.innerHTML = muted ? SOUND_OFF : SOUND_ON; muteBtn.setAttribute("aria-label", muted ? "Activer le son" : "Couper le son"); }
  muteBtn.onclick = () => { muted = !muted; setMuteIcon(); try { localStorage.setItem("111bis-mute", muted ? "1" : "0"); } catch (e) {} };
  setMuteIcon();
  function beep(freqs, dur = .08, type = "square", vol = .06) {
    if (muted) return;
    try {
      ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
      let t = ctx.currentTime;
      freqs.forEach(f => {
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.type = type; o.frequency.value = f;
        g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(.0001, t + dur);
        o.connect(g).connect(ctx.destination); o.start(t); o.stop(t + dur);
        t += dur * .9;
      });
    } catch (e) {}
  }
  const sfx = {
    tick: () => beep([440], .1),
    go: () => beep([880], .25),
    ok: () => beep([660, 990], .07),
    ko: () => beep([180, 120], .12, "sawtooth", .07),
    end: () => beep([523, 659, 784, 1046], .11),
    roll: () => beep([1200], .02, "square", .025)
  };

  /* ---------- Partie ---------- */
  let clients = [], answers = [], idx = 0, t0 = 0, elapsed = 0, raf = 0, busy = false, playing = false;

  const shuffle = a => { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const clock = ms => { const s = ms / 1000, m = Math.floor(s / 60); return String(m).padStart(2, "0") + ":" + (s - m * 60).toFixed(1).padStart(4, "0"); };
  function loop() { elapsed = performance.now() - t0; timerEl.textContent = clock(elapsed); raf = requestAnimationFrame(loop); }
  const wait = ms => new Promise(r => setTimeout(r, reduce ? Math.min(ms, 300) : ms));

  function title() {
    playing = false; cancelAnimationFrame(raf);
    if (stopBoard) { stopBoard(); stopBoard = null; }
    hud.hidden = true;
    stage.innerHTML = `
      <div class="title">
        <h1 class="logo"><b>MIA</b><span>RECOMMANDER</span></h1>
        <div class="duel">
          <div class="fighter"><span id="p1"></span><strong>VOUS</strong></div>
          <div class="vs-tag">VS</div>
          <div class="fighter mia"><span id="p2"></span><strong>MIA</strong></div>
        </div>
        <div class="brief">
          <p class="ask">Saurez-vous prédire si le client va augmenter son versement 111bis&nbsp;?</p>
          <div class="cap"><s>3 200 €</s><span>▸</span><b>4 500 €</b></div>
        </div>
        <div class="actions">
          <button class="start" id="start"><span>START</span></button>
          <button class="help-btn" id="help">111BIS ?</button>
        </div>
      </div>`;
    $("p1").replaceWith(avatar(PLAYER));
    $("p2").replaceWith(robot());
    $("start").onclick = mission;
    $("help").onclick = () => { helpPanel.hidden = false; $("helpClose").focus({ preventScroll: true }); };
    $("start").focus({ preventScroll: true });
  }

  /* ---------- Trigramme : une seule partie chacun ---------- */
  let player = null, currentGame = null, confirmedResult = null;
  const cleanTri = v => v.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase().replace(/[^A-Z]/g, "").slice(0, 3);
  async function claim(tri) {
    try { currentGame = await api.post("claim", { tri }); return "ok"; }
    catch (error) { return error.code || "error"; }
  }
  const MESSAGES = {
    played: "Vous avez déjà joué.",
    limited: "Trop de tentatives. Réessayez dans une minute.",
    error: "Connexion indisponible. Réessayez.",
    unavailable: "Le jeu est momentanément indisponible.",
    forbidden: "Rechargez la page pour réessayer.",
    expired: "La partie a expiré. Rechargez la page."
  };

  function mission() {
    hud.hidden = true;
    stage.innerHTML = `
      <section class="mission">
        <h2>MISSION</h2>
        <div class="lineup" id="lineup"></div>
        <p>Ces ${ROUND} clients vont-ils augmenter leur versement 111bis&nbsp;?</p>
        <div class="controls"><kbd class="k-no">◀ NON</kbd><kbd class="k-yes">OUI ▶</kbd></div>
        <div class="race">Le plus vite possible<small>1 seule partie</small></div>
        <button class="start" id="ok"><span>J'AI COMPRIS</span></button>
      </section>`;
    const lineup = $("lineup");
    ["MIA", "JEU", "OUI", "NON", "TOP", "GOO"].forEach(tri => lineup.appendChild(avatar(lookFor(tri))));
    $("ok").onclick = entry;
    $("ok").focus({ preventScroll: true });
  }

  function entry() {
    hud.hidden = true;
    stage.innerHTML = `
      <form class="entry" id="entry" novalidate>
        <p class="entry-label">TRIGRAMME</p>
        <label class="slots" for="tri">
          <span></span><span></span><span></span>
          <input id="tri" maxlength="3" autocomplete="off" autocorrect="off" autocapitalize="characters" spellcheck="false" aria-label="Trigramme, 3 lettres">
        </label>
        <p class="entry-msg" id="msg" role="status"></p>
        <button class="start" id="go" disabled><span>GO</span></button>
        <button type="button" class="link" id="back">◀ RETOUR</button>
      </form>`;
    const input = $("tri"), slots = [...stage.querySelectorAll(".slots span")], go = $("go"), msg = $("msg");
    const paint = () => {
      const v = cleanTri(input.value);
      if (input.value !== v) input.value = v;
      slots.forEach((s, i) => { s.textContent = v[i] || ""; s.classList.toggle("cur", i === v.length); });
      go.disabled = v.length !== 3;
      msg.textContent = "";
    };
    input.addEventListener("input", paint);
    paint();
    input.focus({ preventScroll: true });
    $("back").onclick = mission;
    $("entry").addEventListener("submit", async e => {
      e.preventDefault();
      const tri = cleanTri(input.value);
      if (tri.length !== 3) return;
      go.disabled = true; input.disabled = true;
      go.firstElementChild.textContent = "…";
      const r = await claim(tri);
      if (r === "ok") { player = tri; countdown(); return; }
      msg.textContent = r === "taken" ? `${tri} a déjà joué.` : (MESSAGES[r] || MESSAGES.error);
      if (r === "taken") sfx.ko();
      go.firstElementChild.textContent = "GO";
      input.disabled = false; go.disabled = false;
      input.focus({ preventScroll: true });
    });
  }

  // Avatar stable déduit du trigramme
  function lookFor(tri) {
    let h = 7;
    for (const ch of tri) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    const pick = (arr, k) => arr[(h >>> k) % arr.length];
    return {
      skin: (h >>> 2) % SKIN.length,
      hair: pick(["#2A1B12", "#6B3A1F", "#120C08", "#B5651D", "#E2B04A", "#8F8F99"], 5),
      style: pick(["short", "long", "bun", "short"], 9),
      shirt: pick(["#4B6BFF", "#E3683A", "#2E8B57", "#8A4BFF", "#C2304F", "#43C6F5", "#FFC94A"], 12),
      glasses: (h >>> 16) % 4 === 0
    };
  }

  let stopBoard = null;
  function leaderboard() {
    hud.hidden = true;
    stage.innerHTML = `
      <section class="lb">
        <h2>CLASSEMENT</h2>
        <div class="podium" id="podium"></div>
        <ol class="ranks" id="ranks"></ol>
        <p class="lb-msg" id="lbmsg">Chargement…</p>
        <button class="start" id="home"><span>ACCUEIL</span></button>
      </section>`;
    $("home").onclick = () => { player = null; title(); };
    $("home").focus({ preventScroll: true });
    const msg = $("lbmsg");
    let active = true, poll;
    stopBoard = () => { active = false; clearTimeout(poll); };
    const refresh = async () => {
      try {
        const data = await api.get("leaderboard");
        if (active && $("podium")) renderBoard(data.rows);
      } catch (error) {
        if (active && $("lbmsg")) msg.textContent = "Classement indisponible. Nouvelle tentative en cours…";
      }
      if (active) poll = setTimeout(refresh, 10000);
    };
    refresh();
  }

  function renderBoard(rows) {
    const podium = $("podium"), ranks = $("ranks"), msg = $("lbmsg");
    if (!podium) return;
    const ratio = r => r.score / (r.total || 5);
    rows.sort((a, b) => ratio(b) - ratio(a) || a.timeMs - b.timeMs);
    const me = rows.findIndex(r => r.tri === player);
    msg.textContent = me >= 0 ? `${player} : ${me + 1}e sur ${rows.length}` : rows.length ? `${rows.length} joueur${rows.length > 1 ? "s" : ""}` : "Aucun joueur pour l'instant.";

    podium.innerHTML = "";
    [1, 0, 2].forEach(i => {
      const r = rows[i], step = document.createElement("div");
      step.className = `step p${i + 1}` + (!r ? " empty" : "") + (i === me ? " me" : "");
      if (r) {
        step.innerHTML = `<span class="tri">${esc(r.tri)}</span><span class="sc">${r.score}/${r.total || 5} · ${clock(r.timeMs)}</span><div class="block">${i + 1}</div>`;
        step.prepend(avatar(lookFor(r.tri)));
      }
      podium.appendChild(step);
    });

    ranks.innerHTML = "";
    const line = i => {
      const r = rows[i], li = document.createElement("li");
      li.className = i === me ? "me" : "";
      li.innerHTML = `<span class="r">${i + 1}</span><span class="av"></span><b>${esc(r.tri)}</b><span>${r.score}/${r.total || 5}</span><span>${clock(r.timeMs)}</span>`;
      li.querySelector(".av").replaceWith(avatar(lookFor(r.tri)));
      ranks.appendChild(li);
    };
    for (let i = 3; i < Math.min(rows.length, 10); i++) line(i);
    if (me >= 10) { const gap = document.createElement("li"); gap.className = "gap"; gap.textContent = "…"; ranks.appendChild(gap); line(me); }
  }

  async function countdown() {
    clients = currentGame.clients; answers = []; idx = 0; elapsed = 0; confirmedResult = null;
    pips.forEach(p => p.className = "");
    timerEl.textContent = clock(0);
    hud.hidden = false;
    for (const n of ["3", "2", "1"]) {
      stage.innerHTML = `<div class="count"><span>${n}</span></div>`;
      sfx.tick();
      await wait(550);
    }
    try { await api.post("start", {}); }
    catch (error) { entry(); $("msg").textContent = MESSAGES[error.code] || MESSAGES.error; return; }
    sfx.go();
    t0 = performance.now(); playing = true;
    raf = requestAnimationFrame(loop);
    showCard();
  }

  function showCard() {
    const c = clients[idx];
    pips.forEach((p, i) => p.classList.toggle("now", i === idx));
    const pct = Math.min(c.paid / NEW_CAP, 1) * 100;
    stage.innerHTML = `
      <div class="deck">
        <article class="card enter" id="card">
          <div class="stamp yes">OUI</div><div class="stamp no">NON</div>
          <div class="who"><span id="face"></span><div><h2>${esc(c.name)}, ${c.age}</h2><p>${esc(c.job)}</p></div></div>
          <div class="stats">
            <div class="stat">${BILL}<b>${fr(c.income / 1000)} k€</b><small>/an</small></div>
            <div class="stat">${COINS}<b>${fr(c.saving)} €</b><small>/mois</small></div>
          </div>
          <div class="gauge">
            <div class="gauge-top"><span>111BIS</span><b>${fr(c.paid)} €</b></div>
            <div class="bar"><div class="zone"></div><div class="fill" style="width:${pct}%"></div></div>
            <div class="ticks"><span class="t-old">3200</span><span class="t-new">4500</span></div>
          </div>
          <div class="tag">${esc(c.tag)}</div>
        </article>
      </div>
      <div class="pad">
        <button class="no" id="bno" aria-label="N'augmentera pas">◀ NON</button>
        <button class="yes" id="byes" aria-label="Augmentera">OUI ▶</button>
      </div>`;
    $("face").replaceWith(avatar(c.look));
    $("bno").onclick = () => choose(false);
    $("byes").onclick = () => choose(true);
    drag($("card"));
    busy = false;
  }

  function drag(card) {
    const yesS = card.querySelector(".stamp.yes"), noS = card.querySelector(".stamp.no");
    let x0 = null, dx = 0;
    const paint = () => {
      card.style.transform = `translateX(${dx}px) rotate(${dx / 18}deg)`;
      yesS.style.opacity = Math.max(0, Math.min(1, dx / 90));
      noS.style.opacity = Math.max(0, Math.min(1, -dx / 90));
    };
    card.addEventListener("pointerdown", e => { if (busy) return; x0 = e.clientX; dx = 0; card.classList.remove("back", "enter"); card.setPointerCapture(e.pointerId); });
    card.addEventListener("pointermove", e => { if (x0 === null) return; dx = e.clientX - x0; paint(); });
    const up = () => {
      if (x0 === null) return;
      x0 = null;
      if (Math.abs(dx) > 90) choose(dx > 0, dx);
      else { card.classList.add("back"); dx = 0; paint(); }
    };
    card.addEventListener("pointerup", up);
    card.addEventListener("pointercancel", up);
  }

  async function choose(yes, fromDx) {
    if (busy || !playing) return;
    busy = true;
    let response;
    try { response = await api.post("answer", { index: idx, yes }); }
    catch (error) {
      busy = false;
      let status = $("networkStatus");
      if (!status) { status = document.createElement("p"); status.id = "networkStatus"; status.setAttribute("role", "status"); stage.appendChild(status); }
      status.textContent = MESSAGES[error.code] || "Réponse non enregistrée. Réessayez le bouton.";
      return;
    }
    const ok = response.correct;
    confirmedResult = response.result;
    answers.push(yes);
    const card = $("card");
    const btn = $(yes ? "byes" : "bno");
    btn.classList.add("hit");
    card.querySelector(`.stamp.${yes ? "yes" : "no"}`).style.opacity = 1;
    card.classList.remove("back", "enter");
    card.classList.add("fly");
    card.style.transform = `translateX(${yes ? 520 : -520}px) rotate(${yes ? 24 : -24}deg)`;

    pips[idx].className = ok ? "ok" : "ko";
    const pop = document.createElement("div");
    pop.className = "pop " + (ok ? "ok" : "ko");
    pop.textContent = ok ? "✓" : "✕";
    stage.appendChild(pop);
    if (ok) sfx.ok(); else { sfx.ko(); if (!reduce) { screen.classList.remove("shake"); void screen.offsetWidth; screen.classList.add("shake"); } }

    idx++;
    if (idx === ROUND) {
      elapsed = confirmedResult.timeMs;
      cancelAnimationFrame(raf);
      timerEl.textContent = clock(elapsed);
      playing = false;
      await wait(500);
      result();
    } else {
      await wait(260);
      showCard();
    }
  }

  function result() {
    hud.hidden = true;
    const perClient = elapsed / 1000 / ROUND;
    // Time and score have already been validated and saved by the server.
    const hours = perClient * PORTFOLIO / 3600, days = hours / 8;
    const useDays = days >= 1, target = useDays ? days : hours;
    const unit = useDays ? (Math.round(days) > 1 ? "JOURS" : "JOUR") : "HEURES";

    stage.innerHTML = `
      <section class="finale" id="finale">
        <p class="f-line">Pour tous les clients du foyer ciblé,<br>ça vous aurait pris</p>
        <div class="days"><span id="roll">0</span> ${unit}</div>
        <div class="f-mia" id="fmia" hidden>
          <span id="bot"></span>
          <p>MIA l'a fait en quelques secondes.</p>
          <strong class="wow">TROP FORT !</strong>
          <button class="start" id="next"><span>CLASSEMENT ▶</span></button>
        </div>
      </section>`;
    $("bot").replaceWith(robot());
    $("next").onclick = leaderboard;

    // Compteur qui défile, puis entrée de MIA
    const roll = $("roll"), start = performance.now(), dur = reduce ? 0 : 1800;
    let lastSound = 0;
    const step = now => {
      if (!$("finale")) return;
      const p = dur ? Math.min(1, (now - start) / dur) : 1;
      const v = target * (1 - Math.pow(1 - p, 3));
      roll.textContent = useDays ? fr(Math.round(v)) : fr(v, 1);
      if (p < 1) {
        if (now - lastSound > 70) { sfx.roll(); lastSound = now; }
        requestAnimationFrame(step);
      } else setTimeout(revealMia, reduce ? 0 : 700);
    };
    requestAnimationFrame(step);
  }

  function revealMia() {
    const box = $("fmia");
    if (!box) return;
    box.hidden = false;
    sfx.end();
    $("next").focus({ preventScroll: true });
    setTimeout(() => { if ($("finale")) leaderboard(); }, 4500);
  }

  document.addEventListener("keydown", e => {
    if (playing && !busy) {
      if (e.key === "ArrowRight") { e.preventDefault(); choose(true); }
      if (e.key === "ArrowLeft") { e.preventDefault(); choose(false); }
    }
  });

  title();
})();

