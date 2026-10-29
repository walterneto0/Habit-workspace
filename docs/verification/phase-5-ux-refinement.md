# Fase 5.1 — refinamento de UX do Layout Studio

## Escopo e baseline

Refinamento da Fase 5 sobre `main` / `origin/main` em
`5c2a5fe3a07efcd19b7a7e328ef0279228246b99`, confirmado com `git fetch origin main`.
A árvore estava limpa; branch de trabalho: `feat/phase-5-1-layout-studio-ux`.
Baseline: **245 passed em 63,19 s**. Nenhuma Fase 7/8, nova dependência, migração ou
mudança de esquema foi implementada.

Antes das alterações foram revisados AGENTS, PRODUCT, ARCHITECTURE, DESIGN_SYSTEM,
LAYOUT_ENGINE, FILE_FORMAT, PRIVACY, ROADMAP, relatórios 5/6/6-refinements, QML,
adaptador, serviços e testes. A proposta priorizou apresentação: biblioteca por
finalidade, formulário único, propriedades progressivas e pontos de partida.
Riscos principais: vínculos incompatíveis, criação duplicada, mudança acidental de
outros períodos, perda de registros e regressões de foco/drop. Aceites definidos:
jornada completa com cofre descartável, persistência após reinício/reindexação,
temas/tamanhos, erros de formulário e regressões dos contratos existentes.

## Problemas identificados e mudanças

- A biblioteca tinha tipos em lista plana e inputs de nome/tags separados do
  diálogo. Agora **Adicionar bloco** leva à biblioteca pesquisável, organizada em
  **Acompanhamento**, **Conteúdo**, **Campos de dados** e **Visualizações**. Lista
  geral/tabela, edição de notas, importação de mídia e gráficos explicam limitações.
- Campos usam um formulário único: **Usar existente / Criar novo**. Busca nominal
  filtra tipos compatíveis; decimal pode reutilizar inteiro. Nome/unidade/tipo ou
  opções aparecem conforme necessário. Tags, limites e regras temporais/de resumo
  ficam em **Opções avançadas**. Fontes existentes têm preferência quando presentes.
- Nome obrigatório, opções repetidas/vazias e limites inválidos têm validação local.
  Erros não fecham o formulário; nome, unidade e demais valores são preservados.
  Vírgula decimal nos limites é aceita. O domínio continua validando os dados.
- UUID e enums deixaram de ser identificação principal. Rótulos são em pt-BR, sem
  alterar os valores serializados. A frequência semanal alerta que a captura pela
  interface ainda não está disponível. A definição existente é consultável em
  opções avançadas; a semântica da fonte existente não é editada pelo bloco.
- Checklist reutiliza os contratos anteriores: vários hábitos manuais ordenados,
  tags OR e contexto da data. Busca e inclusão não criam hábitos; a criação de
  hábitos continua em seu formulário próprio, no acompanhamento.
- Cabeçalho de card tem título, alça de seis pontos e **Editar**. Mover acima/abaixo,
  largura, duplicar e remover ficam no painel identificado pelo nome do bloco.
  Arrastar continua funcionando em grade de uma/duas colunas, com feedback para
  destinos válidos/inválidos; os botões são uma alternativa completa.
- Propriedades têm orientação útil quando não há seleção. Painéis possuem rolagem
  independente. Em 900–1099 px a biblioteca é sobreposta; abaixo de 900 px há abas
  **Página / Propriedades**. Em 1100 px ou mais, as três regiões ficam lado a lado.
- **Ponto de partida** oferece atual, vazio, padrão da escala e versões existentes.
  A substituição do rascunho é explícita e pode ser desfeita. O padrão usa o resolver
  existente; não há uma segunda forma de atribuição de layout.
- **Revisar e salvar** nomeia período, blocos adicionados/removidos/modificados,
  ordem/colunas, novos campos e instante local de ativação. Confirma preservação
  dos registros, modelos e demais períodos. Publica uma revisão pelo serviço atual.
