# Habit Workspace — Motor de layouts visuais (v4)

## 1. Decisão de produto
**Layout visual não é Markdown renderizado como texto corrido.** A interface Qt Quick/QML monta cards, listas, tabelas, inputs, imagens e gráficos a partir de uma descrição de layout declarativa. Markdown é um meio de armazenamento e edição externa de notas; layouts estruturados são JSON local no cofre. O usuário normal não deve precisar editar YAML/JSON/Markdown.

Princípios: desktop clean inspirado em Linear; drag-and-drop com snap em grade responsiva, estados de foco acessíveis, edição imediata; estilo separado do conteúdo. O editor se chama **Layout Studio**.

## 2. Quatro entidades distintas
1. **LayoutTemplate**: definição reutilizável, com ID imutável e versões (`Layouts/<slug>.v1.json`, `.v2.json`, etc.). Contém a árvore de componentes declarativos, posições, estilos e bindings.
2. **LayoutAssignment**: atribuição para um `PeriodRef` concreto (`year/2026`, `month/2026-10`, `week/2026-W44`, `day/2026-10-29`) ou fallback para um tipo de período. **Exatamente um layout efetivo por período em cada instante**. Históricos de versões são permitidos, não layouts simultâneos.
3. **FieldDefinition / DataSource**: define a semântica estável do valor coletado (UUID, tipo, unidade, tags, validação, política temporal, agregação). Um componente de checklist pode criar um novo campo ou fazer bind a hábito/tarefa existente.
4. **Observation**: valor real preenchido com `field_id` ou `habit_id`, `observed_date`/`observed_at`, `recorded_at`, `source_period_ref`, `source_block_id`, valor/status. O dado pertence ao documento canônico, **não** ao layout ou ao SQLite.

Um bloco de gráfico é **read-only e derivado** de Observations/check-ins; não cria fatos. Notas e imagens são conteúdo; só contam como métrica se existir uma definição estruturada explícita. Tabelas podem ter campos com tipos por coluna.

## 3. Resolução do layout — unicidade e precedência
- `resolve(period, instante)` procura primeiro uma atribuição específica vigente naquela data/hora.
- Se ausente, usa o template padrão configurado para o **tipo** (ano, mês, semana, dia).
- Senão usa layout básico interno.
- A tela exibe apenas **um layout composto** para o período. Não mesclar simultaneamente dois templates por herança.
- Ao editar um layout semanal, salvar **nova versão** e atribuí-la à semana escolhida por padrão. Alterar o template global requer uma ação distinta, com prévia do impacto.
- Histórico usa intervalos de vigência semiabertos `[effective_at, next_effective_at)`; não pode haver sobreposição. Toda alteração tem um único instante de ativação, determinado de forma explícita (padrão agora).
- Se há um layout ativo anterior e o usuário altera a semana, v1 -> v2; não existem dois layouts ativos, apenas uma trilha de auditoria. O aplicativo pode renderizar versões históricas quando solicitado, mas nunca considera ambas como atuais.

## 4. Biblioteca inicial do Layout Studio
- **Checklist**: lista de caixas; vincular a hábitos/tarefas existentes ou criar campo booleano novo. Tipo de saída controlado.
- **Lista**: coleção de itens textuais com possíveis tags e estados; itens estruturados quando houver campos.
- **Tabela**: colunas tipadas (texto, número, booleano, data, duração, avaliação); edição inline e validação.
- **Gráfico**: período ano/mês/semana; seleção manual por busca ou dinâmica por tags; configura tipo de agregação e fonte; não cria observação.
- **Nota**: editor rich-text básico armazenado em Markdown com delimitadores estáveis por block ID.
- **Imagem**: escolhe arquivo local; copia para Assets ou referencia caminho relativo controlado; importa mídia conforme manifesto, nunca faz fetch de URL sem autorização.
- **Campo simples**: checkbox, número, avaliação, data, horário, duração, seleção; exige definição de tipo/semântica.
- **Seção**: agrupador de layout sem saída própria.

v4 MVP: grade de 1–2 colunas, largura completa/meia, reorder, adicionar/remover/duplicar, painéis de propriedades, preview, undo/redo, salvar. **Sem canvas de coordenadas livres nem QML gerado dinamicamente a partir de JSON arbitrário**.

## 5. Importante: adicionar um bloco NÃO cria automaticamente hábito
O editor pergunta: (a) **vincular dado existente**, p.ex. hábito `Ler 20 minutos`; ou (b) **criar novo campo de acompanhamento**, p.ex. `Humor (1–5)`; ou (c) bloco apenas visual, como nota/imagem/gráfico. A fonte criada tem UUID e esquema próprios, persistidos separadamente do layout.

Remover um bloco oculta um modo de captura ou visualização. Não apaga dados antigos, nem a definição do hábito/campo, sem ação separada e explícita.

