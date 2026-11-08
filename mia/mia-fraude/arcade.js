/* Original Recommander pixel characters, recolored for Fraude. */
const SKIN = ["#F6D0B1", "#E8B48F", "#C68A62", "#8D5A3B", "#5E3B26"];
export function avatar(look, size = 16) {
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

export const PLAYER = { skin: 1, hair: "#2A1B12", style: "short", shirt: "#ffc45f" };

export function robot() {
    const c = document.createElement("canvas");
    c.width = c.height = 16;
    const g = c.getContext("2d");
    const px = (x, y, col, w = 1, h = 1) => { g.fillStyle = col; g.fillRect(x, y, w, h); };
    px(7, 0, "#ff6340", 2, 1); px(7, 1, "#bca88e", 2, 2);         // antenne
    px(3, 3, "#ffe2bb", 10, 8); px(3, 10, "#bca88e", 10, 1);      // tête
    px(2, 5, "#bca88e", 1, 3); px(13, 5, "#bca88e", 1, 3);        // oreilles
    px(4, 5, "#130d09", 8, 3);                                     // visière
    px(5, 6, "#ff913d", 2, 1); px(9, 6, "#ff913d", 2, 1);          // yeux
    for (let x = 5; x < 11; x += 2) px(x, 9, "#130d09");           // grille
    px(6, 11, "#bca88e", 4, 1);                                    // cou
    px(2, 12, "#78401d", 12, 4); px(6, 13, "#ff913d", 4, 2);       // corps
    return c;
  }


export function lookFor(tri) {
  const seed = [...tri].reduce((a,c) => a*31+c.charCodeAt(0), 7);
  return {skin:seed%5, hair:["#332018","#baa58b","#13100e"][seed%3],
    style:["short","long","bun","bald"][seed%4], shirt:["#ffc45f","#ff913d","#bde5af","#d9afec"][seed%4],glasses:seed%3===0};
}
export function sound() {
  let ctx, muted = false;
  try { muted = localStorage.getItem("mia-fraud-mute") === "1"; } catch {}
  return {
    get muted() { return muted; },
    toggle() { muted = !muted; try { localStorage.setItem("mia-fraud-mute",muted?"1":"0"); } catch {} },
    play(kind) {
      if (muted) return;
      try {
        ctx ||= new (window.AudioContext || window.webkitAudioContext)();
        ctx.resume();
        let t = ctx.currentTime;
        const notes = {ok:[660,990],ko:[180,120],end:[523,659,784,1046],tick:[440],go:[880]}[kind] || [440];
        notes.forEach(f => {
          const o=ctx.createOscillator(),g=ctx.createGain();o.type="square";o.frequency.value=f;
          g.gain.setValueAtTime(.035,t);g.gain.exponentialRampToValueAtTime(.0001,t+.1);
          o.connect(g).connect(ctx.destination);o.start(t);o.stop(t+.1);t+=.09;
        });
      } catch {}
    }
  };
}
