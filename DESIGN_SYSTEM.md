# Design System — Habit Workspace

## Direção visual
Minimalismo denso e sofisticado, inspirado nos **princípios** da interface do Linear: hierarquia sutil, navegação estável, espaço negativo controlado, foco no conteúdo e feedback imediato. Não copiar seus recursos gráficos, marca, layouts pixel a pixel nem ícones proprietários.

## Tokens iniciais (a revisar com testes de contraste)
### Dark (padrão)
- canvas `#101116`
- sidebar `#14161C`
- elevatedSurface `#1A1D25`
- hoverSurface `#242832`
- hairline `#30343D`
- textPrimary `#F2F3F5`
- textSecondary `#A7ADB8`
- textMuted `#808895`
- accent `#8C93F8`
- success `#58B48D`
- warning `#E1AD69`
- error `#DB7A80`

### Light
- canvas `#FAFAFB`
- sidebar `#F2F3F6`
- elevatedSurface `#FFFFFF`
- hairline `#E1E4E9`
- textPrimary `#171A21`
- textSecondary `#596271`
- accent `#565DD7`

Verificar contraste de texto, ícones e estados conforme WCAG; cores exatas são sugestões, não aprovação automática de acessibilidade.

## Tipografia
Fonte sans legível com pesos regulares e médios, de licença adequada à distribuição. Hierarquia pequena e consistente: títulos de página, rótulos, metadados e texto de conteúdo. Evitar título gigante em cada cartão.

## Espaçamento, raios e densidade
- escala: 4, 8, 12, 16, 24, 32 px lógicos
- radius: 6/10/14 px lógicos
- bordas finas; sombras discretas apenas quando houver sobreposição
- cards com conteúdos e ações claras, sem múltiplos níveis de bordas
- lista e checklist acessíveis ao mouse e teclado

## Estrutura desktop
- barra lateral esquerda retrátil, navegação temporal e pastas
- barra de ferramentas superior com breadcrumbs, busca e ações
- área central de páginas e blocos
- painel de propriedades à direita, contextual e opcional
- largura mínima definida por teste; em janelas menores recolher painéis antes de cortar conteúdo
- suporte a redimensionamento e escalas de fonte

## Motion
- hover/focus: 100–160 ms
- entrada/saída de overlays: 150–240 ms
- movimentos de reorganização: 180–280 ms
- animar preferencialmente opacity e transform, não grandes repaints
- confirmar ação com feedback imediato, não com animação decorativa
- respeitar reduce motion e fornecer alternativas sem movimento
- nunca bloquear interação esperando animação

## Estados e acessibilidade
- hover, focus (visível), pressed, selected, disabled
- loading, empty, success, error
- alvo clicável confortável; não usar só cor para indicar progresso
- labels acessíveis, contraste e navegação de teclado
- tab order previsível, atalhos visíveis quando presentes
- componentes com possibilidade de internacionalização

## Ativos gráficos
- biblioteca de ícones aberta e autorizada para distribuição (verificar licença).
- preferência por ícones simples, espessura consistente, sem excesso.
- screenshots de referência devem ser analisados como **direção visual**, não copiados.

## Critério de aprovação de tela
- Lê-se facilmente a hierarquia sem guia externo.
- O estado vazio explica o próximo passo.
- Uma ação primária evidente por contexto.
- Nenhum overflow horizontal inesperado.
- Diálogo, dropdown, tela e cartão seguem tokens consistentes.
- Animações são discretas e podem ser reduzidas.

## Aplicação em Python/Qt Quick
- Implementar tokens via constantes QML compartilhadas e componentes Qt Quick Controls personalizados quando necessário.
- Manter modelos Qt/QML desacoplados do domínio Python.
- Usar animações QML para opacidade, deslocamento e feedback de seleção, respeitando movimento reduzido.
- O painel de seleção de escopo mostra datas de início e fim de forma explícita; a busca/tag do gráfico mostra o conjunto resolvido de hábitos.

## UX de cofre e portabilidade (v3)
- Tela inicial oferece "Criar cofre" e "Abrir cofre existente" com escolha de pasta local.
- Menu visível: "Importar arquivo", "Exportar com dependências", "Backup local", "Reindexar".
- Importação informa prévia, documento reconhecido, conflitos, links ausentes e possíveis dados históricos não incluídos.
- A sidebar representa hierarquia temporal virtual, não caminho físico do arquivo. Uma ação secundária "Revelar arquivo" permite abrir o documento no gerenciador do SO.
- Blocos de gráfico que dependam de registros ausentes mostram aviso discreto e acionável em vez de resultado falsamente completo.

