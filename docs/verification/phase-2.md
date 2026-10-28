# Fase 2 — Interface desktop e navegação

Implementação em Python/PySide6 e Qt Quick, sem mudanças nos formatos canônicos
ou nos serviços da Fase 1. Nenhum commit foi criado. O trabalho para nesta fase.

## Entregue

- Sidebar retrátil com cofre atual, visão geral, calendário, estatísticas,
  documentos/notas, anos, meses, semanas, dias e configurações.
- Breadcrumbs, títulos, ações contextuais, busca por título/tag/UUID/caminho,
  cards, estados vazios, mensagens e painel de propriedades.
- Navegação virtual, calendário de segunda a domingo, números de semana ISO,
  anterior/próximo, hoje e salto por data. Navegar não cria documentos.
- Criar, abrir e trocar cofres, lista de cinco caminhos recentes, importação
  individual com prévia/cancelamento/confirmação e reconstrução do índice.
- Importação explícita de Markdown comum como nota; conflitos não sobrescrevem
  dados. Referências ausentes, ambíguas ou de tipo incompatível são divulgadas.
- Prévia de texto inerte e snapshots já armazenados, sem imagens remotas ou
  execução de conteúdo. A prévia não é o futuro renderizador de layouts.
- Tema claro/escuro, tokens compartilhados, ícones geométricos originais,
  estados de foco/hover/seleção, transições e preferência de movimento reduzido.
- Layout adaptável de 640×480 a 1440×960 nos cenários verificados. A sidebar
  fica compacta abaixo de 1000 px; propriedades usam sobreposição abaixo de
  1280 px. Conteúdo e diálogos têm rolagem; foco por teclado revela controles.
- Preferências locais via QSettings. Domínio e aplicação continuam sem Qt;
  `presentation/navigation.py` implementa somente rotas de apresentação.

## Verificações executadas

| Verificação | Resultado |
| --- | --- |
| Suíte completa `pytest -q` | 67 testes aprovados |
| Ruff check e format --check | Aprovados |
| qmllint com `-W 0` e manifesto qmldir | Aprovado, sem diagnósticos |
| `git diff --check` | Aprovado |
| `tools/verify_phase1.py` em namespace sem rede | PASS |
| `tools/verify_phase2.py`, também sem rede | PASS, zero avisos QML, 17 capturas |
| Build wheel sem dependências/downloads | Aprovado |
| Instalação do wheel em pasta temporária e smoke test | Aprovados; importação confirmada a partir do wheel |

O wheel reutiliza as dependências da `.venv`; isso não valida instalação em uma
máquina limpa. Nenhuma dependência ou fonte nova foi instalada.

A verificação Qt usa mouse, Ctrl+B/O/I/K, Alt+Right, Space, Esc e foco com rolagem.
Cria um cofre pelo diálogo, navega pelo calendário, confirma uma importação,
abre propriedades, busca documentos, troca cofres, renomeia arquivos, apaga e
reconstrói SQLite e verifica preservação de arquivos inválidos. As fixtures são
rotuladas como dados de verificação e ficam em diretórios temporários.

Capturas em `/tmp/habit-workspace-phase2/` foram inspecionadas, incluindo ambos
os temas, calendário, estados vazios, diálogos e propriedades em janela pequena.
São imagens reais do Qt Quick com renderização de software/offscreen.
As combinações básicas de texto dos tokens têm contraste mínimo calculado de
6,15:1 no escuro e 4,59:1 no claro (texto primário/secundário/discreto nos fundos
principais, destaque selecionado e botão primário). Isso não é uma auditoria
completa de acessibilidade, estados desabilitados ou leitores de tela.

## Reproduzir

```bash
.venv/bin/python -m habit_workspace
.venv/bin/python -m habit_workspace --vault /caminho/do/cofre
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/pyside6-qmllint -W 0 -i src/habit_workspace/presentation/qml/qmldir src/habit_workspace/presentation/qml/*.qml
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase2.py
unshare --user --map-root-user --net env QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/verify_phase2.py
```

## Validação manual ainda necessária

Em uma sessão desktop nativa:

1. Execute o aplicativo, crie um cofre em uma pasta vazia usando o seletor de
   pasta e abra outro cofre pelo mesmo diálogo. Verifique cancelar e caminhos
   inválidos sem perder o cofre atual.
2. Redimensione entre 640×480, 1000×740 e 1440×960, nos dois temas e em escala
   de tela de 100%, 150% e 200%. Confira textos, foco, rolagem e propriedades.
3. Navegue com Tab/Shift+Tab e atalhos descritos em Configurações. Use Space
   nos dias do calendário e Esc nos diálogos; confirme retorno do foco.
4. Importe um `.md` pelo seletor nativo, revise a prévia e confirme. Repita com
   documento idêntico, UUID conflitante, nota comum e referência ausente.
5. Edite/renomeie o arquivo externamente; confira a atualização. Teste revelar
   sua pasta no gerenciador de arquivos. Apague somente `index.sqlite`, clique
   em Reindexar e confira o conteúdo.
6. Ative movimento reduzido e reabra o aplicativo. Confira persistência de tema
   e preferências, integração com leitor de tela e navegação pelo sistema.

## Limites e trabalho futuro

- Integração nativa com o gerenciador de janelas, seletores de arquivo/pasta,
  gerenciador de arquivos, GPU, leitores de tela, Windows/macOS e escalas HiDPI
  não foi validada. A verificação automatizada usa offscreen/software.
- Scanner, importação e índice ainda são síncronos, conforme a Fase 1. Cofres
  grandes podem bloquear a interface durante a varredura; não há benchmark nem
  processamento em background nesta entrega.
- A busca filtra metadados da página atual. A prévia de nota tem limite de 6000
  caracteres; a prévia de importação, 800. O original completo é preservado.
- Comparação/resolução de UUIDs conflitantes permanece no editor externo.
  Não há substituição automática ou escolha silenciosa de um dos arquivos.
- Estatísticas informa a futura Fase 8. Exportação com dependências e backup
  integrado são explicados em Configurações como recursos da Fase 9, com
  orientação para copiar a pasta inteira. Não há controles fictícios.
- Layout Studio, domínio de recorrência, captura de hábitos e analytics não
  foram iniciados. Os limites de escrita concorrente da Fase 1 continuam válidos.
