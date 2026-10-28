# Habit Workspace — Codex Specification Kit v4

## Desenvolvimento — Fase 2

Interface desktop em português brasileiro, com sidebar retrátil, calendário,
navegação virtual por ano/mês/semana ISO/dia, documentos e notas, propriedades,
busca local, temas claro/escuro, atalhos e movimento reduzido. Crie, abra e troque
cofres pela interface; importe documentos com prévia e reindexe os arquivos em
Configurações. Nenhum cofre ou documento de exemplo é criado ao iniciar.

Os serviços da Fase 1 e seus contratos continuam preservados. Markdown/YAML é a
fonte canônica, SQLite é reconstruível, e navegar por períodos não grava páginas.
Layout Studio, captura de hábitos e análises continuam em suas fases futuras.

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

O smoke test verifica carregamento e encerramento QML. A verificação da Fase 2
exercita entrada real do Qt e salva capturas renderizadas com cofres temporários:

```bash
.venv/bin/pyside6-qmllint -W 0 -i src/habit_workspace/presentation/qml/qmldir src/habit_workspace/presentation/qml/*.qml
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase2.py
```

Veja [verificação e roteiro manual da Fase 2](docs/verification/phase-2.md),
[dependências](docs/dependencies.md) e [verificação da Fase 1](docs/verification/phase-1.md).
A inspeção offscreen não substitui testes com o gerenciador de janelas, seletores
nativos, GPU e leitor de tela no desktop.

Preferências de tema, movimento, sidebar e até cinco caminhos de cofres recentes
ficam no `QSettings` da máquina (no Linux, normalmente
`$XDG_CONFIG_HOME/Habit Workspace/Habit Workspace.conf`, com o padrão do Qt quando
a variável não está definida). Não são conteúdo do cofre. Nenhum cofre recente é
aberto automaticamente; use Ctrl+O para escolhê-lo. Atalhos completos estão em
Configurações. A busca filtra documentos da página atual; não é busca de conteúdo
Markdown nem um motor de analytics.

### Usar o cofre (diagnóstico da Fase 1)

Escolha explicitamente uma pasta nova/vazia, preferencialmente fora deste
repositório. Não há caminho pessoal fixo nem arquivos criados no repositório por
padrão. Todos os comandos abaixo funcionam offline após a instalação:

```bash
.venv/bin/python -m habit_workspace vault create "$HOME/Documents/HabitWorkspace" --name "Meu cofre"
.venv/bin/python -m habit_workspace vault open "$HOME/Documents/HabitWorkspace"
.venv/bin/python -m habit_workspace vault new-note "$HOME/Documents/HabitWorkspace" --title "Minha nota" --body "Texto da nota"
.venv/bin/python -m habit_workspace vault import "$HOME/Documents/HabitWorkspace" /caminho/pagina.md
.venv/bin/python -m habit_workspace vault show "$HOME/Documents/HabitWorkspace" UUID_DO_DOCUMENTO
.venv/bin/python -m habit_workspace vault scan "$HOME/Documents/HabitWorkspace"
.venv/bin/python -m habit_workspace vault reindex "$HOME/Documents/HabitWorkspace"
.venv/bin/python -m habit_workspace --vault "$HOME/Documents/HabitWorkspace"
```

`show` apresenta metadados, conteúdo e referências indisponíveis. Os comandos
retornam JSON de diagnóstico, não uma interface final de edição Markdown.
`import` aceita vários caminhos e retorna `imported`, `skipped`, `conflicting` e
`invalid`. Um arquivo idêntico é ignorado; o mesmo UUID com conteúdo diferente
exige comparação explícita dos arquivos. Nenhum comando substitui conflitos.
Markdown sem frontmatter exige `import ... --as-note`; YAML inválido não é
"consertado" nem descartado. Código dentro de documentos nunca é executado.

`--vault` abre diretamente o cofre informado na interface. O watcher Qt atualiza
listas, prévias e pendências após alterações externas. Importações idênticas não
criam cópias; UUIDs conflitantes são bloqueados e ficam visíveis, com os caminhos
para comparação no editor. A UI não sobrescreve arquivos conflitantes.

Exportação `.hwpack`, backup integrado e resolução com substituição pertencem à
Fase 9. Configurações informa essa limitação e orienta a cópia manual da pasta.
A prévia de leitura é texto inerte abreviado; não carrega imagens ou URLs e não
executa conteúdo. Edição rica e o renderizador de layouts ainda não fazem parte
desta fase.

Apagar **somente** `.habit-workspace/index.sqlite` e executar `open`/`reindex`
reconstrói o cache a partir dos documentos. Nenhum documento depende do SQLite.
É possível copiar a pasta inteira para outra localização, sem editar caminhos
absolutos. Para demonstrar isso com dois cofres temporários gerados:

```bash
.venv/bin/python tools/verify_phase1.py
.venv/bin/pyside6-qmllint -W 0 -i src/habit_workspace/presentation/qml/qmldir src/habit_workspace/presentation/qml/*.qml
unshare --user --map-root-user --net .venv/bin/python -m pytest -q
```

O último comando requer suporte Linux a namespaces. Os testes também bloqueiam
chamadas de rede no fluxo básico de persistência. Nenhum teste usa dados pessoais.

Os arquivos são texto claro: local/offline não significa criptografia, anonimato
ou backup. Salvamentos pela API preservam a revisão anterior em
`.habit-workspace/backups/`; essas cópias também contêm dados pessoais e não têm
limpeza automática. Consulte [privacidade](PRIVACY.md) e as
[limitações de concorrência e recuperação](docs/verification/phase-1.md).

As especificações abaixo continuam sendo os requisitos das fases futuras.

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
