# -*- coding: utf-8 -*-
"""Acesso à base de dados SQLite, com tratamento centralizado de erros."""

import os
import sqlite3
from contextlib import contextmanager

try:
    _PASTA = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # Ambientes como Acode/Pyodide não definem __file__
    _PASTA = os.getcwd()
DB_PATH = os.path.join(_PASTA, "clinica_virtual.db")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS utilizadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_utilizador TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    sal TEXT NOT NULL,
    papel TEXT NOT NULL CHECK (papel IN ('paciente','medico','administrador'))
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
    medico_id INTEGER NOT NULL REFERENCES medicos(id),
    data_entrada TEXT NOT NULL,
    sintomas TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendente'
        CHECK (estado IN ('pendente','presencial_agendada','concluido')),
    justificacao_presencial TEXT,
    data_consulta_presencial TEXT
);

-- Registo médico guardado na conta do paciente
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

-- Histórico clínico (acesso restrito a médicos e administradores)
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


class ErroBaseDados(Exception):
    """Erro ao aceder à base de dados."""


class BaseDados:
    """Encapsula a ligação SQLite; converte erros do sqlite3 em ErroBaseDados."""

    def __init__(self, caminho=DB_PATH):
        self._caminho = caminho
        self._conexao = None

    def abrir(self):
        try:
            self._conexao = sqlite3.connect(self._caminho)
            self._conexao.row_factory = sqlite3.Row
            self._conexao.execute("PRAGMA foreign_keys = ON")
            self._conexao.executescript(ESQUEMA)
            self._conexao.commit()
        except sqlite3.Error as erro:
            self._conexao = None
            raise ErroBaseDados(f"não foi possível abrir a base de dados ({erro})") from erro

    def fechar(self):
        if self._conexao is not None:
            try:
                self._conexao.close()
            except sqlite3.Error:
                pass
            self._conexao = None

    def _verificar_aberta(self):
        """Garante que a ligação está aberta e devolve-a (nunca None)."""
        if self._conexao is None:
            raise ErroBaseDados("a base de dados não está aberta")
        return self._conexao

    def _executar(self, sql, parametros):
        conexao = self._verificar_aberta()
        try:
            return conexao.execute(sql, parametros)
        except sqlite3.Error as erro:
            raise ErroBaseDados(f"falha na consulta ({erro})") from erro

    def um(self, sql, parametros=()):
        """Devolve a primeira linha do resultado (ou None)."""
        return self._executar(sql, parametros).fetchone()

    def todos(self, sql, parametros=()):
        """Devolve todas as linhas do resultado."""
        return self._executar(sql, parametros).fetchall()

    @contextmanager
    def transacao(self):
        """Agrupa escritas: faz commit no fim ou rollback se houver erro."""
        conexao = self._verificar_aberta()
        try:
            with conexao:
                yield conexao
        except sqlite3.IntegrityError as erro:
            raise ErroBaseDados("os dados entram em conflito com registos existentes") from erro
        except sqlite3.Error as erro:
            raise ErroBaseDados(f"falha ao gravar os dados ({erro})") from erro
