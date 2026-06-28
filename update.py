#!/usr/bin/env python3
"""
update.py — Polla Mundialera Colomas y Asociados
Corre automáticamente en GitHub Actions cada 2 horas.
Usa football-data.org (API gratuita) para obtener resultados oficiales.
Requiere el secreto FOOTBALL_API_KEY en GitHub → Settings → Secrets.
"""

import json, urllib.request, urllib.error, datetime, os, sys, collections

# ── CONFIG ────────────────────────────────────────────────────────────
API_KEY  = os.environ.get('FOOTBALL_API_KEY', '')
API_URL  = 'https://api.football-data.org/v4/competitions/WC/matches'
YOU      = "Pablo (tú)"

# Normalización de nombres (football-data.org → nuestros datos)
# football-data.org usa en muchos casos el nombre oficial FIFA en inglés,
# que a veces difiere del nombre coloquial. Mapeamos todas las variantes conocidas.
NAME_MAP = {
    # USA
    "United States":                "USA",
    "USA":                          "USA",
    "United States of America":     "USA",

    # South Korea
    "Korea Republic":               "South Korea",
    "Republic of Korea":            "South Korea",
    "South Korea":                  "South Korea",

    # Czechia
    "Czech Republic":               "Czechia",
    "Czechia":                      "Czechia",

    # Ivory Coast
    "Côte d'Ivoire":                "Ivory Coast",
    "Cote d'Ivoire":                "Ivory Coast",
    "Ivory Coast":                  "Ivory Coast",

    # Iran
    "IR Iran":                      "Iran",
    "Iran":                         "Iran",

    # Bosnia
    "Bosnia and Herzegovina":       "Bosnia and Herzegovina",
    "Bosnia & Herzegovina":         "Bosnia and Herzegovina",

    # Turkey
    "Türkiye":                      "Türkiye",
    "Turkey":                       "Türkiye",

    # Cape Verde — FIFA/football-data usa "Cabo Verde"
    "Cabo Verde":                   "Cape Verde",
    "Cape Verde":                   "Cape Verde",
    "Cape Verde Islands":           "Cape Verde",

    # DR Congo
    "DR Congo":                     "DR Congo",
    "Congo DR":                     "DR Congo",
    "Congo, DR":                    "DR Congo",
    "Democratic Republic of Congo": "DR Congo",
    "Congo (DR)":                   "DR Congo",

    # Curaçao
    "Curacao":                      "Curaçao",
    "Curaçao":                      "Curaçao",

    # New Zealand
    "New Zealand":                  "New Zealand",

    # Equipos cuyo nombre en football-data puede variar ligeramente
    "Saudi Arabia":                 "Saudi Arabia",
    "KSA":                          "Saudi Arabia",

    "Scotland":                     "Scotland",
    "Morocco":                      "Morocco",
    "Algeria":                      "Algeria",
    "Senegal":                      "Senegal",
    "South Africa":                 "South Africa",
    "Ghana":                        "Ghana",
    "Tunisia":                      "Tunisia",
    "Egypt":                        "Egypt",
    "Panama":                       "Panama",
    "Haiti":                        "Haiti",

    "Uzbekistan":                   "Uzbekistan",
    "Jordan":                       "Jordan",
    "Iraq":                         "Iraq",
    "Qatar":                        "Qatar",
    "Australia":                    "Australia",

    "Paraguay":                     "Paraguay",
    "Ecuador":                      "Ecuador",
    "Colombia":                     "Colombia",
    "Argentina":                    "Argentina",
    "Brazil":                       "Brazil",
    "Brasil":                       "Brazil",
    "Uruguay":                      "Uruguay",

    "England":                      "England",
    "France":                       "France",
    "Spain":                        "Spain",
    "Germany":                      "Germany",
    "Netherlands":                  "Netherlands",
    "Portugal":                     "Portugal",
    "Belgium":                      "Belgium",
    "Norway":                       "Norway",
    "Sweden":                       "Sweden",
    "Switzerland":                  "Switzerland",
    "Austria":                      "Austria",
    "Croatia":                      "Croatia",
    "Japan":                        "Japan",
    "Canada":                       "Canada",
    "Mexico":                       "Mexico",
    "Scotland":                     "Scotland",
}

