# Habit Workspace — Formato de Arquivos, esquema v4 (proposta)

## Implemented Phase 1 profile

The examples and future contracts below remain authoritative. Phase 1 supports
`note`, `page`, `year_page`, `month_page`, `week_page`, and `day_page` at document
schema version **4**, and the representative `habit` at versions **1 and 4**
(version 1 is the example in section 3). Reading/writing does not silently upgrade
versions. Other kinds/versions, including legacy v3 embedded layouts, are reported
as unsupported and left untouched. No legacy migration is invented without a
source contract; future migrations must be explicit and have round-trip tests.

Every document requires a mapping `hw` with integer `schema_version`, string
`kind`, and UUID string `id`. Notes and custom pages may have a string `title`,
string-list `tags`, and UUID `origin_page_id`. These fields are optional. Period
pages require a matching ISO `period` (e.g. `week/2026-W44`); daily pages may
instead use `date: "2026-10-29"`. If both are present they must agree. Habits
require `name`, `scope.start`, nullable `scope.end_exclusive`, and `recurrence`
(`daily` or `weekdays` with unique integer days 1–7). Phase 1 validates storage
only; it does not generate occurrences or compute statistics.

Known `layout_history`, `checkins`, and `observations` structures are validated
and preserved as data. References from these structures and `origin_page_id`
are disclosed by the scanner/importer. Layout JSON and metric definitions are
not indexed in Phase 1, so these references are explicitly **unavailable in this
phase**, even if a JSON/metric file is present. Unknown fields/blocks remain inert
and round-trip; references inside unknown extensions cannot be interpreted.

The Phase 1 record profile uses daily `checkins` with UUID `id`, UUID `habit_id`,
ISO-string `date`, `state` (`done`, `missed`, `skipped`), text `label_snapshot`,
and timezone-qualified ISO-string `recorded_at`. `observations` use UUID `id`,
UUID `field_id`, text `field_label_snapshot`, ISO-string `observed_date`,
timezone-qualified `recorded_at`, and `value`. Record dates must match the page;
record UUIDs and habit/date pairs must be unique within that document. These
records are preserved/inspected only; no capture or analytics service is added.

Frontmatter permits bounded YAML mappings with string keys, sequences, scalar
values and standard timestamps (known date fields still require ISO strings).
Custom tags, anchors, aliases, merge keys, duplicate keys, multiple YAML documents,
non-finite numbers, nesting over 32 levels, and more than 20,000 parser events are
rejected. Files are limited to 2 MiB, frontmatter to 256 KiB. UTF-8 is required;
an existing BOM and Markdown line endings are retained. Comments and quoting in
frontmatter are retained where supported by the round-trip parser. Identical
imports are determined by exact file bytes, conservatively treating formatting
differences with the same UUID as conflicts.

`.habit-workspace/vault.json` is UTF-8 JSON with `schema_version: 1`,
`kind: "vault"`, UUID `id`, and non-empty string `name`. Unknown configuration
fields are preserved (opening never rewrites it). Cache paths are relative to the
vault. `.habit-workspace/backups/` holds exact pre-save recovery copies; `.habit-workspace/write.lock/`
serializes application writers. A leftover lock is reported for explicit recovery,
never automatically stolen. Internal files are excluded from document discovery.
Notes default to `Notes/`; standalone imports use `Imports/<UUID>.md`. Neither
location determines identity. Plain Markdown requires an explicit wrap-as-note
import option; its complete original text becomes the note body.

## 1. Contrato geral
- Um **cofre** (`vault`) é uma pasta escolhida pelo usuário, transportável entre computadores.
- Documentos de domínio e páginas são arquivos de texto Markdown UTF-8 (`.md`) com propriedades YAML iniciais delimitadas por `---`.
- O prefixo `hw` encapsula metadados reconhecidos pelo aplicativo. Todo documento tem `hw.schema_version`, `hw.kind` e um `hw.id` UUID estável. Renomear arquivo NÃO altera ID.
- Datas civis são ISO `YYYY-MM-DD`, serializadas como strings; intervalos têm início inclusivo e fim exclusivo (`end_exclusive`), ou `null` quando aberto.
- Layouts visuais versionados são **arquivos JSON declarativos separados**. Páginas Markdown referenciam layout por ID e versão em `layout_history`. Markdown mantém notas e dados canônicos; nunca contém código QML/Python executável.
- Campos desconhecidos e texto Markdown devem ser preservados durante operações de leitura/gravação; o app suporta esquema versionado e migrações testadas.
- IDs referenciam itens, caminhos não são chaves canônicas. O nome do arquivo é amigável ao humano; um índice resolve ID -> arquivo.

