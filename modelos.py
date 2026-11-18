# -*- coding: utf-8 -*-
"""Classes do domínio: Utilizador (Paciente, Medico, Administrador),
Atendimento e HistoricoClinica. Não contêm código de interface."""

import seguranca
from base_dados import ErroBaseDados
from utils import agora


class Utilizador:
    """Conta de acesso. Classe base de Paciente, Medico e Administrador."""

    papel = None  # definido em cada subclasse

    def __init__(self, conta):
        self.id = conta["id"]
        self.nome_utilizador = conta["nome_utilizador"]
        self._senha_hash = conta["senha_hash"]
        self._sal = conta["sal"]

    @staticmethod
    def existe_nome(bd, nome_utilizador):
        linha = bd.um(
            "SELECT 1 FROM utilizadores WHERE nome_utilizador = ?", (nome_utilizador,)
        )
        return linha is not None

    @classmethod
    def _inserir_conta(cls, conexao, nome_utilizador, senha):
        """Insere a conta dentro de uma transação já aberta. Devolve o id."""
        if not nome_utilizador:
            raise ValueError("o nome de utilizador é obrigatório")
        if len(senha) < seguranca.TAMANHO_MIN_SENHA:
            raise ValueError("a palavra-passe é demasiado curta")
        sal = seguranca.novo_sal()
        cursor = conexao.execute(
            "INSERT INTO utilizadores (nome_utilizador, senha_hash, sal, papel) VALUES (?,?,?,?)",
            (nome_utilizador, seguranca.gerar_hash(senha, sal), sal, cls.papel),
        )
        return cursor.lastrowid

    def verificar_senha(self, senha):
        calculado = seguranca.gerar_hash(senha, self._sal)
        return seguranca.comparar(calculado, self._senha_hash)

    def alterar_senha(self, bd, nova):
        if len(nova) < seguranca.TAMANHO_MIN_SENHA:
            raise ValueError("a palavra-passe é demasiado curta")
        sal = seguranca.novo_sal()
        novo_hash = seguranca.gerar_hash(nova, sal)
        with bd.transacao() as conexao:
            conexao.execute(
                "UPDATE utilizadores SET senha_hash = ?, sal = ? WHERE id = ?",
                (novo_hash, sal, self.id),
            )
        self._senha_hash, self._sal = novo_hash, sal

    @classmethod
    def carregar(cls, bd, conta):
        # `bd` não é usado aqui, mas mantém a mesma assinatura das subclasses
        # (Medico e Paciente precisam dele para ler o perfil).
        del bd
        return cls(conta)

    @classmethod
    def autenticar(cls, bd, nome_utilizador, senha):
        """Devolve o utilizador autenticado ou None se as credenciais forem inválidas."""
        conta = bd.um(
            "SELECT * FROM utilizadores WHERE nome_utilizador = ? AND papel = ?",
            (nome_utilizador, cls.papel),
        )
        if conta is None:
            return None
        calculado = seguranca.gerar_hash(senha, conta["sal"])
        if not seguranca.comparar(calculado, conta["senha_hash"]):
            return None
        return cls.carregar(bd, conta)


class Administrador(Utilizador):
    papel = "administrador"

    @classmethod
    def existe_algum(cls, bd):
        return bd.um("SELECT 1 FROM utilizadores WHERE papel = 'administrador'") is not None

    @classmethod
    def registar(cls, bd, nome_utilizador, senha):
        with bd.transacao() as conexao:
            cls._inserir_conta(conexao, nome_utilizador, senha)