## Layout Studio (v4) — prioridade de experiência
- Três regiões: **Biblioteca de componentes** à esquerda, **canvas com grade** no centro, **Propriedades do componente/atribuição** à direita. Barra superior com breadcrumb, desfazer/refazer, prévia e salvar.
- Drag and drop de checklist, lista, tabela, gráfico, nota, imagem e inputs tipados. A área de soltar deve indicar posição e largura; snap de 1–2 colunas inicialmente, sem posicionamento por pixel arbitrário.
- Arrastar componentes já existentes para reorder; alternativa por teclado e menu de contexto. Movimento de reorder sutil, sem flashes ou efeitos chamativos.
- Propriedades: título, dados vinculados por UUID, escopo da fonte (se aplicável), estilo, largura, validação, filtros/consulta. Não expor JSON/YAML como UI normal.
- O modo **Preview** mostra o layout final com exemplos fictícios explicitamente rotulados, nunca escrevendo esses exemplos no vault.
- Salvar altera somente o período selecionado e cria versão nova. Mostrar 'Ativo desde [data/hora]' e explicar se campos/estatísticas podem ser afetados. Edição global de template é outra operação explícita.
- Layout padrão de resumo mensal inclui widget de fontes dinâmicas configuráveis, capaz de mostrar dados de novas fontes semanais. Manter visual consistente quando um card ganha novas séries.
- Páginas normais renderizam cards QML; notas são apresentadas no bloco de texto, não como documentos Markdown inteiros.
- Usar tokens globais do tema dark/light, hover/focus de alto contraste, animation opacity/transform por 150–280ms e opção para reduzir movimento.
- Estados de drop: válido, inválido, campo requerido, destino ocupado, divergência de tipo; salvar só quando o esquema do layout for validado.

## Refinamento do Layout Studio — Fase 5.1

- **Adicionar bloco** é a entrada principal. A biblioteca tem busca e categorias
  Acompanhamento, Conteúdo, Campos de dados e Visualizações, com limitações futuras
  explícitas. Nomes de tipos e valores de configuração são apresentados em pt-BR.
- Um bloco organiza a página; uma fonte é um hábito/campo reutilizável; um novo
  campo cria uma definição; um valor é registrado no acompanhamento. O formulário
  de campo reúne **Usar existente / Criar novo**, busca compatível e configuração.
  Não repetir nome/tags na biblioteca. Priorizar fontes existentes quando disponíveis.
- Nome, tipo e unidade aparecem primeiro. Tags, limites, agregação, frequência e
  atribuição semanal ficam em **Opções avançadas**. Erros ficam junto aos campos;
  mantêm o diálogo e os valores. A frequência semanal explica a captura indisponível.
- Diálogos do Studio usam a paleta do tema, ações persistentes no rodapé e altura
  proporcional ao conteúdo, limitada à janela. O formulário fica disponível antes
  da animação; o primeiro controle útil recebe foco. Cancelar é uma ação explícita.
- Cabeçalhos dos cards usam título, alça de seis pontos e **Editar**. Propriedades
  identificam o bloco e oferecem mover, largura, duplicar e remover. Drag/drop é
  opcional; mantém encaixe em uma/duas colunas e feedback de validade existente.
- A partir de 1100 px: biblioteca, página e propriedades lado a lado. Entre 900 e
  1099 px: biblioteca abre em painel sobreposto pelo botão Adicionar bloco. Abaixo
  de 900 px: alternar **Página / Propriedades**, com biblioteca sobreposta. Cada
  região tem rolagem própria. Nenhuma ação essencial depende de arrastar.
- Sem seleção, propriedades explicam como começar. **Ponto de partida** oferece
  layout atual, vazio, padrão da escala e versões existentes; a substituição do
  rascunho é explícita e reversível. O resumo antes de salvar nomeia o período,
  blocos alterados, fontes novas e vigência; confirma a preservação do histórico.
- Animações dos diálogos, biblioteca e controles respeitam `Theme.duration`, que
  vale zero com movimento reduzido. Foco visível e navegação Tab são obrigatórios.
