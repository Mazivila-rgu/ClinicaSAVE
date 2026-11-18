# -*- coding: utf-8 -*-
"""Funções utilitárias de interface (entrada e saída na consola)."""

from datetime import datetime
from getpass import getpass


def linha(carater="=", tamanho=60):
    print(carater * tamanho)


def titulo(texto):
    print()
    linha()
    print(texto.upper().center(60))
    linha()


def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def ler_texto(mensagem, obrigatorio=True):
    while True:
        valor = input(mensagem).strip()
        if valor or not obrigatorio:
            return valor
        print("  [!] Este campo é obrigatório.")


def ler_inteiro(mensagem, minimo, maximo):
    while True:
        valor = input(mensagem).strip()
        if valor.isdigit() and minimo <= int(valor) <= maximo:
            return int(valor)
        print(f"  [!] Introduza um número entre {minimo} e {maximo}.")


def ler_sexo():
    while True:
        valor = input("Sexo (M/F): ").strip().upper()
        if valor in ("M", "F"):
            return valor
        print("  [!] Introduza M ou F.")


def ler_senha(mensagem="Palavra-passe: "):
    try:
        return getpass(mensagem)
    except Exception:
        # Alguns terminais/depuradores não suportam getpass
        return input(mensagem)


def ler_data_hora(mensagem):
    while True:
        valor = input(mensagem).strip()
        try:
            datetime.strptime(valor, "%d/%m/%Y %H:%M")
            return valor
        except ValueError:
            print("  [!] Formato inválido. Use dd/mm/aaaa hh:mm (ex.: 25/11/2026 09:30).")


def pausar():
    input("\nPrima ENTER para continuar...")