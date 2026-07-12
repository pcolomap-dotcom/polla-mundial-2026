#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agentes_polla.py — Sistema de agentes de análisis para la Polla Mundialera
===========================================================================

Ayuda a "Pablo (tú)" a decidir cómo jugar lo que queda del Mundial 2026 y
a estimar sus probabilidades de ganar la polla.

Estado del torneo al 12-jul-2026: se jugaron los CUARTOS DE FINAL.
Quedan por jugarse: 2 semifinales, el partido por el 3er lugar y la final,
más la resolución de los premios especiales (campeón/subcampeón/3º,
goleador y mejor jugador), que todavía NO se han otorgado.

El sistema está compuesto por 5 agentes, cada uno con una responsabilidad:

  1. AgenteDatos       -> carga posiciones actuales, especiales y el cuadro.
  2. AgenteEscenarios  -> enumera los 16 desenlaces posibles del podio.
  3. AgenteEspeciales  -> modela goleador y mejor jugador (probabilístico).
  4. AgenteSimulacion  -> Monte Carlo: probabilidad de posición final de Pablo.
  5. AgenteEstrategia  -> traduce todo en un plan concreto de qué hacer/alentar.

Uso:  python3 estrategia/agentes_polla.py
      python3 estrategia/agentes_polla.py --sims 100000

