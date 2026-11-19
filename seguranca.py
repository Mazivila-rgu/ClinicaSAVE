# -*- coding: utf-8 -*-
"""seguranca.py - Hash e verificação de palavras-passe."""

import hashlib
import hmac
import secrets

from utils import Config


# ============================================================================
# SEGURANÇA
# ============================================================================


class Seguranca:
    """Hash de palavras-passe com PBKDF2-HMAC-SHA256 e sal aleatório."""

    @staticmethod
    def novo_sal():
        return secrets.token_hex(16)

    @staticmethod
    def _pbkdf2_manual(senha, sal, iteracoes):
        """Equivalente a hashlib.pbkdf2_hmac (1 bloco de 32 bytes).
        Usado apenas quando o ambiente (ex.: Acode/Pyodide) não o disponibiliza."""
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

    @classmethod
    def gerar_hash(cls, senha, sal_hex):
        dados = senha.encode("utf-8")
        sal = bytes.fromhex(sal_hex)
        if hasattr(hashlib, "pbkdf2_hmac"):
            return hashlib.pbkdf2_hmac("sha256", dados, sal, Config.ITERACOES_HASH).hex()
        return cls._pbkdf2_manual(dados, sal, Config.ITERACOES_HASH).hex()

    @classmethod
    def verificar(cls, senha, sal_hex, hash_guardado):
        return secrets.compare_digest(cls.gerar_hash(senha, sal_hex), hash_guardado)
