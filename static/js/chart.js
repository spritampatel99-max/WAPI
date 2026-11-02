/* Hourly graph: smooth temperature line, rain-chance bars, high/low markers, hover/tap tooltip. */
function drawChart(svg, hours, conv) {
  const v = hours.map(h => conv(h.c)), lo = Math.min(...v), hi = Math.max(...v), n = hours.length - 1;
  const H = 200, step = 54, x = i => 50 + i * step, y = t => 44 + (hi - t) / ((hi - lo) || 1) * 88, w = x(n) + 50;
  const p = v.map((t, i) => [x(i), y(t)]);
  const d = p.map((q, i) => { if (!i) return `M${q[0]},${q[1]}`; const m = (p[i - 1][0] + q[0]) / 2; return `C${m},${p[i - 1][1]} ${m},${q[1]} ${q[0]},${q[1]}`; }).join("");
  svg.setAttribute("viewBox", `0 0 ${w} ${H}`); svg.style.width = w + "px";
  svg.innerHTML = `<defs><linearGradient id="s" gradientUnits="userSpaceOnUse" x1="0" x2="${w}" y1="0" y2="0"><stop offset="0" stop-color="#2aa6ff"/><stop offset="1" stop-color="#2fd9a0"/></linearGradient>
    <linearGradient id="a" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#3fd9a0" stop-opacity=".4"/><stop offset="1" stop-color="#2aa6ff" stop-opacity="0"/></linearGradient></defs>
    <path d="${d}L${x(n)},${H - 26}L${x(0)},${H - 26}Z" fill="url(#a)"/>` +
    hours.map((h, i) => h.p ? `<rect class="pb" x="${x(i) - 9}" y="${H - 26 - h.p * .3}" width="18" height="${h.p * .3}" rx="4"/>` : "").join("") +
    `<path class="ln" d="${d}"/>` +
    p.map(([cx, cy], i) => `<circle cx="${cx}" cy="${cy}" class="${i === v.indexOf(hi) ? "hi" : i === v.indexOf(lo) && lo < hi ? "lo" : ""}"/><text x="${cx}" y="${cy - 14}">${v[i]}°</text><text class="h" x="${cx}" y="${H - 6}">${i ? hours[i].t : "Now"}</text>`).join("") +
    `<g id="tip"><line y1="30" y2="${H - 26}"/><rect x="-46" y="2" width="92" height="38" rx="9"/><text class="t1" y="18"></text><text class="t2" y="33"></text></g>`;
  const tip = svg.querySelector("#tip"), t1 = tip.querySelector(".t1"), t2 = tip.querySelector(".t2");
  svg.onpointermove = svg.onpointerdown = e => {  // nearest hour under the finger / cursor
    const i = Math.max(0, Math.min(n, Math.round((e.clientX - svg.getBoundingClientRect().left - 50) / step)));
    tip.setAttribute("transform", `translate(${x(i)},0)`);
    t1.textContent = `${v[i]}° at ${hours[i].t}`; t2.textContent = `Rain chance ${hours[i].p}%`; tip.classList.add("on");
  };
  svg.onpointerleave = () => tip.classList.remove("on");
}
