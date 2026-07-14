"""Testa a checagem de segurança na subida do app (backend/main.py::lifespan) -- antes disso,
um deploy sem .env configurado subia silenciosamente com a SECRET_KEY padrão em qualquer
ambiente, inclusive produção."""

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import settings  # noqa: E402
from backend.main import _DEFAULT_SECRET_KEY, app, lifespan  # noqa: E402


class LifespanSecretKeyCheckTest(unittest.TestCase):
    def _run_lifespan_enter(self):
        async def _enter():
            ctx = lifespan(app)
            await ctx.__aenter__()
            await ctx.__aexit__(None, None, None)

        asyncio.run(_enter())

    def test_producao_com_secret_key_padrao_recusa_subir(self):
        with patch.object(settings, "ENVIRONMENT", "production"), patch.object(
            settings, "SECRET_KEY", _DEFAULT_SECRET_KEY
        ):
            with self.assertRaises(RuntimeError):
                self._run_lifespan_enter()

    def test_producao_com_secret_key_real_sobe_normalmente(self):
        with patch.object(settings, "ENVIRONMENT", "production"), patch.object(
            settings, "SECRET_KEY", "uma-chave-real-configurada-via-env"
        ):
            self._run_lifespan_enter()  # não deve levantar

    def test_dev_local_com_secret_key_padrao_sobe_normalmente(self):
        with patch.object(settings, "ENVIRONMENT", "development"), patch.object(
            settings, "SECRET_KEY", _DEFAULT_SECRET_KEY
        ):
            self._run_lifespan_enter()  # não deve levantar


if __name__ == "__main__":
    unittest.main()
