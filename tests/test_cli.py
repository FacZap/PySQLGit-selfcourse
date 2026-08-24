"""Pruebas de punta a punta del CLI.

Se llama a ``main(argv)`` directamente en vez de lanzar un subproceso: es mucho
mas rapido, el fallo muestra el traceback real y se puede leer la salida con
``capsys``. Por eso ``main`` recibe ``argv`` y devuelve un int en vez de llamar
a ``sys.exit`` por su cuenta.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tagstats.cli import main


def test_reporte_en_tabla(csv_lecturas: Path, csv_limites: Path, capsys):
    codigo = main([str(csv_lecturas), "--limites", str(csv_limites)])
    salida = capsys.readouterr().out

    assert codigo == 0
    assert "TT-101" in salida and "PT-204" in salida
    assert "TOTAL: 2 tags | 5 muestras | 2 alarmas" in salida


def test_reporte_en_json(csv_lecturas: Path, csv_limites: Path, capsys):
    codigo = main([str(csv_lecturas), "-l", str(csv_limites), "-f", "json"])
    documento = json.loads(capsys.readouterr().out)

    assert codigo == 0
    assert documento["totales"]["alarmas"] == 2

    tt101 = next(item for item in documento["tags"] if item["tag"] == "TT-101")
    assert tt101["minimo"] == pytest.approx(70.0)
    assert tt101["maximo"] == pytest.approx(99.0)
    assert tt101["promedio"] == pytest.approx(83.0)
    assert tt101["alarmas"] == 1


def test_sin_limites_no_cuenta_alarmas(csv_lecturas: Path, capsys):
    main([str(csv_lecturas), "-f", "json"])
    documento = json.loads(capsys.readouterr().out)

    assert documento["totales"]["alarmas"] == 0


def test_filtro_por_tag(csv_lecturas: Path, capsys):
    main([str(csv_lecturas), "-t", "PT-204", "-f", "json"])
    documento = json.loads(capsys.readouterr().out)

    assert [item["tag"] for item in documento["tags"]] == ["PT-204"]


def test_filtro_solo_confiables(csv_lecturas: Path, capsys):
    main([str(csv_lecturas), "-t", "TT-101", "--solo-confiables", "-f", "json"])
    documento = json.loads(capsys.readouterr().out)

    # se cae la muestra de 99.0 marcada como Bad
    assert documento["tags"][0]["muestras"] == 2
    assert documento["tags"][0]["maximo"] == pytest.approx(80.0)


def test_archivo_inexistente_devuelve_1(tmp_path: Path, capsys):
    codigo = main([str(tmp_path / "no_existe.csv")])

    assert codigo == 1
    assert "no se encontro el archivo" in capsys.readouterr().err


def test_fila_invalida_corta_y_sugiere_tolerante(tmp_path: Path, capsys):
    ruta = tmp_path / "sucio.csv"
    ruta.write_text(
        "timestamp,tag,valor,unidad,calidad\n2026-08-24T06:00:00,TT-101,ROTO,degC,Good\n",
        encoding="utf-8",
    )

    codigo = main([str(ruta)])
    error = capsys.readouterr().err

    assert codigo == 1
    assert "error de datos" in error
    assert "--tolerante" in error


def test_modo_tolerante_sigue_y_avisa_por_stderr(tmp_path: Path, capsys):
    ruta = tmp_path / "sucio.csv"
    ruta.write_text(
        "timestamp,tag,valor,unidad,calidad\n"
        "2026-08-24T06:00:00,TT-101,70,degC,Good\n"
        "2026-08-24T06:05:00,TT-101,ROTO,degC,Good\n"
        "2026-08-24T06:10:00,TT-101,72,degC,Good\n",
        encoding="utf-8",
    )

    codigo = main([str(ruta), "--tolerante", "-f", "json"])
    capturado = capsys.readouterr()

    assert codigo == 0
    assert json.loads(capturado.out)["totales"]["muestras"] == 2
    assert "se descartaron 1 filas invalidas" in capturado.err


def test_csv_vacio_avisa_pero_no_es_error(tmp_path: Path, capsys):
    ruta = tmp_path / "vacio.csv"
    ruta.write_text("timestamp,tag,valor,unidad,calidad\n", encoding="utf-8")

    codigo = main([str(ruta)])
    capturado = capsys.readouterr()

    assert codigo == 0
    assert "no quedaron lecturas" in capturado.err


def test_escribe_en_archivo_con_salida(csv_lecturas: Path, tmp_path: Path, capsys):
    destino = tmp_path / "salidas" / "reporte.json"

    codigo = main([str(csv_lecturas), "-f", "json", "-o", str(destino)])

    assert codigo == 0
    assert destino.exists()
    assert json.loads(destino.read_text(encoding="utf-8"))["totales"]["tags"] == 2
    assert capsys.readouterr().out == ""  # el reporte fue al archivo, no a stdout


def test_argumento_desconocido_devuelve_2(csv_lecturas: Path):
    """argparse aborta con SystemExit(2) ante un uso incorrecto."""
    with pytest.raises(SystemExit) as excepcion:
        main([str(csv_lecturas), "--formato", "pdf"])

    assert excepcion.value.code == 2


def test_fecha_invalida_devuelve_2(csv_lecturas: Path):
    with pytest.raises(SystemExit) as excepcion:
        main([str(csv_lecturas), "--desde", "ayer"])

    assert excepcion.value.code == 2
