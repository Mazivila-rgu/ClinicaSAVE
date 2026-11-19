# -*- coding: utf-8 -*-
"""utils.py - Excepções, configuração e interface (terminal)."""

import os
from datetime import datetime
from getpass import getpass


# ============================================================================
# EXCEPÇÕES PERSONALIZADAS
# ============================================================================


class ErroClinica(Exception):
    """Erro base da aplicação (a mensagem pode ser mostrada ao utilizador)."""


class ErroBaseDados(ErroClinica):
    """Falha numa operação da base de dados."""


class ErroAutenticacao(ErroClinica):
    """Credenciais inválidas."""


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================


class Config:
    try:
        _PASTA = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        # Ambientes como Acode/Pyodide não definem __file__
        _PASTA = os.getcwd()

    DB_PATH = os.path.join(_PASTA, "clinica_virtual.db")
    NIVEIS_FORMACAO = ["Licenciatura", "Pós-graduação", "Mestrado", "Doutoramento"]
    ITERACOES_HASH = 200_000
    TAMANHO_MIN_SENHA = 6

    # True  -> a palavra-passe aparece enquanto escreve (útil em testes)
    # False -> a palavra-passe fica oculta (nada aparece ao escrever)
    MOSTRAR_SENHA = True


# ============================================================================
# INTERFACE (terminal)
# ============================================================================


class Interface:
    """Funções de leitura validada e apresentação no terminal."""

    @staticmethod
    def linha(carater="=", tamanho=60):
        print(carater * tamanho)

    @staticmethod
    def titulo(texto):
        print()
        Interface.linha()
        print(texto.upper().center(60))
        Interface.linha()

    @staticmethod
    def agora():
        return datetime.now().strftime("%d/%m/%Y %H:%M")

    @staticmethod
    def pausar():
        input("\nPrima ENTER para continuar...")

    @staticmethod
    def ler_texto(mensagem, obrigatorio=True):
        while True:
            valor = input(mensagem).strip()
            if valor or not obrigatorio:
                return valor
            print("  [!] Este campo é obrigatório.")

    @staticmethod
    def ler_inteiro(mensagem, minimo, maximo):
        while True:
            valor = input(mensagem).strip()
            if valor.isdigit() and minimo <= int(valor) <= maximo:
                return int(valor)
            print(f"  [!] Introduza um número entre {minimo} e {maximo}.")

    @staticmethod
    def ler_sexo():
        while True:
            valor = input("Sexo (M/F): ").strip().upper()
            if valor in ("M", "F"):
                return valor
            print("  [!] Introduza M ou F.")

    @staticmethod
    def ler_senha(mensagem="Palavra-passe: "):
        if Config.MOSTRAR_SENHA:
            return input(mensagem)
        try:
            return getpass(mensagem)
        except Exception:
            # Alguns terminais/depuradores não suportam getpass
            return input(mensagem)

    @staticmethod
    def ler_data_hora(mensagem):
        while True:
            valor = input(mensagem).strip()
            try:
                data = datetime.strptime(valor, "%d/%m/%Y %H:%M")
            except ValueError:
                print("  [!] Formato inválido. Use dd/mm/aaaa hh:mm (ex.: 25/11/2026 09:30).")
                continue
            if data < datetime.now():
                print("  [!] A data da consulta não pode estar no passado.")
                continue
            return data.strftime("%d/%m/%Y %H:%M")
