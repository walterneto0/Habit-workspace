.pragma library

function label(value) {
    return ({habit: "Hábito", checklist: "Lista de hábitos", list: "Lista geral", table: "Tabela",
        note: "Nota", image: "Imagem", section: "Seção", chart: "Gráfico", text: "Texto",
        integer: "Número inteiro", number: "Número decimal", duration: "Duração", date: "Data",
        time: "Horário", boolean: "Sim/Não", selection: "Escolha única", rating: "Avaliação",
        daily: "Diário", weekly: "Semanal", none: "Nenhuma", sum: "Soma", mean: "Média",
        min: "Mínimo", max: "Máximo", count: "Contagem", states: "Estados dos hábitos",
        separate: "Manter semana separada", start: "Mês do início", end: "Mês do fim",
        completion: "Mês da conclusão", bar: "Barras", line: "Linha", total: "Total",
        contain: "Mostrar imagem inteira", cover: "Preencher espaço"})[value.replace("_input", "")] || value;
}
function choices(values) { return values.map(v => ({value: v, name: label(v)})); }
function compatible(kind, source) {
    if (kind.endsWith("_input")) {
        const type = kind.replace("_input", "");
        return source.kind === "metric_definition" && (source.type === type || (type === "number" && source.type === "integer"));
    }
    if (kind === "note") return source.kind === "note";
    if (kind === "table") return source.kind === "metric_definition";
    if (kind === "chart") return source.kind === "habit" || source.kind === "metric_definition";
    if (kind === "list") return source.kind === "task" || source.kind === "habit" || source.kind === "metric_definition";
    return false;
}