## 6. Efeito de uma alteração semanal na visão mensal
Exemplo:
- `week/2026-W44` tem layout v1 até `2026-10-29T10:00:00-03:00`.
- Às 10h de 29/10, o usuário altera o layout: adiciona campo booleano `Leitura realizada` e o associa à tag `#estudos`. O app cria ou vincula **DataSource com UUID estável** e salva layout v2.
- A partir da vigência, a nova entrada fica disponível. Registros preenchidos em 29/10 e 30/10 pertencem a seus dias de observação e entram no conjunto dos dados consultáveis do mês de outubro.
- O **resumo mensal dinâmico** consulta fontes elegíveis e reconhece imediatamente a nova origem; gráficos que filtram `#estudos` também a incluem quando configurados para aceitar o tipo de fonte.
- Um gráfico mensal de seleção **manual por IDs** continua exibindo sua seleção fixa. Não a modificar escondido: mostrar 'Nova fonte disponível' e permitir acrescentar.
- O aumento de entradas **não implica conclusão automática**: o resumo considera novos dados apenas à medida que são preenchidos. Se o campo cria ocorrências esperadas, o denominador dessas ocorrências começa na data de ativação, nunca nos dias anteriores.
- A página mensal mantém **seu único layout atribuído**. O que se atualiza são os **dados das consultas internas**, não a atribuição de um segundo layout mensal.
- Se o usuário volta a layout v1, os registros capturados pela v2 continuam no histórico, pesquisáveis e analisáveis.

**Não misturar alteração visual (mover card) com alteração semântica (criar campo).** Mover card não altera métricas. Criar campo altera a lista de possíveis observações somente da data de ativação em diante.

## 7. Métricas, escala temporal e semanas que cruzam meses
- Métrica diária com `observed_date`: agregado mensal seleciona observações de datas incluídas no mês civil.
- Hábito recorrente: progresso considera apenas ocorrências no escopo do hábito e após a ativação da definição, conforme regra de recorrência.
- Um campo **estritamente semanal** (ex.: 'nota da semana') não pode ser arbitrariamente dividido entre outubro e novembro. Atribuição ao mês deve ser **configurada**: pela data de conclusão, pelo início/fim da semana, ou exibição separada como 'semana que cruza períodos'. Não dividir valores por sete sem decisão explícita.
- Para booleanos: contar `done`, `missed`, `skipped`, `unrecorded` e `future` com semântica explícita; ausência de registro nunca vira `missed` automaticamente.
- Para números: soma, média, mínimo/máximo; para duração: soma de minutos/tempo; para rating: média; para texto e imagens: não criar gráfico numérico sem regra explícita.
- Tags são normalizadas; filtros `by_tags` resolvem fontes dinamicamente; filtros `manual` por UUID mantêm conjunto estável.

## 8. Modelo de estado do editor
`browse -> edit -> preview -> save new version -> resolve`. Alterações ainda não salvas não aparecem em páginas normais. Salvar deve ser operação atômica: persistir novo JSON, revisar atribuição no documento de período e reindexar; se falha parcial, oferecer recuperação idempotente. Como são múltiplos arquivos, manter um registro transacional local recuperável ou fazer versão/assignment em operações cuidadosamente ordenadas, sem prometer transação atômica entre vários arquivos.

Preview antes do save mostra o que muda: componentes adicionados/removidos, novos campos, vigência, possíveis relatórios afetados. Drag/drop deve funcionar também por teclado (mover para cima/baixo, adicionar pelo menu). `prefers-reduced-motion`/configuração local reduz animações.

## 9. Portabilidade e segurança
- JSON de layout é declarativo, **sem Python embutido, expressões arbitrárias executáveis ou QML arbitrário**.
- Importar um `Pages/Weeks/...md` isolado continua possível; se o layout JSON necessário não vier, mostrar conteúdo disponível em modo fallback e informar dependência faltante.
- Exportação `.hwpack` inclui por seleção explícita página + layout versionado + definições de dados + observações + mídia necessária ao período de análise; nunca incluir todo o cofre sem consentimento.
- Importações validam esquema, caminhos, UUID, versões, tamanho e dados desconhecidos; migrações não removem informação original.
- Cache SQLite (busca, fontes, rollups) é inteiramente reconstruível a partir dos documentos JSON/Markdown e mídia.

## 10. Critérios de aceitação obrigatórios
1. Semana `2026-W44` resolve só um layout atual; ao mudar às 10h do dia 29, layout anterior é histórico e novo é atual.
2. Uma página mensal mantém layout intacto e suas métricas dinâmicas passam a incluir observações elegíveis do novo campo semanal.
3. Seleção manual de gráfico não é alterada sem permissão; tag dinâmica agrega novo campo somente se tipo/consulta admitir a fonte.
4. Dias 26–28 não são contabilizados como falhas de campo ativado em 29/10.
5. Mover bloco não cria ou remove fatos; remover bloco não apaga observações.
6. Apagar `index.sqlite` e reconstruir produz o mesmo conjunto de fontes e agregações, inclusive com versões históricas.
7. Editar o JSON do layout externo (válido) permite reabrir com visual correto; JSON inválido mantém o arquivo e mostra erro, sem executar conteúdo.
8. Importar semana isolada avisa falta de layout; importar pacote com dependências recompõe layout e dados.
9. Semana que cruza meses não duplica nem reparte métricas semanais sem regra de atribuição.
