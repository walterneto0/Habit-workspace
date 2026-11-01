# Habit Workspace — Especificação de Produto v4 (rascunho de requisitos)

## Visão
Aplicativo desktop file-first e local-first, feito em Python, para organizar objetivos, tarefas, hábitos, eventos, avaliações e notas por páginas modulares. Referência estética: princípios de navegação, densidade, tipografia e animação do Linear, sem copiar sua marca. No futuro, UX mobile específica, sem prometer que a interface desktop servirá sem mudanças.

## Decisões confirmadas pelo proprietário do projeto
1. Stack principal: Python.
2. Manter o conceito visual da interface desktop de três regiões: sidebar temporal, conteúdo central e propriedades contextuais opcionais.
3. Ano/mês/semana/dia são VISUALIZAÇÕES, não proprietários físicos dos dados.
4. Ao criar um dado numa página temporal, o escopo temporal inicial é o período daquela página; é alterável pelo usuário.
5. Um gráfico escolhe granularidade (ano/mês/semana), período concreto e hábitos por busca nominal OU por tags. Definições de gráficos são persistidas.
6. O cofre de arquivos do usuário é a fonte da verdade: Markdown + metadados YAML/JSON, sem conta ou nuvem obrigatórias. SQLite é índice local descartável e regenerável.
7. Importar páginas e outros itens de outros computadores não deve exigir conta. Itens referenciados ausentes devem ser reconhecidos e explicados, nunca recriados silenciosamente.
8. A interface **não** exibe Markdown cru como documento corrido: as páginas são renderizadas por um motor de layouts visuais.
9. O Layout Studio permite montar layouts drag-and-drop com checklist, lista, tabela, gráfico, nota, imagem e inputs tipados.
10. Cada período concreto possui **um único layout efetivo**. Alterações produzem versões com início de vigência; dados históricos sobrevivem.
11. Um input novo introduz uma fonte de dados com ID estável e pode alimentar resumos mensais dinâmicos a partir da ativação, sem mudar o layout mensal.

## Vocabulário sem ambiguidade
- `PeriodRef`: referência visual com tipo e datas. Ex.: `year/2026`, `month/2026-10`, `week/2026-W44`, `day/2026-10-27`. Não é uma pasta física.
- `Page`: composição visual de blocos, com vínculo opcional a `PeriodRef`, e personalizações persistidas.
- `Block`: componente visual configurável (lista, checklist, nota, agenda, metas, avaliação, gráfico etc.).
- `Item`: registro canônico de domínio (Habit/Task/Goal/Event/Review/Note); não duplicar ao mostrá-lo em páginas distintas.
- `TemporalScope`: intervalo de validade do item. Determina quais datas são elegíveis; não é seu local de armazenamento.
- `Recurrence`: dentro do escopo, decide QUANDO um hábito gera ocorrências esperadas. Não é sinônimo de escopo.
- `OriginPage`: referência opcional para histórico e navegação, não restringe futuras visualizações.
- `Tag`: rótulo N:N independente de período, disponível para busca e filtros.
- `ChartDefinition`: configuração persistida do gráfico; não uma cópia dos logs.
- `LayoutTemplate`: JSON declarativo versionado de componentes e posições.
- `LayoutAssignment`: atribuição exclusiva por período concreto e vigência; template de tipo atua apenas como fallback.
- `DataSource / FieldDefinition`: campo tipado e identificável, independente da posição do componente.
- `Observation`: valor preenchido e datado, independente do layout que o capturou.

## Regra de escopo na criação
Uma criação em página vinculada a período sugere por padrão o período inteiro:
- ano/2026 => 2026-01-01 a 2026-12-31;
- mês/2026-10 => 2026-10-01 a 2026-10-31;
- semana/2026-W44 => 2026-10-26 a 2026-11-01;
- dia/2026-10-27 => apenas 2026-10-27.
O usuário pode, antes ou depois de salvar, escolher outro período fechado, início sem fim previsto ou datas customizadas. UI SEMPRE mostra o período resolvido por extenso. A página original não é um limite oculto.

Exemplo: hábito criado na terça 2026-10-27; escopo inicial só nesse dia. Alterado pelo usuário para 2026-10-27 a 2026-12-31, recorrência seg–sex: tem ocorrências somente nos dias úteis dentro do intervalo escolhido, e pode ser exibido em visões relevantes.

## Apresentação dos dados em páginas
- O domínio mantém cada registro uma vez; páginas e blocos exibem consultas filtradas por período/tags/seleções.
- Uma página anual não faz com que seus registros preencham automaticamente toda página diária: blocos com filtros e visualizações decidem o que aparece.
- Bloco "Hábitos ativos" consulta hábitos cujo escopo intersecta o período visível, e mostra ocorrências programadas nele.
- Nota livre ou avaliação vinculada a uma página só aparece em outros lugares quando um bloco apropriado a consultar ou referenciar; uma nota anual não vira 365 notas diárias.
- Remover uma página ou bloco nunca apaga dados de domínio sem confirmação separada e explícita.
- Editar um item atualiza todas as visualizações que o referenciam.