NOTA sobre puntajes: hay una discrepancia entre el reglamento PDF y el pie
del ranking del sitio (ver AgenteDatos.SCHEMES). El sistema corre ambos.
Los supuestos de fuerza de equipos y de goleador/MVP son EDITABLES abajo y
están claramente marcados: cámbialos y vuelve a correr.
"""
from __future__ import annotations
import json, os, random, argparse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ME = "Pablo (tú)"


# ══════════════════════════════════════════════════════════════════════
#  AGENTE 1 · DATOS
#  Única fuente de verdad: posiciones actuales (ranking live) + especiales.
# ══════════════════════════════════════════════════════════════════════
class AgenteDatos:
    # Posiciones al cierre de cuartos de final (fuente: Ranking live / PDF).
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

    # Cuadro de semifinales (cuartos ya jugados):
    #   Francia 2-0 Marruecos | España 2-1 Bélgica
    #   Noruega 1-2 Inglaterra | Argentina 3-1 Suiza
    SF1 = ("France", "Spain")       # Partido 101 · 14 jul
    SF2 = ("England", "Argentina")  # Partido 102 · 15 jul
    ALIVE = ["France", "Spain", "England", "Argentina"]

    # Dos esquemas de puntaje de ESPECIALES en conflicto entre las fuentes.
    # (El puntaje de PARTIDOS sí está claro: escala por ronda del reglamento;
    #  semis 3/6, 3er y final 4/8.  Eso se maneja en AgenteEstrategia.)
    SCHEMES = {
        # Reglamento PDF oficial:
        "reglamento": dict(champ=20, run=15, third=10, gol=10, mvp=10),
        # Pie del ranking del sitio (app):
        "dashboard":  dict(champ=25, run=15, third=10, gol=15, mvp=20),
    }

    # Goleador líder actual (dato live): Mbappé con 8 goles al 12-jul.
    TOP_SCORER_NOW = ("Mbappé", 8)

    def __init__(self):
        with open(os.path.join(BASE, "predictions.json"), encoding="utf-8") as f:
            self.specials = json.load(f)["specials"]
        self.players = list(self.STANDINGS.keys())

    def pick(self, name):
        return self.specials[name]


# ══════════════════════════════════════════════════════════════════════
#  AGENTE 2 · ESCENARIOS
#  Con 4 semifinalistas el podio tiene solo 16 desenlaces: se enumeran
#  EXACTAMENTE (sin supuestos de probabilidad).
# ══════════════════════════════════════════════════════════════════════
class AgenteEscenarios:
    def __init__(self, datos: AgenteDatos):
        self.d = datos

    def outcomes(self):
        d = self.d
        outs = []
        for w1 in d.SF1:                          # ganador SF1
            l1 = [t for t in d.SF1 if t != w1][0]
            for w2 in d.SF2:                      # ganador SF2
                l2 = [t for t in d.SF2 if t != w2][0]
                for champ in (w1, w2):            # ganador de la final
                    run = w2 if champ == w1 else w1
                    for third in (l1, l2):        # ganador del 3er puesto
                        fourth = l2 if third == l1 else l1
                        outs.append(dict(champ=champ, run=run, third=third,
                                         fourth=fourth,
                                         finish={champ: 1, run: 2, third: 3, fourth: 4}))
        return outs

    def podium_pts(self, name, o, S):
        s = self.d.pick(name); p = 0
        if s["first"] == o["champ"]: p += S["champ"]
        if s["second"] == o["run"]:  p += S["run"]
        if s["third"] == o["third"]: p += S["third"]
        return p

    def enumerate_pablo(self, scheme="reglamento"):
        """Rank de Pablo en cada uno de los 16 brackets (solo podio)."""
        d = self.d; S = d.SCHEMES[scheme]
        rows = []
        for o in self.outcomes():
            tot = {n: d.STANDINGS[n] + self.podium_pts(n, o, S) for n in d.players}
            order = sorted(tot, key=lambda n: -tot[n])
            rows.append(dict(champ=o["champ"], run=o["run"], third=o["third"],
                             pablo_add=self.podium_pts(ME, o, S),
                             pablo_pts=tot[ME], pablo_rank=order.index(ME) + 1,
                             leader=order[0], leader_pts=tot[order[0]]))
        return rows


# ══════════════════════════════════════════════════════════════════════
#  AGENTE 3 · ESPECIALES  (goleador y mejor jugador — probabilístico)
#  >>> SUPUESTOS EDITABLES <<<  Mbappé lidera la bota con 8 goles y sigue
#  vivo. Cambia estos números si tienes mejor información.
# ══════════════════════════════════════════════════════════════════════
class AgenteEspeciales:
    GOL = {  # prob. de terminar como goleador del torneo
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
    MVP_MULT = {1: 2.2, 2: 1.3, 3: 0.7, 4: 0.3}   # peso según cómo terminó su equipo

    def draw_gol(self):
        r = random.random(); c = 0
        for p, x in self.GOL.items():
            c += x
            if r <= c:
                return p
        return "__otro__"

    def draw_mvp(self, finish):
        w = {}
        for p, base in self.MVP_BASE.items():
            t = self.MVP_TEAM.get(p)
            w[p] = base * (self.MVP_MULT.get(finish.get(t, 4), 1.0) if t else 1.0)
        tot = sum(w.values()); r = random.random() * tot; c = 0
        for p, x in w.items():
            c += x
            if r <= c:
                return p
        return "Mbappé"


# ══════════════════════════════════════════════════════════════════════
#  AGENTE 4 · SIMULACION  (Monte Carlo del torneo restante)
#  >>> SUPUESTO EDITABLE <<<  fuerza de cada equipo (estilo ELO).
# ══════════════════════════════════════════════════════════════════════
class AgenteSimulacion:
    ELO = {"Spain": 2085, "France": 2075, "Argentina": 2065, "England": 2010}

    def __init__(self, datos, escenarios, especiales, seed=7):
        self.d, self.e, self.esp = datos, escenarios, especiales
        random.seed(seed)

    def _padv(self, a, b):
        return 1 / (1 + 10 ** (-(self.ELO[a] - self.ELO[b]) / 400))

    def _bracket(self):
        d = self.d
        w1 = d.SF1[0] if random.random() < self._padv(*d.SF1) else d.SF1[1]
        l1 = [t for t in d.SF1 if t != w1][0]
        w2 = d.SF2[0] if random.random() < self._padv(*d.SF2) else d.SF2[1]
        l2 = [t for t in d.SF2 if t != w2][0]
        champ = w1 if random.random() < self._padv(w1, w2) else w2
        run = w2 if champ == w1 else w1
        third = l1 if random.random() < self._padv(l1, l2) else l2
        fourth = l2 if third == l1 else l1
        return dict(champ=champ, run=run, third=third, fourth=fourth,
                    finish={champ: 1, run: 2, third: 3, fourth: 4})

    def _standings(self, o, gol, mvp, S):
        d = self.d; tot = {}
        for n in d.players:
            s = d.pick(n); p = d.STANDINGS[n]
            if s["first"] == o["champ"]: p += S["champ"]
            if s["second"] == o["run"]:  p += S["run"]
            if s["third"] == o["third"]: p += S["third"]
            if s["scorer"] == gol:       p += S["gol"]
            if s["mvp"] == mvp:          p += S["mvp"]
            tot[n] = p
        return tot

    def run(self, N, scheme):
        S = self.d.SCHEMES[scheme]
        win = top2 = top3 = rank_sum = beats_jaime = 0
        for _ in range(N):
            o = self._bracket()
            gol = self.esp.draw_gol(); mvp = self.esp.draw_mvp(o["finish"])
            tot = self._standings(o, gol, mvp, S)
            order = sorted(tot, key=lambda n: -tot[n])
            r = order.index(ME) + 1
            rank_sum += r
            win += (r == 1); top2 += (r <= 2); top3 += (r <= 3)
            beats_jaime += (tot[ME] > tot["Jaime"])
        return dict(win=win / N, top2=top2 / N, top3=top3 / N,
                    avg_rank=rank_sum / N, beats_jaime=beats_jaime / N)

    def by_bracket(self, N, scheme):
        """Prob. de Pablo condicional a cada bracket (marginaliza gol/MVP)."""
        S = self.d.SCHEMES[scheme]; out = {}
        for o in self.e.outcomes():
            win = top2 = top3 = 0
            for _ in range(N):
                gol = self.esp.draw_gol(); mvp = self.esp.draw_mvp(o["finish"])
                tot = self._standings(o, gol, mvp, S)
                order = sorted(tot, key=lambda n: -tot[n])
                r = order.index(ME) + 1
                win += (r == 1); top2 += (r <= 2); top3 += (r <= 3)
            out[(o["champ"], o["run"], o["third"])] = (win / N, top2 / N, top3 / N)
        return out


# ══════════════════════════════════════════════════════════════════════
#  AGENTE 5 · ESTRATEGIA  (plan concreto para Pablo)
# ══════════════════════════════════════════════════════════════════════
class AgenteEstrategia:
    # Pronósticos recomendados para lo que Pablo AÚN puede enviar.
    # Se alinean con el único mundo en que Pablo puede ganar la polla.
    RECS = [
        ("Semifinal 1 · Francia vs España (14 jul)", "España gana  →  1 – 2",
         "Necesitas que Francia caiga al partido por el 3er puesto."),
        ("Semifinal 2 · Inglaterra vs Argentina (15 jul)", "Inglaterra gana  →  2 – 1",
         "El bracket que más te conviene es con Inglaterra de subcampeón."),
        ("Partido por el 3er lugar · Francia vs perdedor SF2", "Francia gana  →  2 – 1",
         "Francia 3º te da +10 y a la vez le NIEGA el +15 a Jaime (él tiene Francia 2º)."),
        ("Final · España vs ganador SF2", "España gana  →  2 – 1",
         "España campeón es tu pilar (tienes España 1º)."),
    ]

    def __init__(self, datos):
        self.d = datos

    def live_dead(self):
        s = self.d.pick(ME)
        alive = self.d.ALIVE
        return {
            "1º " + s["first"]: ("VIVO" if s["first"] in alive else "MUERTO"),
            "2º " + s["second"]: ("VIVO" if s["second"] in alive else "MUERTO ✝"),
            "3º " + s["third"]: ("VIVO" if s["third"] in alive else "MUERTO"),
            "Goleador " + s["scorer"]: "VIVO (longshot, Spain sigue)",
            "MVP " + s["mvp"]: "VIVO (favorito)",
        }


# ══════════════════════════════════════════════════════════════════════
#  ORQUESTADOR
# ══════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=40000)
    args = ap.parse_args()

    datos = AgenteDatos()
    esc = AgenteEscenarios(datos)
    esp = AgenteEspeciales()
    sim = AgenteSimulacion(datos, esc, esp)
    estr = AgenteEstrategia(datos)

    print("╔" + "═" * 68 + "╗")
    print("║  POLLA MUNDIALERA — ANÁLISIS DE ESTRATEGIA PARA PABLO (#12, 107 pts) ║")
    print("╚" + "═" * 68 + "╝")

    print("\n■ AGENTE ESTRATEGIA · tus especiales (bloqueados desde el inicio):")
    for k, v in estr.live_dead().items():
        print(f"    {k:<28} {v}")

    print("\n■ AGENTE ESCENARIOS · rank de Pablo en los 16 podios posibles "
          "(solo podio, esquema reglamento):")
    for r in sorted(esc.enumerate_pablo("reglamento"), key=lambda x: x["pablo_rank"]):
        print(f"    1º {r['champ']:<9} 2º {r['run']:<9} 3º {r['third']:<9} "
              f"| Pablo +{r['pablo_add']:>2} = {r['pablo_pts']:>3}  #{r['pablo_rank']:<2} "
              f"| líder {r['leader']} {r['leader_pts']}")

    print("\n■ AGENTE SIMULACION · probabilidad de posición final de Pablo:")
    for scheme in ("reglamento", "dashboard"):
        r = sim.run(args.sims, scheme)
        print(f"    [{scheme:<10}] P(1º)={r['win']*100:5.2f}%  "
              f"P(top2)={r['top2']*100:5.2f}%  P(top3)={r['top3']*100:5.2f}%  "
              f"rank medio≈{r['avg_rank']:.1f}  P(supera a Jaime)={r['beats_jaime']*100:.1f}%")

    print("\n■ AGENTE SIMULACION · brackets que MÁS te convienen (esquema dashboard):")
    cb = sim.by_bracket(max(3000, args.sims // 12), "dashboard")
    for key in sorted(cb, key=lambda k: -cb[k][1])[:5]:
        w, t2, t3 = cb[key]
        print(f"    {key[0]:<9}/{key[1]:<9}/{key[2]:<9}  "
              f"P(1º)={w*100:5.2f}%  P(top2)={t2*100:5.2f}%  P(top3)={t3*100:5.2f}%")

    print("\n■ AGENTE ESTRATEGIA · pronósticos recomendados (lo único que controlas):")
    for titulo, rec, por in estr.RECS:
        print(f"    • {titulo}\n        → {rec}   ({por})")

    print("\n■ LA LLAVE MAESTRA:")
    print("    Aun con el bracket perfecto (España campeón / Francia 3º) y MVP Mbappé,")
    print("    si el goleador es Mbappé terminas ~#5. El ÚNICO evento que te lleva a #1")
    print("    es que MIKEL OYARZABAL gane la Bota de Oro. Es tu bala de plata: álienta")
    print("    a España a ganarlo todo Y a que Oyarzabal sea el máximo goleador.")


if __name__ == "__main__":
    main()
