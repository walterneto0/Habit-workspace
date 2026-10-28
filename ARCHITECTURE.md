# Habit Workspace v4 — Arquitetura Python file-first

## Stack
- Python 3 + PySide6 / Qt Quick / QML; domínio Python tipado e independente de Qt.
- Markdown UTF-8 com YAML frontmatter para páginas, itens, logs e notas; JSON declarativo versionado para layouts. Ler `FILE_FORMAT.md` e `LAYOUT_ENGINE.md` antes de modelar os parsers.
- Preferir `ruamel.yaml` em modo seguro/round-trip (avaliar superfície de ataque e preservar estrutura); toda entrada externa deve ser validada pelo esquema. `json` padrão para manifesto de pacotes.
- `sqlite3` é **somente índice descartável**, não data store canônico. Pode acelerar FTS/buscas, mapear UUID->path, tags, datas e agregações reconstruíveis.
- Testes com pytest e lint Ruff. Dependências adicionais justificadas, com controle de versões/licenças.

## Separação de camadas
```text
src/habit_workspace/
  domain/           # escopo, recorrência, estados, fontes, analytics (puro Python)
    layouts/         # LayoutTemplate, AssignmentHistory, resolver de layout
    metrics/         # definições de campos, observations e agregações
  application/      # casos de uso: importar, criar, editar, consultar, exportar
  vault/
    format.py       # leitura/escrita tipada e migração de Markdown
    layouts.py      # JSON inerte: parser, versões, resoluções e migração
    repositories.py # arquivos Markdown, fonte da verdade
    watcher.py      # mudanças externas, reindexação
    bundles.py      # pacotes .hwpack
    atomic_io.py    # gravação atômica, backups, conflitos
  indexing/
    cache.py        # SQLite derivado: rebuild sempre possível
    search.py
  presentation/
    models.py       # QAbstractListModel e adaptadores
    layout_studio.py # comandos add/move/bind/version/save e undo/redo
    controllers.py
    qml/
  __main__.py
```

Fluxo de escrita: QML -> caso de uso -> validação de domínio -> escrita **atômica** no documento -> atualizar índice e notificar UI.
Fluxo de leitura: QML -> caso de uso -> índice (se válido) -> repositório de arquivos -> domínio -> UI.
**NUNCA** persistir alterações somente no SQLite. Atualizar o índice não é condição para uma escrita documental bem-sucedida; índice é reparável.

## Coffre / vault
- Usuário escolhe diretório na primeira execução: criar/abrir cofre. Não amarrar a `~/.local/share` nem salvar conteúdo pessoal no repositório.
- Configuração do cofre em `.habit-workspace/vault.json` (ID/versionamento do cofre); configurações da máquina como tamanho/posição da janela ficam fora do cofre (QStandardPaths).
- Páginas físicas preferencialmente por tipo de período (`Days`, `Weeks`, `Months`, `Years`) e itens por tipo (`Habits`, etc.), mas localização física é escolha do usuário.
- A árvore temporal Ano -> Mês -> Semana -> Dia é **virtual**, independente da estrutura de diretórios. Semana ISO pode cruzar mês e ano.
- UUID no documento é identidade canônica; nome/caminho não determina ID, período, domínio ou autoridade da informação.