class Medico(Utilizador):
    papel = "medico"
    NIVEIS_FORMACAO = ["Licenciatura", "Pós-graduação", "Mestrado", "Doutoramento"]

    def __init__(self, conta, perfil):
        super().__init__(conta)
        self.perfil_id = perfil["id"]
        self.nome = perfil["nome"]
        self.idade = perfil["idade"]
        self.sexo = perfil["sexo"]
        self.formacao = perfil["formacao"]
        self.nivel_formacao = perfil["nivel_formacao"]
        self.especializacao = perfil["especializacao"] or "Sem especialização"

    @classmethod
    def carregar(cls, bd, conta):
        perfil = bd.um("SELECT * FROM medicos WHERE utilizador_id = ?", (conta["id"],))
        if perfil is None:
            raise ErroBaseDados("o perfil do médico não foi encontrado")
        return cls(conta, perfil)

    @classmethod
    def cadastrar(cls, bd, nome_utilizador, senha, nome, idade, sexo,
                  formacao, nivel_formacao, especializacao=None):
        with bd.transacao() as conexao:
            utilizador_id = cls._inserir_conta(conexao, nome_utilizador, senha)
            conexao.execute(
                """INSERT INTO medicos
                   (utilizador_id, nome, idade, sexo, formacao, nivel_formacao, especializacao)
                   VALUES (?,?,?,?,?,?,?)""",
                (utilizador_id, nome, idade, sexo, formacao, nivel_formacao,
                 especializacao or None),
            )

    @classmethod
    def listar(cls, bd):
        medicos = []
        for perfil in bd.todos("SELECT * FROM medicos ORDER BY nome"):
            conta = bd.um("SELECT * FROM utilizadores WHERE id = ?", (perfil["utilizador_id"],))
            medicos.append(cls(conta, perfil))
        return medicos

    def pedidos(self, bd, estado):
        return Atendimento.do_medico(bd, self.perfil_id, estado)


class Paciente(Utilizador):
    papel = "paciente"

    def __init__(self, conta, perfil):
        super().__init__(conta)
        self.perfil_id = perfil["id"]
        self.nome = perfil["nome"]
        self.idade = perfil["idade"]
        self.sexo = perfil["sexo"]
        self.moradia = perfil["moradia"]

    @classmethod
    def carregar(cls, bd, conta):
        perfil = bd.um("SELECT * FROM pacientes WHERE utilizador_id = ?", (conta["id"],))
        if perfil is None:
            raise ErroBaseDados("o perfil do paciente não foi encontrado")
        return cls(conta, perfil)

    @classmethod
    def cadastrar(cls, bd, nome_utilizador, senha, nome, idade, sexo, moradia):
        with bd.transacao() as conexao:
            utilizador_id = cls._inserir_conta(conexao, nome_utilizador, senha)
            conexao.execute(
                "INSERT INTO pacientes (utilizador_id, nome, idade, sexo, moradia) VALUES (?,?,?,?,?)",
                (utilizador_id, nome, idade, sexo, moradia),
            )

    @classmethod
    def listar(cls, bd):
        pacientes = []
        for perfil in bd.todos("SELECT * FROM pacientes ORDER BY nome"):
            conta = bd.um("SELECT * FROM utilizadores WHERE id = ?", (perfil["utilizador_id"],))
            pacientes.append(cls(conta, perfil))
        return pacientes

    def pedir_atendimento(self, bd, medico_id, sintomas):
        return Atendimento.criar(bd, self.perfil_id, medico_id, sintomas)

    def pedidos_em_curso(self, bd):
        return Atendimento.em_curso_do_paciente(bd, self.perfil_id)

    def registos(self, bd):
        """Registo médico guardado na conta do paciente."""
        return bd.todos(
            "SELECT * FROM registos_paciente WHERE paciente_id = ? ORDER BY id DESC",
            (self.perfil_id,),
        )


