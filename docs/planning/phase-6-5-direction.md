# Habit Workspace — Direção do produto para a versão 6.5

> **Documento de orientação para agentes de IA e revisores humanos.**
> Uso recomendado no repositório: `docs/planning/phase-6-5-direction.md`.
> Este documento descreve **a intenção da versão**, não substitui `PRODUCT.md`, `FILE_FORMAT.md`, `ARCHITECTURE.md`, `DESIGN_SYSTEM.md`, `LAYOUT_ENGINE.md` ou `AGENTS.md`. Em caso de conflito técnico, preserve o contrato existente e registre a divergência.

## 1. Por que esta versão existe

O Habit Workspace deve ajudar pessoas a organizar a vida **do micro ao macro**: registrar ações diárias, compreender prioridades, planejar períodos maiores e, futuramente, relacionar ações a responsabilidades e objetivos.

A visão do fundador é facilitar uma vida organizada em serviço da própria vocação. Essa motivação **não significa impor linguagem religiosa, pressupostos teológicos ou exigências de fé** a quem usa o aplicativo.

A versão **6.5** não é uma corrida para adicionar funcionalidades. É uma ponte entre o núcleo já implementado (cofre, páginas temporais, layouts e hábitos) e o planejamento mais amplo da Fase 7 (notas, tarefas, metas, eventos e agenda).

**Promessa de produto:** uma pessoa leiga deve conseguir começar a organizar a própria rotina sem conhecer Markdown, JSON, UUID, banco de dados ou conceitos de arquitetura.

## 2. O que significa uma experiência integrada

Os módulos não devem parecer aplicativos separados reunidos numa janela. A identidade canônica do dado permanece única, embora apareça em várias visualizações.

- **Hábito:** criado uma vez, encontrado por busca/tags e exibido em checklists e períodos elegíveis; renomeá-lo não cria cópias.
- **Dia, semana, mês e ano:** são perspectivas sobre os mesmos dados, não pastas que determinam sua propriedade física.
- **Layout Studio:** configura como apresentar ou capturar informações; não é necessário entrar nele para realizar check-ins cotidianos.
- **Acompanhamento:** registra ocorrências e valores canônicos; não grava fatos dentro do JSON do layout.
- **Detalhes e navegação:** a pessoa consegue sair de um bloco para a entidade correspondente e voltar sem perder o contexto.
- **Notas, objetivos, tarefas e eventos:** ainda dependem da Fase 7; não criar implementações parciais disfarçadas durante a 6.5.

### Exemplo real de uso

A pessoa abre uma página diária, cria **“Estudar Python”**, define recorrência e escopo, marca como concluído e fecha o aplicativo. No dia seguinte encontra o hábito na mesma rotina; na página semanal visualiza a mesma entidade quando o componente a consulta. Ao tocar/clicar no nome, vê os detalhes e pode editar propriedades sem duplicar o hábito. Ao modificar o layout, os registros anteriores permanecem.

## 3. Princípios inegociáveis

1. **File-first e offline:** Markdown/YAML/JSON são a fonte da verdade; SQLite é índice regenerável. Não exigir login, nuvem ou telemetria.
2. **Integridade antes de conveniência:** nenhuma mudança visual apaga registros; detectar conflitos e preservar arquivos desconhecidos e metadados adicionais.
3. **Identidade estável:** UUIDs não mudam devido a renomeação, reorganização de páginas ou troca de layout.
4. **Tempo explícito:** distinguir período de visualização, escopo/recorrência, data da ocorrência, instante de ativação do layout e data atual.
5. **Ausência de registro não é falha:** `unrecorded` nunca vira automaticamente `missed`. Datas futuras não geram check-ins antecipados.
6. **Uma apresentação, muitos usos:** um mesmo hábito pode aparecer em diferentes checklists/períodos, sempre apontando aos mesmos registros canônicos.
7. **Interface familiar:** português do Brasil, vocabulário claro, ações contextuais, acessibilidade e alternativas ao drag-and-drop.
8. **Autonomia:** explicar que armazenamento local **não equivale** a anonimato absoluto, criptografia ou backup.
9. **Sem migração especulativa:** manter compatibilidade com vaults existentes e schemas atuais, salvo necessidade demonstrada e documentada.
10. **Sem falsa funcionalidade:** não criar botões ou visualizações que sugiram que gráficos, notas editáveis e agenda completa já funcionam.

## 4. Política de experiência do usuário

