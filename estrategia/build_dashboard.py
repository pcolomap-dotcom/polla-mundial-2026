#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Construye el tablero visual multi-jugador embebiendo dashboard_data.json."""
import json, os

BASE = "/home/user/polla-mundial-2026"
data = json.load(open(os.path.join(BASE, "estrategia", "dashboard_data.json"), encoding="utf-8"))

FLAG = {"España": "🇪🇸", "Francia": "🇫🇷", "Inglaterra": "🏴", "Argentina": "🇦🇷"}

CSS = """
:root{
  --pitch:#0f3d2e; --chalk:#f4f7f2; --chalk-dim:#c7d4cb; --gold:#e8b73a;
  --gold-deep:#c8931c; --red:#d8402f; --green-ok:#4caf7d; --line:rgba(244,247,242,.15);
  --paper:#f3f5ef; --paper-ink:#183329; --paper-dim:#5c6f63; --paper-line:#d3dad0;
  --bg:var(--pitch); --fg:var(--chalk); --fg-dim:var(--chalk-dim);
  --panel:rgba(255,255,255,.05); --panel-line:var(--line); --accent:var(--gold);
  --chip:rgba(255,255,255,.07);
}
@media (prefers-color-scheme: light){
  :root{ --bg:var(--paper); --fg:var(--paper-ink); --fg-dim:var(--paper-dim);
    --panel:#ffffff; --panel-line:var(--paper-line); --accent:var(--gold-deep);
    --chip:#eef1ea; --line:var(--paper-line); }
}
:root[data-theme="dark"]{ --bg:var(--pitch); --fg:var(--chalk); --fg-dim:var(--chalk-dim);
  --panel:rgba(255,255,255,.05); --panel-line:var(--line); --accent:var(--gold); --chip:rgba(255,255,255,.07);}
:root[data-theme="light"]{ --bg:var(--paper); --fg:var(--paper-ink); --fg-dim:var(--paper-dim);
  --panel:#ffffff; --panel-line:var(--paper-line); --accent:var(--gold-deep); --chip:#eef1ea;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font-family:"Segoe UI",system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif;line-height:1.5;}
.wrap{max-width:960px;margin:0 auto;padding:clamp(16px,4vw,40px);}
.kicker{font-size:.7rem;letter-spacing:.22em;text-transform:uppercase;color:var(--accent);font-weight:700;}
h1{font-family:"Arial Narrow","Helvetica Neue",Impact,sans-serif;font-weight:800;
  font-size:clamp(1.9rem,5.5vw,3rem);line-height:1.02;margin:.12em 0;text-wrap:balance;}
h2{font-family:"Arial Narrow","Helvetica Neue",sans-serif;font-weight:800;text-transform:uppercase;
  letter-spacing:.04em;font-size:1rem;margin:0 0 .35em;display:flex;align-items:center;gap:.45em;}
.sub{color:var(--fg-dim);max-width:64ch;}
.tnum{font-variant-numeric:tabular-nums;}
.panel{background:var(--panel);border:1px solid var(--panel-line);border-radius:14px;padding:16px 18px;}
section{margin:22px 0;}
.shared{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
@media(max-width:720px){.shared{grid-template-columns:1fr;}}
table{width:100%;border-collapse:collapse;font-size:.92rem;}
th,td{text-align:left;padding:7px 6px;border-bottom:1px solid var(--panel-line);}
th{font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;color:var(--fg-dim);font-weight:700;}
td.r,th.r{text-align:right;font-variant-numeric:tabular-nums;}
.mini{font-size:.82rem;color:var(--fg-dim);margin-top:6px;}

nav.players{display:flex;flex-wrap:wrap;gap:8px;margin:26px 0 8px;}
.pill{border:1px solid var(--panel-line);background:var(--chip);color:var(--fg);
  padding:8px 15px;border-radius:999px;cursor:pointer;font-size:.9rem;font-weight:600;
  transition:.15s;}
.pill:hover{border-color:var(--accent);}
.pill[aria-selected="true"]{background:var(--accent);color:#12231a;border-color:var(--accent);}
.pill .rk{opacity:.7;font-weight:700;font-size:.8em;margin-right:5px;}

.head{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-end;gap:12px;
  border-bottom:1px solid var(--panel-line);padding-bottom:14px;margin-bottom:16px;}
.head .who{font-family:"Arial Narrow",sans-serif;font-weight:800;font-size:2rem;line-height:1;}
.tierbadge{font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;font-weight:800;
  padding:3px 9px;border-radius:999px;}
.tier-candidato{background:color-mix(in srgb,var(--accent) 22%,transparent);color:var(--accent);
  border:1px solid var(--accent);}
.tier-longshot{background:var(--chip);color:var(--fg-dim);border:1px solid var(--panel-line);}
.tier-fondo{background:color-mix(in srgb,var(--red) 15%,transparent);color:var(--red);
  border:1px solid color-mix(in srgb,var(--red) 45%,var(--panel-line));}

.stats{display:flex;flex-wrap:wrap;gap:10px;margin:4px 0 2px;}
.stat{flex:1 1 90px;background:var(--panel);border:1px solid var(--panel-line);border-radius:11px;padding:10px 12px;}
.stat .lab{font-size:.6rem;letter-spacing:.1em;text-transform:uppercase;color:var(--fg-dim);}
.stat .big{font-family:"Arial Narrow",sans-serif;font-weight:800;font-size:1.55rem;line-height:1;margin-top:3px;}
.stat.win .big{color:var(--accent);}
.stat.risk .big{color:var(--red);}

.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:16px;}
@media(max-width:720px){.cols{grid-template-columns:1fr;}}
ul.clean{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px;}
ul.clean li{display:flex;gap:9px;align-items:flex-start;font-size:.92rem;}
.ok{color:var(--green-ok);font-weight:800;flex:none;}
.no{color:var(--red);font-weight:800;flex:none;}
.note{font-size:.85rem;color:var(--fg-dim);background:var(--chip);border-radius:10px;padding:9px 12px;margin-top:8px;}

.bet{display:flex;justify-content:space-between;align-items:baseline;gap:10px;padding:9px 0;
  border-bottom:1px solid var(--panel-line);}
.bet:last-child{border:none;}
.bet .m{font-size:.82rem;}
.bet .m .why{display:block;color:var(--fg-dim);font-size:.76rem;margin-top:2px;}
.bet .pick{text-align:right;white-space:nowrap;}
.bet .pick .sc{font-family:"Arial Narrow",sans-serif;font-weight:800;font-size:1.15rem;color:var(--accent);
  font-variant-numeric:tabular-nums;}
.badge{font-size:.58rem;letter-spacing:.08em;text-transform:uppercase;font-weight:800;
  padding:2px 6px;border-radius:6px;margin-left:6px;vertical-align:middle;}
.b-fav{background:var(--chip);color:var(--fg-dim);}
.b-contra{background:color-mix(in srgb,var(--red) 18%,transparent);color:var(--red);
  border:1px solid color-mix(in srgb,var(--red) 40%,transparent);}

.dream{background:linear-gradient(135deg,color-mix(in srgb,var(--accent) 16%,transparent),transparent 70%);
  border:1px solid color-mix(in srgb,var(--accent) 40%,var(--panel-line));}
.podchips{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;}
.podchip{background:var(--chip);border:1px solid var(--panel-line);border-radius:9px;padding:6px 11px;font-weight:700;font-size:.9rem;}
.podchip small{display:block;font-size:.62rem;color:var(--fg-dim);font-weight:700;letter-spacing:.08em;text-transform:uppercase;}
.sanm{margin-top:14px;padding:12px 14px;border-radius:12px;font-size:.9rem;}
.sanm.hi{background:color-mix(in srgb,var(--red) 13%,transparent);border:1px solid color-mix(in srgb,var(--red) 45%,var(--panel-line));}
.sanm.lo{background:var(--chip);border:1px solid var(--panel-line);}
.key{font-size:.95rem;border-left:3px solid var(--accent);padding-left:12px;margin-top:14px;}
.foot{margin-top:30px;padding-top:14px;border-top:1px solid var(--panel-line);color:var(--fg-dim);font-size:.78rem;}
.styletag{display:inline-block;font-weight:800;color:var(--accent);}
"""

