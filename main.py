# -*- coding: utf-8 -*-
"""CLÍNICA VIRTUAL - Projecto Final de Python (PTP I, UniSave)
Execução: python main.py"""

from base_dados import BaseDados
from clinica import Clinica
from utils import Config, ErroBaseDados, ErroClinica, Interface


# ============================================================================
# FORMULÁRIOS DE CADASTRO
# ============================================================================


class Formularios:
    @staticmethod
    def credenciais_novas(clinica):
        while True:
            nome_utilizador = Interface.ler_texto("Nome de utilizador: ")
            if clinica.existe_nome_utilizador(nome_utilizador):
                print("  [!] Esse nome de utilizador já existe. Escolha outro.")
                continue
            break
        while True:
            senha = Interface.ler_senha(
                f"Palavra-passe (mín. {Config.TAMANHO_MIN_SENHA} caracteres): "
            )
            if len(senha) < Config.TAMANHO_MIN_SENHA:
                print("  [!] A palavra-passe é demasiado curta.")
                continue
            if senha != Interface.ler_senha("Confirme a palavra-passe: "):
                print("  [!] As palavras-passe não coincidem.")
                continue
            return nome_utilizador, senha

    @staticmethod
    def cadastrar_administrador(clinica, executor):
        Interface.titulo("Registar novo administrador")
        nome_utilizador, senha = Formularios.credenciais_novas(clinica)
        clinica.cadastrar_administrador(executor, nome_utilizador, senha)
        print("\nAdministrador registado com sucesso.")

    @staticmethod
    def cadastrar_medico(clinica, executor):
        Interface.titulo("Cadastro de médico (administrador)")
        print("Defina as credenciais de acesso do médico:\n")
        nome_utilizador, senha = Formularios.credenciais_novas(clinica)
        print("\n-- Perfil profissional --")
        nome = Interface.ler_texto("Nome completo: ")
        idade = Interface.ler_inteiro("Idade: ", 18, 100)
        sexo = Interface.ler_sexo()
        formacao = Interface.ler_texto("Formação (ex.: Medicina Geral): ")
        print("Nível de formação:")
        for i, nivel in enumerate(Config.NIVEIS_FORMACAO, 1):
            print(f"  {i}. {nivel}")
        nivel = Config.NIVEIS_FORMACAO[
            Interface.ler_inteiro("Escolha: ", 1, len(Config.NIVEIS_FORMACAO)) - 1
        ]
        especializacao = Interface.ler_texto("Especialização (ENTER se não tiver): ", False)
        clinica.cadastrar_medico(executor, nome_utilizador, senha, nome, idade, sexo,
                                 formacao, nivel, especializacao)
        print("\nMédico cadastrado com sucesso. Entregue-lhe o nome de utilizador e a palavra-passe.")

    @staticmethod
    def cadastrar_paciente(clinica):
        Interface.titulo("Cadastro de paciente")
        nome_utilizador, senha = Formularios.credenciais_novas(clinica)
        print("\n-- Dados pessoais --")
        nome = Interface.ler_texto("Nome completo: ")
        idade = Interface.ler_inteiro("Idade: ", 0, 120)
        sexo = Interface.ler_sexo()
        moradia = Interface.ler_texto("Moradia (bairro/cidade): ")
        clinica.cadastrar_paciente(nome_utilizador, senha, nome, idade, sexo, moradia)
        print("\nPaciente cadastrado com sucesso. Já pode iniciar sessão.")


# ============================================================================
# MENUS (herança e polimorfismo)
# ============================================================================