- Diálogos seguem os temas e adaptam altura ao conteúdo/janela. Ações ficam no
  rodapé; o formulário recebe foco e fica disponível antes de terminar a transição.
  Movimento reduzido zera a duração das transições do Studio.

## Arquivos e integridade

Novos componentes: `StudioLibrary.qml` e `StudioDialog.qml`; `StudioLabels.js`
centraliza rótulos e compatibilidade de apresentação e está incluído no package
data. Alterados: `LayoutStudio.qml`, `MetricSetup.qml`, `StudioProperties.qml`,
`ChecklistProperties.qml`, `LayoutComposition.qml`, `StudioCheckBox.qml` e
`Glyph.qml`. O adaptador `presentation/layout_studio.py` acrescenta pontos de
partida e resumo legível, nomeia blocos e recusa notas como campos de texto.

Markdown/JSON continuam canônicos; SQLite permanece descartável. IDs de fontes,
seleções manuais, registros, layouts imutáveis, conflitos e vigência permanecem nos
contratos anteriores. Nenhum código é executado a partir de arquivos de layout.
Abrir, trocar ponto de partida ou visualizar o rascunho não publica arquivos.
Templates e atribuições de períodos diferentes permanecem intactos. Campos de
rascunho não referenciados não são publicados. Remover/reordenar não apaga fatos.

## Verificação executada

| Verificação | Resultado |
| --- | --- |
| `.venv/bin/python -m pytest -q` | **250 passed em 92,44 s**; inclui regressões e nova jornada Qt |
| `.venv/bin/python -m ruff check .` | All checks passed |
| `.venv/bin/python -m ruff format --check .` | 94 files already formatted |
| `git diff --check` | Sem erros |
| `python -m habit_workspace --smoke-test`, offscreen/software | PASS; janela QML criada/encerrada |
| `tools/verify_phase5.py` | PASS, via suíte offscreen |
| `tools/verify_phase5_interaction.py` | PASS, direto e via suíte offscreen |
| `tools/verify_phase6.py` | PASS, direto offscreen/software |
| `tools/verify_phase6_refinements.py` | PASS, via suíte offscreen |
| `tools/verify_phase51_ux.py` | PASS offscreen/software e Linux/X11 nativo (`xcb`) |
| Avisos QML | Nenhum nas execuções aprovadas |

A suíte mantém testes de importações, duplicatas/conflitos, referências ausentes,
round-trip, ativação e unicidade temporal, consultas entre períodos, remoção visual,
registros e reconstrução de SQLite. Os novos testes verificam pontos de partida
reversíveis, isolamento dos padrões/períodos, resumo de reordenação, reutilização de
fontes sem criar definições e rejeição de nota como métrica de texto.

O script da Fase 5 recebeu apenas dois passos adicionais para abrir as opções
avançadas antes de operar limites e gráficos; as assertions anteriores permanecem.
Falhas intermediárias foram investigadas: o Drawer interceptava entrada fora do
Studio, um valor de ComboBox indefinido gerava aviso, o formulário aguardava a
animação para existir e um Loader inativo preservava altura. Foram corrigidas na
interface, sem enfraquecer assertions ou aumentar sleeps. A validação nova de
nota/metric foi demonstrada falhando antes da correção do adaptador.

## Jornada real e revisão das imagens

`tools/verify_phase51_ux.py` usa eventos reais de teclado/mouse em `QQuickWindow`,
o harness da Fase 6 e relógio fixo em 29/10/2026. Apenas cofres temporários e
preferências temporárias são usados. A jornada:

1. Abre um cofre descartável pela interface e navega para o dia.
2. Cria dois hábitos existentes e abre o Studio.
3. Escolhe começar vazio pelo diálogo de ponto de partida.
4. Adiciona uma lista de hábitos por botão; busca/inclui ambos.
5. Adiciona uma seção, reordena com arraste e depois com botão; verifica undo/redo.
6. Busca o bloco de duração; abre o formulário e valida nome obrigatório.
7. Preenche nome/unidade; provoca limites invertidos, confirma preservação dos
   inputs e corrige os limites antes de adicionar.