## 2. Estrutura ilustrativa do cofre (pastas físicas livres)
```text
MeuHabitWorkspace/
  .habit-workspace/
    vault.json             # ID do cofre, versão, opções compartilháveis
    index.sqlite           # cache REGENERÁVEL; nunca fonte principal
  Pages/
    Days/2026-10-23.md
    Weeks/2026-W43.md
    Months/2026-10.md
    Years/2026.md
  Layouts/
    weekly-study.v1.json
    weekly-study.v2.json
  Items/
    Habits/estudar-python.md
    Metrics/reading-minutes.md
    Tasks/
    Goals/
    Events/
  Assets/
  Templates/
```

A árvore visual Ano -> Mês -> Semana -> Dia é construída pelo aplicativo a partir dos períodos, **não** pela localização física destas pastas. Semanas ISO cruzam meses/anos.
O aplicativo deve funcionar mesmo que o usuário reorganize seus arquivos em outras subpastas do cofre.

## 3. Exemplo — hábito, registro canônico
`Items/Habits/estudar-python.md`:
```markdown
---
hw:
  schema_version: 1
  kind: habit
  id: "ed64a1a4-3b60-4b51-9063-187fd0359241"
  name: "Estudar Python"
  scope:
    start: "2026-10-01"
    end_exclusive: "2027-01-01"
  recurrence:
    kind: weekdays
    days: [1, 2, 3, 4, 5] # 1=segunda; 7=domingo
  tags: [estudos, programacao]
---
# Estudar Python

Estudar Python por 30 minutos nos dias úteis.
```

## 4. Exemplos — layout separado e página com assignment (sem QML no documento)
`Layouts/weekly-study.v2.json` (ilustrativo, com IDs estáveis):
```json
{
  "schema_version": 4,
  "kind": "layout_template",
  "id": "3dd70d9e-2a21-4710-a3f8-3c8cf91465e4",
  "version": 2,
  "name": "Semana de estudos",
  "grid": { "columns": 2, "gap": 16 },
  "blocks": [
    { "id": "5e7ebbb0-6364-4803-b193-fb0e39b01a7e", "type": "checklist", "width": 2, "source": { "mode": "habits_by_tags", "tags": ["estudos"] } },
    { "id": "8018df30-bd44-46c4-bab3-518f16b14cf3", "type": "number_input", "width": 1, "field_id": "838a7ebc-38a1-4a14-a9cb-f992558310e8" },
    { "id": "4484184e-42fd-4624-a23a-e19606c08955", "type": "note", "width": 2 }
  ]
}
```

`Pages/Weeks/2026-W44.md`: a única fonte das atribuições específicas da semana. Histórico não significa layouts simultâneos.
````markdown
---
hw:
  schema_version: 4
  kind: week_page
  id: "a9adba57-c095-4a1b-8709-4b11e7cd7ccb"
  period: "week/2026-W44"
  layout_history:
    - layout_id: "3dd70d9e-2a21-4710-a3f8-3c8cf91465e4"
      version: 1
      effective_at: "2026-10-26T00:00:00-03:00"
    - layout_id: "3dd70d9e-2a21-4710-a3f8-3c8cf91465e4"
      version: 2
      effective_at: "2026-10-29T10:00:00-03:00"
---
# Semana 44

<!-- hw:content id="4484184e-42fd-4624-a23a-e19606c08955" -->
## Observações
Revisar fundamentos de Python.
<!-- /hw:content -->
````

`Items/Metrics/reading-minutes.md` define um campo mensurável separado do layout:
```yaml
---
hw:
  schema_version: 4
  kind: metric_definition
  id: "838a7ebc-38a1-4a14-a9cb-f992558310e8"
  name: "Tempo de estudo"
  value_type: integer
  unit: minutes
  aggregation: sum
  tags: [estudos]
  active_from: "2026-10-29T10:00:00-03:00"
---
```

`Pages/Days/2026-10-29.md` armazena uma observação efetiva, nunca apenas uma célula do layout:
```yaml
---
hw:
  schema_version: 4
  kind: day_page
  id: "531f4227-872c-4605-84eb-6bbf270481df"
  date: "2026-10-29"
  observations:
    - id: "325b2da4-2d06-46d2-bf1a-879d66e1034e"
      field_id: "838a7ebc-38a1-4a14-a9cb-f992558310e8"
      field_label_snapshot: "Tempo de estudo"
      observed_date: "2026-10-29"
      recorded_at: "2026-10-29T19:12:00-03:00"
      value: 40
      source_period_ref: "week/2026-W44"
---
```

