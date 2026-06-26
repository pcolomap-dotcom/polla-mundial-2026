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
NAME_MAP = {
    "USA":                       "USA",
    "United States":             "USA",
    "Korea Republic":            "South Korea",
    "Republic of Korea":         "South Korea",
    "Czechia":                   "Czechia",
    "Czech Republic":            "Czechia",
    "Côte d'Ivoire":             "Ivory Coast",
    "Cote d'Ivoire":             "Ivory Coast",
    "Iran":                      "Iran",
    "IR Iran":                   "Iran",
    "Bosnia and Herzegovina":    "Bosnia and Herzegovina",
    "Türkiye":                   "Türkiye",
    "Turkey":                    "Türkiye",
    "Cape Verde Islands":        "Cape Verde",
    "DR Congo":                  "DR Congo",
    "Congo DR":                  "DR Congo",
    "Congo, DR":                 "DR Congo",
    "Democratic Republic of Congo": "DR Congo",
    "Korea DPR":                 "North Korea",
    "Curacao":                   "Curaçao",
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
                print(f"  SIN MATCH: {t1} vs {t2}")
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

# ── ALL MATCHES (resultados completos con exactos/aciertos) ───────────
all_matches_out = []
for m in sorted(matches, key=lambda x: (dkey(known[x['num']]['fecha']) if x['num'] in known else 999, x['num'])):
    res = known.get(m['num'])
    if not res:
        continue
    rh, ra = res['h'], res['a']
    preds_detail = []
    for nm, pr in m['preds'].items():
        pts = compute_pts(pr[0], pr[1], rh, ra)
        preds_detail.append({'name': nm, 'h': pr[0], 'a': pr[1], 'pts': pts})
    preds_detail.sort(key=lambda x: (-x['pts'], x['name']))
    all_matches_out.append({
        'num': m['num'], 'grupo': m['grupo'], 'fecha': res['fecha'],
        'team1': m['team1'], 'team2': m['team2'],
        'resH': rh, 'resA': ra,
        'exact': sorted([p['name'] for p in preds_detail if p['pts'] == 3]),
        'right': sorted([p['name'] for p in preds_detail if p['pts'] == 1]),
        'wrong': sorted([p['name'] for p in preds_detail if p['pts'] == 0]),
        'preds': preds_detail,
    })

# ── GUARDAR ───────────────────────────────────────────────────────────
now_str = datetime.datetime.now(datetime.timezone.utc).strftime('%d %b %Y %H:%M UTC')
top_scorer = prev_scorer or {'name': 'Lionel Messi', 'goals': 5, 'asOf': '25 jun'}

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