class Menu:
    """Classe base dos menus. Cada subclasse define o seu título e as suas opções."""

    def __init__(self, clinica, utilizador):
        self.clinica = clinica
        self.utilizador = utilizador
        self.opcoes = []  # lista de (texto, método)

    def cabecalho(self):
        return "Menu"

    def executar(self):
        while True:
            Interface.titulo(self.cabecalho())
            for i, (texto, _) in enumerate(self.opcoes, 1):
                print(f"{i}. {texto}")
            print("0. Terminar sessão")
            opcao = Interface.ler_inteiro("\nOpção: ", 0, len(self.opcoes))
            if opcao == 0:
                return
            try:
                resultado = self.opcoes[opcao - 1][1]()
            except (KeyboardInterrupt, EOFError):
                raise
            except ErroClinica as erro:
                print(f"\n  [!] {erro}")
            except Exception as erro:  # rede de segurança: o programa não deve fechar
                print(f"\n  [!] Ocorreu um erro inesperado: {erro}")
            else:
                if resultado == "sair":
                    return
            Interface.pausar()


class MenuClinico(Menu):
    """Funcionalidades comuns a médicos e administradores."""

    def consultar_historico(self):
        Interface.titulo("Histórico clínico dos pacientes")
        filtro = Interface.ler_texto(
            "Pesquisar por nome do paciente (ENTER para ver todos): ", False
        )
        registos = self.clinica.historico_clinica(filtro or None)
        if not registos:
            print("\nNenhum registo encontrado no histórico clínico.")
            return
        print(f"\n{len(registos)} registo(s) encontrado(s):")
        for registo in registos:
            registo.mostrar()


class MenuPaciente(Menu):
    def __init__(self, clinica, utilizador):
        super().__init__(clinica, utilizador)
        self.paciente = clinica.obter_paciente(utilizador["id"])
        self.opcoes = [
            ("Ver médicos e pedir atendimento", self.pedir_atendimento),
            ("Os meus pedidos em curso", self.ver_pedidos),
            ("O meu registo médico", self.ver_registo),
            ("Reencaminhar pedidos sem médico", self.reencaminhar_pedidos),
        ]

    def cabecalho(self):
        return f"Paciente: {self.paciente.nome}"

    def executar(self):
        # Ao iniciar sessão, avisa se algum pedido ficou sem médico
        try:
            if self.clinica.pedidos_sem_medico(self.paciente.id):
                self.reencaminhar_pedidos()
                Interface.pausar()
        except ErroClinica as erro:
            print(f"\n  [!] {erro}")
        super().executar()

    @staticmethod
    def _escolher_medico(medicos):
        ids_validos = {m.id for m in medicos}
        while True:
            escolha = input("Introduza o número do médico (0 para voltar): ").strip()
            if escolha == "0":
                return None
            if escolha.isdigit() and int(escolha) in ids_validos:
                return int(escolha)
            print("  [!] Médico inválido.")

    def reencaminhar_pedidos(self):
        Interface.titulo("Pedidos sem médico")
        pedidos = self.clinica.pedidos_sem_medico(self.paciente.id)
        if not pedidos:
            print("\nNão tem pedidos sem médico.")
            return
        print("O médico destes pedidos foi removido da clínica. Os seus pedidos foram mantidos.")
        for pedido in pedidos:
            Interface.linha("-")
            print(f"Pedido de {pedido.data_entrada}")
            print(f"Sintomas: {pedido.sintomas}")
            resposta = Interface.ler_texto(
                "Deseja levar este pedido para outro médico à sua escolha? (S/N): "
            ).upper()
            if resposta != "S":
                print("Pedido mantido. Pode reencaminhá-lo mais tarde neste menu.")
                continue
            medicos = self.clinica.listar_medicos()
            if not medicos:
                print("\nNão há médicos disponíveis de momento.")
                return
            print()
            for medico in medicos:
                medico.mostrar()
                print()
            medico_id = self._escolher_medico(medicos)
            if medico_id is None:
                print("Pedido mantido. Pode reencaminhá-lo mais tarde neste menu.")
                continue
            self.clinica.reencaminhar_pedido(self.paciente.id, pedido.id, medico_id)
            print("\nPedido reencaminhado com sucesso.")

    def pedir_atendimento(self):
        Interface.titulo("Escolher médico")
        medicos = self.clinica.listar_medicos()
        if not medicos:
            print("\nAinda não há médicos cadastrados.")
            return
        for medico in medicos:
            medico.mostrar()
            print()
        medico_id = self._escolher_medico(medicos)
        if medico_id is None:
            return
        print("\nDescreva os seus sintomas (seja o mais detalhado possível):")
        sintomas = Interface.ler_texto("> ")
        self.clinica.criar_atendimento(self.paciente.id, medico_id, sintomas)
        print("\nPedido enviado ao médico. Acompanhe o estado em 'Os meus pedidos em curso'.")

    def ver_pedidos(self):
        Interface.titulo("Os meus pedidos em curso")
        pedidos = self.clinica.pedidos_em_curso_do_paciente(self.paciente.id)
        if not pedidos:
            print("\nNão tem pedidos em curso.")
            return
        for pedido in pedidos:
            pedido.mostrar_ao_paciente()

    def ver_registo(self):
        Interface.titulo("O meu registo médico")
        registos = self.clinica.registos_do_paciente(self.paciente.id)
        if not registos:
            print("\nAinda não tem registos médicos.")
            return
        for registo in registos:
            registo.mostrar()