## Regras específicas por tipo
### Hábito
`name`, `tags`, `valid_from`, `valid_until?`, `schedule`, `archived_at?`, `log` por ocorrência. Na versão inicial: recorrência diária ou dias da semana. Uma meta de "N vezes/semana sem dias fixos" NÃO cabe no modelo diário simples: deixar para fase posterior, exigindo regra específica de geração e contagem.

Estados de uma ocorrência: `done`, `missed` (falha declarada), `skipped` (dispensa voluntária), `unrecorded` (dia passado sem confirmação), `pending` (hoje ainda aberto), `future`, `not_scheduled`. Não converter ausência de registro automaticamente em `missed`. Jamais criar ocorrências fora do escopo.

### TODO
Escopo define janela contextual da tarefa; `due_date` opcional indica prazo específico. Tarefa não recebe checkbox diário apenas por estar num escopo anual. Conclusão é uma ação na tarefa canônica. Subtarefas podem ficar para futura versão.

### Objetivo
Escopo identifica o período de referência da meta; progresso pode ser manual inicialmente, com métricas vinculadas em fase posterior.

### Evento
O evento possui `starts_at`/`ends_at`, fuso e opção all-day; também pode ter origem e tags. Um evento criado na página de outubro NÃO significa que dura todo outubro: escolher data e hora concretas é obrigatório. Recorrência de eventos: futuro.

### Nota e avaliação
Podem ser associadas a uma página/período como contexto, sem gerar ocorrências. Suportar texto livre e indicadores opcionais na avaliação.

## Páginas e templates
- Estrutura visual: Ano → Mês → Semana → Dia; NÃO representar isso como chave estrangeira rígida entre períodos.
- Semanas ISO podem cruzar meses e anos. Uma semana tem identidade única, mesmo se aparecer na navegação de dois meses.
- Não pré-gerar todos os dias/meses como linhas; materializar personalização de página quando necessário.
- Templates iniciais: Ano (objetivos, avaliação, overview), Mês (objetivos, agenda, gráfico), Semana (prioridades, TODO, agenda, avaliação), Dia (hábitos, TODO, eventos, notas, avaliação).
- Usuário pode começar de página vazia, editar, duplicar template, adicionar/remover/ordenar/configurar blocos no Layout Studio. Grid de 1–2 colunas inicialmente; canvas arbitrário livre e plugins externos ficam fora do MVP.
- Um período tem um único layout ativo por instante; edição cria nova versão com vigência, e mantém histórico.
- Layout e dados são independentes: os componentes vinculam por UUID a hábitos, tarefas ou campos tipados; não há valor canônico gravado unicamente em layout.
- Nota Markdown é renderizada por componente visual, não como página de texto sem formatação. Ver `LAYOUT_ENGINE.md`.

## Seleção de dados no gráfico
Configurações persistidas:
- Granularidade selecionada: year, month ou ISO-week.
- Período concreto: ex. outubro/2026, semana 44/2026 ou ano/2026; pode acompanhar página atual se opção explícita `follow_page_period=true`.
- Seleção dos hábitos em DOIS modos explícitos:
  1. `manual`: busca textual é usada para LOCALIZAR hábitos e salvar uma lista fixa de IDs;
  2. `by_tags`: salvar IDs das tags e resolver dinamicamente os hábitos com as tags ao atualizar o gráfico.
- Dentro de `by_tags`, v1 usa correspondência a QUALQUER tag selecionada (OR), explicada na interface. Combinar modos e interseções avançadas fica para depois.
- Métrica: contagem por estado; opcional taxa de conclusão SOBRE resultados confirmados = done/(done+missed), separando quantos registros ficaram `unrecorded`, `skipped` e `pending`. Caso denominador=0, mostrar "sem dados suficientes", não 0%.
- Agrupamento inicial para série temporal: ano→meses, mês→dias, semana→dias; opção de visualização por total de estados.
- Remover gráfico não remove hábitos ou logs.
- Mudanças de tags e escopo recalculam a fonte; o gráfico não guarda agregações como verdade principal.

## UX — formulários essenciais
### Criar hábito
Nome; tags opcionais; período de validade (preenchido pelo contexto); recorrência (diário/dias da semana); prévia de próximas ocorrências; salvar. Após salvar, usuário pode ajustar escopo com confirmação se alterações afetarem logs existentes.

### Adicionar gráfico
Tipo visual (barras inicial); período analisado (ano/mês/semana + qual); modo de seleção (busca manual ou tags); multisseleção; legenda de estados; prévia e salvar. Em modo `by_tags`, indicar atualização dinâmica da seleção.

## Agenda
Agenda não duplica dados: combina eventos por data, tarefas com `due_date` e ocorrências de hábitos, claramente identificadas por tipo. Clicar em qualquer entrada abre o registro canônico.

## Questões de produto que ainda exigem decisão
- Se o usuário alterar um escopo e deixar logs existentes fora dele, a primeira versão deve PRESERVAR logs, alertar e excluí-los da agregação atual; oferecer limpeza explícita somente em função posterior.
- Páginas podem ser vistas por período canônico ou um conjunto de páginas customizadas. MVP inclui ambas, mas sem motor genérico de consultas livre.
- Ajustes em semanas cruzando meses exigem apresentação clara de dias de outro mês.
- Habit N vezes por semana, gestão de fusos entre dispositivos e sync são posteriores.

