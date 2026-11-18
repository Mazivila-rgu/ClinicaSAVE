# -*- coding: utf-8 -*-
"""Interface de consola e controlo do programa (classe Clinica)."""

import seguranca
from base_dados import BaseDados, ErroBaseDados
from modelos import Administrador, HistoricoClinica, Medico, Paciente, Utilizador
from utils import (linha, titulo, ler_texto, ler_inteiro, ler_sexo,
                   ler_senha, ler_data_hora, pausar)


class Clinica:
    """Orquestra os menus e liga a interface às classes do domínio."""

    PAPEIS = {
        1: ("Paciente", Paciente),
        2: ("Médico", Medico),
        3: ("Administrador", Administrador),
    }

    def __init__(self, bd=None):
        self.bd = bd or BaseDados()

    # ------------------------------------------------------------------
    # Arranque e tratamento de erros
    # ------------------------------------------------------------------

    def executar(self):
        try:
            self.bd.abrir()
            self._seguro(self._configurar_primeiro_administrador)
            self._menu_principal()
        except ErroBaseDados as erro:
            print(f"\n  [!] Erro na base de dados: {erro}.")
        except (KeyboardInterrupt, EOFError):
            print("\n\nSessão terminada.")
        except Exception as erro:  # última barreira: o programa nunca "rebenta"
            print(f"\n  [!] Erro inesperado: {erro}")
        finally:
            self.bd.fechar()

    def _seguro(self, funcao, *args):
        """Executa uma ação e mostra uma mensagem amigável se algo falhar."""
        try:
            return funcao(*args)
        except ErroBaseDados as erro:
            print(f"\n  [!] Erro na base de dados: {erro}.")
        except ValueError as erro:
            print(f"\n  [!] Dados inválidos: {erro}.")
        return None

    # ------------------------------------------------------------------
    # Menu principal e acesso
    # ------------------------------------------------------------------

    def _menu_principal(self):
        while True:
            titulo("Clínica Virtual")
            print("Quem é o utilizador?")
            print("1. Paciente")
            print("2. Médico")
            print("3. Administrador do sistema")
            print("0. Sair")
            opcao = ler_inteiro("\nOpção: ", 0, 3)
            if opcao == 0:
                print("\nObrigado por utilizar a Clínica Virtual. Até breve!")
                return
            rotulo, classe = self.PAPEIS[opcao]
            self._seguro(self._fluxo_acesso, rotulo, classe)

    def _fluxo_acesso(self, rotulo, classe):
        eh_admin = classe is Administrador
        while True:
            titulo(f"Acesso - {rotulo}")
            print("1. Iniciar sessão")
            if not eh_admin:
                print("2. Cadastrar-me")
            print("0. Voltar")
            opcao = ler_inteiro("\nOpção: ", 0, 1 if eh_admin else 2)
            if opcao == 0:
                return
            if opcao == 2:
                self._seguro(self._cadastrar, classe)
                pausar()
                continue
            utilizador = self._seguro(self._autenticar, classe)
            if utilizador is None:
                pausar()
                continue
            if classe is Paciente:
                self._menu_paciente(utilizador)
            elif classe is Medico:
                self._menu_medico(utilizador)
            else:
                self._menu_administrador(utilizador)
            return

    def _autenticar(self, classe):
        nome_utilizador = ler_texto("Nome de utilizador: ")
        senha = ler_senha()
        utilizador = classe.autenticar(self.bd, nome_utilizador, senha)
        if utilizador is None:
            print("  [!] Credenciais inválidas.")
        return utilizador

    def _configurar_primeiro_administrador(self):
        if Administrador.existe_algum(self.bd):
            return
        titulo("Primeira execução")
        print("Ainda não existe nenhum administrador. Crie a conta de administrador.\n")
        nome_utilizador, senha = self._pedir_credenciais_novas()
        Administrador.registar(self.bd, nome_utilizador, senha)
        print("\nAdministrador criado com sucesso.")

    # ------------------------------------------------------------------
    # Entrada de dados partilhada
    # ------------------------------------------------------------------

    def _pedir_nova_senha(self, mensagem="Palavra-passe"):
        minimo = seguranca.TAMANHO_MIN_SENHA
        while True:
            senha = ler_senha(f"{mensagem} (mín. {minimo} caracteres): ")
            if len(senha) < minimo:
                print("  [!] A palavra-passe é demasiado curta.")
                continue
            if senha != ler_senha("Confirme a palavra-passe: "):
                print("  [!] As palavras-passe não coincidem.")
                continue
            return senha

    def _pedir_credenciais_novas(self):
        while True:
            nome_utilizador = ler_texto("Nome de utilizador: ")
            if Utilizador.existe_nome(self.bd, nome_utilizador):
                print("  [!] Esse nome de utilizador já existe. Escolha outro.")
                continue
            break
        return nome_utilizador, self._pedir_nova_senha()

    # ------------------------------------------------------------------
    # Cadastro
    # ------------------------------------------------------------------

    def _cadastrar(self, classe):
        if classe is Medico:
            self._cadastrar_medico()
        else:
            self._cadastrar_paciente()

    def _cadastrar_medico(self):
        titulo("Cadastro de médico")
        nome_utilizador, senha = self._pedir_credenciais_novas()
        print("\n-- Perfil profissional --")
        nome = ler_texto("Nome completo: ")
        idade = ler_inteiro("Idade: ", 18, 100)
        sexo = ler_sexo()
        formacao = ler_texto("Formação (ex.: Medicina Geral): ")
        print("Nível de formação:")
        for i, nivel in enumerate(Medico.NIVEIS_FORMACAO, 1):
            print(f"  {i}. {nivel}")
        escolha = ler_inteiro("Escolha: ", 1, len(Medico.NIVEIS_FORMACAO))
        nivel = Medico.NIVEIS_FORMACAO[escolha - 1]
        especializacao = ler_texto("Especialização (ENTER se não tiver): ", obrigatorio=False)
        Medico.cadastrar(self.bd, nome_utilizador, senha, nome, idade, sexo,
                         formacao, nivel, especializacao)
        print("\nMédico cadastrado com sucesso. Já pode iniciar sessão.")

    def _cadastrar_paciente(self):
        titulo("Cadastro de paciente")
        nome_utilizador, senha = self._pedir_credenciais_novas()
        print("\n-- Dados pessoais --")
        nome = ler_texto("Nome completo: ")
        idade = ler_inteiro("Idade: ", 0, 120)
        sexo = ler_sexo()
        moradia = ler_texto("Moradia (bairro/cidade): ")
        Paciente.cadastrar(self.bd, nome_utilizador, senha, nome, idade, sexo, moradia)
        print("\nPaciente cadastrado com sucesso. Já pode iniciar sessão.")

    # ------------------------------------------------------------------
    # Apresentação de dados
    # ------------------------------------------------------------------

    @staticmethod
    def _mostrar_medico(m):
        print(f"  [{m.perfil_id}] Dr(a). {m.nome}")
        print(f"      Idade: {m.idade} | Sexo: {m.sexo}")
        print(f"      Formação: {m.formacao} ({m.nivel_formacao})")
        print(f"      Especialização: {m.especializacao}")

    @staticmethod
    def _mostrar_registo(r):
        linha("-")
        print(f"Data de entrada : {r['data_entrada']}")
        print(f"Médico          : {r['nome_medico']}")
        print(f"Tipo de consulta: {r['tipo_consulta'].capitalize()}")
        print(f"Diagnóstico     : {r['diagnostico']}")
        print(f"Prescrição      : {r['prescricao']}")

    @staticmethod
    def _mostrar_historico(h):
        linha("-")
        print(f"Paciente        : {h['nome_paciente']} ({h['idade']} anos, {h['sexo']})")
        print(f"Data de entrada : {h['data_entrada']}")
        print(f"Sintomas        : {h['sintomas']}")
        print(f"Resultados testes: {h['resultados_testes']}")
        print(f"Diagnóstico     : {h['diagnostico']}")
        print(f"Prescrição      : {h['prescricao']}")
        print(f"Médico          : {h['nome_medico']}")
        print(f"Tipo de consulta: {h['tipo_consulta'].capitalize()}")
        if h["tipo_consulta"] == "presencial":
            print(f"Justificação da consulta presencial: {h['justificacao_presencial']}")

    @staticmethod
    def _mostrar_pedido_medico(a):
        linha("-")
        print(f"Pedido n.º {a.id} | Entrada: {a.data_entrada}")
        print(f"Paciente: {a.nome_paciente} ({a.idade_paciente} anos, {a.sexo_paciente}) - {a.moradia}")
        print(f"Sintomas: {a.sintomas}")
        if a.estado == "presencial_agendada":
            print(f"Consulta presencial: {a.data_consulta}")
            print(f"Justificação       : {a.justificacao}")

    @staticmethod
    def _mostrar_pedido_paciente(a):
        linha("-")
        print(f"Data do pedido: {a.data_entrada}")
        print(f"Médico        : {a.nome_medico}")
        print(f"Sintomas      : {a.sintomas}")
        if a.estado == "pendente":
            print("Estado        : Aguarda resposta do médico")
        else:
            print("Estado        : CONSULTA PRESENCIAL MARCADA")
            print(f"Data da consulta: {a.data_consulta}")
            print(f"Motivo          : {a.justificacao}")

    def _consultar_historico(self):
        """Acessível apenas a médicos e administradores."""
        titulo("Histórico clínico dos pacientes")
        filtro = ler_texto("Pesquisar por nome do paciente (ENTER para ver todos): ", False)
        registos = HistoricoClinica.pesquisar(self.bd, filtro or None)
        if not registos:
            print("\nNenhum registo encontrado no histórico clínico.")
            return
        print(f"\n{len(registos)} registo(s) encontrado(s):")
        for h in registos:
            self._mostrar_historico(h)

    # ------------------------------------------------------------------
    # Menu do paciente
    # ------------------------------------------------------------------

    def _menu_paciente(self, paciente):
        acoes = {
            1: self._paciente_pedir_atendimento,
            2: self._paciente_ver_pedidos,
            3: self._paciente_ver_registo,
        }
        while True:
            titulo(f"Paciente: {paciente.nome}")
            print("1. Ver médicos e pedir atendimento")
            print("2. Os meus pedidos em curso")
            print("3. O meu registo médico")
            print("0. Terminar sessão")
            opcao = ler_inteiro("\nOpção: ", 0, 3)
            if opcao == 0:
                return
            self._seguro(acoes[opcao], paciente)
            pausar()

    def _paciente_pedir_atendimento(self, paciente):
        titulo("Escolher médico")
        medicos = Medico.listar(self.bd)
        if not medicos:
            print("\nAinda não há médicos cadastrados.")
            return
        for m in medicos:
            self._mostrar_medico(m)
            print()
        ids_validos = {m.perfil_id for m in medicos}
        while True:
            escolha = input("Introduza o número do médico (0 para voltar): ").strip()
            if escolha == "0":
                return
            if escolha.isdigit() and int(escolha) in ids_validos:
                medico_id = int(escolha)
                break
            print("  [!] Médico inválido.")
        print("\nDescreva os seus sintomas (seja o mais detalhado possível):")
        sintomas = ler_texto("> ")
        paciente.pedir_atendimento(self.bd, medico_id, sintomas)
        print("\nPedido enviado ao médico. Acompanhe o estado em 'Os meus pedidos'.")

    def _paciente_ver_pedidos(self, paciente):
        titulo("Os meus pedidos em curso")
        pedidos = paciente.pedidos_em_curso(self.bd)
        if not pedidos:
            print("\nNão tem pedidos em curso.")
            return
        for p in pedidos:
            self._mostrar_pedido_paciente(p)

    def _paciente_ver_registo(self, paciente):
        titulo("O meu registo médico")
        registos = paciente.registos(self.bd)
        if not registos:
            print("\nAinda não tem registos médicos.")
            return
        for r in registos:
            self._mostrar_registo(r)

    # ------------------------------------------------------------------
    # Menu do médico
    # ------------------------------------------------------------------

    def _menu_medico(self, medico):
        acoes = {
            1: self._medico_tratar_pendentes,
            2: self._medico_consultas_presenciais,
            3: lambda _medico: self._consultar_historico(),
            4: self._medico_ver_perfil,
        }
        while True:
            titulo(f"Médico: {medico.nome}")
            print("1. Pedidos de atendimento pendentes")
            print("2. Consultas presenciais agendadas")
            print("3. Histórico clínico dos pacientes")
            print("4. O meu perfil")
            print("0. Terminar sessão")
            opcao = ler_inteiro("\nOpção: ", 0, 4)
            if opcao == 0:
                return
            self._seguro(acoes[opcao], medico)
            pausar()

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

    def _medico_tratar_pendentes(self, medico):
        titulo("Pedidos de atendimento pendentes")
        pedidos = medico.pedidos(self.bd, "pendente")
        if not pedidos:
            print("\nNão há pedidos pendentes.")
            return
        for p in pedidos:
            self._mostrar_pedido_medico(p)
        pedido = self._escolher_pedido(pedidos)
        if pedido is None:
            return

        print("\nO que pretende fazer?")
        print("1. Prescrever diagnóstico virtual")
        print("2. Marcar consulta presencial (necessidade de testes)")
        print("0. Voltar")
        opcao = ler_inteiro("Opção: ", 0, 2)
        if opcao == 1:
            diagnostico = ler_texto("Diagnóstico: ")
            prescricao = ler_texto("Prescrição médica: ")
            pedido.concluir(self.bd, medico.nome, "virtual",
                            "Não aplicável (atendimento virtual)", diagnostico, prescricao)
            print("\nAtendimento virtual concluído e registado.")
        elif opcao == 2:
            justificacao = ler_texto("Justificação médica da consulta presencial: ")
            data_consulta = ler_data_hora("Data e hora da consulta (dd/mm/aaaa hh:mm): ")
            pedido.agendar_presencial(self.bd, justificacao, data_consulta)
            print("\nConsulta presencial marcada. O paciente será informado na sua conta.")

    def _medico_consultas_presenciais(self, medico):
        titulo("Consultas presenciais agendadas")
        pedidos = medico.pedidos(self.bd, "presencial_agendada")
        if not pedidos:
            print("\nNão há consultas presenciais agendadas.")
            return
        for p in pedidos:
            self._mostrar_pedido_medico(p)
        pedido = self._escolher_pedido(pedidos)
        if pedido is None:
            return
        print("\nRegisto da consulta presencial:")
        resultados = ler_texto("Resultados dos testes realizados: ")
        diagnostico = ler_texto("Diagnóstico: ")
        prescricao = ler_texto("Prescrição médica: ")
        pedido.concluir(self.bd, medico.nome, "presencial", resultados, diagnostico, prescricao)
        print("\nConsulta presencial concluída e registada.")

    def _medico_ver_perfil(self, medico):
        titulo("O meu perfil")
        self._mostrar_medico(medico)

    # ------------------------------------------------------------------
    # Menu do administrador
    # ------------------------------------------------------------------

    def _menu_administrador(self, admin):
        acoes = {
            1: lambda _admin: self._consultar_historico(),
            2: lambda _admin: self._admin_listar_medicos(),
            3: lambda _admin: self._admin_listar_pacientes(),
            4: lambda _admin: self._admin_novo_administrador(),
        }
        while True:
            titulo(f"Administrador: {admin.nome_utilizador}")
            print("1. Histórico clínico dos pacientes")
            print("2. Listar médicos")
            print("3. Listar pacientes")
            print("4. Registar novo administrador")
            print("5. Alterar a minha palavra-passe")
            print("0. Terminar sessão")
            opcao = ler_inteiro("\nOpção: ", 0, 5)
            if opcao == 0:
                return
            if opcao == 5:
                if self._seguro(self._admin_alterar_senha, admin):
                    return
            else:
                self._seguro(acoes[opcao], admin)
            pausar()

    def _admin_listar_medicos(self):
        titulo("Médicos cadastrados")
        medicos = Medico.listar(self.bd)
        if not medicos:
            print("\nNenhum médico cadastrado.")
        for m in medicos:
            self._mostrar_medico(m)
            print()

    def _admin_listar_pacientes(self):
        titulo("Pacientes cadastrados")
        pacientes = Paciente.listar(self.bd)
        if not pacientes:
            print("\nNenhum paciente cadastrado.")
        for p in pacientes:
            print(f"  [{p.perfil_id}] {p.nome} | {p.idade} anos | {p.sexo} | {p.moradia}")

    def _admin_novo_administrador(self):
        titulo("Registar novo administrador")
        nome_utilizador, senha = self._pedir_credenciais_novas()
        Administrador.registar(self.bd, nome_utilizador, senha)
        print("\nNovo administrador registado.")

    def _admin_alterar_senha(self, admin):
        titulo("Alterar palavra-passe")
        atual = ler_senha("Palavra-passe atual: ")
        if not admin.verificar_senha(atual):
            print("  [!] Palavra-passe atual incorreta.")
            return False
        nova = self._pedir_nova_senha("Nova palavra-passe")
        admin.alterar_senha(self.bd, nova)
        print("\nPalavra-passe alterada. Será necessário iniciar sessão novamente.")
        return True