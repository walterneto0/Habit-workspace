# Habit Workspace — Codex Specification Kit v4

## Desenvolvimento — Fase 0

A base técnica contém uma janela Qt Quick mínima em português. Cofres, dados de
hábitos e Layout Studio ainda não estão implementados. Nenhum dado pessoal é
criado ao iniciar o aplicativo.

Ambiente inicial: Linux e Python 3.14. Instalação local reproduzível:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e '.[dev]'
.venv/bin/python -m habit_workspace
```

A instalação pode precisar de internet; executar o aplicativo instalado não
requer rede ou conta. Dependências não são instaladas globalmente. A janela usa
a fonte sans-serif do sistema, sem baixar fontes ou recursos externos.

Verificações:

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m pytest -q
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m habit_workspace --smoke-test
.venv/bin/python -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
```

O teste offscreen verifica carregamento e encerramento QML, não aprova qualidade
visual nem integração completa com o desktop. Veja
[dependências](docs/dependencies.md) e
[verificação da Fase 0](docs/verification/phase-0.md).

O cofre pessoal será escolhido pelo usuário na Fase 1 e deve ficar fora deste
repositório por padrão. As especificações abaixo continuam sendo os requisitos
das fases futuras.

Kit de **especificação** para desenvolver um aplicativo desktop com **Python + PySide6 / Qt Quick (QML)**. Não é um aplicativo pronto. Substitui a especificação v3 e preserva as decisões anteriores de períodos, hábitos, gráficos, file-first e privacidade.

## Conceito consolidado
- UI moderna inspirada nos princípios visuais de Linear, com cards, navegação temporal e microinterações. **O usuário não trabalha sobre Markdown cru**; usa um editor visual drag-and-drop de layouts.
- Templates reutilizáveis e layouts visuais por período concreto; **um layout efetivo por ano/mês/semana/dia**, com histórico de versões e data de ativação.
- Inputs criam ou vinculam **fontes de dados tipadas com IDs estáveis**; a posição dos blocos não determina o local nem o período de armazenamento de dados.
- Modificar layout semanal e registrar novos valores faz os resumos e gráficos mensais **dinâmicos** considerarem novos dados elegíveis a partir da data de ativação. Filtros manuais de gráfico permanecem fixos.
- Coffre local de Markdown/YAML, JSON de layout, imagens e Assets; SQLite é índice descartável/regenerável. Sem conta, nuvem ou internet obrigatória.

## Arquivos
- `LAYOUT_ENGINE.md` **NOVO — principal documento v4**, regras de templates, período único, componentes, versão, métricas, rollup e testes.
- `PRODUCT.md` — produto e fluxo de uso.
- `FILE_FORMAT.md` — formato file-first de páginas, layout JSON e medições.
- `ARCHITECTURE.md` — camadas Python e Qt, regras de persistência.
- `DESIGN_SYSTEM.md` — tema e Layout Studio.
- `ROADMAP.md` — fases com critérios de aceitação.
- `AGENTS.md` — instruções persistentes do Codex CLI.
- `PROMPTS.md` — prompts sequenciais P0 a P10.
- `PRIVACY.md` — segurança, backups e anonimato limitado.

## Como começar
1. Salve um commit/backup das especificações v3.
2. Extraia os documentos v4 **na raiz do repositório do aplicativo**, substituindo os documentos antigos, não os dados pessoais do vault.
3. Execute `codex`, entre em modo de planejamento (`/plan` se disponível) e envie P0 de `PROMPTS.md`.
4. Valide o plano e execute uma fase por vez; testes de período/IDs/layout/rollup antes de funcionalidades visuais de dependência.

## Nota de projeto
Os JSON e YAML dos exemplos são **propostas de contrato**, não equivalem a um parser já implementado. Regras de migração devem ser verificadas antes de existir conteúdo real de usuários.
