#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agentes_polla.py — Sistema de agentes de análisis para la Polla Mundialera
===========================================================================

Analiza lo que queda del Mundial 2026 (semifinales en adelante) y arma un
informe individual para cualquier jugador: probabilidades, qué alentar, qué
pronosticar y con qué estilo de juego.

Estado al 12-jul-2026: se jugaron los CUARTOS DE FINAL. Faltan: 2 semifinales,
3er puesto, final y los premios especiales (campeón/subcampeón/3º, goleador y
mejor jugador), que todavía NO se otorgan.

REGLAS DE PUNTAJE (según el reglamento oficial):
  Partidos por ronda — acierta ganador / marcador exacto:
    grupos 1/3 · ronda32 2/4 · octavos 2/4 · cuartos 3/6 · semis 3/6 · 3º y final 4/8
  Especiales: Campeón 20 · Subcampeón 15 · 3er lugar 10 · Goleador 10 · Balón de Oro 10
  >>> Un mismo jugador NO puede ganar Goleador y Balón de Oro a la vez. <<<

Cinco agentes:
  1. AgenteDatos       posiciones, especiales, cuadro.
  2. AgenteEscenarios  enumera exacto los 16 desenlaces del podio.
  3. AgentePartidos    modelo Poisson: probabilidades de marcadores/avance.
  4. AgenteEspeciales  goleador y MVP (con la regla de exclusión mutua).
  5. AgenteSimulacion  Monte Carlo -> prob. de posición final por jugador.
  + AgenteEstrategia   estilo de juego y pronósticos recomendados.

Uso:  python3 estrategia/agentes_polla.py            (resumen general)
      python3 estrategia/agentes_polla.py --sims 60000