## Contratos de domínio
- Page: id, kind, periodRef?, content Markdown, `layout_history` (atribuição exclusiva por instante), tags. Origem de nota independente do escopo de itens.
- LayoutTemplate: JSON versionado; componentes são declarativos e fazem bind com dados canônicos. Nunca executar JS/QML de arquivo.
- FieldDefinition: ID estável e semântica tipada; Observation: valor datado armazenado em documento do cofre, com fonte e origem. Não persistir apenas no layout.
- Layout resolver: atribuição concreta vigente > template padrão da escala > fallback interno. Uma versão ativa por período e instante.
- Habit: id, título, tags, scope, recurrence e arquivamento; armazenado em um `.md` do hábito.
- Checkin: id, habitId, date, state, labelSnapshot, recordedAt e nota opcional; armazenado na página diária da data. Um `habitId` + data permite um check-in efetivo no MVP. Não duplicar o registro canônico no arquivo do hábito.
- Task/Goal/Event/Review: documentos `.md` do próprio tipo ou conteúdo local à página conforme contrato; nunca registros só no banco.
- Chart: bloco persistido dentro de uma página, com período concreto (ou seguir período da página), seleção por IDs manuais ou tags dinâmicas, métrica e visualização. Resultados são computados, não fonte da verdade.
- Block: configuração JSON estritamente declarativa, `kind`, `schema_version`, `id`, posição e binding de fonte. Conteúdo Markdown livre preservado em documentos. Um bloco não é fonte de dados; seu binding aponta para fonte.

## Analytics e dados ausentes
- Índice de check-ins deriva do escaneamento de páginas diárias, não de dados gerados em memória. Histórico incompleto após importação parcial deve ficar sinalizado.
- Ausência de log de ocorrência vencida = `unrecorded`, **nunca** `missed`. Eventos futuros = `future`/`pending` conforme horário civil e política.
- Se a definição do hábito não existe no cofre, um `checkin` com snapshot pode ser mostrado, mas recorrência/denominador completo não podem ser reconstruídos corretamente: sinalizar dependência ausente; não inventar agendamento.
- Gráficos usam dados realmente disponíveis, com aviso de período parcial e fontes faltantes. A seleção via tags é dinâmica e depende dos arquivos de hábitos presentes no cofre.

## Arquivos externos, índice e conflitos
- Observar mudanças de arquivos e diretórios com `QFileSystemWatcher` (Qt); reanexar monitor após renomeações/gravação atômica; para grandes cofres considerar watcher por diretório + revarredura com debounce e fallback de reindexação manual.
- Validar `mtime`, tamanho e hash para não sobrescrever arquivo externamente modificado entre a leitura e a gravação.
- Índice local SQLite pode ser excluído e reconstruído de todos os `.md`; usar transações em reindexação. Índice não é exportado como requisito de portabilidade.
- Usar escrita atômica com `QSaveFile` ou arquivo temporário no mesmo volume + replace; ao encontrar parse inválido, manter original e mostrar erro com caminho/linha quando possível.
- IDs iguais + conteúdos divergentes exigem resolução de conflito em UI, sem sobrescrever automaticamente.
- Segurança: YAML seguro, validação rigorosa, nunca execução dinâmica de conteúdo, arquivo ZIP importado apenas após saneamento de caminhos/tamanhos/hashes; ver `PRIVACY.md`.

## Mobile futuro
- Interface QML deve ser adaptada a telas móveis; contratos do domínio e formato de cofre devem ser multiplataforma. Diretórios e APIs móveis têm restrições próprias; não prometer transferência transparente sem testar.
- Ausência de nuvem é escolha de produto; backup e eventual sincronização local voluntária podem ser adicionados sem invalidar o modelo documental.

## Testes de aceitação fundamentais
1. Criar cofre, três documentos e reiniciar: tudo recuperado apenas dos documentos.
2. Apagar índice SQLite, reabrir e comparar contagens de hábitos, filtros e gráficos com o estado anterior.
3. Mover/renomear arquivos e diretórios do cofre sem perder referências por ID.
4. Importar isoladamente página diária com check-in de hábito não presente; conteúdo importado é legível e o item referenciado fica sinalizado.
5. Importar depois o hábito do mesmo UUID e resolver referência sem recriar check-in.
6. Exportar `.hwpack` com dependências e abrir em cofre limpo com dados e gráficos necessários.
7. Conteúdo inválido, ZIP com traversal, documento duplicado ou alteração externa concorrente nunca causa overwrite silencioso.
8. Escopo, recorrência, semanas ISO, tags, gráficos e estados permanecem corretos após importação/exportação.