class MenuMedico(MenuClinico):
    def __init__(self, clinica, utilizador):
        super().__init__(clinica, utilizador)
        self.medico = clinica.obter_medico(utilizador["id"])
        self.opcoes = [
            ("Pedidos de atendimento pendentes", self.tratar_pendentes),
            ("Consultas presenciais agendadas", self.consultas_presenciais),
            ("Histórico clínico dos pacientes", self.consultar_historico),
            ("O meu perfil", self.ver_perfil),
        ]

    def cabecalho(self):
        return f"Médico: {self.medico.nome}"

    @staticmethod
    def _escolher_pedido(pedidos):
        ids = {p.id for p in pedidos}
        while True:
            escolha = input("\nNúmero do pedido a tratar (0 para voltar): ").strip()
            if escolha == "0":
                return None
            if escolha.isdigit() and int(escolha) in ids:
                return next(p for p in pedidos if p.id == int(escolha))
            print("  [!] Pedido inválido.")

    def tratar_pendentes(self):
        Interface.titulo("Pedidos de atendimento pendentes")
        pedidos = self.clinica.pedidos_do_medico(self.medico.id, "pendente")
        if not pedidos:
            print("\nNão há pedidos pendentes.")
            return
        for pedido in pedidos:
            pedido.mostrar()
        pedido = self._escolher_pedido(pedidos)
        if pedido is None:
            return

        print("\nO que pretende fazer?")
        print("1. Prescrever diagnóstico virtual")
        print("2. Marcar consulta presencial (necessidade de testes)")
        print("0. Voltar")
        opcao = Interface.ler_inteiro("Opção: ", 0, 2)

        if opcao == 1:
            diagnostico = Interface.ler_texto("Diagnóstico: ")
            prescricao = Interface.ler_texto("Prescrição médica: ")
            self.clinica.finalizar_atendimento(
                pedido.id, self.medico, "virtual",
                "Não aplicável (atendimento virtual)", diagnostico, prescricao,
            )
            print("\nAtendimento virtual concluído e registado.")
        elif opcao == 2:
            justificacao = Interface.ler_texto("Justificação médica da consulta presencial: ")
            data_consulta = Interface.ler_data_hora(
                "Data e hora da consulta (dd/mm/aaaa hh:mm): "
            )
            self.clinica.agendar_presencial(pedido.id, self.medico, justificacao, data_consulta)
            print("\nConsulta presencial marcada. O paciente será informado na sua conta.")

    def consultas_presenciais(self):
        Interface.titulo("Consultas presenciais agendadas")
        pedidos = self.clinica.pedidos_do_medico(self.medico.id, "presencial_agendada")
        if not pedidos:
            print("\nNão há consultas presenciais agendadas.")
            return
        for pedido in pedidos:
            pedido.mostrar()
        pedido = self._escolher_pedido(pedidos)
        if pedido is None:
            return
        print("\nRegisto da consulta presencial:")
        resultados = Interface.ler_texto("Resultados dos testes realizados: ")
        diagnostico = Interface.ler_texto("Diagnóstico: ")
        prescricao = Interface.ler_texto("Prescrição médica: ")
        self.clinica.finalizar_atendimento(
            pedido.id, self.medico, "presencial", resultados, diagnostico, prescricao
        )
        print("\nConsulta presencial concluída e registada.")

    def ver_perfil(self):
        Interface.titulo("O meu perfil")
        self.medico.mostrar()


