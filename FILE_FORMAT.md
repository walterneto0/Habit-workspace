# Habit Workspace — Formato de Arquivos, esquema v4 (proposta)

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