## Atualização entre semana e mês (v4)
- `LayoutChanged` atualiza apenas a atribuição/estrutura visual; `FieldCreated/Activated` atualiza índice de fontes; `ObservationRecorded` atualiza índices de dados e invalida queries afetadas.
- Widgets mensais dinâmicos usam consultas de fonte por período, tags e tipo de métrica, nunca 'copiar campos visuais' da página semanal. Gráficos manuais por UUID permanecem fixos.
- Guardar `active_from` na definição do campo e `effective_at` no histórico do layout; mudança visual sem campo novo não altera contagens.
- Operações multi-documento (novo JSON + atribuição de página + eventualmente definição de campo) não são atomicamente garantidas pelo filesystem como conjunto: usar escrita ordenada, retries idempotentes e recovery journal simples se necessário.
- Testar comparação dos gráficos antes/depois de reindexação, versões históricas e semana ISO cruzando meses.

## Perfil implementado da Fase 2

`presentation/controllers.py` adapta `VaultSession`, `ImportService` e
`VaultWatcher` a um estado Qt observável. `presentation/navigation.py` contém
somente rotas de apresentação e cálculos de calendário, sem escopo, recorrência,
resolver de layouts ou agregação. As camadas de domínio/aplicação continuam sem
importar Qt. Os componentes em `presentation/qml/` compartilham tokens de tema.

A UI não grava páginas ao navegar, não infere períodos de caminhos e não executa
layouts externos. Preferências de tema, movimento, sidebar e caminhos recentes
usam QSettings da máquina; os formatos canônicos da Fase 1 não foram alterados.
A prévia documental é limitada a texto inerte e snapshots já armazenados. A
varredura síncrona e os limites de concorrência da Fase 1 continuam aplicáveis;
veja `docs/verification/phase-2.md` antes de assumir suporte a cofres grandes.

## Implemented Phase 3 temporal domain

- `domain/temporal.py`: immutable `PeriodRef`, `TemporalScope`, `Recurrence` and
  scale/kind enums. ISO week identity is independent of the civil month/year;
  periods order by start/end/identifier, without implying a parent relationship.
  Recurrence requires a finite query interval, clips to validity first and yields
  dates lazily, jumping over non-selected weekdays.
- `domain/habits.py`: immutable canonical `Habit`, normalized tag projection,
  origin UUID and optional archival metadata. No Qt, filesystem or SQLite imports.
- `vault/habits.py`: typed mapping over existing `Document` frontmatter. Updates
  retain Markdown, schema version and unknown metadata instead of serializing the
  typed projection as a replacement for the complete document.
- `application/habits.py`: `HabitService.create/load/update/query/query_report`,
  revision-bearing `LoadedHabit`, immutable query/occurrence/check-in DTOs and
  `HistoryImpactError`. Check-ins are inspected only. Missing and unscheduled
  records remain distinguishable; ambiguous habit/check-in identities fail
  explicitly. Parse issues and missing references accompany query results.
- `presentation/navigation.py` reuses `PeriodRef`. The existing document list
  includes scope-intersecting habits from the current scan; its styling and QML
  are unchanged. Navigation does not scan files or expand occurrences.

Canonical writes still use `VaultSession` and `DocumentRepository`; index schema
and ownership are unchanged. A query scans once and derives its result from files,
with at most one calendar year's dates per habit. `query_report` is a no-I/O
projection of an existing scan. These synchronous application methods are intended
for a worker-owned session when future QML occurrence binding is added; they are
not connected to GUI slots. Do not share a mutable `VaultSession` across threads.
The Phase 1/2 synchronous watcher/import/reindex limitations remain; this phase
adds no background scan manager or claim of large-vault responsiveness.

Current scope and recurrence are editable definitions, not versioned historical
schedules. Existing records always survive edits, and out-of-schedule records are
reported separately. Archive metadata is available to callers; historical queries
include archived definitions rather than silently modifying their validity.
Phase 4 adds versioned layout assignments, metric definitions, canonical
observations and file-derived source queries. Visual Layout Studio, habit capture
UI and chart rendering/rollups remain in later roadmap phases.