Para check-ins de hábitos, continuam valendo `checkins` e `habit_id` conforme contrato v3; **não duplicar o mesmo fato em `observations`**. Um checklist vinculado a hábito produz check-in; um checklist de campo customizado produz observação booleana.

- `layout_history` ordenado por `effective_at` define exatamente uma versão vigente em cada instante, com término implícito na próxima atribuição. Antes de qualquer atribuição, aplica-se template por tipo ou fallback interno.
- Layout JSON carrega **somente apresentação e bindings**; não carrega histórico de respostas.
- Campos sem referência presente são exibidos com descrição disponível/snapshot e alerta de dependência; não são inventados.
- O bloco de texto guarda seu conteúdo em Markdown delimitado por UUID de componente. Ao copiar uma página sem JSON do layout, notas continuam legíveis.
- Exportação com dependências leva `Layouts`, `Metrics`, outros itens referenciados, observações e Assets necessários, conforme seleção explícita.
- Conteúdo JSON inválido não é executado; manter arquivo e alertar o usuário.

## 5. Entidades e origem
- Outros itens (task, goal, event, review) seguem `hw.kind`, UUID, tags, conteúdo Markdown e metadados por tipo, com esquema documentado antes da implementação.
- Origem da criação (`origin_page_id`) e escopo são independentes. Ao importar página, origem ausente não invalida item.
- Páginas anuais/mensais/semanais guardam **atribuição única e histórico de layout** e notas e preferências; blocos e sua configuração visual ficam nos layouts JSON; entidades compartilhadas são referenciadas por ID.
- A referência de tag é feita por nome normalizado na v1, sem obrigar um documento de tag; normalização, renomeação e colisões devem ser testados.

## 6. Exportação/importação
### A. Copiar um único `.md`
1. Escolher arquivo e validar extensão, tamanho, YAML seguro e versão.
2. Exibir prévia: tipo, ID, período, blocos, dados internos, referências externas.
3. Resolver ID repetido: conteúdo idêntico = ignorar; conteúdo diferente = escolher comparar/substituir/fazer cópia com novo ID (sem reatribuir IDs internamente sem mapear referências).
4. Importar atomicamente e reindexar somente os arquivos necessários.
5. Exibir dependências ausentes: gráfico pode ficar sem dados; check-in pode exibir o rótulo salvo; nunca inventar histórico ou concluir que ausência de documento significa falha.

### B. Exportar pacote autocontido (`.hwpack`)
- Contêiner ZIP contendo `manifest.json`, documentos `.md` e arquivos de mídia explicitamente escolhidos.
- Manifesto lista IDs, caminhos relativos, tipos, versões, checksums e dependências; sem caminhos absolutos.
- Modos: página isolada; página com dependências; cofre inteiro. Para gráficos históricos, informar intervalo requerido e o que será incluído.
- Antes da importação, listar conteúdos, revisar escopo da exportação e validar hashes, quantidade de arquivos, tamanhos e caminhos (proibir path traversal e links perigosos).
- Não copiar arquivo de cache `index.sqlite` como dado necessário, nem telemetria/configurações globais da máquina.

## 7. Invariantes e testes obrigatórios
- Um arquivo diário é importado em cofre limpo e abre mesmo sem arquivo do hábito referenciado; nota e check-in aparecem, com indicação explícita de referência ausente.
- Copiar o hábito referido ou importar um pacote que o inclua resolve a referência pelo UUID, independentemente do caminho.
- Deletar `index.sqlite` e reabrir reconstrói índices, gráficos e filtros sem perder registros.
- Renomear/mover páginas e itens não rompe links internos identificados por UUID.
- Importar mesmo ID com conteúdo diferente apresenta conflito; nunca substitui silenciosamente.
- Um arquivo editado no editor de texto é reindexado sem sobregravação indevida.
- Datas e períodos, estado `unrecorded` versus `missed`, e filtros de gráficos funcionam apenas a partir dos documentos presentes.
- Round-trip: load -> save preserva notas, metadados desconhecidos, quebras de linha relevantes e blocos não reconhecidos; no mínimo preservação semântica e de conteúdo, e preferencialmente estrutural.

## 8. Invariantes adicionais v4
- Um período tem zero/uma atribuição explícita **por instante**, e sempre resolve um layout efetivo pelo fallback.
- Não sobrescrever versões de layout já utilizadas; salvar versão nova e registrar ativação.
- Saídas estruturadas ficam em documentos canônicos com UUID e data de observação; a mesma medição nunca tem duas origens de verdade.
- Migração de v3, se houver dados de usuários, deve ser explícita e testada: `blocks` embutidos em páginas v3 são reconhecidos somente para leitura e migração, não como formato novo.
- Uma fonte semanal ativada em 29/10 não produz falhas automáticas retroativas em 26–28/10.
- Resumos mensais dinâmicos leem campos e check-ins pelos identificadores e datas; a atribuição do layout mensal continua única e imutável até o usuário editá-la.

