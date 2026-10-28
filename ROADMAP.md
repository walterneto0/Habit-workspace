# Habit Workspace v4 — Roadmap incremental (file-first)

Cada fase exige testes executados ou limitações explicitadas. O formato de arquivos é **pré-requisito**, não exportação adicionada ao final.

## Fase 0 — Ambiente e protótipo mínimo
Python + PySide6/QML, pyproject.toml, pytest, Ruff, .venv, janela mínima. Teste de execução offline e licenças.

## Fase 1 — Contrato file-first e cofre (PRIORIDADE)
Escolher criar/abrir pasta-cofre; implementar leitor/escritor de Markdown+YAML, versionamento, documentos tipados e UUIDs estáveis; scanner, índice SQLite regenerável, reconstrução, escrita atômica, watcher e erros seguros. Inicialmente apenas notas/páginas e um tipo de item em testes.
Aceite: copiar arquivo de outro PC (simulado por outro diretório), importá-lo e visualizá-lo; apagar índice e recriar; editar externamente e atualizar; arquivo corrompido não é perdido; UUID duplicado não sobrescreve.

## Fase 2 — Identidade visual e navegação
Shell QML com sidebar virtual Year/Month/Week/Day, notas e propriedades; light/dark, tokens, teclado, hover e animações discretas; ações abrir/criar/importar cofre.
Aceite: UI resize, estados de cofre vazio, importações e navegação sem path rígido.

## Fase 3 — Domínio temporal e entidades canônicas
PeriodRef, TemporalScope e recorrência; arquivos `.md` de hábitos e outros itens; origem e validade independentes; referência por UUID, testes de semana ISO e mudanças de escopo.
Aceite: um hábito aparece nas visões pertinentes sem duplicar arquivo; renomear/mover arquivo não quebra referência.

Implementada e verificada: [relatório da Fase 3](docs/verification/phase-3.md).
Entidade de hábito e notas/páginas existentes preservadas; tarefas, objetivos e
eventos continuam na Fase 7.

## Fase 4 — Contrato de layouts e campos (testes de domínio antes de UI)
Layouts JSON versionados, assignment único por período/instante, template de tipo como fallback, histórico de ativação, campos tipados estáveis, observações canônicas datadas; resolver e testes de colisão de vigência.
Aceite: criar campo em semana 44 com ativação em 29/10, não afetar 26–28; duas versões históricas, só uma ativa no mesmo instante; remoção de bloco não apaga dados.

Implementada e verificada: [relatório da Fase 4](docs/verification/phase-4.md).

## Fase 5 — Layout Studio visual e renderizador
QML com biblioteca de checklist, lista, tabela, gráfico placeholder, nota, imagem e campo tipado; drag-drop, reordenar, propriedades, preview, undo/redo, snap 1–2 colunas, teclado e redução de movimento. Páginas renderizadas como interface composta, NÃO Markdown cru.
Aceite: criar e editar layout semanal na UI, salvar nova versão em arquivo JSON, reabrir e renderizar mesmo visual; uma atribuição efetiva; exportar página sem layout avisa dependência ausente.

Implementação parcial: [relatório da Fase 5](docs/verification/phase-5.md).
Fluxo integrado disponível; aceites de propriedades, interação e revisão nativa
ainda pendentes. A fase não está concluída.

## Fase 6 — Hábitos e captura estruturada
Check-ins vinculados a hábito por UUID e observações vinculadas a Fields por UUID, arquivo diário canônico; tags, busca e escopo/recorrência.
Aceite: checklist vinculada a hábito gera check-in correto, campo numérico em layout gera observação tipada, alteração visual não altera valor e observação permanece após bloco removido.

Implementada e verificada por testes automatizados: [relatório da Fase 6](docs/verification/phase-6.md).
Modo de acompanhamento, formulário de hábitos e captura tipada disponíveis; revisão
visual/acessibilidade humana pendente; aguarda revisão do responsável.

## Fase 7 — Agenda, notas, imagens e planejamento
Tarefas, objetivos, avaliações, eventos e notas; bloco de texto Markdown com marcador por ID, imagens em Assets; agenda referenciando dados canônicos.
Aceite: exportar/importar itens com dependências, preservar notas/imagens e abrir em outro cofre.

## Fase 8 — Gráficos e rollups entre escalas
Blocos de gráfico por ano/mês/semana, seleção manual ou tags dinâmicas, agregadores tipados e estado de dados ausentes; widget mensal padrão detecta fontes novas por tag/consulta.
Aceite: alterar layout semanal em 29/10, registrar novos inputs 29–30/10, ver rollup atualizado em outubro sem trocar layout mensal; não contar 26–28/10 como falha; manual não adiciona fonte; reindexação igual; métricas semanais atravessando mês exigem regra explícita.

## Fase 9 — Pacotes, backup, estabilização e distribuição
`.hwpack` com página, layout JSON, definições de campo, registros e Assets selecionados; backup local, testes de recovery, packaging e revisão visual.
Aceite: outro computador abre o pacote, reconstitui interface e métricas incluídas, offline e sem SQLite original.

## Fora do MVP
Cloud, login, sync automático, criptografia própria de cofre, mobile, plataforma web, plugins arbitrários, colaboração e canvas de posicionamento livre.
