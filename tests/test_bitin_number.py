"""Testes de scripts/backend.bitin_number -- geração do número sequencial do BITin
(isolado do resto da API, ver tests/test_backend_bitins.py para os testes end-to-end)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.bitin_number import SetorInvalido, gerar_e_salvar_bitin_sql  # noqa: E402
from backend.db.session import Base  # noqa: E402


class GerarBitinSqlTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_setor_invalido_levanta_excecao(self) -> None:
        db = self.Session()
        with self.assertRaises(SetorInvalido):
            gerar_e_salvar_bitin_sql(db, "Setor Inexistente", "mongo-id-1")

    def test_criado_por_default_none_sem_autenticacao(self) -> None:
        """Ainda não existe autenticação -- criado_por fica None até o login existir
        (ver docs/BACKEND.md, 'criado_por')."""
        db = self.Session()
        bitin_sql = gerar_e_salvar_bitin_sql(db, "Proteína Animal", "mongo-id-2")
        self.assertIsNone(bitin_sql.criado_por)

    def test_criado_por_aceita_valor_quando_informado(self) -> None:
        db = self.Session()
        bitin_sql = gerar_e_salvar_bitin_sql(
            db, "Proteína Animal", "mongo-id-3", criado_por="alessandro",
        )
        self.assertEqual(bitin_sql.criado_por, "alessandro")


if __name__ == "__main__":
    unittest.main()
