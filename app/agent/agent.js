// MIA Agent : ciel tramé en WebGL autour d'un nuage qui suit le contenu, et formulaire « Je suis intéressé ».
const $ = (id) => document.getElementById(id);
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- Icône parapluie en matrice de points ---------- */
const UMBRELLA = ["....#....", "..#####..", ".#######.", "#########", "#.#.#.#.#", "....#....", "....#....", "..#.#....", "...#....."];
function drawLed(cv, rows, s) {
  const n = rows.length, dpr = 2, size = n * s;
  cv.width = size * dpr; cv.height = size * dpr; cv.style.width = size + "px"; cv.style.height = size + "px";
  const x = cv.getContext("2d"); x.scale(dpr, dpr);
  rows.forEach((r, j) => [...r].forEach((ch, i) => {
    x.fillStyle = ch === "#" ? "#3d6fd6" : "#e3ebfb";
    x.beginPath(); x.arc(i * s + s / 2, j * s + s / 2, s * .42, 0, Math.PI * 2); x.fill();
  }));
}
drawLed($("logo"), UMBRELLA, Math.max(8, Math.min(13, Math.round(innerWidth / 110))));

/* ---------- Ciel et nuages en trame de points ---------- */
const VERT = "attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}";
const FRAG = `precision highp float;
uniform vec2 uRes; uniform float uTime, uK;
uniform vec4 uZone; uniform vec3 uB[3];
float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float n(vec2 p){vec2 i=floor(p),f=fract(p);vec2 u=f*f*(3.-2.*f);
  return mix(mix(h(i),h(i+vec2(1,0)),u.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),u.x),u.y);}
float fbm(vec2 p){float v=0.,a=.5;for(int i=0;i<5;i++){v+=a*n(p);p=p*2.03+vec2(1.7,9.2);a*=.5;}return v;}
float b2(vec2 a){a=floor(a);return fract(dot(a,vec2(.5,a.y*.75)));}
float b4(vec2 a){return b2(.5*a)*.25+b2(a);}
float b8(vec2 a){return b4(.5*a)*.25+b2(a);}
float sdBox(vec2 p,vec2 b){vec2 d=abs(p)-b;return length(max(d,0.))+min(max(d.x,d.y),0.);}
void main(){
  float cell=7.*uK;
  vec2 fc=vec2(gl_FragCoord.x,uRes.y-gl_FragCoord.y);
  vec2 ci=floor(fc/cell), cc=(ci+.5)*cell;
  vec2 uv=cc/(1080.*uK);
  float t=uTime;
  float edge=fbm(uv*5.+vec2(t*.025,t*.01));
  float bil=abs(fbm(uv*13.+vec2(-t*.02,0.))*2.-1.);
  vec2 rc=(uZone.xy+uZone.zw)*.5, rh=max((uZone.zw-uZone.xy)*.5,vec2(0.));
  float sd=sdBox(uv-rc,rh);
  float m=.015+edge*.12+bil*.05-sd;
  float low=0.;
  for(int i=0;i<3;i++){ vec3 b=uB[i]; if(b.z<=.001) continue;
    float d=length((uv-b.xy)*vec2(.75,1.25))/b.z;
    float mb=(1.-d)*b.z+(edge-.5)*.22+bil*.07;
    if(mb>m){ m=mb; low=clamp((uv.y-b.y)/b.z+.05,0.,1.); }
  }
  float tone;
  if(m<=0.){
    float s=fbm(uv*vec2(1.6,6.)+vec2(t*.012,0.));
    float s2=fbm(uv*vec2(2.5,8.)+vec2(5.2-t*.01,1.3));
    tone=.86+.14*smoothstep(.4,.6,s);
    tone=mix(tone,.42,smoothstep(.6,.64,s2));
  } else {
    float e=1.-smoothstep(0.,.03,m);
    tone=e*.5 + smoothstep(.45,.72,fbm(uv*8.+3.1))*low*.6;
    if(sd<.015) tone=0.;
  }
  float on=step(b8(ci),tone-.001);
  float r=length(fc-cc)/cell;
  float dotm=on*(1.-smoothstep(.44,.5,r));
  gl_FragColor=vec4(mix(vec3(1.),vec3(.239,.435,.839),dotm),1.);
}`;

