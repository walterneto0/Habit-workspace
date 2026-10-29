# Fase 6 — refinamentos de checklist e navegação

Base: `main` / `origin/main` em `518db92056a5ed75c23f8ffeadc35b09e46b5d3a`,
confirmada após `git fetch origin main`. A árvore estava limpa. Trabalho na branch
`feat/phase-6-refinements`. O baseline passou em **234 testes**. Nenhuma Fase 7,
dependência, reorganização física do cofre ou mudança de esquema foi introduzida.

## Mudanças entregues

Uma checklist aceita vários hábitos canônicos. **Seleção manual** oferece busca
pelo nome, inclusão sem duplicatas, remoção e botões de reordenação acessíveis ao
teclado. A ordem é persistida como UUIDs; renomear o hábito ou mover o arquivo não
altera o vínculo. Campos booleanos existentes continuam disponíveis por opção
explícita; criar uma métrica continua separado de vincular hábitos.

**Tags dinâmicas** aceita tags existentes ou nomes separados por vírgulas. As tags
são combinadas por **OU**: basta uma correspondência. Novos hábitos compatíveis
entram automaticamente na consulta. **Contextual · data selecionada** usa escopo e
recorrência no dia de acompanhamento dentro do período aberto. Dias inelegíveis
não viram pendências; registros históricos fora da programação permanecem visíveis,
identificados e sem edição, conforme o contrato anterior.

Cada hábito mantém seus próprios controles **Concluído**, **Dispensado**,
**Não cumprido** e **Limpar registro**. A data aparece no bloco e no cabeçalho.
Semanas e meses continuam capturando uma ocorrência diária explicitamente escolhida,
sem conclusão única do período. Duas checklists do mesmo hábito leem/escrevem o
mesmo registro diário. Ausência de registro nunca vira falha.

**Hábitos** tem coleção própria, busca por nome/tags, criação e edição pelo serviço
existente. A prévia apresenta nome, tags, escopo, recorrência, status da última data
de acompanhamento e descrição Markdown opcional. **Documentos e notas** lista
notas, páginas livres e definições de métricas; páginas temporais ficam na navegação
temporal existente. O inventário e as pendências continuam completos internamente.
A lista deixa de usar filenames UUID como identificação principal; o caminho
continua disponível nas propriedades. Importações abrem a coleção do tipo importado.

A prévia de notas continua usando o texto inerte existente. Outros documentos
estruturados têm fallback por tipo/período e preservam a apresentação dos registros.
Nenhum arquivo canônico é alterado por navegar ou abrir uma prévia. No painel
"Hábitos deste período", **Ver definições** expande os metadados; por padrão, ficam
recolhidos para dar espaço às checklists.

## Compatibilidade e persistência

O esquema v4 já tem `ChecklistConfig.selection` / `SourceSelection`. Não foi
necessária migração. Os formatos e semântica estão documentados em
[FILE_FORMAT.md](../../FILE_FORMAT.md) e [LAYOUT_ENGINE.md](../../LAYOUT_ENGINE.md).

- `manual`: `source_ids` únicos e ordenados, `value_types: ["habit"]` para hábitos.
- `by_tags`: tags normalizadas, sem UUIDs fixos, correspondência OU.
- `all`: seleção contextual, sem IDs ou tags; acompanha a data de captura.
- Bindings antigos de um hábito ou campo booleano continuam legíveis sem regravação.
  Ao acrescentar fontes, o Studio converte explicitamente aquele binding para uma
  seleção em uma nova revisão do layout, preservando o UUID original.
- Desfazer/refazer e publicação usam o histórico existente. Remover seleção ou bloco
  preserva definições, observações e check-ins. Versões antigas não são substituídas.
- Fonte incompatível em uma seleção importada aparece sem edição; não habilita
  captura numérica indevida numa checklist.
- `CaptureService` continua gravando exclusivamente no `day_page` canônico por
  hábito/data, com detecção de revisão obsoleta, escrita atômica e IDs estáveis.
  Não há alteração do formato de hábitos, logs, observações ou SQLite.

## Verificação executada

| Verificação | Resultado |
| --- | --- |
| `.venv/bin/pytest -q` | **245 passed em 62,83 s** |
| `.venv/bin/ruff check .` | **All checks passed!** |
| `.venv/bin/ruff format --check .` | **91 files already formatted** |
| `git diff --check` | Sem erros |
| `python -m habit_workspace --smoke-test`, offscreen/software | Janela QML criada e encerrada |
| `tools/verify_phase1.py` | PASS: importação, UUID após rename, reconstrução do índice |
| `tools/verify_phase3.py` | PASS: temporalidade, referências, importação parcial, histórico |
| `tools/verify_phase2.py` | PASS, executado pela suíte em subprocesso offscreen |
| `tools/verify_phase5.py` | PASS, executado pela suíte em subprocesso offscreen |
| `tools/verify_phase5_interaction.py` | PASS, executado pela suíte em subprocesso offscreen |
| `tools/verify_phase6.py` | PASS offscreen/software, nenhum aviso QML ou stderr |
| `tools/verify_phase6_refinements.py` | PASS offscreen/software e **X11 nativo (`xcb`)**, nenhum aviso QML |