def flag(t): return FLAG.get(t, "")

# --- shared HTML ---
semis_html = ""
for sm in data["semis"]:
    sc = "".join(f"<div>{s}</div>" for s in sm["scores"])
    semis_html += f"""
    <div class="panel">
      <h2>{flag(sm['a'])} {sm['a']} <span style="color:var(--fg-dim)">vs</span> {sm['b']} {flag(sm['b'])}</h2>
      <div style="font-size:1.05rem;font-weight:700">Avanza: {sm['a']} <b class="tnum">{sm['advA']}%</b>
        · {sm['b']} <b class="tnum">{sm['advB']}%</b></div>
      <div class="mini">{sc}</div>
    </div>"""

camino_rows = "".join(
    f"<tr><td>{flag(c['team'])} {c['team']}</td><td class='r tnum'>{c['champ']}%</td>"
    f"<td class='r tnum'>{c['final']}%</td><td class='r tnum'>{c['third']}%</td></tr>"
    for c in data["camino"])

pills = "".join(
    f'<button class="pill" role="tab" data-i="{i}" onclick="pick({i})">'
    f'<span class="rk">#{p["rank"]}</span>{p["disp"]}</button>'
    for i, p in enumerate(data["players"]))

HTML = f"""<title>Tableros de estrategia · Polla Mundial 2026</title>
<style>{CSS}</style>
<div class="wrap">
  <header>
    <div class="kicker">Polla Mundialera Colomas y Asociados · 12 jul 2026</div>
    <h1>Tableros de estrategia por jugador</h1>
    <p class="sub">Cuartos jugados. Faltan 2 semifinales, 3er puesto y final, más los
      premios especiales. Puntaje del reglamento; el goleador no puede ser además mejor
      jugador; y <b>no se pierden puntos por fallar</b> un pronóstico.</p>
  </header>

  <section class="shared">
    {semis_html}
  </section>
  <section class="panel">
    <h2>🔮 Camino a la final</h2>
    <table>
      <thead><tr><th>Equipo</th><th class="r">Campeón</th><th class="r">Finalista</th><th class="r">3er lugar</th></tr></thead>
      <tbody>{camino_rows}</tbody>
    </table>
    <div class="mini">La final más probable es España–Argentina. Puntos que quedan en juego por
      partido: semifinal 3 (acierto) / 6 (exacto); 3er puesto y final 4 / 8.</div>
  </section>

  <nav class="players" role="tablist">{pills}</nav>
  <main id="board" class="panel"></main>

  <p class="foot">Generado por <code>estrategia/agentes_polla.py</code> (Monte Carlo, 30.000
    simulaciones + enumeración exacta del podio). Supuestos de fuerza de equipos y carrera de
    goleador editables en el código. Elige tu nombre arriba.</p>
</div>
<script>
const DATA = {json.dumps(data['players'], ensure_ascii=False)};
const FLAG = {json.dumps(FLAG, ensure_ascii=False)};
function fl(t){{return FLAG[t]||"";}}
function esc(s){{return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;");}}
function render(p){{
  const spec = p.specials.map(s=>{{
    const good = s.alive;
    return `<li><span class="${{good?'ok':'no'}}">${{good?'✓':'✕'}}</span>
      <div>${{esc(s.txt)}} ${{good?'':'<b style=\\'color:var(--red)\\'>— eliminado</b>'}}</div></li>`;
  }}).join("");
  const bets = p.apuestas.map(a=>`
    <div class="bet">
      <div class="m">${{esc(a.match)}}
        <span class="why">${{esc(a.reason)}}</span></div>
      <div class="pick">${{fl(a.pick)}} <b>${{esc(a.pick)}}</b>
        <span class="badge ${{a.fav?'b-fav':'b-contra'}}">${{a.fav?'favorito':'contrarian'}}</span><br>
        <span class="sc">${{esc(a.score)}}</span></div>
    </div>`).join("");
  const d=p.dream;
  const riskHi = p.last>=15;
  const board = `
    <div class="head">
      <div>
        <div class="kicker">Tu posición</div>
        <div class="who">#${{p.rank}} · ${{esc(p.disp)}}</div>
        <div style="color:var(--fg-dim)">${{p.pts}} pts · a ${{p.gapLead}} del líder</div>
      </div>
      <span class="tierbadge tier-${{p.tier}}">${{p.tier==='candidato'?'Candidato real':p.tier==='longshot'?'Opción lejana':'Fondo de tabla'}}</span>
    </div>

    <div class="stats">
      <div class="stat win"><div class="lab">Ganar</div><div class="big tnum">${{p.win}}%</div></div>
      <div class="stat"><div class="lab">Top-3</div><div class="big tnum">${{p.top3}}%</div></div>
      <div class="stat"><div class="lab">Top-5</div><div class="big tnum">${{p.top5}}%</div></div>
      <div class="stat ${{riskHi?'risk':''}}"><div class="lab">Último</div><div class="big tnum">${{p.last}}%</div></div>
      <div class="stat"><div class="lab">Puesto medio</div><div class="big tnum">#${{p.avgRank}}</div></div>
    </div>

    <div class="key">${{esc(p.keyInsight)}}</div>

    <div class="cols">
      <div class="panel">
        <h2>📌 Tus especiales</h2>
        <ul class="clean">${{spec}}</ul>
        <div class="note">${{esc(p.golMvpNote)}}</div>
      </div>
      <div class="panel dream">
        <h2>📣 Qué alentar</h2>
        <div class="podchips">
          <div class="podchip"><small>Campeón</small>${{fl(d.champ)}} ${{esc(d.champ)}}</div>
          <div class="podchip"><small>Subcampeón</small>${{fl(d.run)}} ${{esc(d.run)}}</div>
          <div class="podchip"><small>3er lugar</small>${{fl(d.third)}} ${{esc(d.third)}}</div>
        </div>
        <div class="note">Ese cuadro te da <b>+${{d.podium}}</b> de podio.
          ${{p.tier==='candidato'?('En él tu prob. de ganar sube a ~'+d.condWin+'%.'):
             p.tier==='longshot'?('Con tus especiales, te pone a pelear el top-5.'):
             ('El título está lejos; el objetivo es escalar y no quedar último.')}}</div>
      </div>
    </div>

    <div class="panel" style="margin-top:14px">
      <h2>🎯 Tus apuestas (pronósticos a enviar)</h2>
      <div style="font-size:.82rem;color:var(--fg-dim);margin-bottom:4px">
        Alineadas al escenario donde mejor terminas. Como no se pierden puntos por fallar,
        ir <b>contrarian</b> no tiene costo.</div>
      ${{bets}}
    </div>

    <div class="sanm ${{riskHi?'hi':'lo'}}">${{esc(p.sanMarino)}}</div>

    <div style="margin-top:14px" class="note">
      <b>Estilo de juego:</b> <span class="styletag">${{esc(p.style.label)}}</span> — ${{esc(p.style.desc)}}</div>
  `;
  document.getElementById("board").innerHTML = board;
}}
function pick(i){{
  document.querySelectorAll(".pill").forEach((b,j)=>b.setAttribute("aria-selected", j===i?"true":"false"));
  render(DATA[i]);
}}
pick(0);
</script>
"""

# Envuelve el cuerpo en un documento HTML autónomo para el repo.
import re as _re
_m = _re.search(r"<title>(.*?)</title>", HTML)
_title = _m.group(1)
_body = HTML.replace(_m.group(0), "", 1).strip()
DOC = ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
       f'<title>{_title}</title>\n</head>\n<body>\n{_body}\n</body>\n</html>\n')
out = os.path.join(BASE, "estrategia", "tableros.html")
open(out, "w", encoding="utf-8").write(DOC)
print("written", out, len(DOC), "bytes")
