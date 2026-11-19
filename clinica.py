# -*- coding: utf-8 -*-
"""clinica.py - Regras de negócio (camada de serviço)."""

from modelos import (Administrador, Atendimento, Medico, Paciente,
                     RegistoHistorico, RegistoPaciente)
from seguranca import Seguranca
from utils import ErroAutenticacao, ErroClinica, Interface


# ============================================================================
# CLÍNICA (regras de negócio)
# ============================================================================


class Clinica:
    """Camada de serviço: todas as operações sobre utilizadores e atendimentos."""

    def __init__(self, bd):
        self.bd = bd

    # ---------------- utilizadores e autenticação ----------------

    def existe_nome_utilizador(self, nome_utilizador):
        return self.bd.um(
            "SELECT 1 FROM utilizadores WHERE nome_utilizador = ?", (nome_utilizador,)
        ) is not None

    def existe_administrador(self):
        return self.bd.um(
            "SELECT 1 FROM utilizadores WHERE papel = 'administrador'"
        ) is not None

    @staticmethod
    def _inserir_utilizador(conexao, nome_utilizador, senha, papel, chefe=False):
        sal = Seguranca.novo_sal()
        cursor = conexao.execute(
            """INSERT INTO utilizadores (nome_utilizador, senha_hash, sal, papel, chefe)
               VALUES (?,?,?,?,?)""",
            (nome_utilizador, Seguranca.gerar_hash(senha, sal), sal, papel, int(chefe)),
        )
        return cursor.lastrowid

    # ---------------- permissões ----------------

    @staticmethod
    def _exigir_administrador(executor):
        if executor is None or executor["papel"] != "administrador":
            raise ErroClinica("Apenas administradores podem realizar esta operação.")

    @staticmethod
    def _exigir_chefe(executor):
        if executor is None or executor["papel"] != "administrador" or not executor["chefe"]:
            raise ErroClinica("Apenas o administrador chefe pode realizar esta operação.")

    # ---------------- administradores ----------------

    def cadastrar_chefe(self, nome_utilizador, senha):
        """Cria o administrador chefe (só é possível quando ainda não há administradores)."""
        if self.existe_administrador():
            raise ErroClinica("Já existe um administrador chefe.")
        with self.bd.transacao() as conexao:
            self._inserir_utilizador(conexao, nome_utilizador, senha, "administrador", chefe=True)

    def cadastrar_administrador(self, executor, nome_utilizador, senha):
        """Apenas o administrador chefe pode registar novos administradores."""
        self._exigir_chefe(executor)
        with self.bd.transacao() as conexao:
            self._inserir_utilizador(conexao, nome_utilizador, senha, "administrador")

    def listar_administradores(self):
        linhas = self.bd.todos(
            """SELECT id, nome_utilizador, chefe FROM utilizadores
               WHERE papel = 'administrador' ORDER BY chefe DESC, id"""
        )
        return [Administrador(l) for l in linhas]

    def remover_administrador(self, executor, administrador_id):
        """Apenas o chefe remove administradores; o chefe nunca pode ser removido."""
        self._exigir_chefe(executor)
        alvo = self.bd.um(
            "SELECT * FROM utilizadores WHERE id = ? AND papel = 'administrador'",
            (administrador_id,),
        )
        if alvo is None:
            raise ErroClinica("Administrador inexistente.")
        if alvo["chefe"]:
            raise ErroClinica("O administrador chefe não pode ser removido.")
        with self.bd.transacao() as conexao:
            conexao.execute("DELETE FROM utilizadores WHERE id = ?", (alvo["id"],))

    # ---------------- médicos e pacientes ----------------

    def cadastrar_medico(self, executor, nome_utilizador, senha, nome, idade, sexo,
                         formacao, nivel_formacao, especializacao):
        """Os médicos só podem ser cadastrados por administradores."""
        self._exigir_administrador(executor)
        with self.bd.transacao() as conexao:
            utilizador_id = self._inserir_utilizador(conexao, nome_utilizador, senha, "medico")
            conexao.execute(
                """INSERT INTO medicos
                   (utilizador_id, nome, idade, sexo, formacao, nivel_formacao, especializacao)
                   VALUES (?,?,?,?,?,?,?)""",
                (utilizador_id, nome, idade, sexo, formacao, nivel_formacao, especializacao or None),
            )

    def remover_medico(self, executor, medico_id):
        """Qualquer administrador pode remover um médico.
        - Os registos médicos já concluídos são mantidos (guardam o nome do médico).
        - Os pedidos ainda por tratar são MANTIDOS, ficam sem médico e o paciente é
          convidado a reencaminhá-los para outro médico (ver reencaminhar_pedido).
        - Consultas presenciais já marcadas por este médico voltam a pedidos pendentes,
          para o novo médico decidir.
        Devolve o número de pedidos que ficaram sem médico."""
        self._exigir_administrador(executor)
        medico = self.bd.um("SELECT * FROM medicos WHERE id = ?", (medico_id,))
        if medico is None:
            raise ErroClinica("Médico inexistente.")
        with self.bd.transacao() as conexao:
            conexao.execute(
                """UPDATE atendimentos
                   SET estado = 'pendente', justificacao_presencial = NULL,
                       data_consulta_presencial = NULL
                   WHERE medico_id = ? AND estado = 'presencial_agendada'""",
                (medico["id"],),
            )
            sem_medico = conexao.execute(
                "SELECT COUNT(*) FROM atendimentos WHERE medico_id = ? AND estado = 'pendente'",
                (medico["id"],),
            ).fetchone()[0]
            # Todos os atendimentos deixam de apontar para o médico removido
            conexao.execute(
                "UPDATE atendimentos SET medico_id = NULL WHERE medico_id = ?", (medico["id"],)
            )
            conexao.execute("DELETE FROM medicos WHERE id = ?", (medico["id"],))
            conexao.execute("DELETE FROM utilizadores WHERE id = ?", (medico["utilizador_id"],))
        return sem_medico

    def pedidos_sem_medico(self, paciente_id):
        linhas = self.bd.todos(
            """SELECT * FROM atendimentos
               WHERE paciente_id = ? AND medico_id IS NULL AND estado = 'pendente'
               ORDER BY id""",
            (paciente_id,),
        )
        return [Atendimento(l) for l in linhas]

    def reencaminhar_pedido(self, paciente_id, atendimento_id, novo_medico_id):
        """Passa um pedido sem médico para o médico escolhido pelo paciente."""
        pedido = self.bd.um(
            """SELECT 1 FROM atendimentos
               WHERE id = ? AND paciente_id = ? AND medico_id IS NULL AND estado = 'pendente'""",
            (atendimento_id, paciente_id),
        )
        if pedido is None:
            raise ErroClinica("Pedido inválido ou já reencaminhado.")
        if self.bd.um("SELECT 1 FROM medicos WHERE id = ?", (novo_medico_id,)) is None:
            raise ErroClinica("Médico inexistente.")
        with self.bd.transacao() as conexao:
            conexao.execute(
                "UPDATE atendimentos SET medico_id = ? WHERE id = ?",
                (novo_medico_id, atendimento_id),
            )

    def cadastrar_paciente(self, nome_utilizador, senha, nome, idade, sexo, moradia):
        with self.bd.transacao() as conexao:
            utilizador_id = self._inserir_utilizador(conexao, nome_utilizador, senha, "paciente")
            conexao.execute(
                "INSERT INTO pacientes (utilizador_id, nome, idade, sexo, moradia) VALUES (?,?,?,?,?)",
                (utilizador_id, nome, idade, sexo, moradia),
            )

    def autenticar(self, nome_utilizador, senha, papel):
        linha = self.bd.um(
            "SELECT * FROM utilizadores WHERE nome_utilizador = ? AND papel = ?",
            (nome_utilizador, papel),
        )
        if linha is None or not Seguranca.verificar(senha, linha["sal"], linha["senha_hash"]):
            raise ErroAutenticacao("Credenciais inválidas.")
        return linha

    def alterar_senha(self, utilizador, senha_atual, nova_senha):
        if not Seguranca.verificar(senha_atual, utilizador["sal"], utilizador["senha_hash"]):
            raise ErroAutenticacao("Palavra-passe actual incorrecta.")
        sal = Seguranca.novo_sal()
        with self.bd.transacao() as conexao:
            conexao.execute(
                "UPDATE utilizadores SET senha_hash = ?, sal = ? WHERE id = ?",
                (Seguranca.gerar_hash(nova_senha, sal), sal, utilizador["id"]),
            )

    # ---------------- perfis ----------------

    def obter_medico(self, utilizador_id):
        linha = self.bd.um("SELECT * FROM medicos WHERE utilizador_id = ?", (utilizador_id,))
        if linha is None:
            raise ErroClinica("Perfil de médico não encontrado.")
        return Medico(linha)

    def obter_paciente(self, utilizador_id):
        linha = self.bd.um("SELECT * FROM pacientes WHERE utilizador_id = ?", (utilizador_id,))
        if linha is None:
            raise ErroClinica("Perfil de paciente não encontrado.")
        return Paciente(linha)

    def listar_medicos(self):
        return [Medico(l) for l in self.bd.todos("SELECT * FROM medicos ORDER BY nome")]

    def listar_pacientes(self):
        return [Paciente(l) for l in self.bd.todos("SELECT * FROM pacientes ORDER BY nome")]

    # ---------------- atendimentos ----------------

    def criar_atendimento(self, paciente_id, medico_id, sintomas):
        if self.bd.um("SELECT 1 FROM medicos WHERE id = ?", (medico_id,)) is None:
            raise ErroClinica("Médico inexistente.")
        with self.bd.transacao() as conexao:
            conexao.execute(
                """INSERT INTO atendimentos (paciente_id, medico_id, data_entrada, sintomas)
                   VALUES (?,?,?,?)""",
                (paciente_id, medico_id, Interface.agora(), sintomas),
            )

    def pedidos_do_medico(self, medico_id, estado):
        linhas = self.bd.todos(
            """SELECT a.*, p.nome AS nome_paciente, p.idade, p.sexo, p.moradia
               FROM atendimentos a JOIN pacientes p ON p.id = a.paciente_id
               WHERE a.medico_id = ? AND a.estado = ? ORDER BY a.id""",
            (medico_id, estado),
        )
        return [Atendimento(l) for l in linhas]

    def pedidos_em_curso_do_paciente(self, paciente_id):
        linhas = self.bd.todos(
            """SELECT a.*, m.nome AS nome_medico FROM atendimentos a
               LEFT JOIN medicos m ON m.id = a.medico_id
               WHERE a.paciente_id = ? AND a.estado != 'concluido' ORDER BY a.id DESC""",
            (paciente_id,),
        )
        return [Atendimento(l) for l in linhas]

    def _obter_pedido(self, atendimento_id, medico_id, estado):
        linha = self.bd.um(
            "SELECT * FROM atendimentos WHERE id = ? AND medico_id = ? AND estado = ?",
            (atendimento_id, medico_id, estado),
        )
        if linha is None:
            raise ErroClinica("Pedido inválido ou já tratado.")
        return Atendimento(linha)

    def agendar_presencial(self, atendimento_id, medico, justificacao, data_consulta):
        pedido = self._obter_pedido(atendimento_id, medico.id, "pendente")
        with self.bd.transacao() as conexao:
            conexao.execute(
                """UPDATE atendimentos
                   SET estado = 'presencial_agendada',
                       justificacao_presencial = ?, data_consulta_presencial = ?
                   WHERE id = ?""",
                (justificacao, data_consulta, pedido.id),
            )

    def finalizar_atendimento(self, atendimento_id, medico, tipo, resultados,
                              diagnostico, prescricao):
        """Conclui o atendimento e grava os dois registos médicos numa só transacção."""
        if tipo not in ("virtual", "presencial"):
            raise ErroClinica("Tipo de consulta inválido.")
        estado_necessario = "pendente" if tipo == "virtual" else "presencial_agendada"
        pedido = self._obter_pedido(atendimento_id, medico.id, estado_necessario)
        justificacao = pedido.justificacao_presencial if tipo == "presencial" else None

        with self.bd.transacao() as conexao:
            conexao.execute(
                "UPDATE atendimentos SET estado = 'concluido' WHERE id = ?", (pedido.id,)
            )
            # 1) Registo na conta do paciente
            conexao.execute(
                """INSERT INTO registos_paciente
                   (atendimento_id, paciente_id, data_entrada, diagnostico, prescricao,
                    nome_medico, tipo_consulta) VALUES (?,?,?,?,?,?,?)""",
                (pedido.id, pedido.paciente_id, pedido.data_entrada,
                 diagnostico, prescricao, medico.nome, tipo),
            )
            # 2) Registo no histórico da clínica (acesso restrito)
            conexao.execute(
                """INSERT INTO historico_clinica
                   (atendimento_id, paciente_id, data_entrada, sintomas, resultados_testes,
                    diagnostico, prescricao, nome_medico, tipo_consulta, justificacao_presencial)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (pedido.id, pedido.paciente_id, pedido.data_entrada, pedido.sintomas,
                 resultados, diagnostico, prescricao, medico.nome, tipo, justificacao),
            )

    # ---------------- registos médicos ----------------

    def registos_do_paciente(self, paciente_id):
        linhas = self.bd.todos(
            "SELECT * FROM registos_paciente WHERE paciente_id = ? ORDER BY id DESC",
            (paciente_id,),
        )
        return [RegistoPaciente(l) for l in linhas]

    def historico_clinica(self, nome_paciente=None):
        """Apenas para médicos e administradores (garantido pelos menus)."""
        sql = """SELECT h.*, p.nome AS nome_paciente, p.idade, p.sexo
                 FROM historico_clinica h JOIN pacientes p ON p.id = h.paciente_id"""
        parametros = ()
        if nome_paciente:
            sql += " WHERE p.nome LIKE ?"
            parametros = (f"%{nome_paciente}%",)
        sql += " ORDER BY h.id DESC"
        return [RegistoHistorico(l) for l in self.bd.todos(sql, parametros)]
