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
        "Mbappé": 0.34, "Lamine Yamal": 0.16, "Harry Kane": 0.08, "Julián Álvarez": 0.07,
        "Rodri": 0.05, "Messi": 0.05, "Dembélé": 0.03, "Désiré Doué": 0.03,
        "Ferran Torres": 0.03, "Mikel Oyarzabal": 0.02, "Lautaro Martínez": 0.03,
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


# ══════════════════════════════════════════════════════════════════════
#  AGENTE 5 · SIMULACION  (Monte Carlo del torneo restante)
# ══════════════════════════════════════════════════════════════════════
class AgenteSimulacion:
    def __init__(self, d, esc, par, esp, seed=7):
        self.d, self.e, self.par, self.esp = d, esc, par, esp
        random.seed(seed)

    def _bracket(self):
        d = self.d
        pa = self.par.advance(*d.SF1); w1 = d.SF1[0] if random.random() < pa[0] else d.SF1[1]
        l1 = [t for t in d.SF1 if t != w1][0]
        pb = self.par.advance(*d.SF2); w2 = d.SF2[0] if random.random() < pb[0] else d.SF2[1]
        l2 = [t for t in d.SF2 if t != w2][0]
        cf = self.par.advance(w1, w2); champ = w1 if random.random() < cf[0] else w2
        run = w2 if champ == w1 else w1
        c3 = self.par.advance(l1, l2); third = l1 if random.random() < c3[0] else l2
        fourth = l2 if third == l1 else l1
        return dict(champ=champ, run=run, third=third, fourth=fourth,
                    finish={champ: 1, run: 2, third: 3, fourth: 4})

    def _totals(self, o, gol, mvp):
        d = self.d; S = d.SPECIAL_PTS; tot = {}
        for n in d.players:
            s = d.pick(n); p = d.STANDINGS[n]
            if s["first"] == o["champ"]: p += S["champ"]
            if s["second"] == o["run"]:  p += S["run"]
            if s["third"] == o["third"]: p += S["third"]
            if s["scorer"] == gol:       p += S["gol"]
            if s["mvp"] == mvp:          p += S["mvp"]
            tot[n] = p
        return tot

    def player_stats(self, name, N):
        win = top2 = top3 = top5 = rank_sum = 0
        for _ in range(N):
            o = self._bracket()
            gol = self.esp.draw_gol(); mvp = self.esp.draw_mvp(o["finish"], exclude=gol)
            tot = self._totals(o, gol, mvp)
            order = sorted(tot, key=lambda n: -tot[n])
            r = order.index(name) + 1
            rank_sum += r
            win += (r == 1); top2 += (r <= 2); top3 += (r <= 3); top5 += (r <= 5)
        return dict(win=win / N, top2=top2 / N, top3=top3 / N, top5=top5 / N,
                    avg_rank=rank_sum / N)

    def best_brackets(self, name, N):
        out = {}
        for o in self.e.outcomes():
            win = top3 = 0
            for _ in range(N):
                gol = self.esp.draw_gol(); mvp = self.esp.draw_mvp(o["finish"], exclude=gol)
                tot = self._totals(o, gol, mvp)
                order = sorted(tot, key=lambda n: -tot[n])
                r = order.index(name) + 1
                win += (r == 1); top3 += (r <= 3)
            out[(o["champ"], o["run"], o["third"])] = (win / N, top3 / N)
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
        # Maximiza P(win); a igualdad, P(top3); a igualdad (p.ej. trailers con
        # todo en 0), el bracket que le da más PUNTOS DE PODIO propios.
        key = max(brackets, key=lambda k: (brackets[k][0], brackets[k][1],
                                           self._podium_pts_key(name, k)))
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

    players = ["Pablo (tú)", "Martín", "José Pablo", "Benja", "Coni", "Caro", "Carola P"]
    for name in players:
        disp = DISPLAY.get(name, name)
        s = d.pick(name); rank = comp_rank(d, name); pts = d.STANDINGS[name]
        st = estr.style(name)
        stats = sim.player_stats(name, N)
        brackets = sim.best_brackets(name, NB)
        best, (bw, bt3) = estr.dream_bracket(name, brackets)
        rows, conflict = estr.live_dead(name)
        preds = estr.predictions_for(best)

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

        # probabilidades
        W("**Tus probabilidades** (Monte Carlo, {} sims):\n".format(N))
        W(f"- 🏆 Ganar la polla: **{stats['win']*100:.1f}%**")
        W(f"- 🥉 Terminar top-3: **{stats['top3']*100:.1f}%**")
        W(f"- Top-5: **{stats['top5']*100:.1f}%**  ·  puesto medio esperado: ~#{stats['avg_rank']:.0f}\n")

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

        # pronósticos recomendados
        W("**Pronósticos recomendados** (envíalos antes de cada partido):\n")
        W("| Partido | Tu marcador |")
        W("|---|---|")
        for titulo, winner, score in preds:
            W(f"| {titulo} | **{score}** |")
        W("")

        # estilo de juego
        W(f"**Estilo de juego: _{st['label']}_.** {st['desc']}")
        if st["warn_last"]:
            W("\n> ⚠️ Estás en zona de último lugar (polera de San Marino). Recuerda: el "
              "reglamento castiga con puntaje quien intente **quedar último a propósito**, "
              "así que juega a ganar puntos, no a perderlos.")
        W("\n---\n")

    W("_Generado por `estrategia/agentes_polla.py`. Supuestos de fuerza de equipos y "
      "carrera de goleador editables en el código; el ‘qué alentar’ es combinatoria "
      "exacta de los 16 desenlaces del podio._")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return out_path


# ══════════════════════════════════════════════════════════════════════
#  RESUMEN GENERAL
# ══════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=40000)
    ap.add_argument("--informes", action="store_true", help="genera estrategia/INFORMES.md")
    args = ap.parse_args()
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
