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