def norm(name):
    return NAME_MAP.get(name, name)

def oo(h, a):
    return 'H' if h > a else ('A' if a > h else 'D')

def compute_pts(ph, pa, rh, ra):
    if ph == rh and pa == ra: return 3
    if oo(ph, pa) == oo(rh, ra): return 1
    return 0

# ── CARGAR PREDICCIONES ESTÁTICAS ─────────────────────────────────────
with open('predictions.json') as f:
    static = json.load(f)

players  = static['players']
specials = static['specials']
matches  = static['matches']

# Índice para mapear pares de equipos → número de partido
pair_index = {}
for m in matches:
    pair_index[(m['team1'], m['team2'])] = m['num']
    pair_index[(m['team2'], m['team1'])] = m['num']

# ── RESULTADOS PREVIOS ────────────────────────────────────────────────
known = {}  # num -> {num, h, a, fecha}
try:
    with open('data.json') as f:
        prev = json.load(f)
    for r in prev.get('_raw_results', []):
        known[r['num']] = r
    print(f"Resultados previos cargados: {len(known)}")
except Exception as e:
    print(f"Sin data.json previo: {e}")

prev_scorer = None
try:
    prev_scorer = prev.get('topScorer')
except:
    pass
api_scorer = None  # se rellena desde la API si está disponible

def _today_label():
    d = datetime.date.today()
    return f"{d.day} jun" if d.month == 6 else f"{d.day} jul"

# ── FETCH FOOTBALL-DATA.ORG ───────────────────────────────────────────
new_found = 0

if not API_KEY:
    print("⚠️  FOOTBALL_API_KEY no configurada — usando resultados previos")
