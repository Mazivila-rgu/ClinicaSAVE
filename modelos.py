# -*- coding: utf-8 -*-
"""modelos.py - Classes que representam os dados."""

from utils import Interface


# ============================================================================
# MODELOS (cada classe sabe apresentar-se no terminal)
# ============================================================================


class Modelo:
    """Classe base: transforma uma linha da base de dados em objecto."""

    def __init__(self, linha):
        for chave, valor in dict(linha).items():
            setattr(self, chave, valor)

    def mostrar(self):
        raise NotImplementedError


class Medico(Modelo):
    def mostrar(self):
        especializacao = self.especializacao or "Sem especialização"
        print(f"  [{self.id}] Dr(a). {self.nome}")
        print(f"      Idade: {self.idade} | Sexo: {self.sexo}")
        print(f"      Formação: {self.formacao} ({self.nivel_formacao})")
        print(f"      Especialização: {especializacao}")


class Administrador(Modelo):
    def mostrar(self):
        funcao = "Administrador chefe" if self.chefe else "Administrador"
        print(f"  [{self.id}] {self.nome_utilizador} - {funcao}")


class Paciente(Modelo):
    def mostrar(self):
        print(f"  [{self.id}] {self.nome} | {self.idade} anos | {self.sexo} | {self.moradia}")


class Atendimento(Modelo):
    def mostrar(self):
        """Visão do médico (precisa dos dados do paciente)."""
        Interface.linha("-")
        print(f"Pedido n.º {self.id} | Entrada: {self.data_entrada}")
        print(f"Paciente: {self.nome_paciente} ({self.idade} anos, {self.sexo}) - {self.moradia}")
        print(f"Sintomas: {self.sintomas}")
        if self.estado == "presencial_agendada":
            print(f"Consulta presencial: {self.data_consulta_presencial}")
            print(f"Justificação       : {self.justificacao_presencial}")

    def mostrar_ao_paciente(self):
        Interface.linha("-")
        print(f"Data do pedido: {self.data_entrada}")
        print(f"Médico        : {self.nome_medico or 'Sem médico (o médico foi removido)'}")
        print(f"Sintomas      : {self.sintomas}")
        if self.medico_id is None:
            print("Estado        : Aguarda novo médico (reencaminhe o pedido)")
        elif self.estado == "pendente":
            print("Estado        : Aguarda resposta do médico")
        else:
            print("Estado        : CONSULTA PRESENCIAL MARCADA")
            print(f"Data da consulta: {self.data_consulta_presencial}")
            print(f"Motivo          : {self.justificacao_presencial}")


class RegistoPaciente(Modelo):
    def mostrar(self):
        Interface.linha("-")
        print(f"Data de entrada : {self.data_entrada}")
        print(f"Médico          : {self.nome_medico}")
        print(f"Tipo de consulta: {self.tipo_consulta.capitalize()}")
        print(f"Diagnóstico     : {self.diagnostico}")
        print(f"Prescrição      : {self.prescricao}")


class RegistoHistorico(Modelo):
    def mostrar(self):
        Interface.linha("-")
        print(f"Paciente         : {self.nome_paciente} ({self.idade} anos, {self.sexo})")
        print(f"Data de entrada  : {self.data_entrada}")
        print(f"Sintomas         : {self.sintomas}")
        print(f"Resultados testes: {self.resultados_testes}")
        print(f"Diagnóstico      : {self.diagnostico}")
        print(f"Prescrição       : {self.prescricao}")
        print(f"Médico           : {self.nome_medico}")
        print(f"Tipo de consulta : {self.tipo_consulta.capitalize()}")
        if self.tipo_consulta == "presencial":
            print(f"Justificação da consulta presencial: {self.justificacao_presencial}")
