import os
import subprocess
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from tileup import InstanciaError, JugadaIlegal, TileUp, DERROTA, VICTORIA  # noqa: E402
from tileup.instancia import parsear_instancia  # noqa: E402
from tileup.juego import jugar  # noqa: E402
from agentes import voraz, aleatorio, busqueda, evolutivo  # noqa: E402
import verificador  # noqa: E402


def inst(n, k, fichas):
    txt = f"{n} {k}\n{len(fichas)}\n" + "\n".join(f"{c} {v}" for c, v in fichas)
    return parsear_instancia(txt)


class TestMotor(unittest.TestCase):
    def test_colocacion_sin_fusion(self):
        j = TileUp(inst(3, 2, [(1, 2), (2, 5)]))
        r = j.step(0, 0, 0)
        self.assertFalse(r.info["fusion"])
        self.assertEqual(r.recompensa, 0)
        r = j.step(1, 0, 1)                      # adyacente pero de otro color
        self.assertFalse(r.info["fusion"])
        self.assertEqual(j.ocupadas, 2)
        self.assertEqual(j.tablero()[0][:2], [(1, 2), (2, 5)])

    def test_fusion_dos(self):
        j = TileUp(inst(3, 1, [(1, 2), (1, 3)]))
        j.step(0, 1, 1)
        r = j.step(1, 1, 2)
        self.assertTrue(r.info["fusion"])
        self.assertEqual(r.recompensa, 1)
        self.assertEqual(j.celda(1, 2), (1, 5))
        self.assertIsNone(j.celda(1, 1))
        self.assertEqual(j.ocupadas, 1)

    def test_fusion_componente_de_tres_o_mas(self):
        # colocar en (0,1) une (0,0) y (0,2): componente de 3
        j = TileUp(inst(3, 2, [(1, 1), (1, 2), (2, 9), (1, 4)]))
        j.step(0, 0, 0)
        j.step(1, 0, 2)
        j.step(2, 2, 2)
        r = j.step(3, 0, 1)
        self.assertEqual(r.info["tam_grupo"], 3)
        self.assertEqual(r.recompensa, 2)
        self.assertEqual(j.celda(0, 1), (1, 7))
        self.assertEqual(j.ocupadas, 2)

    def test_fusion_no_encadena_y_conserva_suma(self):
        j = TileUp(inst(2, 2, [(1, 1), (2, 1), (1, 1)]))
        j.step(0, 0, 0)
        j.step(1, 1, 1)
        j.step(2, 0, 1)
        self.assertEqual(j.celda(0, 1), (1, 2))
        self.assertEqual(j.celda(1, 1), (2, 1))
        self.assertEqual(sum(j.valor), 3)

    def test_derrota(self):
        j = TileUp(inst(1, 2, [(1, 1), (2, 1)]))
        r = j.step(0, 0, 0)
        self.assertTrue(r.terminado)
        self.assertEqual(j.estado, DERROTA)
        self.assertEqual(j.acciones_legales(), [])
        with self.assertRaises(JugadaIlegal):
            j.step(1, 0, 0)

    def test_victoria(self):
        j = TileUp(inst(1, 1, [(1, 1)]))
        self.assertTrue(j.step(0, 0, 0).terminado)
        self.assertEqual(j.estado, VICTORIA)

    def test_jugadas_ilegales_no_cambian_estado(self):
        j = TileUp(inst(2, 1, [(1, 1), (1, 1)]))
        j.step(0, 0, 0)
        antes = j.clave()
        for args in [(0, 1, 1), (2, 1, 1), (1, 0, 0), (1, 2, 0), (1, -1, 0)]:
            with self.assertRaises(JugadaIlegal):
                j.step(*args)
        self.assertEqual(j.clave(), antes)

    def test_deshacer_y_clonar(self):
        j = TileUp(inst(3, 2, [(1, 1), (1, 2), (2, 9), (1, 4)]))
        claves = [j.clave()]
        for f, c in [(0, 0), (0, 2), (2, 2), (0, 1)]:
            j.step(j.siguiente, f, c)
            claves.append(j.clave())
        copia = j.clonar()
        while j.jugadas:
            claves.pop()
            j.deshacer()
            self.assertEqual(j.clave(), claves[-1])
        self.assertEqual(copia.ocupadas, 2)
        self.assertEqual(j.ocupadas, 0)

    def test_ejemplo_enunciado(self):
        j = TileUp(inst(4, 3, [(1, 2), (2, 1), (1, 3), (3, 1), (1, 1), (2, 4)]))
        j.jugar_secuencia([(0, 0), (1, 1), (0, 1), (2, 2), (0, 2), (1, 2)])
        self.assertEqual(j.solucion_texto().splitlines()[-1], "# colocadas=6 ocupadas=3 mayor=6")

    def test_instancia_mal_formada(self):
        for txt in ["", "3\n1\n1 1", "3 2\n2\n1 1", "3 2\n1\n5 1", "3 2\n1\n1 0", "3 x\n1\n1 1"]:
            with self.assertRaises(InstanciaError):
                parsear_instancia(txt)