class MenuAdministrador(MenuClinico):
    def __init__(self, clinica, utilizador):
        super().__init__(clinica, utilizador)
        self.e_chefe = bool(utilizador["chefe"])
        self.opcoes = [
            ("Histórico clínico dos pacientes", self.consultar_historico),
            ("Listar médicos", self.listar_medicos),
            ("Listar pacientes", self.listar_pacientes),
            ("Cadastrar médico", self.cadastrar_medico),
            ("Remover médico", self.remover_medico),
        ]
        if self.e_chefe:  # funções exclusivas do administrador chefe
            self.opcoes += [
                ("Listar administradores", self.listar_administradores),
                ("Registar novo administrador", self.novo_administrador),
                ("Remover administrador", self.remover_administrador),
            ]
        self.opcoes.append(("Alterar a minha palavra-passe", self.alterar_senha))

    def cabecalho(self):
        funcao = "Administrador chefe" if self.e_chefe else "Administrador"
        return f"{funcao}: {self.utilizador['nome_utilizador']}"

    def listar_medicos(self):
        Interface.titulo("Médicos cadastrados")
        medicos = self.clinica.listar_medicos()
        if not medicos:
            print("\nNenhum médico cadastrado.")
        for medico in medicos:
            medico.mostrar()
            print()

    def listar_pacientes(self):
        Interface.titulo("Pacientes cadastrados")
        pacientes = self.clinica.listar_pacientes()
        if not pacientes:
            print("\nNenhum paciente cadastrado.")
        for paciente in pacientes:
            paciente.mostrar()

    def cadastrar_medico(self):
        Formularios.cadastrar_medico(self.clinica, self.utilizador)

    def remover_medico(self):
        Interface.titulo("Remover médico")
        medicos = self.clinica.listar_medicos()
        if not medicos:
            print("\nNenhum médico cadastrado.")
            return
        for medico in medicos:
            medico.mostrar()
            print()
        ids = {m.id for m in medicos}
        while True:
            escolha = input("Número do médico a remover (0 para voltar): ").strip()
            if escolha == "0":
                return
            if escolha.isdigit() and int(escolha) in ids:
                break
            print("  [!] Médico inválido.")
        print("\nOs registos médicos já concluídos são mantidos no histórico.")
        print("Os pedidos ainda por tratar são mantidos: cada paciente será convidado")
        print("a levá-los para outro médico à sua escolha.")
        if Interface.ler_texto("Tem a certeza? (S/N): ").upper() != "S":
            print("\nOperação cancelada.")
            return
        sem_medico = self.clinica.remover_medico(self.utilizador, int(escolha))
        print("\nMédico removido.")
        if sem_medico:
            print(f"{sem_medico} pedido(s) pendente(s) mantido(s), à espera de novo médico.")

    def listar_administradores(self):
        Interface.titulo("Administradores")
        for administrador in self.clinica.listar_administradores():
            administrador.mostrar()

    def novo_administrador(self):
        Formularios.cadastrar_administrador(self.clinica, self.utilizador)

    def remover_administrador(self):
        Interface.titulo("Remover administrador")
        administradores = [a for a in self.clinica.listar_administradores() if not a.chefe]
        if not administradores:
            print("\nNão há outros administradores.")
            return
        for administrador in administradores:
            administrador.mostrar()
        ids = {a.id for a in administradores}
        while True:
            escolha = input("\nNúmero do administrador a remover (0 para voltar): ").strip()
            if escolha == "0":
                return
            if escolha.isdigit() and int(escolha) in ids:
                break
            print("  [!] Administrador inválido.")
        if Interface.ler_texto("Tem a certeza? (S/N): ").upper() != "S":
            print("\nOperação cancelada.")
            return
        self.clinica.remover_administrador(self.utilizador, int(escolha))
        print("\nAdministrador removido.")

    def alterar_senha(self):
        Interface.titulo("Alterar palavra-passe")
        actual = Interface.ler_senha("Palavra-passe actual: ")
        while True:
            nova = Interface.ler_senha(
                f"Nova palavra-passe (mín. {Config.TAMANHO_MIN_SENHA} caracteres): "
            )
            if len(nova) < Config.TAMANHO_MIN_SENHA:
                print("  [!] A palavra-passe é demasiado curta.")
                continue
            if nova != Interface.ler_senha("Confirme a nova palavra-passe: "):
                print("  [!] As palavras-passe não coincidem.")
                continue
            break
        self.clinica.alterar_senha(self.utilizador, actual, nova)
        print("\nPalavra-passe alterada. Inicie sessão novamente.")
        return "sair"