## Princípio file-first e portabilidade
- Na primeira execução o usuário escolhe **Criar cofre** ou **Abrir cofre existente**, selecionando uma pasta local livremente.
- O app cria documentos reconhecíveis com contrato de formato aberto e versionado (`FILE_FORMAT.md`), preservando notas Markdown editáveis externamente.
- Páginas, layouts de blocos, gráficos, hábitos, tarefas, objetivos, eventos, notas e registros diários devem persistir em documentos do cofre; nenhum desses dados pode existir apenas no SQLite.
- O índice SQLite serve para busca, cruzamento de referências e agregações; apagar o índice e reconstruí-lo não pode causar perda de conteúdo nem mudança de resultados.
- Importação de um `.md` individual: detecta o documento, apresenta prévia e resolve identidade/conflitos; notas e logs internos permanecem legíveis. Referências externas ausentes são apresentadas como pendências, sem inventar hábitos nem estatísticas.
- Exportação de **pacote com dependências** inclui, mediante seleção explícita do usuário, os documentos referenciados e dados históricos necessários; não exportar outros dados privados silenciosamente.
- Transferir um cofre inteiro funciona por cópia da pasta, sem reconfiguração obrigatória de caminhos absolutos.
- Arquivos podem ser renomeados/movidos no cofre sem perder identidade: IDs estáveis no conteúdo são canônicos; caminho é apresentação, não identidade.
- Arquivos comuns sem metadados do aplicativo podem ser importados como notas livres; não inferir registros de hábito de texto arbitrário sem confirmação.
- Editar um arquivo Markdown externamente deve refletir-se na UI após detecção de alterações/atualização; erros de parsing não podem sobrescrever o conteúdo original.

## Privacidade e ausência de contas
- Aplicativo operável inteiramente offline, sem cadastro, serviços remotos, telemetria ou login.
- Usuário controla destino, cópias e exclusão de seus arquivos. Backup manual e proteção local são prioridades.
- Sem conta NÃO é sinônimo de anonimato nem de criptografia: arquivos podem conter informações identificáveis e ser lidos por processos/usuários com acesso ao dispositivo.
- Aplicativo não deve prometer segurança contra malware, roubo de dispositivo ou cópias externas. Consulte `PRIVACY.md`.

## MVP
Desktop offline funcional, com páginas temporais, blocos configuráveis, criação com escopo editável, hábitos recorrentes e logs, tags e busca, TODO/eventos/notas/objetivos/avaliação simples, agenda, gráficos semanais/mensais/anuais configuráveis, temas claro/escuro, backup/restauração e testes. Sem contas, sync, IA incorporada, marketplace ou integração externa.

## Adendo v4 — dinâmicas entre escalas
- Os widgets mensais consultam registros por data e tags, independentemente da origem semanal/diária. Um novo campo em layout semanal passa a ser elegível a partir de sua ativação e, depois de preenchido, entra nos resumos mensais dinâmicos.
- Gráficos de seleção manual não absorvem automaticamente novas fontes; filtros de tags podem absorvê-las, respeitando tipos aceitos.
- Uma semana entre meses pode ter registros diários em cada mês; métricas semanais indivisíveis exigem regra de atribuição.
- Excluir componente, trocar versão ou transferir página nunca apaga registros canônicos automaticamente.
- Leia `LAYOUT_ENGINE.md` antes de modelar Layout Studio, campos e analytics.

## Adendo v4 — propriedade do período e cadência explícita

Decisão confirmada: o período de propriedade do item (`home_period_ref`), seu
`TemporalScope` e a frequência de acompanhamento (`tracking`) são distintos.
Escopo anual **não** implica visibilidade mensal/semanal/diária. Novos objetivos
pertencem por padrão somente ao período escolhido; se a pessoa desejar
acompanhar mensalmente, semanalmente ou diariamente, precisa escolher isso
explicitamente. A página menor recebe uma **referência de acompanhamento** ao
mesmo objetivo, nunca outro objetivo canônico.

Tarefas são ações canônicas de conclusão única, sem ocorrências diárias
fabricadas; prazo/pendência e busca global são projeções distintas. Hábitos
conservam a recorrência e check-ins existentes, sem mudança silenciosa.
Notas e avaliações só aparecem no período associado ou onde deliberadamente
vinculadas. A ausência de um acompanhamento não é fracasso declarado.

**Implementação 7B:** objetivos têm propriedade e cadência explícitas;
acompanhamentos guardam comentários por período sem inferir progresso. Notas,
regiões locais e avaliações exatas têm edição assíncrona com preservação de
rascunhos. Avaliações aceitam nota manual opcional de 1 a 5, sem gerar observações
diárias. Imagens locais validadas são importadas para Assets e exibidas offline.
Veja FILE_FORMAT.md e docs/verification/phase-7b-final.md para contratos e limites.