8. Verifica foco e renderiza 640×480, 1024×768, 1440×900 e 1920×1080 nos dois temas.
9. Pela biblioteca sobreposta em janela pequena, busca fonte existente, testa
   busca sem resultado e reutiliza a fonte sem duplicar definição; remove o bloco
   extra. Alterna para o canvas na janela pequena.
10. Ativa movimento reduzido, visualiza a prévia e confirma ausência de gravações.
11. Revisa e salva; retorna ao acompanhamento e registra um hábito e duração 30.
12. Encerra a aplicação, apaga apenas o índice do cofre de teste e abre outro
    processo; verifica layout, estados, valor e reconstrução do índice. Os bytes
    dos arquivos Markdown/JSON são comparados antes/depois da reabertura.

A Fase 6 original também verifica um campo inteiro, correção/limpeza, entrada
numérica inválida e captura semanal. A Fase 5 verifica arraste para canvas vazio,
entre colunas, drop inválido e fora do canvas, edição de seção, tabela e gráfico.

Capturas nativas foram inspecionadas pelo agente, incluindo formulário básico,
validação junto aos limites, biblioteca, estado vazio, seleção, painel estreito,
busca vazia, prévia, resumo e acompanhamento. Ajustes resultantes: alça desenhada
em vez de glifo ilegível, checkbox com quebra de texto, contraste dos diálogos no
tema escuro e remoção de espaço de Loader inativo. Evidências sintéticas:

- [Biblioteca e checklist](phase-5-ux-refinement/checklist-selected.png)
- [Formulário básico](phase-5-ux-refinement/field-basic.png)
- [Validação preservando os valores](phase-5-ux-refinement/field-validation.png)
- [Propriedades em 640×480](phase-5-ux-refinement/light-640.png)
- [Revisão antes de salvar](phase-5-ux-refinement/save-review.png)

As 19 capturas completas ficam em `/tmp/habit-workspace-phase51/{offscreen,xcb}/`.
Reprodução:

```sh
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase51_ux.py
QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase51_ux.py
```

## Limitações e aceite

- A revisão visual foi de imagens renderizadas reais pelo agente, com interação
  automatizada em Linux/X11. Não substitui revisão humana de usabilidade ou leitor
  de tela; Wayland, Windows, macOS e escala de fonte ampliada não foram validados.
- O padrão interno continua simples. O seletor reutiliza versões de layouts já
  existentes; não cria uma nova galeria de modelos prontos nem edita padrões globais.
- Sem editor de notas/tarefas/eventos, importação de mídia, captura de linhas de
  tabelas ou gráficos calculados. As limitações estão explícitas na biblioteca e
  nos blocos. Os controles de data/horário/duração existentes não ganharam pickers.
- Regras semânticas de campos publicados são consultáveis; sua edição continua fora
  deste refinamento. A captura de campos com frequência semanal continua indisponível.
- O seletor avançado de período de gráfico ainda usa referência canônica textual.
  Diagnósticos de documentos importados podem conter detalhes técnicos do parser.
- Leitura/captura síncronas e grandes cofres continuam com as limitações anteriores.
  A prévia é inerte, com exemplos; o acompanhamento usa o layout efetivo atual.
- CI remoto e publicação do PR não foram executados.

O aceite técnico da jornada de refinamento 5.1 foi atendido: checklist múltipla,
campo, organização, revisão, publicação e acompanhamento funcionam sem depender
de drag/drop ou conhecimento dos formatos. O editor está tecnicamente pronto para
servir de base à Fase 7, mantendo revisão humana de UX/acessibilidade pendente.
**A Fase 7 não foi iniciada.**

## Pull Request

Destino: `main`. Branch: `feat/phase-5-1-layout-studio-ux`.
[Título e descrição preparados](phase-5-ux-refinement-pr.md).
Sem commit, push, PR remoto ou merge. `AGENTS.md`, seção Workflow, item 5, exige
aprovação explícita para commits e push; a publicação fica para essa autorização.
Nenhum cofre privado, fixture persistente ou credencial integra a alteração.
