# Calendário e módulos — refinamento de apresentação da 7C

## Entrega

- Removida a agenda corrida de hábitos do painel Planejamento pessoal.
- Calendário com prévia por hover/foco, seleção de data sem navegação implícita,
  entradas acionáveis e criação contextual de tarefa, objetivo, evento, hábito,
  nota e avaliação. A consulta diária reutiliza o relatório e agenda existentes.
- Módulos Calendário, Tarefas e objetivos, Hábitos e registros, Página personalizada
  e Documentos: recolher, ampliar (ocultar os demais módulos) e restaurar.
- Avisos compactos com indicador de status, separados dos cartões funcionais.
- Largura mínima da sidebar corrigida para evitar corte de rótulos.
- Nenhuma alteração de schema, migração ou dados canônicos. Transferência seletiva
  da 7C permanece pendente.

## Verificação

- `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python -m pytest -q`:
  **386 passed in 111.80s**.
- Durante essa execução, foram finalizados reset da seleção de calendário ao
  navegar, apresentação do calendário e menu Hábito; a jornada de eventos foi
  ampliada para foco/preview e criação de nota na data escolhida. Após esses ajustes,
  `tests/test_event_gui.py tests/test_event_workflows.py`: **12 passed in 5.53s**.
- Ruff check, Ruff format --check e git diff --check aprovados.
- `QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software ./habit-workspace --smoke-test`:
  aprovado.
- Jornadas existentes adaptadas à seleção explícita + Abrir dia e ao menu do
  calendário; verificações de persistência/conflito/reabertura preservadas.
- Captura offscreen inspecionada em `/tmp/habit-workspace-phase7c/offscreen/agenda.png`.

## Limites

Sem nova validação nativa X11/Windows/macOS ou aprovação humana de acessibilidade.
Prévia textual limitada a 12 entradas; lista do dia permite abrir os itens de agenda.
Notas/avaliações/objetivos da prévia usam associação exata ao dia; um objetivo anual
não é replicado automaticamente em cada dia. Preferências de recolhimento/ampliação
são transitórias, não persistidas no cofre. Nenhum commit criado.
