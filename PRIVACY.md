# Privacidade, segurança e autonomia do usuário — v1

## Garantias de produto
- O aplicativo não exige contas, autenticação remota, Google, e-mail ou serviços web.
- O funcionamento principal (edição, busca, agenda, gráfico, importação) deve operar com rede desligada.
- Não coletar telemetria, diagnóstico remoto, métricas de uso ou rastreadores de terceiros no MVP.
- O usuário escolhe a pasta do cofre e consegue copiá-la, excluí-la, fazer backup ou usar outro editor.
- Evitar usar diretórios temporários externos ao cofre para salvar conteúdo pessoal persistente; cache pode ficar no próprio cofre ou no cache de aplicativo, com caminho e operação documentados.

## Limites que devem ser comunicados
- **Sem conta não significa anonimato absoluto.** Arquivos podem incluir informações pessoais, horários e nomes; o sistema operacional e ferramentas de backup podem acessá-los.
- **Local não significa criptografado.** Arquivos Markdown são texto claro. Para confidencialidade inicial, recomendar criptografia do dispositivo/volume. Criptografia de cofre opcional é uma funcionalidade futura com implicações de interoperabilidade e recuperação.
- **Sem nuvem não é backup.** Disco pode falhar ou ser perdido. Implementar exportação de cofre, backup local versionado e guia de restauração. Sincronização (se algum dia existir) é opcional e não substitui backup.
- Usar vários dispositivos sem sincronização demanda transferência manual. Em edição concorrente, conflitos precisam de resolução explícita.

## Entrada não confiável
- Nunca executar código Python, QML, HTML ativo ou comandos provenientes de arquivos do cofre, tags ou importações.
- Tratar YAML/JSON/Markdown como **dados**: usar carregamento seguro e schemas/validações estritos, inclusive para IDs, datas, enums e tamanho dos documentos.
- Não permitir caminhos `../` ou absolutos em pacotes, links simbólicos que escapem do cofre nem extração de arquivos além dos limites estabelecidos.
- Prevenir zip bombs com limite agregado de bytes, quantidade de arquivos e proporção de compressão, antes de extrair.
- Links externos devem ser abertos somente por ação consciente do usuário; o aplicativo não busca recursos web automaticamente.
- Escrever documentos com operação atômica e backups; conflito entre editor externo e aplicativo nunca causa overwrite silencioso.

## Preferências futuras
- Sincronização local peer-to-peer explicitamente opt-in (ex.: ferramenta externa), com conflitos bem definidos; NÃO precisa fazer parte do app.
- Criptografia de cofre opcional, cuidadosamente projetada. Não prometer criptografia e legibilidade por outros editores ao mesmo tempo sem explicar a contradição.

## Layout Studio e importação (v4)
- Definições JSON de layout são dados inertes; proibir execução de QML/JS/Python embutidos, scripts, HTML ativo ou plugins trazidos por um cofre.
- Imagens importadas precisam de validação de tipo/tamanho e devem permanecer locais; não resolver URLs externas automaticamente.
- Pacote com layout deve listar os campos/observações pessoais que inclui, além das imagens, para que exportação não vaze dados de outras semanas/meses sem escolha explícita.