const sky = $("sky");
const gl = sky.getContext("webgl", { antialias: false });
let U = {}, zone = [0, 0, 0, 0], target = null, blobs = new Float32Array(9);
if (gl) {
  const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; };
  const pr = gl.createProgram();
  gl.attachShader(pr, sh(gl.VERTEX_SHADER, VERT)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, FRAG));
  gl.linkProgram(pr); gl.useProgram(pr);
  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(pr, "p"); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  ["uRes", "uTime", "uK", "uZone", "uB"].forEach((k) => (U[k] = gl.getUniformLocation(pr, k)));
} else {
  document.body.style.background = "#fff";
}

// Le nuage blanc épouse la carte de contenu ; deux petits nuages décorent les côtés libres.
function layout() {
  const dpr = Math.min(2, devicePixelRatio || 1);
  sky.width = Math.round(innerWidth * dpr); sky.height = Math.round(innerHeight * dpr);
  const H = innerHeight, W = innerWidth / H, r = $("card").getBoundingClientRect(), pad = Math.min(.06, 34 / H);
  target = [r.left / H - pad, r.top / H - pad, r.right / H + pad, r.bottom / H + pad];
  if (W > 1.15) blobs.set([W - .2, .2, .16, W - .3, .86, .18, .12, .92, .11]);
  else blobs.set([W * .82, .09, .1, W * .2, .93, .11, 0, 0, 0]);
  if (!zone[2]) zone = target.map((v, i) => v + [-.04, .03, .04, -.03][i]);
}
addEventListener("resize", layout);
layout();
document.fonts && document.fonts.ready.then(layout);

let last = 0;
function frame(ts) {
  requestAnimationFrame(frame);
  if (!gl || ts - last < 33) return; last = ts;
  zone = zone.map((v, i) => v + (target[i] - v) * .12);
  gl.viewport(0, 0, sky.width, sky.height);
  gl.uniform2f(U.uRes, sky.width, sky.height);
  gl.uniform1f(U.uTime, reduce ? 0 : ts / 1000);
  gl.uniform1f(U.uK, sky.height / 1080);
  gl.uniform4f(U.uZone, ...zone);
  gl.uniform3fv(U.uB, blobs);
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
}
requestAnimationFrame(frame);

/* ---------- Je suis intéressé ---------- */
const API = "/mia-agent/api/";
const ui = { button: $("interest"), form: $("form"), input: $("tri"), send: $("send"), done: $("done"), msg: $("msg") };
let csrf = "";

function showDone(tri) {
  ui.button.hidden = true; ui.form.hidden = true;
  $("doneTri").textContent = tri; ui.done.hidden = false; ui.msg.textContent = "";
  requestAnimationFrame(layout);
}

async function session() {
  const res = await fetch(API + "session", { credentials: "same-origin", cache: "no-store" });
  if (!res.ok) throw new Error("session");
  const data = await res.json();
  csrf = data.csrf;
  if (data.tri) showDone(data.tri);
  ui.button.disabled = false;
}
session().catch(() => { ui.button.disabled = false; ui.msg.textContent = "Connexion impossible pour le moment."; });

ui.button.addEventListener("click", () => {
  ui.button.hidden = true; ui.form.hidden = false; ui.input.focus(); requestAnimationFrame(layout);
});
ui.input.addEventListener("input", () => {
  const clean = ui.input.value.toUpperCase().replace(/[^A-Z]/g, "").slice(0, 3);
  if (clean !== ui.input.value) ui.input.value = clean;
  ui.msg.textContent = "";
});

const ERRORS = { invalid_trigram: "Trois lettres, sans accent.", limited: "Trop d'essais, réessayez dans une minute.",
  forbidden: "Session expirée, rechargez la page." };
ui.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const tri = ui.input.value;
  if (!/^[A-Z]{3}$/.test(tri)) { ui.msg.textContent = ERRORS.invalid_trigram; ui.input.focus(); return; }
  ui.send.disabled = true;
  try {
    if (!csrf) await session();
    const res = await fetch(API + "interest", {
      method: "POST", credentials: "same-origin", cache: "no-store",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({ tri }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "unavailable");
    showDone(data.tri);
  } catch (err) {
    ui.msg.textContent = ERRORS[err.message] || "Connexion impossible, réessayez.";
  } finally {
    ui.send.disabled = false;
  }
});