## Implemented Phase 3 temporal profile

Phase 3 uses the same habit schemas **1 and 4** and creates new habits at **4**.
There is no format migration or new canonical record type. `scope.start` is
inclusive, `scope.end_exclusive` is exclusive or `null`; an inclusive user range
October 27–December 31 is stored as `2026-10-27` to `2027-01-01`.
`recurrence.kind` remains `daily` or `weekdays`; selected days are unique ISO
integers 1–7. Origin is the optional `origin_page_id` UUID, independent of scope
and schedule. A virtual period need not have a materialized page or origin UUID.

The previously specified optional lifecycle field `hw.archived_at` is recognized
on habits as a timezone-qualified ISO timestamp string, or `null`. It is exposed
as metadata and does not silently shorten scope or erase historical schedules.
Invalid values are reported without altering their files. No creation/activation
timestamp is invented for older habits. Validity starts at the explicit scope
start, including when the user deliberately overrides the creation default.

New habit tags use NFC Unicode normalization, trimming and case folding;
empty tags are omitted and normalization collisions within a habit are deduplicated
in first-seen order. Different habits sharing tags retain different UUIDs. Existing
tag spelling and ordering are preserved on scope/recurrence-only edits. No global
tag rename/merge operation is introduced.

`HabitService` updates only the requested semantic fields through the existing
round-trip serializer and revision-checked atomic writer. Nested unknown scope
and recurrence metadata, body text, comments, version and supported extensions
survive. Switching to daily recurrence removes the obsolete known `days` field.
Check-ins remain solely in daily documents. Queries never save generated dates or
states. A scope/schedule edit that makes an existing eligible check-in ineligible
requires acknowledgement in the service API; records remain intact and are
returned separately from currently scheduled occurrences.

Calendar identifiers use canonical ASCII digits and civil Gregorian/ISO dates.
Parsing remains possible through year 9999. Calculations requiring an exclusive
boundary beyond `9999-12-31` raise an explicit range error rather than silently
turning a closed scope into an open one; those existing documents remain readable.
Desktop navigation retains its existing years 2–9998 range.

## Implemented Phase 4 layout and metric profile

Phase 4 adds runtime support for schema-v4 `metric_definition` Markdown documents
and declarative schema-v4 layout JSON. Unsupported schema versions, unknown
component types and malformed files are reported without rewriting their original
bytes. There is no implicit migration of legacy embedded layouts.

Layout JSON uses `kind: "layout_template"`, a stable UUID `id`, immutable positive
`version`, `name`, a one- or two-column `grid`, and declarative `blocks`. Supported
blocks are `checklist`, `list`, `table`, `chart`, `note`, `image`, `section`, and
typed `<value_type>_input` components. Components have UUIDs, configuration,
optional source bindings and grid placement. Layout files may be moved or renamed;
identity is read from their contents. The scanner recognizes layout JSON and the
optional `kind: "layout_defaults"` registry; other or invalid JSON files are
diagnosed and left untouched. JSON is bounded by the same 2 MiB document limit,
rejects duplicate keys and non-finite numbers, and is never executed.

Period-page `layout_history` entries contain `layout_id`, `version` and a
timezone-qualified `effective_at`. Strictly increasing effective instants define
non-overlapping half-open revisions. Resolution uses the active explicit period
assignment, then the active default for its period scale, then a deterministic
built-in layout. Missing dependencies are disclosed and do not resurrect an older
revision. `Templates/defaults.json` stores versioned defaults by period scale.

A `metric_definition` is a canonical Markdown document with UUID, name, `value_type`,
timezone-qualified `active_from`, tags, optional unit and validation bounds,
aggregation metadata, and optional selection options. It may also declare a daily
or weekly temporal policy. Daily observations are stored in the canonical daily
page's `hw.observations`; records retain their UUID, `field_id`, label snapshot,
observed date, timezone-qualified `recorded_at`, value, and optional source period
and component IDs. Weekly observations require a source ISO week containing the
observed date and an explicit month-attribution policy. A pre-activation observed
date is accepted only with `historical_entry: true` and non-empty provenance; it
does not create inferred missing or failed records.

The application publishes new metric definitions, immutable layout revisions and
period assignments in that order. These multi-file changes are not a filesystem
transaction: a failure may leave an unassigned definition or revision, which is
preserved and can be reused by an idempotent retry. The SQLite v2 index includes
layout and assignment projections but remains disposable; scans and metric queries
derive canonical results from the files.
