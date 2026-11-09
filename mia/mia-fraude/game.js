import { api } from "./api.js";
import { lockGameViewport } from "./viewport.js";
import { avatar, documents, PLAYER, lookFor, sound } from "./arcade.js";
import { imageRect, imagePoint, swipeDecision } from "./geometry.js";

const $=id=>document.getElementById(id);
const screen=$("screen"),stage=$("stage"),hud=$("hud"),notice=$("notice"),viewer=$("viewer");
const pips=Array.from({length:6},()=>$("pips").appendChild(document.createElement("i")));
const sfx=sound(),reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
let preview=false;
let state=null, ownTri=null, panel=0, busy=false, raf=0, receivedAt=0, boardInterval=null, mode="title";
const esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const clock=ms=>{const s=ms/1000;return `${String(Math.floor(s/60)).padStart(2,"0")}:${(s%60).toFixed(1).padStart(4,"0")}`;};
lockGameViewport(screen,stage,$("helpPanel"));
function muteIcon() { $("mute").textContent=sfx.muted?"♪×":"♪";$("mute").setAttribute("aria-label",sfx.muted?"Activer le son":"Couper le son"); }
$("mute").onclick=()=>{sfx.toggle();muteIcon();};muteIcon();
$("helpClose").onclick=()=>{$("helpPanel").hidden=true;$("help")?.focus({preventScroll:true});};
let viewerZoom = 1;
$("viewerClose").onclick=()=>viewer.close();
$("viewerZoom").onclick=()=>setViewerZoom(viewerZoom===4?1:viewerZoom*2);
function setViewerZoom(value) {
  const media=$("zoomMedia");
  viewerZoom=value;
  media.classList.toggle("zoomed",value>1);
  media.style.setProperty("--zoom",String(value));
  media.scrollTop=0;media.scrollLeft=0;
  $("viewerZoom").textContent=`ZOOM ×${value}`;
  $("viewerZoom").setAttribute("aria-label",`Zoom : ${value} fois`);
}

viewer.addEventListener("click",e=>{if(e.target===viewer)viewer.close();});
// Mouse drag pans the inspector; touch devices use their native scroll gesture.
let pan=null;
$("zoomMedia").addEventListener("pointerdown",e=>{
  if(e.pointerType!=="mouse"||viewerZoom===1)return;
  pan={x:e.clientX,y:e.clientY,left:$("zoomMedia").scrollLeft,top:$("zoomMedia").scrollTop,moved:false};
});
$("zoomMedia").addEventListener("pointermove",e=>{
  if(!pan||!e.buttons){pan=null;return;}
  if(Math.hypot(e.clientX-pan.x,e.clientY-pan.y)>6)pan.moved=true;
  if(!pan.moved)return;
  e.preventDefault();
  $("zoomMedia").setPointerCapture(e.pointerId);
  $("zoomMedia").scrollLeft=pan.left+pan.x-e.clientX;
  $("zoomMedia").scrollTop=pan.top+pan.y-e.clientY;
  const surface=$("zoomMedia").querySelector(".image-surface");
  if(surface)surface.dataset.dragged="true";
});
$("zoomMedia").addEventListener("pointerup",()=>{pan=null;});
$("zoomMedia").addEventListener("pointercancel",()=>{pan=null;});

