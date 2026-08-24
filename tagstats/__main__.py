"""Permite ejecutar el paquete con ``python -m tagstats``.

``SystemExit(main())`` propaga el codigo de salida al shell: en PowerShell se
lee con ``$LASTEXITCODE``.
"""

from .cli import main

raise SystemExit(main())