class TestVerificador(unittest.TestCase):
    def setUp(self):
        self.n, self.k, self.f = 2, 2, [(1, 1), (2, 1), (1, 1)]

    def test_acepta(self):
        r = verificador.verificar(self.n, self.k, self.f, [(1, 0, 0, 0), (2, 1, 1, 1), (3, 2, 0, 1)],
                                  {"colocadas": 3, "ocupadas": 2, "mayor": 2})
        self.assertTrue(r["legal"])
        self.assertEqual(r["estado"], "victoria")

    def test_rechaza(self):
        casos = [
            [(1, 0, 0, 0), (2, 1, 0, 0)],          # celda ocupada
            [(1, 0, 0, 0), (2, 2, 1, 1)],          # indice fuera de orden
            [(1, 0, 5, 0)],                        # fuera del tablero
        ]
        for jug in casos:
            self.assertFalse(verificador.verificar(self.n, self.k, self.f, jug)["legal"])
        r = verificador.verificar(self.n, self.k, self.f, [(1, 0, 0, 0)],
                                  {"colocadas": 1, "ocupadas": 9, "mayor": 1})
        self.assertFalse(r["legal"])               # resumen incoherente


class TestIntegracion(unittest.TestCase):
    def test_agentes_base_producen_soluciones_legales(self):
        ruta = os.path.join(RAIZ, "instancias", "n4_k8_m60_s1.txt")
        for agente in (voraz, aleatorio):
            with tempfile.TemporaryDirectory() as d:
                sol = os.path.join(d, "sol.txt")
                res = jugar(ruta, agente, semilla=1, salida=sol, verbose=False)
                n, k, f = verificador.leer_instancia(ruta)
                jug, resumen = verificador.leer_solucion(sol)
                v = verificador.verificar(n, k, f, jug, resumen)
                self.assertTrue(v["legal"], v["errores"])
                self.assertEqual((v["colocadas"], v["ocupadas"]), (res["colocadas"], res["ocupadas"]))

    def test_busqueda_encuentra_solucion_del_ejemplo(self):
        ruta = os.path.join(RAIZ, "instancias", "ejemplo.txt")
        with tempfile.TemporaryDirectory() as d:
            sol = os.path.join(d, "sol.txt")
            res = jugar(ruta, busqueda, semilla=1, limite_s=1, salida=sol, verbose=False)
            n, k, f = verificador.leer_instancia(ruta)
            jug, resumen = verificador.leer_solucion(sol)
            validacion = verificador.verificar(n, k, f, jug, resumen)
            self.assertTrue(validacion["legal"], validacion["errores"])
            self.assertEqual(res["colocadas"], len(f))

    def test_busqueda_prechecks_imposibles(self):
        un_casillero = TileUp(inst(1, 2, [(1, 1), (2, 1)]))
        plan, esfuerzo = busqueda(un_casillero, semilla=1, limite_s=1)
        self.assertEqual((len(plan), esfuerzo), (1, 0))

        colores_unicos = TileUp(inst(2, 5, [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1)]))
        plan, esfuerzo = busqueda(colores_unicos, semilla=1, limite_s=1)
        self.assertEqual((len(plan), esfuerzo), (4, 0))

    def test_cli_visualiza_estados_del_plan(self):
        with tempfile.TemporaryDirectory() as d:
            sol = os.path.join(d, "sol.txt")
            p = subprocess.run(
                [sys.executable, os.path.join(RAIZ, "main.py"),
                 os.path.join(RAIZ, "instancias", "ejemplo.txt"),
                 "--agente", "busqueda", "--limite", "0", "--visual",
                 "--salida", sol],
                capture_output=True, text=True,
            )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("Estado inicial 0/6", p.stdout)
        for estado in range(1, 7):
            self.assertIn(f"Estado {estado}/6 |", p.stdout)
    def test_evolutivo_legal_y_determinista(self):
        ruta = os.path.join(RAIZ, "instancias", "n4_k10_m60_s2.txt")
        with tempfile.TemporaryDirectory() as d:
            sol = os.path.join(d, "sol.txt")
            a = jugar(ruta, evolutivo, semilla=3, limite_s=2, salida=sol, verbose=False)
            n, k, f = verificador.leer_instancia(ruta)
            jug, resumen = verificador.leer_solucion(sol)
            self.assertTrue(verificador.verificar(n, k, f, jug, resumen)["legal"])
            b = jugar(ruta, evolutivo, semilla=3, limite_s=2, verbose=False)
            self.assertEqual(a["jugadas"], b["jugadas"])
            self.assertGreater(a["esfuerzo"], 0)          # evaluaciones de aptitud
            self.assertLessEqual(a["tiempo_s"], 2.0)      # respeta el limite

    def test_determinismo(self):
        ruta = os.path.join(RAIZ, "instancias", "n5_k15_m100_s2.txt")
        a = jugar(ruta, voraz, semilla=7, verbose=False)["jugadas"]
        b = jugar(ruta, voraz, semilla=7, verbose=False)["jugadas"]
        self.assertEqual(a, b)

    def test_cli_error_legible(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as t:
            t.write("hola\n")
        p = subprocess.run([sys.executable, os.path.join(RAIZ, "main.py"), t.name],
                           capture_output=True, text=True)
        os.unlink(t.name)
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn("Traceback", p.stderr)


if __name__ == "__main__":
    unittest.main()