function clear() { screen.dataset.phase="";cancelAnimationFrame(raf);clearInterval(boardInterval);boardInterval=null;notice.replaceChildren();stage.replaceChildren();hud.hidden=true; }
function message(text) { notice.textContent=text; }
const errors={taken:"Ce trigramme est déjà pris. Essayez-en un autre.",played:"Une partie est déjà associée à ce navigateur.",expired:"La partie a expiré après 30 minutes. Rechargez la page pour recommencer.",limited:"Beaucoup de connexions. Réessayez dans une minute.",forbidden:"La session doit être actualisée. Rechargez la page.",too_fast:"Un peu trop rapide. Réessayez.",invalid_trigram:"Saisissez trois lettres de A à Z.",unavailable:"Le jeu est momentanément indisponible."};
async function run(action,retry) {
  if(busy)return;busy=true;screen.setAttribute("aria-busy","true");notice.replaceChildren();
  try { await action(); }
  catch(e) {
    message(errors[e.code]||"Connexion interrompue. Votre progression est conservée.");
    if(retry) {const b=document.createElement("button");b.className="retry";b.textContent="RÉESSAYER";b.onclick=retry;notice.appendChild(b);}
  } finally {busy=false;screen.removeAttribute("aria-busy");}
}
function send(route,body) {
  return run(async()=>{const previous=state;state=await api.post(route,body);receivedAt=performance.now();
    if(route==="locate" && previous?.phase!=="feedback")sfx.play(state.feedback.correct?"ok":"ko");
    render();},()=>send(route,body));
}
function title() {
  clear();mode="title";
  stage.innerHTML=`<div class="title"><h1 class="logo"><b>MIA</b><span>FRAUDE</span></h1>
    <div class="duel"><div class="fighter"><span id="player"></span><strong>VOUS</strong></div>
    <div class="vs-tag">VS</div><div class="fighter mia"><span id="bot"></span><strong>LES DOCUMENTS</strong></div></div>
    <div class="brief"><p class="ask">Saurez-vous repérer ce qui mérite une vérification ?</p><p class="title-meta">6 dossiers · votre sens de l’observation</p></div>
    <div class="actions"><button class="start" id="start"><span>START</span></button><button class="help-btn" id="help">RÈGLES</button></div>
    <button class="link" id="board">CLASSEMENT</button></div>`;
  $("player").replaceWith(avatar(PLAYER));$("bot").replaceWith(documents());
  $("start").onclick=begin;$("help").onclick=()=>{$("helpPanel").hidden=false;$("helpClose").focus();};$("board").onclick=leaderboard;
}
function begin() {
  return run(async()=>{
    const session=await api.session();
    preview=session.preview===true;
    if(session.participation) {
      if(session.participation.status==="done")return returning(session.participation.tri);
      state=await api.post("start",{});receivedAt=performance.now();return render();
    }
    entry();
  },begin);
}
function returning(tri) {
  ownTri=tri;clear();mode="returning";
  stage.innerHTML=`<div class="mission"><h2>PARTIE TERMINÉE</h2><div id="returnAvatar"></div><p>${esc(tri)}, vous avez déjà joué.</p><div class="race">Votre score est enregistré.</div><button class="start" id="board">CLASSEMENT</button>${preview?'<button class="help-btn" id="replay">NOUVEL ESSAI</button>':""}<button class="link" id="back">ACCUEIL</button></div>`;
  $("returnAvatar").replaceWith(avatar(lookFor(tri)));$("board").onclick=leaderboard;$("back").onclick=title;if(preview)$("replay").onclick=replay;
}
function replay() {
  return run(async()=>{await api.post("replay",{});state=null;ownTri=null;panel=0;entry();},replay);
}
function entry() {
  clear();mode="entry";
  stage.innerHTML=`<form class="entry" id="entry"><h2 class="entry-label">VOTRE TRIGRAMME</h2><p>Trois lettres pour le classement.<br>${preview?"Aperçu local : vous pouvez refaire un essai.":"Une partie par navigateur et par trigramme."}</p>
  <div class="slots"><span></span><span></span><span></span><input id="tri" aria-label="Trigramme de trois lettres" maxlength="3" pattern="[A-Za-z]{3}" autocomplete="off" autocapitalize="characters" spellcheck="false" required></div>
  <p class="entry-msg" id="entryMessage"></p><button class="start" id="claim" disabled>CONTINUER</button><button type="button" class="link" id="back">RETOUR</button></form>`;
  const input=$("tri"),slots=[...document.querySelectorAll(".slots span")];
  input.oninput=()=>{input.value=input.value.toUpperCase().replace(/[^A-Z]/g,"").slice(0,3);slots.forEach((s,i)=>{s.textContent=input.value[i]||"";s.classList.toggle("cur",i===input.value.length);});$("claim").disabled=input.value.length!==3;};
  $("entry").onsubmit=e=>{e.preventDefault();if(input.value.length!==3)return;
    run(async()=>{state=await api.post("claim",{tri:input.value});input.blur();mission();},()=>$("claim").click());};
  $("back").onclick=title;input.focus({preventScroll:true});
}
function mission() {
  clear();mode="mission";
  stage.innerHTML=`<div class="mission"><h2>À VOUS DE JOUER</h2><div class="lineup" id="lineup"></div><p>Cette pièce mérite-t-elle<br>une vérification ?</p><div class="controls"><kbd class="k-no">← NON</kbd><kbd class="k-yes">OUI →</kbd></div><p class="mission-detail">Consultez les autres pièces avec les onglets.<br>Après chaque décision, touchez l’indice<br>pour gagner un bonus.</p><div class="race">Décisions › bonus › chrono<small>Le bonus et la correction ne sont pas chronométrés.</small></div><button class="start" id="go">C’EST PARTI</button></div>`;
  for(let i=0;i<6;i++)$("lineup").appendChild(avatar(lookFor(String.fromCharCode(65+i)+"IA")));
  $("go").onclick=()=>run(async()=>{
    mode="count";
    for(const n of [3,2,1]) {stage.innerHTML=`<div class="count"><span>${n}</span></div>`;sfx.play("tick");await new Promise(r=>setTimeout(r,reduce?100:650));}
    sfx.play("go");state=await api.post("start",{});receivedAt=performance.now();render();
  },()=>send("start",{}));
}
function render() {
  clear();mode="case";hud.hidden=false;
  if(state.phase==="reserved")return mission();
  panel=Math.min(panel,state.case.panels.length-1);
  pips.forEach((p,i)=>{p.className=i<state.progress.length?(state.progress[i].correct?"ok":"ko"):i===state.index?"now":"";p.title=`Dossier ${i+1}`;});
  ownTri=state.tri;
  const phase=state.phase,f=state.feedback;screen.dataset.phase=phase;
  stage.innerHTML=`<header class="case-heading"><div class="case-number">DOSSIER ${state.index+1} / 6</div><h2>${esc(state.case.title)}</h2><p>${esc(state.case.context)}</p></header>
    <div class="evidence-tabs" id="tabs" role="tablist" aria-label="Pièces du dossier"></div>
    <div class="deck" id="deck"><div class="evidence enter" id="evidence"><div class="media" id="media"></div><div class="evidence-footer"><span id="caption"></span><button class="enlarge" id="enlarge" aria-label="Agrandir la pièce">⛶ AGRANDIR</button></div><span class="swipe-stamp" id="stamp"></span></div></div>
    <div id="phaseContent" class="phase-content"></div>`;
  tabs($("tabs"));displayMedia($("media"));$("enlarge").onclick=openViewer;
  const content=$("phaseContent");
  if(phase==="decision") {
    content.innerHTML=`<p class="question">Cette pièce mérite-t-elle une vérification ?</p><div class="pad"><button class="no" id="no"><small>←</small> PAS D’ALERTE</button><button class="yes" id="yes">À VÉRIFIER <small>→</small></button></div><p class="control-note">Glissez la pièce ou utilisez les boutons.</p>`;
    $("no").onclick=()=>decide(false);$("yes").onclick=()=>decide(true);bindSwipe();
  } else if(phase==="locate") {
    content.innerHTML=`<div class="bonus-prompt"><strong>BONUS D’OBSERVATION</strong><p>Touchez le détail qui motive votre décision.<br>Si tout concorde, touchez ce qui l’explique.</p></div><button class="help-btn skip" id="skip">PASSER LE BONUS →</button><p class="control-note">Chrono en pause · 1 essai · agrandissement disponible</p>`;
    $("skip").onclick=()=>send("locate",{index:state.index,skip:true});
  } else {
    content.innerHTML=`<div class="correction ${f.correct?"correct":"incorrect"}"><div class="correction-head"><strong>${f.correct?"✓ BONNE DÉCISION":"✕ DÉCISION À REVOIR"}</strong><span>${f.hit?"+1 INDICE":"BONUS : 0"}</span></div><b class="verdict">${f.review?"À vérifier":"Pas d’alerte sur ces pièces"}</b><p>${esc(f.explanation)}</p></div><button class="start next" id="next">${state.result?"MON SCORE":"DOSSIER SUIVANT →"}</button>`;
    $("next").onclick=()=>{if(state.result)finale();else {panel=0;send("next",{index:state.index});}};
  }
  tick();
}
function tick() {
  const ms=state.timeMs+(state.phase==="decision"?state.runningMs+performance.now()-receivedAt:0);
  $("timer").textContent=clock(ms);$("timer").classList.toggle("paused",state.phase!=="decision");
  if(mode==="case" && state.phase==="decision")raf=requestAnimationFrame(tick);
}
function tabs(container) {
  container.replaceChildren();state.case.panels.forEach((p,i)=>{
    const b=document.createElement("button");b.role="tab";b.setAttribute("aria-selected",i===panel?"true":"false");b.textContent=`${i+1}. ${p.label}`;
    b.onclick=()=>{if(busy)return;panel=i;setViewerZoom(1);tabs($("tabs"));displayMedia($("media"));if(viewer.open){tabs($("viewerTabs"));displayMedia($("zoomMedia"));$("viewerTitle").textContent=state.case.panels[panel].label;}};
    container.appendChild(b);
  });
}
function displayMedia(container) {
  const p=state.case.panels[panel];container.replaceChildren();
  const img=document.createElement("img");img.src=`/fraude/assets/${p.src}`;img.alt=p.alt;img.draggable=false;
  const surface=document.createElement("div");surface.className="image-surface";surface.appendChild(img);container.appendChild(surface);
  $("caption").textContent=p.label;
  if(state.phase==="feedback") {
    for(const z of state.feedback.zones.filter(z=>z.panel===panel)) {
      const box=document.createElement("div");box.className="hotspot";box.style.cssText=`left:${z.x*100}%;top:${z.y*100}%;width:${z.w*100}%;height:${z.h*100}%`;
      box.setAttribute("aria-label",z.label);box.title=z.label;surface.appendChild(box);
    }
    const sel=state.feedback.selection;
    if(sel?.panel===panel){const mark=document.createElement("span");mark.className="selected-point";mark.style.left=`${sel.x*100}%`;mark.style.top=`${sel.y*100}%`;surface.appendChild(mark);}
  }
  // The surface has the intrinsic aspect ratio; borders/letterboxing stay outside.
  img.onload=()=>{surface.style.aspectRatio=`${img.naturalWidth}/${img.naturalHeight}`;surface.style.setProperty("--ratio",img.naturalWidth/img.naturalHeight);};
  if(img.complete && img.naturalWidth)img.onload();
  if(state.phase==="locate") {
    surface.tabIndex=0;surface.setAttribute("role","button");surface.setAttribute("aria-label","Choisir un indice dans l’image. Flèches pour déplacer le repère, Entrée pour valider.");
    let cursor={x:.5,y:.5};
    surface.onclick=e=>{
      if(busy||surface.dataset.dragged==="true"){surface.dataset.dragged="false";return;}const rect=imageRect(surface.getBoundingClientRect(),img.naturalWidth,img.naturalHeight);
      const point=imagePoint(e.clientX,e.clientY,rect);if(point)selectClue(point);
    };
    // Scrolling in the magnifier must not submit the finger's final position.
    let down=null;
    surface.addEventListener("pointerdown",e=>{down={x:e.clientX,y:e.clientY};surface.dataset.dragged="false";});
    surface.addEventListener("pointermove",e=>{if(down&&Math.hypot(e.clientX-down.x,e.clientY-down.y)>8)surface.dataset.dragged="true";});
    surface.addEventListener("pointercancel",()=>{surface.dataset.dragged="true";down=null;});
    surface.addEventListener("pointerup",()=>{down=null;});
    surface.onkeydown=e=>{
      const d={ArrowLeft:[-.05,0],ArrowRight:[.05,0],ArrowUp:[0,-.05],ArrowDown:[0,.05]}[e.key];
      if(d){e.preventDefault();cursor={x:Math.max(0,Math.min(1,cursor.x+d[0])),y:Math.max(0,Math.min(1,cursor.y+d[1]))};
        let mark=surface.querySelector(".cursor");if(!mark){mark=document.createElement("i");mark.className="cursor";surface.appendChild(mark);}mark.style.left=`${cursor.x*100}%`;mark.style.top=`${cursor.y*100}%`;
      }else if(e.key==="Enter"||e.key===" "){e.preventDefault();selectClue(cursor);}
    };
  }
}
function selectClue(point) { if(viewer.open)viewer.close();send("locate",{index:state.index,panel,...point}); }
function openViewer() {
  setViewerZoom(1);
  $("viewerTitle").textContent=state.case.panels[panel].label;
  $("viewerHint").textContent=state.phase==="locate"?"Touchez directement l’indice dans l’image. Un seul essai.":state.phase==="feedback"?"Les zones encadrées expliquent la correction.":"Consultez les pièces avant de décider. Le chrono continue.";
  tabs($("viewerTabs"));displayMedia($("zoomMedia"));viewer.showModal();$("viewerClose").focus();
}
function decide(review) {
  if(mode!=="case"||state.phase!=="decision"||busy||viewer.open)return;
  sfx.play("tick");send("answer",{index:state.index,review});
}
function bindSwipe() {
  const deck=$("evidence");let drag=null;
  deck.onpointerdown=e=>{if(e.target.closest("button")||busy)return;drag={x:e.clientX,y:e.clientY,id:e.pointerId};deck.setPointerCapture(e.pointerId);};
  deck.onpointermove=e=>{
    if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;deck.style.transform=`translateX(${dx*.6}px) rotate(${dx*.025}deg)`;
    const decision=swipeDecision(dx,dy,deck.getBoundingClientRect().width),stamp=$("stamp");stamp.textContent=dx>0?"À VÉRIFIER":"PAS D’ALERTE";stamp.style.opacity=String(Math.min(1,Math.abs(dx)/85));stamp.classList.toggle("positive",decision===true);
  };
  const release=(e,cancelled=false)=>{
    if(!drag)return;const decision=swipeDecision(e.clientX-drag.x,e.clientY-drag.y,deck.getBoundingClientRect().width);drag=null;deck.style.transform="";$("stamp").style.opacity="0";
    if(!cancelled&&decision!==null)decide(decision);
  };
  deck.onpointerup=e=>release(e);deck.onpointercancel=e=>release(e,true);
}
function finale() {
  clear();mode="finale";sfx.play("end");const r=state.result;
  stage.innerHTML=`<div class="finale"><h2 class="entry-label">MISSION TERMINÉE</h2><div class="grade">${r.grade}</div><div id="finalAvatar"></div><div class="result-score"><span id="score">0</span><small> / 6 décisions</small></div><div class="result-extra"><b>${r.bonus}/6 indices</b><span>${clock(r.timeMs)}</span></div><div class="final-rank" id="finalRank" aria-live="polite">Chargement du classement…</div><p class="control-note">${esc(r.tri)} · temps des décisions uniquement</p><button class="start" id="board">VOIR LE PODIUM</button>${preview?'<button class="link" id="replay">NOUVEL ESSAI</button>':""}</div>`;
  $("finalAvatar").replaceWith(avatar(lookFor(r.tri)));$("board").onclick=leaderboard;if(preview)$("replay").onclick=replay;
  finalRank(r.tri);
  let begin=performance.now();function count(t){const progress=reduce?1:Math.min(1,(t-begin)/800);$("score").textContent=String(Math.round(r.score*progress));if(progress<1)raf=requestAnimationFrame(count);else document.querySelector(".result-score").classList.add("score-pulse");}raf=requestAnimationFrame(count);
}
async function finalRank(tri) {
  try {
    const {rows}=await api.get("leaderboard");
    if(mode!=="finale")return;
    const place=rows.findIndex(row=>row.tri===tri)+1;
    $("finalRank").innerHTML=place?`<b>${place===1?"1er":place+"e"}</b><span>sur ${rows.length} joueur${rows.length>1?"s":""}</span>`:"Votre score est enregistré.";
  } catch {if(mode==="finale")$("finalRank").textContent="Votre score est enregistré.";}
}
async function leaderboard() {
  clear();mode="board";
  stage.innerHTML=`<section class="lb"><h2>CLASSEMENT</h2><p class="board-rule">Décisions › indices › temps de décision</p><div class="podium" id="podium"></div><ol class="ranks" id="ranks"></ol><p class="lb-msg" id="boardMessage">Chargement…</p><button class="start" id="back">RETOUR</button></section>`;
  $("back").onclick=title;await refreshBoard();if(mode==="board")boardInterval=setInterval(refreshBoard,10000);
}
let boardFetching=false;
async function refreshBoard() {
  if(boardFetching)return;boardFetching=true;
  try {
    const data=await api.get("leaderboard");if(mode!=="board")return;
    $("podium").replaceChildren();$("ranks").replaceChildren();
    for(const i of [1,0,2]) {
      const r=data.rows[i],step=document.createElement("div");step.className=`step p${i+1}${!r?" empty":""}${r?.tri===ownTri?" me":""}`;
      if(r){step.appendChild(avatar(lookFor(r.tri)));step.insertAdjacentHTML("beforeend",`<b class="tri">${esc(r.tri)}</b><span class="sc">${r.score}/6 · +${r.bonus}</span><span class="sc">${clock(r.timeMs)}</span><div class="block">${i+1}</div>`);}$("podium").appendChild(step);
    }
    const own=data.rows.findIndex(r=>r.tri===ownTri),indices=Array.from({length:Math.min(5,data.rows.length)},(_,i)=>i);if(own>=5)indices.push(own);
    for(const i of indices){const r=data.rows[i],li=document.createElement("li");li.className=r.tri===ownTri?"me":"";li.innerHTML=`<span class="r">${i+1}</span><span class="rank-avatar"></span><b>${esc(r.tri)}</b><span>${r.score}/6 <small>+${r.bonus}</small></span><span>${clock(r.timeMs)}</span>`;li.querySelector(".rank-avatar").replaceWith(avatar(lookFor(r.tri)));$("ranks").appendChild(li);}
    $("boardMessage").textContent=data.rows.length?`${data.rows.length} partie${data.rows.length>1?"s":""} terminée${data.rows.length>1?"s":""} · actualisation 10 s`:"La première place vous attend.";
  } catch {if(mode==="board")$("boardMessage").textContent="Classement indisponible. Nouvelle tentative dans 10 s.";}
  finally{boardFetching=false;}
}
addEventListener("keydown",e=>{
  if(e.repeat||viewer.open||$("helpPanel").hidden===false||e.target.closest("input,button,[role=button]"))return;
  if(mode==="case"&&state.phase==="decision"&&["ArrowLeft","ArrowRight"].includes(e.key)){e.preventDefault();decide(e.key==="ArrowRight");}
});
addEventListener("online",()=>{if(mode==="case"&&!busy)send("start",{});});
title();
