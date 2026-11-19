# -*- coding: utf-8 -*-
"""base_dados.py - Ligação e transacções SQLite."""

import sqlite3
from contextlib import contextmanager

from utils import Config, ErroBaseDados


# ============================================================================
# BASE DE DADOS
# ============================================================================


class BaseDados:
    """Encapsula a ligação SQLite e converte erros em ErroBaseDados."""

    ESQUEMA = """
    CREATE TABLE IF NOT EXISTS utilizadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_utilizador TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        sal TEXT NOT NULL,
        papel TEXT NOT NULL CHECK (papel IN ('paciente','medico','administrador')),
        chefe INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS medicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        utilizador_id INTEGER NOT NULL UNIQUE REFERENCES utilizadores(id),
        nome TEXT NOT NULL,
        idade INTEGER NOT NULL,
        sexo TEXT NOT NULL,
        formacao TEXT NOT NULL,
        nivel_formacao TEXT NOT NULL,
        especializacao TEXT
    );

    CREATE TABLE IF NOT EXISTS pacientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        utilizador_id INTEGER NOT NULL UNIQUE REFERENCES utilizadores(id),
        nome TEXT NOT NULL,
        idade INTEGER NOT NULL,
        sexo TEXT NOT NULL,
        moradia TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS atendimentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER NOT NULL REFERENCES pacientes(id),
        medico_id INTEGER REFERENCES medicos(id),
        data_entrada TEXT NOT NULL,
        sintomas TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'pendente'
            CHECK (estado IN ('pendente','presencial_agendada','concluido')),
        justificacao_presencial TEXT,
        data_consulta_presencial TEXT
    );

    CREATE TABLE IF NOT EXISTS registos_paciente (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        atendimento_id INTEGER NOT NULL UNIQUE REFERENCES atendimentos(id),
        paciente_id INTEGER NOT NULL REFERENCES pacientes(id),
        data_entrada TEXT NOT NULL,
        diagnostico TEXT NOT NULL,
        prescricao TEXT NOT NULL,
        nome_medico TEXT NOT NULL,
        tipo_consulta TEXT NOT NULL CHECK (tipo_consulta IN ('virtual','presencial'))
    );

    CREATE TABLE IF NOT EXISTS historico_clinica (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        atendimento_id INTEGER NOT NULL UNIQUE REFERENCES atendimentos(id),
        paciente_id INTEGER NOT NULL REFERENCES pacientes(id),
        data_entrada TEXT NOT NULL,
        sintomas TEXT NOT NULL,
        resultados_testes TEXT NOT NULL,
        diagnostico TEXT NOT NULL,
        prescricao TEXT NOT NULL,
        nome_medico TEXT NOT NULL,
        tipo_consulta TEXT NOT NULL CHECK (tipo_consulta IN ('virtual','presencial')),
        justificacao_presencial TEXT
    );
    """

    def __init__(self, caminho=Config.DB_PATH):
        self.caminho = caminho
        try:
            self.conexao = sqlite3.connect(caminho)
            self.conexao.row_factory = sqlite3.Row
            self.conexao.execute("PRAGMA foreign_keys = ON")
            self.conexao.executescript(self.ESQUEMA)
            self._migrar()
            self.conexao.commit()
        except sqlite3.Error as erro:
            raise ErroBaseDados(f"Não foi possível abrir a base de dados: {erro}") from erro

    def _migrar(self):
        """Actualiza bases de dados antigas e garante um único administrador chefe."""
        colunas = [l["name"] for l in self.conexao.execute("PRAGMA table_info(utilizadores)")]
        if "chefe" not in colunas:
            self.conexao.execute(
                "ALTER TABLE utilizadores ADD COLUMN chefe INTEGER NOT NULL DEFAULT 0"
            )
        sem_chefe = self.conexao.execute(
            "SELECT 1 FROM utilizadores WHERE chefe = 1"
        ).fetchone() is None
        if sem_chefe:
            # Base antiga: o primeiro administrador criado passa a ser o chefe
            self.conexao.execute(
                """UPDATE utilizadores SET chefe = 1 WHERE id =
                   (SELECT MIN(id) FROM utilizadores WHERE papel = 'administrador')"""
            )
        self.conexao.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS um_so_chefe ON utilizadores(chefe) WHERE chefe = 1"
        )
        self._permitir_medico_removido()

    def _permitir_medico_removido(self):
        """Bases antigas tinham medico_id obrigatório; passa a aceitar NULL (médico removido)."""
        colunas = list(self.conexao.execute("PRAGMA table_info(atendimentos)"))
        medico = next((c for c in colunas if c["name"] == "medico_id"), None)
        if medico is None or not medico["notnull"]:
            return
        self.conexao.commit()
        self.conexao.execute("PRAGMA foreign_keys = OFF")
        try:
            self.conexao.executescript(
                """
                BEGIN;
                CREATE TABLE atendimentos_nova (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paciente_id INTEGER NOT NULL REFERENCES pacientes(id),
                    medico_id INTEGER REFERENCES medicos(id),
                    data_entrada TEXT NOT NULL,
                    sintomas TEXT NOT NULL,
                    estado TEXT NOT NULL DEFAULT 'pendente'
                        CHECK (estado IN ('pendente','presencial_agendada','concluido')),
                    justificacao_presencial TEXT,
                    data_consulta_presencial TEXT
                );
                INSERT INTO atendimentos_nova SELECT id, paciente_id, medico_id, data_entrada,
                    sintomas, estado, justificacao_presencial, data_consulta_presencial
                    FROM atendimentos;
                DROP TABLE atendimentos;
                ALTER TABLE atendimentos_nova RENAME TO atendimentos;
                COMMIT;
                """
            )
        finally:
            self.conexao.execute("PRAGMA foreign_keys = ON")

    @contextmanager
    def transacao(self):
        """Confirma (commit) se tudo correr bem; desfaz (rollback) em caso de erro."""
        try:
            with self.conexao as conexao:
                yield conexao
        except sqlite3.Error as erro:
            raise ErroBaseDados(f"Erro na base de dados: {erro}") from erro

    def um(self, sql, parametros=()):
        try:
            return self.conexao.execute(sql, parametros).fetchone()
        except sqlite3.Error as erro:
            raise ErroBaseDados(f"Erro na base de dados: {erro}") from erro

    def todos(self, sql, parametros=()):
        try:
            return self.conexao.execute(sql, parametros).fetchall()
        except sqlite3.Error as erro:
            raise ErroBaseDados(f"Erro na base de dados: {erro}") from erro

    def fechar(self):
        try:
            self.conexao.close()
        except sqlite3.Error:
            pass