Os testes novos usam cofres temporários e a data determinística **2026-10-29**.
`tests/test_phase6_refinements.py` cobre múltiplos hábitos, ordem manual,
deduplicação, round-trip, binding antigo, UUID após mover arquivo, referências
ausentes, tags OU e atualização dinâmica, escopo/recorrência, datas futuras,
registros independentes, correção/limpeza, duas checklists compartilhando registros,
reinício, exclusão/reconstrução do SQLite, prévias por tipo, descrição, filtros,
criação/edição na coleção e datas explícitas em semanas/meses. Também verifica
compatibilidade de fontes booleanas e recusa visual de fonte incompatível.

Dois testes anteriores foram atualizados para a separação intencional da navegação:
a busca de hábitos usa a coleção **Hábitos**; hábitos pertinentes a períodos continuam
no modelo de acompanhamento, enquanto a lista documental temporal contém páginas.
As verificações de não duplicar arquivos e não fazer I/O ao navegar foram mantidas.
Toda a suíte anterior de importação, conflitos, referências, temporalidade de layouts,
agregados de fontes e round-trip continua executada.

## Fluxo na aplicação e inspeção visual

O novo script usa cliques e eventos reais de teclado em `QQuickWindow`, sem chamar
slots para substituir as interações principais. Ele:

1. Abre um cofre temporário pela interface e cria três hábitos pelo formulário.
2. Adiciona uma checklist ao layout diário; busca e inclui os três hábitos.
3. Reordena pelo teclado/clique, configura tags e modo contextual, e usa desfazer
   para restaurar exatamente a seleção manual antes de publicar.
4. Registra um hábito como concluído e outro dispensado; confere os dois registros
   no Markdown diário e o terceiro hábito sem registro.
5. Navega para mês e retorna ao dia; verifica os estados.
6. Abre **Hábitos**, inspeciona as propriedades e edita o nome pelo formulário.
7. Abre uma nota comum e confere a prévia existente.
8. Redimensiona para 640×480 e 1024×768, mantendo acesso por foco/rolagem.
9. Encerra a aplicação, apaga apenas o SQLite do cofre de teste e abre uma nova
   aplicação em outro processo; verifica reconstrução, layout e estados.

Execução reproduzível:

```sh
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase6_refinements.py
QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase6_refinements.py
```

Capturas nativas foram inspecionadas pelo agente. Ajustes resultantes: definições
recolhidas para reduzir repetição, nomes legíveis em vez de UUIDs na composição,
seleção e foco consistentes, e data explícita na checklist. Evidências sintéticas:

- [Seleção manual](phase-6-refinements/manual-selection.png)
- [Tags dinâmicas](phase-6-refinements/dynamic-tags.png)
- [Seleção contextual](phase-6-refinements/contextual-selection.png)
- [Checklist com registros independentes](phase-6-refinements/checklist-saved.png)
- [Detalhes do hábito](phase-6-refinements/habit-detail.png)
- [Prévia de nota comum](phase-6-refinements/note-preview.png)

As nove capturas de cada execução, incluindo redimensionamento e reinício, ficam em
`/tmp/habit-workspace-phase6-refinements/{offscreen,xcb}/`. A verificação original da
Fase 6 também exercita captura numérica, temas claro/escuro e datas futuras.

## Limitações restantes

- Verificação nativa automatizada em Linux/X11 e inspeção das imagens pelo agente;
  não houve revisão humana de acessibilidade/leitor de tela, nem teste em Wayland,
  Windows ou macOS.
- Leitura/captura síncronas existentes; desempenho de cofres grandes não foi medido.
- O Studio mantém prévias inertes. A captura usa o layout ativo agora, mesmo ao
  selecionar um dia passado, preservando as regras de ativação existentes.
- Registros fora da programação são preservados e apresentados sem edição;
  limpar/corrigir essas exceções exige restaurar a elegibilidade no escopo/recorrência.
- Edição de notas, gráficos avançados, campos semanais capturáveis e demais fases
  posteriores continuam fora deste refinamento.
- CI remoto não observado. `gh auth status` informou ausência de autenticação;
  nenhum PR, commit, push ou merge foi realizado.

## Preparação do Pull Request

Título sugerido: **Refine Phase 6 multi-habit checklists and document navigation**.
Após revisão, estes comandos criam o commit, publicam a branch e abrem um PR draft:

```sh
git add FILE_FORMAT.md LAYOUT_ENGINE.md \
  src/habit_workspace/application/capture.py src/habit_workspace/presentation \
  tests/test_desktop_controller.py tests/test_tracking.py \
  tests/test_phase6_refinements.py tests/test_qml_startup.py \
  tools/verify_phase6_refinements.py docs/verification/phase-6-refinements.md \
  docs/verification/phase-6-refinements
git commit -m "Refine Phase 6 multi-habit checklists and document navigation"
git push -u origin feat/phase-6-refinements
gh auth login
gh pr create --draft --base main --head feat/phase-6-refinements \
  --title "Refine Phase 6 multi-habit checklists and document navigation" \
  --body-file /tmp/phase6-refinements-pr.md
```

O arquivo de descrição preparado em `/tmp/phase6-refinements-pr.md` contém problema,
comportamento final e validação. Esses comandos são entregues para execução pelo
responsável; não foram executados pelo agente.
