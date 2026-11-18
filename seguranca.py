# -*- coding: utf-8 -*-
"""Geração e verificação de palavras-passe (PBKDF2-HMAC-SHA256 com sal)."""

import hashlib
import hmac
import secrets

ITERACOES = 200_000
TAMANHO_MIN_SENHA = 6


def novo_sal():
    return secrets.token_hex(16)


def _pbkdf2_manual(senha, sal, iteracoes):
    """Equivalente a hashlib.pbkdf2_hmac, para ambientes (ex.: Pyodide) que não o têm."""
    base = hmac.new(senha, digestmod=hashlib.sha256)

    def prf(dados):
        h = base.copy()
        h.update(dados)
        return h.digest()

    u = prf(sal + b"\x00\x00\x00\x01")
    resultado = int.from_bytes(u, "big")
    for _ in range(iteracoes - 1):
        u = prf(u)
        resultado ^= int.from_bytes(u, "big")
    return resultado.to_bytes(32, "big")


def gerar_hash(senha, sal_hex):
    dados = senha.encode("utf-8")
    sal = bytes.fromhex(sal_hex)
    if hasattr(hashlib, "pbkdf2_hmac"):
        return hashlib.pbkdf2_hmac("sha256", dados, sal, ITERACOES).hex()
    return _pbkdf2_manual(dados, sal, ITERACOES).hex()


def comparar(hash_a, hash_b):
    return secrets.compare_digest(hash_a, hash_b)