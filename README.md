# Clínica Virtual

Sistema de consultas médicas em linha, feito em Python. Permite que pacientes escolham um médico, descrevam os sintomas e recebam um diagnóstico virtual ou uma marcação de consulta presencial, mantendo um registo médico seguro de cada atendimento.

## Elementos do Grupo

- Emilio Felix Mazivila (Mazivila-rgu)
- Jaime de Henriqueta Nelson Cuinica (jaimecuinica80-ai)
- Piedade Celestino Boa (boapiedadecelestino-sudo)
- Henriqueta Gabriela Bombe (HenriquetaGabrielabombegit)

## Funcionalidades

- Acesso por perfil: paciente, médico e administrador, com palavras-passe protegidas por hash.
- O paciente cadastra-se, vê os perfis dos médicos, escolhe um e descreve os sintomas.
- O médico escolhe entre diagnóstico virtual ou consulta presencial (com justificação médica e registo dos resultados dos testes).
- Os médicos só podem ser cadastrados por administradores.
- Vários administradores, com um **administrador chefe** (o primeiro a ser criado): só o chefe regista e remove outros administradores; o chefe não pode ser removido.
- Todos os administradores cadastram e removem médicos, listam utilizadores e consultam o histórico clínico. Ao remover um médico, os registos médicos já concluídos são mantidos e os pedidos pendentes também: quando o paciente entra na conta, o programa pergunta se quer levar o pedido para outro médico à sua escolha.
- Dois registos médicos: um na conta do paciente e outro no histórico da clínica (acesso restrito a médicos e administradores).

## Stack Técnica

- Linguagem: Python 3.x
- Paradigma: Programação Orientada a Objetos (POO)
- Armazenamento: SQLite
- Dependências: nenhuma (apenas a biblioteca padrão: sqlite3, hashlib, hmac, secrets, datetime)

## Arquitetura

- `utils.py`: excepções personalizadas, configuração (`Config`) e `Interface` (leitura validada e apresentação no terminal).
- `seguranca.py`: `Seguranca` (hash e verificação das palavras-passe com PBKDF2).
- `base_dados.py`: `BaseDados` (ligação ao SQLite, criação das tabelas e transacções).
- `modelos.py`: `Modelo` e as classes filhas `Administrador`, `Medico`, `Paciente`, `Atendimento`, `RegistoPaciente` e `RegistoHistorico`.
- `clinica.py`: `Clinica` (regras de negócio: cadastros, atendimentos e registos).
- `main.py`: `Formularios`, os menus (`MenuPaciente`, `MenuMedico` e `MenuAdministrador`, que herdam de `Menu`) e `Aplicacao` (login e fluxo principal).

## Requisitos

- Python 3.8 ou superior instalado no computador.

## Execução


Na primeira execução, o programa pede para criar a conta do administrador chefe. A base de dados (`clinica_virtual.db`) é criada automaticamente.