- O primeiro uso deve enfatizar **Criar/abrir cofre → Criar hábito → Registrar ocorrência → Encontrar registro**.
- Personalização é **opt-in**: modelos e defaults úteis primeiro, configurações avançadas quando necessárias.
- Ações comuns devem ficar próximas do conteúdo: **Novo hábito**, **Adicionar à lista**, **Concluir**, **Ver detalhes**, **Editar hábito**, **Personalizar página**.
- Drag-and-drop é opcional para organização espacial, não um requisito para conseguir usar o aplicativo.
- Mensagens de erro devem dizer o que aconteceu, o efeito sobre os dados e o próximo passo seguro.
- Um usuário não deve ver caminhos físicos ou UUIDs como rótulo principal; essas informações permanecem disponíveis para diagnósticos.
- O usuário deve perceber claramente quando visualiza **o layout atual de um período** ou **uma revisão histórica**. Ver um dia passado não autoriza alterar atribuições históricas ou interpretar a ausência de dado como falha.
- O resultado desejado é **uso diário tranquilo**, não um editor visual complexo.

## 5. Decisões temporais a preservar e esclarecer

- `PeriodRef`: período visual (ano/mês/semana/dia).
- `TemporalScope`: intervalo em que o item é válido.
- `Recurrence`: quando há ocorrência esperada dentro do escopo.
- `capture_day`: data da ocorrência que o usuário está registrando.
- `layout effective_at`: instante a partir do qual uma revisão visual vale.
- `today`: data civil local que precisa mudar após a meia-noite e ao retornar da suspensão do computador.

**Direção de UX sugerida:** acompanhamento normal usa o layout efetivo atual do período, com indicação compreensível quando isso importar; inspeção histórica deve ser identificada como tal e não editar silenciosamente o presente. O agente deve confrontar essa direção com `LAYOUT_ENGINE.md` e os contratos existentes antes de decidir uma implementação.

## 6. Duas entregas, uma única direção

### Fase 6.5A — Estabilidade e integridade

Objetivo: confiar que o aplicativo não confunde datas, não perde dados, não trava desnecessariamente nem oferece recuperação insegura.

Escopo:
- virada do dia/suspensão e relógio determinístico para testes;
- política clara para resolução temporal do layout;
- medição de desempenho de scan, index, navegação e captura;
- correção de gargalos *comprovados*;
- recuperação/diagnóstico seguro de locks e publicações interrompidas;
- regressões automatizadas e relatório de evidências.

**Gate A:** só passar à 6.5B quando a base está estável, os limites restantes estão documentados e os testes aplicáveis passaram.

### Fase 6.5B — Integração e usabilidade

Objetivo: um usuário novo conseguir criar e acompanhar uma rotina e transitar entre elementos conectados, sem entender conceitos internos.

Escopo:
- integração de navegação hábitos ↔ checklists ↔ períodos ↔ detalhes;
- primeiros passos/contextos vazios e ações claras;
- consistência de apresentação por tipo de documento;
- validação do fluxo completo com GUI real em vault temporário;
- pequenos padrões reutilizáveis para futura Fase 7, **sem** implementar suas entidades.

**Gate B:** demonstrar o fluxo de usuário do início ao fim, persistência após reinício, referências estáveis, interface acessível e testes de regressão aprovados.

## 7. O que NÃO pertence à versão 6.5

Não implementar a Fase 7 (notas editáveis, avaliações completas, TODO, objetivos, eventos e agenda), a Fase 8 (gráficos calculados), a Fase 9 (sistema de backup/pacotes completo), autenticação, sincronização, mobile, novo frontend nem frameworks genéricos especulativos.

**Não inferir relações causais:** concluir “Estudar Python” não deve alterar automaticamente o progresso de um objetivo anual que ainda não possui contrato explícito.

## 8. Como julgar uma mudança

Antes de escrever código, perguntar:

1. O problema foi reproduzido ou há evidência verificável?
2. A correção reduz fricção ou apenas adiciona opções?
3. Mantém o arquivo canônico independente do layout?
4. Está claro para uma pessoa leiga o que mudou?
5. Existe teste para casos normais, falha e reinício?
6. A mudança aumenta a complexidade para a Fase 7?

Se uma melhoria não passa por essas perguntas, reduza seu escopo ou documente-a para depois.

## 9. Critério final da versão 6.5

Uma pessoa leiga abre o aplicativo, cria um cofre, registra um hábito, acompanha datas corretamente, usa o mesmo hábito em diferentes visões, altera a apresentação sem apagar registros, entende eventuais erros de recuperação e consegue retomar o trabalho após fechar e reabrir o programa. As mesmas operações devem funcionar sem acesso à internet.

**Métrica qualitativa:** menos dúvidas sobre “onde clicar” e “onde meus dados foram parar”. **Métrica técnica:** testes, integridade, latência medida e verificações de GUI real — sem alegações não comprovadas.