# ============================================================================
# APLICAÇÃO (login e fluxo principal)
# ============================================================================


class Aplicacao:
    PAPEIS = {
        1: ("paciente", "Paciente", MenuPaciente),
        2: ("medico", "Médico", MenuMedico),
        3: ("administrador", "Administrador", MenuAdministrador),
    }

    def __init__(self):
        self.bd = BaseDados()
        self.clinica = Clinica(self.bd)

    def _configurar_primeiro_administrador(self):
        if self.clinica.existe_administrador():
            return
        Interface.titulo("Primeira execução")
        print("Ainda não existe nenhum administrador.")
        print("Crie a conta do ADMINISTRADOR CHEFE (responsável máximo do sistema).\n")
        nome_utilizador, senha = Formularios.credenciais_novas(self.clinica)
        self.clinica.cadastrar_chefe(nome_utilizador, senha)
        print("\nAdministrador chefe criado com sucesso.")

    def _fluxo_acesso(self, papel, rotulo, classe_menu):
        while True:
            Interface.titulo(f"Acesso - {rotulo}")
            print("1. Iniciar sessão")
            if papel == "paciente":
                print("2. Cadastrar-me")
            elif papel == "medico":
                print("(O acesso do médico é criado pelo administrador da clínica.)")
            print("0. Voltar")
            opcao = Interface.ler_inteiro("\nOpção: ", 0, 2 if papel == "paciente" else 1)
            if opcao == 0:
                return
            if opcao == 2:
                Formularios.cadastrar_paciente(self.clinica)
                Interface.pausar()
                continue
            nome_utilizador = Interface.ler_texto("Nome de utilizador: ")
            senha = Interface.ler_senha()
            utilizador = self.clinica.autenticar(nome_utilizador, senha, papel)
            classe_menu(self.clinica, utilizador).executar()
            return

    def executar(self):
        try:
            self._configurar_primeiro_administrador()
            while True:
                Interface.titulo("Clínica Virtual")
                print("Quem é o utilizador?")
                print("1. Paciente")
                print("2. Médico")
                print("3. Administrador do sistema")
                print("0. Sair")
                opcao = Interface.ler_inteiro("\nOpção: ", 0, 3)
                if opcao == 0:
                    print("\nObrigado por utilizar a Clínica Virtual. Até breve!")
                    break
                papel, rotulo, classe_menu = self.PAPEIS[opcao]
                try:
                    self._fluxo_acesso(papel, rotulo, classe_menu)
                except (KeyboardInterrupt, EOFError):
                    raise
                except ErroClinica as erro:
                    print(f"\n  [!] {erro}")
                    Interface.pausar()
                except Exception as erro:  # rede de segurança
                    print(f"\n  [!] Ocorreu um erro inesperado: {erro}")
                    Interface.pausar()
        except (KeyboardInterrupt, EOFError):
            print("\n\nSessão terminada.")
        except ErroClinica as erro:
            print(f"\n  [!] {erro}")
        finally:
            self.bd.fechar()


def main():
    try:
        aplicacao = Aplicacao()
    except ErroBaseDados as erro:
        print(f"\n  [!] {erro}")
        return
    aplicacao.executar()


if __name__ == "__main__":
    main()