else:
    print("Consultando football-data.org…")
    req = urllib.request.Request(
        API_URL + '?stage=GROUP_STAGE&status=FINISHED',
        headers={'X-Auth-Token': API_KEY,
                 'User-Agent': 'PollaMundialBot/1.0'}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        
        # Loguear todos los nombres que devuelve la API (ayuda a detectar
        # nombres no mapeados sin necesidad de ver el código)
        api_names = sorted(set(
            name
            for m in data.get('matches', [])
            for name in (m['homeTeam']['name'], m['awayTeam']['name'])
        ))
        print(f"  Nombres en API ({len(api_names)}): {api_names}")

        for match in data.get('matches', []):
            score = match.get('score', {})
            ft    = score.get('fullTime', {})
            rh    = ft.get('home')
            ra    = ft.get('away')
            if rh is None or ra is None:
                continue
            
            t1 = norm(match['homeTeam']['name'])
            t2 = norm(match['awayTeam']['name'])
            num = pair_index.get((t1, t2)) or pair_index.get((t2, t1))
            
            if not num:
                print(f"  SIN MATCH: {match['homeTeam']['name']!r} → {t1!r}  vs  {match['awayTeam']['name']!r} → {t2!r}")
                continue
            
            # Swap score if teams were reversed
            m = next(x for x in matches if x['num'] == num)
            if m['team1'] == t2:
                rh, ra = ra, rh
            
            date_str = match.get('utcDate', '')[:10]
            try:
                dt = datetime.date.fromisoformat(date_str)
                fecha = f"{dt.day} jun" if dt.month == 6 else f"{dt.day} jul"
            except:
                fecha = date_str
            
            if num not in known:
                new_found += 1
                print(f"  ✓ M{num} {m['team1']} {rh}-{ra} {m['team2']}")
            
            known[num] = {'num': num, 'h': int(rh), 'a': int(ra), 'fecha': fecha}
        
        print(f"\nResultados totales: {len(known)} (+{new_found} nuevos)")
    
    except Exception as e:
        print(f"Error API: {e} — usando resultados previos")

    # ── GOLEADOR LÍDER (automático) ───────────────────────────────────
    try:
        sreq = urllib.request.Request(
            'https://api.football-data.org/v4/competitions/WC/scorers?limit=1',
            headers={'X-Auth-Token': API_KEY,
                     'User-Agent': 'PollaMundialBot/1.0'}
        )
        with urllib.request.urlopen(sreq, timeout=20) as r:
            sdata = json.load(r)
        sc = sdata.get('scorers') or []
        if sc:
            top = sc[0]
            goals = top.get('goals')
            if goals is None:
                goals = top.get('numberOfGoals', 0)
            api_scorer = {'name': top['player']['name'],
                          'goals': goals,
                          'asOf': _today_label()}
            print(f"  ⚽ Goleador: {api_scorer['name']} ({api_scorer['goals']})")
    except Exception as e:
        print(f"Error scorers: {e} — usando goleador previo")

# ── RECOMPUTAR RANKING ────────────────────────────────────────────────
tot    = {p: 0 for p in players}
exact  = {p: 0 for p in players}
outc   = {p: 0 for p in players}

for m in matches:
    res = known.get(m['num'])
    if not res:
        continue
    for nm, pr in m['preds'].items():
        pts = compute_pts(pr[0], pr[1], res['h'], res['a'])
        tot[nm] += pts
        if pts == 3: exact[nm] += 1
        elif pts == 1: outc[nm] += 1

arr = sorted(players, key=lambda p: (-tot[p], p))
rk = {}; rv=0; pv=None; sv=0
for p in arr:
    sv += 1
    if tot[p] != pv: rv=sv; pv=tot[p]
    rk[p] = rv

ranking = [{'name': p, 'pts': tot[p], 'rank': rk[p],
            'exact': exact[p], 'outc': outc[p]} for p in arr]

# ── RECOMPUTAR EVOLUCIÓN ──────────────────────────────────────────────
played_ms = [m for m in matches if m['num'] in known]

def dkey(fecha):
    try:    return int(fecha.split()[0])
    except: return 0

date_keys = sorted(set(dkey(known[m['num']]['fecha']) for m in played_ms))
dlabel    = {dkey(known[m['num']]['fecha']): known[m['num']]['fecha'] for m in played_ms}

ranks_by = {p: [] for p in players}
pts_by   = {p: [] for p in players}

for dk in date_keys:
    t2 = {p: 0 for p in players}
    for m in played_ms:
        res = known[m['num']]
        if dkey(res['fecha']) > dk:
            continue
        for nm, pr in m['preds'].items():
            t2[nm] += compute_pts(pr[0], pr[1], res['h'], res['a'])
    arr2 = sorted(players, key=lambda p: (-t2[p], p))
    r2={}; rv2=0; pv2=None; sv2=0
    for p in arr2:
        sv2 += 1
        if t2[p] != pv2: rv2=sv2; pv2=t2[p]
        r2[p] = rv2
    for p in players:
        ranks_by[p].append(r2[p])
        pts_by[p].append(t2[p])

evo_order = sorted(players, key=lambda p: (-pts_by[p][-1] if pts_by[p] else 0, p))
evolution = {
    'dates': [dlabel[k] for k in date_keys],
    'players': [{'name': p, 'ranks': ranks_by[p], 'pts': pts_by[p],
                 'final': pts_by[p][-1] if pts_by[p] else 0} for p in evo_order]
}

# ── PARTIDOS RECIENTES ────────────────────────────────────────────────
recent_dkeys = sorted(date_keys, reverse=True)[:2]
recent_matches = []
for m in played_ms:
    res = known[m['num']]
    if dkey(res['fecha']) not in recent_dkeys:
        continue
    preds_list = [{'name': nm, 'h': pr[0], 'a': pr[1],
                   'pts': compute_pts(pr[0], pr[1], res['h'], res['a'])}
                  for nm, pr in m['preds'].items()]
    preds_list.sort(key=lambda x: -x['pts'])
    recent_matches.append({
        'num': m['num'], 'grupo': m['grupo'], 'fecha': res['fecha'],
        'team1': m['team1'], 'team2': m['team2'],
        'resH': res['h'], 'resA': res['a'], 'preds': preds_list
    })
recent_matches.sort(key=lambda x: (dkey(x['fecha']), x['num']))

# ── PRÓXIMOS PARTIDOS ─────────────────────────────────────────────────
unplayed = [m for m in matches if m['num'] not in known]
next_dks = sorted(set(int(m['fecha_orig'].split()[0])
                       for m in unplayed if m.get('fecha_orig')))
next_dk = next_dks[0] if next_dks else None
upcoming = []
if next_dk:
    for m in unplayed:
        try:
            if int(m['fecha_orig'].split()[0]) != next_dk: continue
        except: continue
        upcoming.append({
            'num': m['num'], 'grupo': m['grupo'], 'fecha': m['fecha_orig'],
            'team1': m['team1'], 'team2': m['team2'],
            'preds': [{'name': nm, 'h': pr[0], 'a': pr[1]}
                      for nm, pr in m['preds'].items()]
        })
    upcoming.sort(key=lambda x: x['num'])

# ── TODOS LOS PARTIDOS (vista de resultados de rev2) ──────────────────
# rev2/index.html (buildResultados) consume data.allMatches. Aquí lo
# generamos para que el dashboard se alimente 100% de data.json.
all_matches_out = []
for m in matches:
    res = known.get(m['num'])
    if not res:
        continue  # sólo partidos ya jugados
    exact_n, right_n, wrong_n, preds_l = [], [], [], []
    for nm, pr in m['preds'].items():
        pts = compute_pts(pr[0], pr[1], res['h'], res['a'])
        preds_l.append({'name': nm, 'h': pr[0], 'a': pr[1], 'pts': pts})
        if pts == 3:
            exact_n.append(nm)
        elif pts == 1:
            right_n.append(nm)
        else:
            wrong_n.append(nm)
    exact_n.sort(); right_n.sort(); wrong_n.sort()
    preds_l.sort(key=lambda x: -x['pts'])
    all_matches_out.append({
        'num': m['num'], 'grupo': m['grupo'], 'fecha': res['fecha'],
        'team1': m['team1'], 'team2': m['team2'],
        'resH': res['h'], 'resA': res['a'],
        'exact': exact_n, 'right': right_n, 'wrong': wrong_n,
        'preds': preds_l,
    })
all_matches_out.sort(key=lambda x: x['num'])

# ── SALVAGUARDA ───────────────────────────────────────────────────────
# Si no hay NINGÚN resultado conocido (p.ej. API caída + sin _raw_results
# previo), NO sobrescribimos data.json: dejaríamos el tablero en blanco.
if not known:
    print("⛔ Sin resultados conocidos (API sin datos y sin _raw_results "
          "previo). No se sobrescribe data.json para no borrar el tablero.")
    sys.exit(0)

# ── GUARDAR ───────────────────────────────────────────────────────────
now_str = datetime.datetime.now(datetime.timezone.utc).strftime('%d %b %Y %H:%M UTC')
top_scorer = api_scorer or prev_scorer or {'name': 'Lionel Messi', 'goals': 5, 'asOf': '25 jun'}

output = {
    'lastUpdated':   now_str,
    'playedCount':   len(known),
    'totalCount':    len(matches),
    'topScorer':     top_scorer,
    'ranking':       ranking,
    'evolution':     evolution,
    'recentMatches': recent_matches,
    'upcoming':      upcoming,
    'allMatches':    all_matches_out,
    'specials':      [{'name': p, **specials[p]} for p in players],
    '_raw_results':  list(known.values()),
}

with open('data.json', 'w') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✅ data.json actualizado — {len(known)}/{len(matches)} partidos — {now_str}")
print(f"   Top 3: {[(r['name'], r['pts']) for r in ranking[:3]]}")