"""
from __future__ import annotations
import json, os, math, random, argparse


BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ══════════════════════════════════════════════════════════════════════
#  AGENTE 1 · DATOS
# ══════════════════════════════════════════════════════════════════════
class AgenteDatos:
    STANDINGS = {
        "Jaime": 136, "Seb": 122, "Juanco": 121, "Cata": 120, "Martín": 116,
        "Vale": 115, "Fernando IV": 113, "Felipe Coloma": 112, "Tío Gucho": 112,
        "Diego": 110, "joaco": 108, "Pablo (tú)": 107, "Domingo": 107,
        "Pedro": 104, "Mely": 104, "Fernando II": 104, "Lito": 104,
        "Trini Coloma": 103, "Carola P": 100, "Juan": 100, "Tono": 100,
        "Paz": 97, "AguColoma": 96, "Caro": 95, "Tomi": 94, "Rodrigo": 94,
        "Carmen": 93, "Benja": 93, "Joselin": 90, "José Pablo": 89,
        "Ignacolo": 88, "Victo": 86, "lica": 84, "Coni": 75,
    }
    SF1 = ("France", "Spain")       # Partido 101 · 14 jul
    SF2 = ("England", "Argentina")  # Partido 102 · 15 jul
    ALIVE = ["France", "Spain", "England", "Argentina"]

    # Solo reglamento (por instrucción del organizador de este análisis).
    SPECIAL_PTS = dict(champ=20, run=15, third=10, gol=10, mvp=10)

    TOP_SCORER_NOW = ("Mbappé", 8)   # dato live al 12-jul

    # ── EDITABLE: cómo apuesta JAIME (el líder) cada partido ──────────────
    # Marcadores 90' en orden (equipo1, equipo2) de cada semifinal.
    # SF1 (Francia–España): 1–2  → ya lo envió: gana España.
    # SF2 (Inglaterra–Argentina): por defecto Argentina (favorito). CÁMBIALO
    #   aquí si sabes/estimas otra cosa; toda la estrategia de "apostar distinto
    #   a Jaime" se recalcula sola.
    # Final y 3er puesto: Jaime apuesta al favorito del cruce real (cobertura).
    JAIME_BETS = {"SF1": (1, 2), "SF2": (1, 2)}

    def jaime_winner(self, which):
        sc = self.JAIME_BETS[which]; pair = self.SF1 if which == "SF1" else self.SF2
        if sc[0] > sc[1]: return pair[0]
        if sc[1] > sc[0]: return pair[1]
        return None   # Jaime apostó empate

    # ── EDITABLE: contra QUIÉN se diferencia cada jugador en sus apuestas ──
    # La idea: apostar DISTINTO a tu competencia directa para recortarle si se
    # da tu escenario. Valores posibles:
    #   "Jaime"  → te diferencias del líder (para pelear el título).
    #   "chalk"  → te diferencias de quien apuesta a los favoritos (útil para
    #              salir del último lugar o para escalar contra el pelotón).
    #   "<nombre>" → te diferencias de ese jugador puntual.
    REFERENCE = {
        "Pablo (tú)": "Jaime",     # persigue al líder
        "Martín":     "Jaime",     # persigue al líder
        "Caro":       "Jaime",     # persigue al líder
        "Coni":       "chalk",     # salir de zona San Marino: distínguete del pelotón
        "José Pablo": "chalk",     # escalar
        "Benja":      "chalk",     # escalar
        "Carola P":   "chalk",     # escalar
    }

    ES = {  # nombres de equipos en español para los informes
        "Spain": "España", "France": "Francia", "England": "Inglaterra",
        "Argentina": "Argentina", "Brazil": "Brasil", "Portugal": "Portugal",
        "Germany": "Alemania", "Netherlands": "Países Bajos", "Norway": "Noruega",
        "Belgium": "Bélgica", "Colombia": "Colombia", "Uruguay": "Uruguay",
        "USA": "EE.UU.", "Denmark": "Dinamarca", "Morocco": "Marruecos",
    }

    def __init__(self):
        with open(os.path.join(BASE, "predictions.json"), encoding="utf-8") as f:
            self.specials = json.load(f)["specials"]
        self.players = list(self.STANDINGS.keys())

    def pick(self, name):
        return self.specials[name]

    def es(self, team):
        return self.ES.get(team, team)


# ══════════════════════════════════════════════════════════════════════
#  AGENTE 2 · ESCENARIOS  (16 desenlaces exactos del podio)
# ══════════════════════════════════════════════════════════════════════
class AgenteEscenarios:
    def __init__(self, d): self.d = d

    def outcomes(self):
        d = self.d; outs = []
        for w1 in d.SF1:
            l1 = [t for t in d.SF1 if t != w1][0]
            for w2 in d.SF2:
                l2 = [t for t in d.SF2 if t != w2][0]
                for champ in (w1, w2):
                    run = w2 if champ == w1 else w1
                    for third in (l1, l2):
                        fourth = l2 if third == l1 else l1
                        outs.append(dict(champ=champ, run=run, third=third, fourth=fourth,
                                         finish={champ: 1, run: 2, third: 3, fourth: 4}))
        return outs

    def podium_pts(self, name, o):
        s = self.d.pick(name); S = self.d.SPECIAL_PTS; p = 0
        if s["first"] == o["champ"]: p += S["champ"]
        if s["second"] == o["run"]:  p += S["run"]
        if s["third"] == o["third"]: p += S["third"]
        return p


# ══════════════════════════════════════════════════════════════════════
#  AGENTE 3 · PARTIDOS  (Poisson -> marcadores y avance)
#  >>> SUPUESTO EDITABLE <<<  fuerza ELO y goles base.
# ══════════════════════════════════════════════════════════════════════
class AgentePartidos:
    ELO = {"Spain": 2085, "France": 2075, "Argentina": 2065, "England": 2010}
    GBASE = 1.35
    MAXG = 8

    def lambdas(self, a, b):
        dd = self.ELO[a] - self.ELO[b]
        return self.GBASE * 10 ** (dd / 800), self.GBASE * 10 ** (-dd / 800)

    @staticmethod
    def _pois(k, l): return math.exp(-l) * l ** k / math.factorial(k)

    def matrix(self, a, b):
        la, lb = self.lambdas(a, b)
        return {(ga, gb): self._pois(ga, la) * self._pois(gb, lb)
                for ga in range(self.MAXG + 1) for gb in range(self.MAXG + 1)}, la, lb

    def probs(self, a, b):
        M, la, lb = self.matrix(a, b)
        pa = sum(p for (x, y), p in M.items() if x > y)
        pd = sum(p for (x, y), p in M.items() if x == y)
        pb = 1 - pa - pd
        dd = self.ELO[a] - self.ELO[b]
        pa_pen = 1 / (1 + 10 ** (-dd / 800))
        adv_a = pa + pd * pa_pen
        top = sorted(M.items(), key=lambda kv: -kv[1])[:6]
        return dict(a=a, b=b, la=la, lb=lb, pa=pa, pd=pd, pb=pb,
                    adv_a=adv_a, adv_b=1 - adv_a, top=top)

    def advance(self, a, b):
        r = self.probs(a, b); return r["adv_a"], r["adv_b"]

    def modal_score(self, a, b, winner):
        """Marcador decisivo más probable (ga,gb) con el ganador indicado."""
        M, _, _ = self.matrix(a, b)
        best, bestp = (1, 0) if winner == a else (0, 1), -1
        for (ga, gb), p in M.items():
            ok = (ga > gb) if winner == a else (gb > ga)
            if ok and p > bestp:
                best, bestp = (ga, gb), p
        return best

    def draw_score(self, a, b):
        """Sortea un marcador (90') según Poisson."""
        la, lb = self.lambdas(a, b)
        return self._rpois(la), self._rpois(lb)

    @staticmethod
    def _rpois(l):
        import random as _r
        # inversión simple
        L = math.exp(-l); k = 0; p = 1.0
        while True:
            k += 1; p *= _r.random()
            if p <= L: return k - 1

    def tournament_probs(self):
        """P(campeón), P(finalista), P(3º) por equipo — enumeración exacta."""
        d0 = AgenteDatos()
        champ = {t: 0 for t in d0.ALIVE}
        final = {t: 0 for t in d0.ALIVE}
        third = {t: 0 for t in d0.ALIVE}
        a_sf1 = self.advance(*d0.SF1); a_sf2 = self.advance(*d0.SF2)
        padv = {d0.SF1[0]: a_sf1[0], d0.SF1[1]: a_sf1[1],
                d0.SF2[0]: a_sf2[0], d0.SF2[1]: a_sf2[1]}
        for w1 in d0.SF1:
            l1 = [t for t in d0.SF1 if t != w1][0]
            for w2 in d0.SF2:
                l2 = [t for t in d0.SF2 if t != w2][0]
                pth = padv[w1] * padv[w2]
                final[w1] += pth; final[w2] += pth
                cf = self.advance(w1, w2)   # final
                champ[w1] += pth * cf[0]; champ[w2] += pth * cf[1]
                c3 = self.advance(l1, l2)   # 3er puesto
                third[l1] += pth * c3[0]; third[l2] += pth * c3[1]
        return champ, final, third


# ══════════════════════════════════════════════════════════════════════
#  AGENTE 4 · ESPECIALES  (goleador y MVP, con exclusión mutua)
#  >>> SUPUESTOS EDITABLES <<<  Mbappé lidera la bota (8) y sigue vivo.
# ══════════════════════════════════════════════════════════════════════
class AgenteEspeciales:
    GOL = {
        "Mbappé": 0.50, "Harry Kane": 0.15, "Julián Álvarez": 0.07,
        "Lautaro Martínez": 0.05, "Mikel Oyarzabal": 0.05, "Ferran Torres": 0.03,
        "Lamine Yamal": 0.03, "Messi": 0.02, "Dembélé": 0.02, "Désiré Doué": 0.01,
        "Giuliano Simeone": 0.005, "Vinícius Júnior": 0.005, "__otro__": 0.045,
    }
    MVP_TEAM = {
        "Mbappé": "France", "Désiré Doué": "France", "Dembélé": "France",
        "Lamine Yamal": "Spain", "Rodri": "Spain", "Ferran Torres": "Spain",
        "Mikel Oyarzabal": "Spain", "Harry Kane": "England",
        "Julián Álvarez": "Argentina", "Lautaro Martínez": "Argentina", "Messi": "Argentina",
    }
    MVP_BASE = {
        "Mbappé": 0.32, "Lamine Yamal": 0.15, "Harry Kane": 0.08, "Julián Álvarez": 0.07,
        "Rodri": 0.05, "Messi": 0.05, "Dembélé": 0.03, "Désiré Doué": 0.03,
        "Ferran Torres": 0.03, "Mikel Oyarzabal": 0.02, "Lautaro Martínez": 0.03,
        "__otro__": 0.05,   # un jugador fuera de la lista (arquero, sorpresa, etc.)
    }
    MVP_MULT = {1: 2.2, 2: 1.3, 3: 0.7, 4: 0.3}

    def draw_gol(self):
        r = random.random(); c = 0
        for p, x in self.GOL.items():
            c += x
            if r <= c: return p
        return "__otro__"

    def draw_mvp(self, finish, exclude=None):
        # Regla: el goleador (exclude) no puede ser MVP.
        w = {}
        for p, base in self.MVP_BASE.items():
            if p == exclude:      # excluido por ganar la Bota de Oro
                continue
            t = self.MVP_TEAM.get(p)
            w[p] = base * (self.MVP_MULT.get(finish.get(t, 4), 1.0) if t else 1.0)
        tot = sum(w.values()); r = random.random() * tot; c = 0
        for p, x in w.items():
            c += x
            if r <= c: return p
        return next(iter(w))


# ──────────────────────────────────────────────────────────────────────
#  Helpers de apuestas y puntos de partido
# ──────────────────────────────────────────────────────────────────────
# Preferencia que dictan los ESPECIALES del jugador (None = le da igual ese partido).
def spec_pref_semi(d, name, pair):
    s = d.pick(name); a, b = pair
    def val(t):
        if s["first"] == t:  return 20   # campeón: debe ser finalista
        if s["second"] == t: return 15   # subcampeón: debe ser finalista
        if s["third"] == t:  return -10  # 3º: debe PERDER la semi
        return 0
    va, vb = val(a), val(b)
    return (a if va > vb else b) if va != vb else None


def spec_pref_final(d, name, X, Y):
    s = d.pick(name)
    if s["first"] in (X, Y):  return s["first"]
    if s["second"] == X:      return Y      # quiere que su subcampeón pierda la final
    if s["second"] == Y:      return X
    return None


def spec_pref_third(d, name, X, Y):
    s = d.pick(name)
    return s["third"] if s["third"] in (X, Y) else None


def _fav(par, X, Y):
    return X if par.advance(X, Y)[0] >= 0.5 else Y


# Wrappers con fallback al favorito (para referencias de jugador puntual).
def sf_pick(d, par, name, pair):
    return spec_pref_semi(d, name, pair) or _fav(par, *pair)


def final_pick(d, par, name, X, Y):
    return spec_pref_final(d, name, X, Y) or _fav(par, X, Y)


def third_pick(d, par, name, X, Y):
    return spec_pref_third(d, name, X, Y) or _fav(par, X, Y)


def ref_winner(d, par, ref, which, X=None, Y=None):
    """A quién apostaría la REFERENCIA en un partido. ref: 'Jaime'|'chalk'|nombre."""
    pair = d.SF1 if which == "SF1" else d.SF2 if which == "SF2" else (X, Y)
    if ref == "chalk":
        return _fav(par, *pair)
    if ref == "Jaime":
        if which == "SF1": return d.jaime_winner("SF1")
        if which == "SF2": return d.jaime_winner("SF2")
        return _fav(par, *pair)            # final/3º: cobertura al favorito
    if which == "SF1": return sf_pick(d, par, ref, d.SF1)
    if which == "SF2": return sf_pick(d, par, ref, d.SF2)
    if which == "final": return final_pick(d, par, ref, X, Y)
    return third_pick(d, par, ref, X, Y)


def resolve_pick(d, par, name, which, X=None, Y=None):
    """Apuesta RECOMENDADA sabiendo de antemano lo que apuesta tu referencia:
    1) si tus especiales dictan un pick, ese; 2) si te da igual ese partido,
    apuesta lo OPUESTO a tu referencia (separación gratis, no se pierden puntos)."""
    pair = d.SF1 if which == "SF1" else d.SF2 if which == "SF2" else (X, Y)
    if which in ("SF1", "SF2"): pref = spec_pref_semi(d, name, pair)
    elif which == "final":      pref = spec_pref_final(d, name, X, Y)
    else:                       pref = spec_pref_third(d, name, X, Y)
    if pref is not None:
        return pref
    ref = d.REFERENCE.get(name, "Jaime")
    rp = ref_winner(d, par, ref, which, X, Y)
    if rp is None:                          # la referencia apostó empate
        return _fav(par, *pair)
    return pair[0] if pair[1] == rp else pair[1]   # lo opuesto a la referencia


def _oo(h, a):
    return "H" if h > a else ("A" if a > h else "D")


def match_pts(ph, pa, rh, ra, win_pts, exact_pts):
    if ph == rh and pa == ra:            return exact_pts
    if _oo(ph, pa) == _oo(rh, ra):       return win_pts
    return 0


# ══════════════════════════════════════════════════════════════════════
#  AGENTE 5 · SIMULACION  (Monte Carlo del torneo restante)
# ══════════════════════════════════════════════════════════════════════
class AgenteSimulacion:
    def __init__(self, d, esc, par, esp, seed=7):
        self.d, self.e, self.par, self.esp = d, esc, par, esp
        random.seed(seed)
        # Precompute: predicción de CADA jugador para los 4 partidos (no cambia
        # entre sims). Cada jugador apuesta alineado a sus especiales en los 4;
        # JAIME usa sus apuestas configuradas (editable) en las semis y el
        # favorito en final/3º (cobertura de líder).
        def favmodal(X, Y):
            fav = X if par.advance(X, Y)[0] >= 0.5 else Y
            return par.modal_score(X, Y, fav)
        self._pred = {}
        for n in d.players:
            jaime = (n == "Jaime")
            if jaime:
                s1 = tuple(d.JAIME_BETS["SF1"]); s2 = tuple(d.JAIME_BETS["SF2"])
            else:
                s1 = par.modal_score(d.SF1[0], d.SF1[1], resolve_pick(d, par, n, "SF1"))
                s2 = par.modal_score(d.SF2[0], d.SF2[1], resolve_pick(d, par, n, "SF2"))
            fin, ter = {}, {}
            for X in d.SF1:            # finalista lado SF1 / perdedor lado SF1
                for Y in d.SF2:        # finalista lado SF2 / perdedor lado SF2
                    if jaime:
                        fin[(X, Y)] = favmodal(X, Y)
                        ter[(X, Y)] = favmodal(X, Y)
                    else:
                        fin[(X, Y)] = par.modal_score(X, Y, resolve_pick(d, par, n, "final", X, Y))
                        ter[(X, Y)] = par.modal_score(X, Y, resolve_pick(d, par, n, "third", X, Y))
            self._pred[n] = dict(sf1=s1, sf2=s2, final=fin, third=ter)

    def _bracket(self):
        d = self.d; par = self.par
        # semifinales: marcador 90' -> avance por ELO si hay empate
        s1 = par.draw_score(*d.SF1)
        if s1[0] != s1[1]:
            w1 = d.SF1[0] if s1[0] > s1[1] else d.SF1[1]
        else:
            w1 = d.SF1[0] if random.random() < par.advance(*d.SF1)[0] else d.SF1[1]
        l1 = [t for t in d.SF1 if t != w1][0]
        s2 = par.draw_score(*d.SF2)
        if s2[0] != s2[1]:
            w2 = d.SF2[0] if s2[0] > s2[1] else d.SF2[1]
        else:
            w2 = d.SF2[0] if random.random() < par.advance(*d.SF2)[0] else d.SF2[1]
        l2 = [t for t in d.SF2 if t != w2][0]
        # final y 3er puesto
        sf = par.draw_score(w1, w2)
        champ = w1 if (sf[0] > sf[1] or (sf[0] == sf[1] and random.random() < par.advance(w1, w2)[0])) else w2
        run = w2 if champ == w1 else w1
        s3 = par.draw_score(l1, l2)
        third = l1 if (s3[0] > s3[1] or (s3[0] == s3[1] and random.random() < par.advance(l1, l2)[0])) else l2
        fourth = l2 if third == l1 else l1
        return dict(champ=champ, run=run, third=third, fourth=fourth,
                    finish={champ: 1, run: 2, third: 3, fourth: 4},
                    w1=w1, l1=l1, w2=w2, l2=l2,
                    sf1=s1, sf2=s2, final=(w1, w2, sf), tercero=(l1, l2, s3))

    def _match_pts(self, name, o):
        """Puntos de partido del jugador en los 4 partidos (apuesta propia)."""
        pr = self._pred[name]
        w1, w2, sfsc = o["final"]; l1, l2, s3 = o["tercero"]
        pf = pr["final"][(w1, w2)]; pt = pr["third"][(l1, l2)]
        s1, s2 = pr["sf1"], pr["sf2"]
        return (match_pts(s1[0], s1[1], o["sf1"][0], o["sf1"][1], 3, 6) +
                match_pts(s2[0], s2[1], o["sf2"][0], o["sf2"][1], 3, 6) +
                match_pts(pf[0], pf[1], sfsc[0], sfsc[1], 4, 8) +
                match_pts(pt[0], pt[1], s3[0], s3[1], 4, 8))

    def _totals(self, o, gol, mvp, with_match=True):
        d = self.d; S = d.SPECIAL_PTS; tot = {}
        for n in d.players:
            s = d.pick(n); p = d.STANDINGS[n]
            if s["first"] == o["champ"]: p += S["champ"]
            if s["second"] == o["run"]:  p += S["run"]
            if s["third"] == o["third"]: p += S["third"]
            if s["scorer"] == gol:       p += S["gol"]
            if s["mvp"] == mvp:          p += S["mvp"]
            if with_match:               p += self._match_pts(n, o)
            tot[n] = p
        return tot

    def player_stats(self, name, N):
        win = top2 = top3 = top5 = last = rank_sum = 0
        nP = len(self.d.players)
        for _ in range(N):
            o = self._bracket()
            gol = self.esp.draw_gol(); mvp = self.esp.draw_mvp(o["finish"], exclude=gol)
            tot = self._totals(o, gol, mvp)
            order = sorted(tot, key=lambda n: -tot[n])
            r = order.index(name) + 1
            rank_sum += r
            win += (r == 1); top2 += (r <= 2); top3 += (r <= 3); top5 += (r <= 5)
            last += (r == nP)
        return dict(win=win / N, top2=top2 / N, top3=top3 / N, top5=top5 / N,
                    last=last / N, avg_rank=rank_sum / N)

    def simulate_all(self, N):
        """Una sola pasada que tabula a los 34 jugadores a la vez."""
        d = self.d; nP = len(d.players)
        agg = {n: dict(win=0, top3=0, top5=0, last=0, rank_sum=0) for n in d.players}
        for _ in range(N):
            o = self._bracket()
            gol = self.esp.draw_gol(); mvp = self.esp.draw_mvp(o["finish"], exclude=gol)
            tot = self._totals(o, gol, mvp)
            order = sorted(d.players, key=lambda n: -tot[n])
            for i, n in enumerate(order):
                r = i + 1; a = agg[n]
                a["rank_sum"] += r
                if r == 1: a["win"] += 1
                if r <= 3: a["top3"] += 1
                if r <= 5: a["top5"] += 1
                if r == nP: a["last"] += 1
        return {n: dict(win=a["win"]/N, top3=a["top3"]/N, top5=a["top5"]/N,
                        last=a["last"]/N, avg_rank=a["rank_sum"]/N)
                for n, a in agg.items()}

    def best_brackets(self, name, N):
        out = {}
        for o0 in self.e.outcomes():
            win = top3 = 0
            for _ in range(N):
                gol = self.esp.draw_gol(); mvp = self.esp.draw_mvp(o0["finish"], exclude=gol)
                # bracket fijo pero marcadores sorteados para puntos de partido
                o = dict(o0)
                o["sf1"] = self.par.draw_score(*self.d.SF1)
                o["sf2"] = self.par.draw_score(*self.d.SF2)
                w1 = o["champ"] if o["champ"] in self.d.SF1 else o["run"] if o["run"] in self.d.SF1 else o["third"]
                w1 = w1 if w1 in self.d.SF1 else self.d.SF1[0]
                l1 = [t for t in self.d.SF1 if t != w1][0]
                w2 = o["champ"] if o["champ"] in self.d.SF2 else o["run"] if o["run"] in self.d.SF2 else o["third"]
                w2 = w2 if w2 in self.d.SF2 else self.d.SF2[0]
                l2 = [t for t in self.d.SF2 if t != w2][0]
                o["w1"], o["l1"], o["w2"], o["l2"] = w1, l1, w2, l2
                o["final"] = (w1, w2, self.par.draw_score(w1, w2))
                o["tercero"] = (l1, l2, self.par.draw_score(l1, l2))
                tot = self._totals(o, gol, mvp)
                order = sorted(self.d.players, key=lambda n: -tot[n])
                r = order.index(name) + 1
                win += (r == 1); top3 += (r <= 3)
            out[(o0["champ"], o0["run"], o0["third"])] = (win / N, top3 / N)
        return out


# ══════════════════════════════════════════════════════════════════════
#  AGENTE 6 · ESTRATEGIA  (estilo de juego + pronósticos por jugador)
# ══════════════════════════════════════════════════════════════════════
class AgenteEstrategia:
    def __init__(self, d, esc, par, sim):
        self.d, self.e, self.par, self.sim = d, esc, par, sim

    def live_dead(self, name):
        s = self.d.pick(name); alive = self.d.ALIVE
        gol, mvp = s["scorer"], s["mvp"]
        rows = []
        rows.append(("1º " + self.d.es(s["first"]),  s["first"] in alive))
        rows.append(("2º " + self.d.es(s["second"]), s["second"] in alive))
        rows.append(("3º " + self.d.es(s["third"]),  s["third"] in alive))
        rows.append(("Goleador " + gol, True))   # jugadores vivos; se matiza en texto
        rows.append(("Balón de Oro " + mvp, True))
        conflict = (gol == mvp)
        return rows, conflict

    def _podium_pts_key(self, name, key):
        s = self.d.pick(name); S = self.d.SPECIAL_PTS; champ, run, third = key; p = 0
        if s["first"] == champ: p += S["champ"]
        if s["second"] == run:  p += S["run"]
        if s["third"] == third: p += S["third"]
        return p

    def dream_bracket(self, name, brackets):
        # Criterio robusto e intuitivo: primero el bracket que le da más PUNTOS
        # DE PODIO propios (alienta tus propios picks); la prob. de ganar y de
        # top-3 solo desempatan (p.ej. define slots que no tocan su podio).
        key = max(brackets, key=lambda k: (self._podium_pts_key(name, k),
                                           brackets[k][0], brackets[k][1]))
        return key, brackets[key]

    def predictions_for(self, bracket):
        """Marcadores recomendados coherentes con el bracket objetivo."""
        d = self.d; champ, run, third = bracket
        # finalista del lado SF1 (France/Spain) y del lado SF2 (England/Argentina)
        sf1_winner = champ if champ in d.SF1 else (run if run in d.SF1 else champ)
        sf2_winner = champ if champ in d.SF2 else (run if run in d.SF2 else run)
        sf1_loser = [t for t in d.SF1 if t != sf1_winner][0]
        sf2_loser = [t for t in d.SF2 if t != sf2_winner][0]
        return [
            (f"SF1 · {d.es(d.SF1[0])} vs {d.es(d.SF1[1])}",
             sf1_winner, self._score(d.SF1[0], d.SF1[1], sf1_winner)),
            (f"SF2 · {d.es(d.SF2[0])} vs {d.es(d.SF2[1])}",
             sf2_winner, self._score(d.SF2[0], d.SF2[1], sf2_winner)),
            (f"3er lugar · {d.es(sf1_loser)} vs {d.es(sf2_loser)}",
             third, self._score(sf1_loser, sf2_loser, third)),
            (f"Final · {d.es(sf1_winner)} vs {d.es(sf2_winner)}",
             champ, self._score(sf1_winner, sf2_winner, champ)),
        ]

    def _score(self, a, b, winner):
        """Marcador plausible a–b (perspectiva equipo a) con el ganador indicado."""
        adv = self.par.advance(a, b)
        pw = adv[0] if winner == a else adv[1]
        g_win, g_lose = ("2", "0") if pw >= 0.60 else ("2", "1")
        return f"{g_win} – {g_lose}" if winner == a else f"{g_lose} – {g_win}"

    def apuestas(self, name, bracket=None):
        """Las 4 apuestas recomendadas (SABIENDO de antemano lo que apuesta tu
        referencia): tus especiales mandan y, donde te da igual, apuestas lo
        opuesto a tu referencia (editable: Jaime / chalk / nombre). Marca ⚡ los
        partidos donde apuestas distinto. No se pierden puntos por fallar."""
        d = self.d; par = self.par; s = d.pick(name)
        ref = d.REFERENCE.get(name, "Jaime")
        reflabel = "Jaime" if ref == "Jaime" else ("los favoritos" if ref == "chalk" else ref)

        # picks recomendados (mismos que usa la simulación)
        f1 = resolve_pick(d, par, name, "SF1")     # finalista lado SF1
        f2 = resolve_pick(d, par, name, "SF2")     # finalista lado SF2
        l1 = [t for t in d.SF1 if t != f1][0]
        l2 = [t for t in d.SF2 if t != f2][0]
        champ = resolve_pick(d, par, name, "final", f1, f2)
        third = resolve_pick(d, par, name, "third", l1, l2)

        # apuestas de la referencia (para comparar)
        r1 = ref_winner(d, par, ref, "SF1"); r2 = ref_winner(d, par, ref, "SF2")
        r3 = ref_winner(d, par, ref, "third", l1, l2); rf = ref_winner(d, par, ref, "final", f1, f2)

        def why_semi(pick, pair):
            other = [t for t in pair if t != pick][0]
            if s["first"] == pick:  return "tu campeón: debe ser finalista"
            if s["second"] == pick: return "tu subcampeón: debe ser finalista"
            if s["third"] == other: return f"así {d.es(other)} cae al 3er puesto (tu 3º)"
            return f"te da igual: apuestas distinto a {reflabel} para separarte"

        def refname(w):
            return d.es(w) if w else "empate"

        rows = [
            dict(match=f"Semifinal · {d.es(d.SF1[0])} vs {d.es(d.SF1[1])}",
                 pick=d.es(f1), score=self._score(d.SF1[0], d.SF1[1], f1),
                 fav=(f1 == _fav(par, *d.SF1)), reason=why_semi(f1, d.SF1),
                 ref=refname(r1), diff=(f1 != r1)),
            dict(match=f"Semifinal · {d.es(d.SF2[0])} vs {d.es(d.SF2[1])}",
                 pick=d.es(f2), score=self._score(d.SF2[0], d.SF2[1], f2),
                 fav=(f2 == _fav(par, *d.SF2)), reason=why_semi(f2, d.SF2),
                 ref=refname(r2), diff=(f2 != r2)),
            dict(match=f"3er lugar · {d.es(l1)} vs {d.es(l2)}",
                 pick=d.es(third), score=self._score(l1, l2, third),
                 fav=(third == _fav(par, l1, l2)),
                 reason=("tu 3º: +10" if s["third"] == third else
                         f"te da igual: apuestas distinto a {reflabel}"),
                 ref=refname(r3), diff=(third != r3)),
            dict(match=f"Final · {d.es(f1)} vs {d.es(f2)}",
                 pick=d.es(champ), score=self._score(f1, f2, champ),
                 fav=(champ == _fav(par, f1, f2)),
                 reason=("tu campeón: +20" if s["first"] == champ else
                         "tu subcampeón pierde la final" if s["second"] == champ else
                         f"te da igual: apuestas distinto a {reflabel}"),
                 ref=refname(rf), diff=(champ != rf)),
        ]
        return rows, reflabel

    def style(self, name):
        d = self.d; pts = d.STANDINGS[name]
        order = sorted(d.players, key=lambda n: -d.STANDINGS[n])
        rank = order.index(name) + 1
        leader = d.STANDINGS[order[0]]; last = d.STANDINGS[order[-1]]
        gap_lead = leader - pts; gap_last = pts - last
        n = len(order)
        if rank <= 6:
            label = "Cobertura / chalk"
            desc = ("Estás arriba: juega a los favoritos y replica lo que harían tus "
                    "rivales directos. No busques héroe; que nadie te pase barato.")
        elif rank <= n * 0.6:
            label = "Contrarian selectivo"
            desc = ("Vas en el pelotón: apuesta tus marcadores al escenario donde tus "
                    "especiales vivos pagan, aunque no sea el resultado más probable.")
        else:
            label = "Máxima varianza"
            desc = ("Vas atrás: necesitas caos. Pronostica resultados diferenciados y "
                    "alienta al outsider; tu única vía es que pase lo inesperado.")
        warn_last = (rank >= n - 3)
        return dict(rank=rank, gap_lead=gap_lead, gap_last=gap_last,
                    label=label, desc=desc, warn_last=warn_last)


# ══════════════════════════════════════════════════════════════════════
#  GENERADOR DE INFORMES (markdown)
# ══════════════════════════════════════════════════════════════════════
DISPLAY = {"Pablo (tú)": "Pablo", "Carola P": "Carola Puga"}
REL = {"Pablo (tú)": "Tú", "Martín": "Hermano", "Caro": "Hermana", "Benja": "Hermano",
       "José Pablo": "Papá", "Carola P": "Mamá", "Coni": "Cuñada"}


def comp_rank(d, name):
    return 1 + sum(1 for n in d.players if d.STANDINGS[n] > d.STANDINGS[name])


def gol_mvp_note(d, name):
    s = d.pick(name); gol, mvp = s["scorer"], s["mvp"]
    if gol == mvp:
        return (f"⚠️ Elegiste a **{gol}** para goleador **y** para mejor jugador, pero "
                f"un jugador no puede ganar los dos. En la práctica solo puedes sumar "
                f"**uno** de esos dos premios (máx. 10 pts, no 20).")
    if gol == "Mbappé":
        return (f"Tu goleador es **Mbappé** (favorito, hoy 8 goles). Pero ojo: si Mbappé "
                f"gana la Bota de Oro, ya **no** puede ser tu MVP **{mvp}** salvo que ese "
                f"sea otro jugador.")
    if mvp == "Mbappé":
        return (f"Tu MVP es **Mbappé** (favorito). Como el goleador no puede ser también "
                f"MVP, para que tu Mbappé-MVP pague hace falta que **Mbappé NO sea el "
                f"máximo goleador** (que lo supere otro, idealmente tu goleador **{gol}**).")
    return (f"Tu goleador (**{gol}**) y tu MVP (**{mvp}**) son jugadores distintos: pueden "
            f"pagarte los dos a la vez.")


def generar_informes(d, esc, par, esp, sim, estr, out_path, N=20000, NB=4000):
    L = []
    W = L.append
    W("# 📋 Informes de estrategia — Polla Mundialera 2026\n")
    W("_Estado: cuartos jugados (12-jul). Faltan semifinales, 3er puesto, final y los "
      "premios especiales. Puntaje del **reglamento**; el goleador **no** puede ser "
      "también mejor jugador._\n")

    # -- sección común: probabilidades de partidos --
    W("## 🔮 Probabilidades de resultados (comunes a todos)\n")
    W("Modelo Poisson sobre fuerza de equipos (editable en el código).\n")
    for a, b in (d.SF1, d.SF2):
        r = par.probs(a, b)
        W(f"**Semifinal · {d.es(a)} vs {d.es(b)}**  ")
        W(f"→ avanza **{d.es(a)} {r['adv_a']*100:.0f}%** / **{d.es(b)} {r['adv_b']*100:.0f}%** "
          f"(gana en 90′: {d.es(a)} {r['pa']*100:.0f}%, empate {r['pd']*100:.0f}%, {d.es(b)} {r['pb']*100:.0f}%)  ")
        tops = " · ".join(f"{d.es(a)} {x}-{y} {d.es(b)} {p*100:.0f}%" for (x, y), p in r["top"][:4])
        W(f"Marcadores más probables: {tops}\n")
    champ, final, third = par.tournament_probs()
    W("**Camino a la final** (campeón / finalista / 3er lugar):\n")
    W("| Equipo | Campeón | Finalista | 3er lugar |")
    W("|---|---|---|---|")
    for t in sorted(d.ALIVE, key=lambda x: -champ[x]):
        W(f"| {d.es(t)} | {champ[t]*100:.0f}% | {final[t]*100:.0f}% | {third[t]*100:.0f}% |")
    W("\n> La final más probable es **España/Argentina** (los dos con mayor prob. de "
      "llegar por lados opuestos del cuadro).\n")
    W("---\n")

    stats_all = sim.simulate_all(N)

    jw1 = d.jaime_winner("SF1"); jw2 = d.jaime_winner("SF2")
    W(f"## 👑 Cómo apuesta Jaime (el líder, {fmt_pct(stats_all['Jaime']['win'])} de ganar)\n")
    W(f"Apuestas de Jaime (editable en el código): **SF1 → {d.es(jw1) if jw1 else 'empate'}**, "
      f"**SF2 → {d.es(jw2) if jw2 else 'empate'}**, final y 3er puesto al favorito.\n")
    W("> **Idea clave (tu pregunta):** como no se pierden puntos por fallar, a los que van "
      "detrás les conviene **apostar DISTINTO a Jaime**. Si se da el resultado que necesitan "
      "(el de sus especiales), suman puntos de partido donde Jaime no, y así **le recortan**. "
      "En cada informe se marca ⚡ cuándo tu apuesta difiere de la de Jaime.\n")
    W("---\n")
    players = ["Pablo (tú)", "Martín", "José Pablo", "Benja", "Coni", "Caro", "Carola P"]
    for name in players:
        disp = DISPLAY.get(name, name)
        s = d.pick(name); rank = comp_rank(d, name); pts = d.STANDINGS[name]
        st = estr.style(name)
        stats = stats_all[name]
        brackets = sim.best_brackets(name, NB)
        best, (bw, bt3) = estr.dream_bracket(name, brackets)
        rows, conflict = estr.live_dead(name)
        apu, reflabel = estr.apuestas(name, best)

        W(f"## 🧑 Informe · {disp}\n")
        W(f"**Posición actual:** #{rank} con **{pts} pts** "
          f"(líder Jaime 136, últimos ~75). Distancia al líder: **{136-pts}**.\n")

        # especiales vivos/muertos
        W("**Tus especiales (bloqueados desde el inicio):**\n")
        W("| Predicción | Estado |")
        W("|---|---|")
        labels = ["1º", "2º", "3º", "Goleador", "Balón de Oro"]
        for (txt, alive) in rows:
            estado = "✅ vivo" if alive else "❌ **MUERTO** (equipo eliminado)"
            W(f"| {txt} | {estado} |")
        W("")
        W(gol_mvp_note(d, name) + "\n")

        # probabilidades (incluyen puntos de partido)
        W("**Tus probabilidades** (Monte Carlo, {} sims, con puntos de partido):\n".format(N))
        W(f"- 🏆 Ganar la polla: **{fmt_pct(stats['win'])}**")
        W(f"- 🥉 Terminar top-3: **{fmt_pct(stats['top3'])}**  ·  Top-5: **{fmt_pct(stats['top5'])}**")
        W(f"- 🔻 Terminar último: **{fmt_pct(stats['last'])}**  ·  puesto medio esperado: ~#{stats['avg_rank']:.0f}\n")

        # qué alentar (texto según el nivel real del jugador)
        pod = estr._podium_pts_key(name, best)
        W("**Qué debes alentar** (tu mejor escenario):\n")
        W(f"- Campeón **{d.es(best[0])}**, subcampeón **{d.es(best[1])}**, 3º **{d.es(best[2])}** "
          f"(te da +{pod} de podio).")
        if stats["win"] >= 0.02:
            W(f"- En ese cuadro tu prob. de **ganar** sube a ~{bw*100:.0f}% y de top-3 a ~{bt3*100:.0f}%. "
              f"Eres candidato real: ese es el resultado que tienes que empujar.\n")
        elif stats["top5"] >= 0.02:
            W(f"- El título es casi inalcanzable, pero ese cuadro (más tus especiales) te "
              f"mete en pelea por el **top-5**. Apunta a escalar, no al 1º.\n")
        else:
            W(f"- El título está fuera de alcance por la distancia. Tu objetivo realista es "
              f"**sumar puntos y escalar puestos** (y, si estás abajo, salir de la zona roja).\n")

        # apuestas (pronósticos a enviar) con comparación vs la referencia del jugador
        ndiff = sum(1 for a in apu if a["diff"])
        W(f"**Tus apuestas** (pronósticos a enviar; te comparas contra **{reflabel}**):\n")
        W(f"| Partido | Tu apuesta | Marcador | {reflabel.capitalize()} | Por qué |")
        W("|---|---|---|---|---|")
        for a in apu:
            jcell = ("⚡ **distinto** (" + a["ref"] + ")") if a["diff"] else a["ref"]
            W(f"| {a['match']} | {a['pick']} | **{a['score']}** | {jcell} | {a['reason']} |")
        W("")
        W(f"> Apuestas **distintas a {reflabel}: {ndiff} de 4**. Cada una que aciertes en tu "
          f"escenario te separa de tu competencia directa.\n")

        # escenario San Marino
        W("**Escenario San Marino:** " + _san_marino(d, name, stats["last"], rank, len(d.players)) + "\n")

        # estilo de juego
        W(f"**Estilo de juego: _{st['label']}_.** {st['desc']}\n")
        W("---\n")

    W("_Generado por `estrategia/agentes_polla.py`. Supuestos de fuerza de equipos y "
      "carrera de goleador editables en el código; el ‘qué alentar’ es combinatoria "
      "exacta de los 16 desenlaces del podio._")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return out_path


REPORT_PLAYERS = ["Pablo (tú)", "Martín", "José Pablo", "Benja", "Coni", "Caro", "Carola P"]


def fmt_pct(x):
    """Formatea una probabilidad (fracción) con decimales útiles cuando es chica."""
    v = x * 100
    if v >= 1:    return f"{v:.1f}%"
    if v >= 0.01: return f"{v:.2f}%"
    if v > 0:     return f"{v:.3f}%"
    return "<0.001%"


def _san_marino(d, name, last_p, rank, nP):
    if last_p >= 0.15:
        return (f"🚨 Riesgo ALTO de último lugar: **{last_p*100:.0f}%** de terminar 34º "
                f"(polera de San Marino). Para salvarte necesitas que **tus especiales "
                f"vivos sumen** (que tu equipo llegue lejos) y acertar pronósticos de "
                f"partidos; recuerda que **no pierdes puntos por fallar**, así que arriesga. "
                f"El reglamento además castiga a quien intente quedar último a propósito.")
    if last_p >= 0.02:
        return (f"⚠️ Riesgo moderado de último lugar (~{last_p*100:.0f}%). Manda tus "
                f"pronósticos (no cuesta nada) y ojalá tu equipo sume: eso te aleja del fondo.")
    return "✅ Prácticamente sin riesgo de último lugar."


def _key_insight(d, name, s, stats, best, podium):
    gol, mvp = s["scorer"], s["mvp"]
    if stats["win"] >= 0.02:
        return (f"Eres candidato real ({stats['win']*100:.0f}% de ganar). Tu podio vivo "
                f"({d.es(s['first'])}/{d.es(s['second'])}/{d.es(s['third'])}) es tu fortaleza: "
                f"empuja ese cuadro y no te compliques.")
    if gol == mvp:
        return (f"Tu goleador y tu MVP son el mismo jugador ({gol}): solo puedes sumar uno "
                f"de los dos. Ese techo te limita; necesitas además acertar podio y partidos.")
    if mvp == "Mbappé" and gol != "Mbappé":
        return (f"Tu combo depende de que **{gol}** sea goleador: eso libera a Mbappé para "
                f"MVP y te paga los dos. Si Mbappé es goleador, pierdes ambos.")
    return (f"Tu mejor escenario ({d.es(best[0])} campeón, {d.es(best[2])} 3º) te da +{podium} "
            f"de podio. El título está lejos; juega a escalar y a no quedar último.")


def export_dashboard(d, esc, par, esp, sim, estr, out_path, N=30000, NB=2500):
    stats_all = sim.simulate_all(N)
    champ, final, third = par.tournament_probs()
    data = {"generated": True, "leader": {"name": "Jaime", "pts": 136}}
    # sección común
    sf = []
    for a, b in (d.SF1, d.SF2):
        r = par.probs(a, b)
        sf.append(dict(a=d.es(a), b=d.es(b), advA=round(r["adv_a"]*100),
                       advB=round(r["adv_b"]*100),
                       scores=[f"{d.es(a)} {x}-{y} {d.es(b)} · {p*100:.0f}%"
                               for (x, y), p in r["top"][:3]]))
    data["semis"] = sf
    data["camino"] = [dict(team=d.es(t), champ=round(champ[t]*100),
                           final=round(final[t]*100), third=round(third[t]*100))
                      for t in sorted(d.ALIVE, key=lambda x: -champ[x])]
    jw1 = d.jaime_winner("SF1"); jw2 = d.jaime_winner("SF2")
    data["jaime"] = dict(sf1=d.es(jw1) if jw1 else "empate",
                         sf2=d.es(jw2) if jw2 else "empate",
                         winPct=fmt_pct(stats_all["Jaime"]["win"]))
    # jugadores
    players = []
    for name in REPORT_PLAYERS:
        s = d.pick(name); rank = comp_rank(d, name); pts = d.STANDINGS[name]
        st = estr.style(name); stx = stats_all[name]
        brackets = sim.best_brackets(name, NB)
        best, (bw, bt3) = estr.dream_bracket(name, brackets)
        rows, conflict = estr.live_dead(name)
        podium = estr._podium_pts_key(name, best)
        apu, reflabel = estr.apuestas(name, best)
        ndiff = sum(1 for a in apu if a["diff"])
        tier = ("candidato" if stx["win"] >= 0.02 else
                "longshot" if stx["top5"] >= 0.02 else "fondo")
        players.append(dict(
            name=name, disp=DISPLAY.get(name, name), rel=REL.get(name, ""),
            rank=rank, pts=pts, gapLead=136 - pts, tier=tier,
            win=round(stx["win"]*100, 1), winStr=fmt_pct(stx["win"]),
            top3=round(stx["top3"]*100, 1),
            top5=round(stx["top5"]*100, 1), last=round(stx["last"]*100),
            avgRank=round(stx["avg_rank"]),
            specials=[dict(txt=t, alive=al) for (t, al) in rows],
            golMvpNote=gol_mvp_note(d, name),
            dream=dict(champ=d.es(best[0]), run=d.es(best[1]), third=d.es(best[2]),
                       podium=podium, condWin=round(bw*100), condTop3=round(bt3*100)),
            apuestas=apu, ndiff=ndiff, ref=reflabel,
            style=dict(label=st["label"], desc=st["desc"]),
            sanMarino=_san_marino(d, name, stx["last"], rank, len(d.players)),
            keyInsight=_key_insight(d, name, s, stx, best, podium),
        ))
    data["players"] = players
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return out_path


# ══════════════════════════════════════════════════════════════════════
#  RESUMEN GENERAL
# ══════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=60000)
    ap.add_argument("--informes", action="store_true", help="genera estrategia/INFORMES.md")
    ap.add_argument("--dashboard", action="store_true", help="genera estrategia/dashboard_data.json")
    args = ap.parse_args()
    if args.dashboard:
        d = AgenteDatos(); esc = AgenteEscenarios(d); par = AgentePartidos()
        esp = AgenteEspeciales(); sim = AgenteSimulacion(d, esc, par, esp)
        estr = AgenteEstrategia(d, esc, par, sim)
        p = export_dashboard(d, esc, par, esp, sim, estr,
                             os.path.join(BASE, "estrategia", "dashboard_data.json"),
                             N=args.sims)
        print("Dashboard data en", p)
        return
    if args.informes:
        d = AgenteDatos(); esc = AgenteEscenarios(d); par = AgentePartidos()
        esp = AgenteEspeciales(); sim = AgenteSimulacion(d, esc, par, esp)
        estr = AgenteEstrategia(d, esc, par, sim)
        p = generar_informes(d, esc, par, esp, sim, estr,
                             os.path.join(BASE, "estrategia", "INFORMES.md"),
                             N=args.sims, NB=max(3000, args.sims // 8))
        print("Informes escritos en", p)
        return
    d = AgenteDatos(); esc = AgenteEscenarios(d); par = AgentePartidos()
    esp = AgenteEspeciales(); sim = AgenteSimulacion(d, esc, par, esp)
    estr = AgenteEstrategia(d, esc, par, sim)

    print("PROBABILIDADES DE PARTIDOS (Poisson, ELO editable)")
    for a, b in (d.SF1, d.SF2):
        r = par.probs(a, b)
        print(f"\n {d.es(a)} vs {d.es(b)}  (xG {r['la']:.2f}-{r['lb']:.2f})")
        print(f"   avanza {d.es(a)} {r['adv_a']*100:.0f}%  |  avanza {d.es(b)} {r['adv_b']*100:.0f}%")
        for (x, y), p in r["top"][:4]:
            print(f"     {d.es(a)} {x}-{y} {d.es(b)}: {p*100:.1f}%")
    champ, final, third = par.tournament_probs()
    print("\n Camino a la final:")
    for t in sorted(d.ALIVE, key=lambda x: -champ[x]):
        print(f"   {d.es(t):<11} campeón {champ[t]*100:4.0f}%  finalista {final[t]*100:4.0f}%  3º {third[t]*100:4.0f}%")

    print("\nPROBABILIDAD DE POSICIÓN FINAL (7 jugadores del informe)")
    for name in ["Pablo (tú)", "Martín", "José Pablo", "Benja", "Coni", "Caro", "Carola P"]:
        s = sim.player_stats(name, args.sims)
        st = estr.style(name)
        print(f"   {name:<12} #{st['rank']:<2} {d.STANDINGS[name]}pts | "
              f"P(1º)={s['win']*100:4.1f}% top3={s['top3']*100:4.1f}% top5={s['top5']*100:4.1f}% "
              f"| estilo: {st['label']}")


if __name__ == "__main__":
    main()
