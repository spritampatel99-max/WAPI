/* SkyCast UI: day/night theme, units, particles, search helpers. */
const $ = id => document.getElementById(id);
const { w: W, q: Q } = JSON.parse($("data").textContent);
const store = { get: k => { try { return localStorage[k]; } catch (e) {} }, set: (k, v) => { try { localStorage[k] = v; } catch (e) {} } };
const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
let F = store.get("unit") === "F", mode = "auto";  // mode: auto = the city's real local time; day/night = your tap
const conv = c => Math.round(F ? c * 9 / 5 + 32 : c);
const isNight = () => mode === "auto" ? !!(W && W.night) : mode === "night";

function theme() {  // apply day/night: background, orb, icon, browser bar colour
  const n = isNight();
  document.body.classList.toggle("night", n);
  document.querySelector('meta[name="theme-color"]').content = n ? "#0d2b4d" : "#7fd0ff";
  $("theme").textContent = n ? "🌙 Night" : "☀️ Day";
  const ico = document.querySelector(".ico"); if (ico && W) ico.textContent = n ? W.nicon : W.icon;
}
function flip() {  // tap: the sun sets / moon rises, and the sky recolours for the same weather
  const was = isNight(); mode = was ? "day" : "night";
  if (calm) return theme();
  document.body.classList.add("swap"); setTimeout(theme, 450); setTimeout(() => document.body.classList.remove("swap"), 1000);
}

function paint() {  // everything that depends on the unit
  document.querySelectorAll("[data-c]").forEach(e => e.textContent = conv(+e.dataset.c) + "°");
  document.querySelectorAll("[data-ms]").forEach(e => e.textContent = (F ? (e.dataset.ms * 2.237).toFixed(1) + " mph " : e.dataset.ms + " m/s ") + e.dataset.dir);
  $("unit").textContent = F ? "°F" : "°C";
  if (W) { $("big").textContent = conv(W.temp) + "°"; drawChart($("chart"), W.hours, conv); const s = $("chart").parentNode; $("hint").hidden = s.scrollWidth <= s.clientWidth; }
}

$("theme").onclick = flip;
$("unit").onclick = () => { F = !F; store.set("unit", F ? "F" : "C"); paint(); };
$("f").onsubmit = () => { $("go").classList.add("busy"); $("go").textContent = "Searching…"; };
$("loc").onclick = () => {
  if (!navigator.geolocation) return alert("Your browser can't share its location.");
  $("loc").classList.add("busy");
  navigator.geolocation.getCurrentPosition(
    p => location.href = `/?lat=${p.coords.latitude.toFixed(3)}&lon=${p.coords.longitude.toFixed(3)}`,
    () => { $("loc").classList.remove("busy"); alert("Location access was blocked. Allow it in your browser, or search by city."); });
};
addEventListener("keydown", e => {  // "/" to search, "d" to flip day/night
  if (e.target.tagName === "INPUT" || e.ctrlKey || e.metaKey) return;
  if (e.key === "/") { e.preventDefault(); $("q").focus(); } else if (e.key.toLowerCase() === "d") flip();
});

let timer;  // live city suggestions
$("q").oninput = () => {
  clearTimeout(timer); const v = $("q").value.trim(); if (v.length < 2) return;
  timer = setTimeout(async () => {
    try { const r = await (await fetch("/api/suggest?q=" + encodeURIComponent(v))).json();
      $("sugg").replaceChildren(...r.map(o => Object.assign(new Option(o.n), { label: o.l }))); } catch (e) {}
  }, 250);
};

let recent = []; try { recent = JSON.parse(store.get("recent") || "[]"); } catch (e) {}
if (W && Q) { recent = [W.city, ...recent.filter(c => c !== W.city)].slice(0, 6); store.set("recent", JSON.stringify(recent)); }
$("chips").append(...[...new Set([...recent, "Delhi", "Mumbai", "London", "Tokyo", "New York"])].slice(0, 6)
  .map(c => Object.assign(document.createElement("a"), { href: "/?city=" + encodeURIComponent(c), textContent: c })));

for (let i = 0; i < 45; i++) {  // night stars
  const s = document.createElement("i");
  Object.assign(s.style, { left: Math.random() * 100 + "%", top: Math.random() * 70 + "%", animationDelay: Math.random() * 3 + "s" });
  $("stars").append(s);
}

theme(); paint();
if (W) {
  if (!calm && ["rain", "storm", "snow"].includes(W.scene)) {  // weather-matched particles
    $("fx").className = W.scene;
    for (let i = 0; i < (innerWidth < 600 ? 35 : 70); i++) {
      const d = document.createElement("i");
      Object.assign(d.style, { left: Math.random() * 100 + "%", animationDelay: "-" + Math.random() * 3 + "s", animationDuration: (W.scene === "snow" ? 5 : .8) + Math.random() + "s" });
      $("fx").append(d);
    }
  }
  const big = $("big"); let t0;  // count-up on load
  const step = n => { t0 ??= n; const k = Math.min((n - t0) / 900, 1); big.textContent = Math.round(conv(W.temp) * k) + "°"; if (k < 1) requestAnimationFrame(step); };
  if (!calm) requestAnimationFrame(step);
  const loaded = Date.now();  // refresh stale data when you come back to the tab
  $("upd").textContent = "Updated " + new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  document.addEventListener("visibilitychange", () => { if (!document.hidden && Date.now() - loaded > 600000) location.reload(); });
}