class Atendimento:
    """Pedido de atendimento de um paciente a um médico."""

    def __init__(self, linha):
        d = dict(linha)
        self.id = d["id"]
        self.paciente_id = d["paciente_id"]
        self.medico_id = d["medico_id"]
        self.data_entrada = d["data_entrada"]
        self.sintomas = d["sintomas"]
        self.estado = d["estado"]
        self.justificacao = d["justificacao_presencial"]
        self.data_consulta = d["data_consulta_presencial"]
        # Campos extra (vêm dos JOINs)
        self.nome_paciente = d.get("nome_paciente")
        self.idade_paciente = d.get("idade")
        self.sexo_paciente = d.get("sexo")
        self.moradia = d.get("moradia")
        self.nome_medico = d.get("nome_medico")

    @classmethod
    def criar(cls, bd, paciente_id, medico_id, sintomas):
        if not sintomas:
            raise ValueError("os sintomas são obrigatórios")
        with bd.transacao() as conexao:
            conexao.execute(
                """INSERT INTO atendimentos (paciente_id, medico_id, data_entrada, sintomas)
                   VALUES (?,?,?,?)""",
                (paciente_id, medico_id, agora(), sintomas),
            )

    @classmethod
    def do_medico(cls, bd, medico_id, estado):
        linhas = bd.todos(
            """SELECT a.*, p.nome AS nome_paciente, p.idade, p.sexo, p.moradia
               FROM atendimentos a JOIN pacientes p ON p.id = a.paciente_id
               WHERE a.medico_id = ? AND a.estado = ?
               ORDER BY a.id""",
            (medico_id, estado),
        )
        return [cls(linha) for linha in linhas]

    @classmethod
    def em_curso_do_paciente(cls, bd, paciente_id):
        linhas = bd.todos(
            """SELECT a.*, m.nome AS nome_medico FROM atendimentos a
               JOIN medicos m ON m.id = a.medico_id
               WHERE a.paciente_id = ? AND a.estado != 'concluido'
               ORDER BY a.id DESC""",
            (paciente_id,),
        )
        return [cls(linha) for linha in linhas]

    def agendar_presencial(self, bd, justificacao, data_consulta):
        with bd.transacao() as conexao:
            conexao.execute(
                """UPDATE atendimentos
                   SET estado = 'presencial_agendada',
                       justificacao_presencial = ?, data_consulta_presencial = ?
                   WHERE id = ?""",
                (justificacao, data_consulta, self.id),
            )
        self.estado = "presencial_agendada"
        self.justificacao = justificacao
        self.data_consulta = data_consulta

    def concluir(self, bd, nome_medico, tipo, resultados, diagnostico, prescricao):
        """Conclui o atendimento e grava os dois registos médicos."""
        if self.estado == "concluido":
            raise ValueError("este atendimento já foi concluído")
        justificacao = self.justificacao if tipo == "presencial" else None
        with bd.transacao() as conexao:
            conexao.execute(
                "UPDATE atendimentos SET estado = 'concluido' WHERE id = ?", (self.id,)
            )
            # 1) Registo na conta do paciente
            conexao.execute(
                """INSERT INTO registos_paciente
                   (atendimento_id, paciente_id, data_entrada, diagnostico, prescricao,
                    nome_medico, tipo_consulta) VALUES (?,?,?,?,?,?,?)""",
                (self.id, self.paciente_id, self.data_entrada,
                 diagnostico, prescricao, nome_medico, tipo),
            )
            # 2) Registo no histórico da clínica (acesso restrito)
            conexao.execute(
                """INSERT INTO historico_clinica
                   (atendimento_id, paciente_id, data_entrada, sintomas, resultados_testes,
                    diagnostico, prescricao, nome_medico, tipo_consulta, justificacao_presencial)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (self.id, self.paciente_id, self.data_entrada, self.sintomas, resultados,
                 diagnostico, prescricao, nome_medico, tipo, justificacao),
            )
        self.estado = "concluido"


class HistoricoClinica:
    """Histórico clínico (acesso restrito a médicos e administradores)."""

    @staticmethod
    def pesquisar(bd, nome_paciente=None):
        sql = """SELECT h.*, p.nome AS nome_paciente, p.idade, p.sexo
                 FROM historico_clinica h JOIN pacientes p ON p.id = h.paciente_id"""
        parametros = ()
        if nome_paciente:
            sql += " WHERE p.nome LIKE ?"
            parametros = (f"%{nome_paciente}%",)
        sql += " ORDER BY h.id DESC"
        return bd.todos(sql, parametros)
