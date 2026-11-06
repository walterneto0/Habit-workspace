# Refinamento visual do checkpoint 7C

Mudança apenas de apresentação: paleta escura mais clara, criação agrupada em
Novo (tarefa, objetivo, evento, nota e avaliação), filtro de concluídas explícito,
paginação condicional e busca única nas páginas temporais. Contratos de arquivos,
domínio e persistência permanecem iguais. Transferência seletiva continua pendente.

Verificação local:
- Ruff check e format --check aprovados; git diff --check aprovado.
- Smoke test QML offscreen aprovado.
- Suíte completa offscreen: 384 aprovados e uma falha no roteiro 7A que ainda
  procurava a busca removida. Roteiro atualizado para document-search; repetição
  de tests/test_qml_startup.py::test_phase7a_planning_pointer_keyboard_and_reopen:
  1 aprovado em 2,42 s. A suíte completa não foi repetida após essa correção do teste.
- Jornadas existentes atualizadas para abrir Novo antes de escolher a criação.
- Captura da agenda offscreen inspecionada em /tmp/habit-workspace-phase7c/offscreen/agenda.png.
- Sem validação nativa nova, aprovação humana de acessibilidade ou teste Windows/macOS.
