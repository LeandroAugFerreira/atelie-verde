export const RAF_EXPRESSIONS = {
  neutral: "greeting",
  welcome: "greeting",
  greeting: "greeting",
  happy: "happy",
  celebrating: "celebrating",
  excited: "celebrating",
  serious: "serious",
  angry: "angry",
  concerned: "serious",
  thinking: "thinking",
  curious: "thinking",
  sleepy: "sleepy",
  shy: "shy",
  skeptical: "skeptical",
  delighted: "delighted",
  surprised: "surprised",
  sad: "sad",
  confident: "delighted",
  relieved: "happy",
  confused: "skeptical",
  explaining: "greeting",
} as const;
export type RafinhaExpression = keyof typeof RAF_EXPRESSIONS;
export function expressionAsset(value: string) {
  return `/rafinha/official/rafinha_${RAF_EXPRESSIONS[value as RafinhaExpression] || RAF_EXPRESSIONS.neutral}.webp`;
}
export const EXPRESSION_LABELS: Record<string, string> = {
  happy: "feliz",
  sad: "triste",
  serious: "atento",
  angry: "alertando",
  thinking: "pensativo",
  sleepy: "sonolento",
  greeting: "saudando",
  surprised: "surpreso",
  shy: "carinhoso",
  skeptical: "avaliando uma dúvida",
  delighted: "encantado",
  celebrating: "comemorando",
};
export function initialReaction(text: string): RafinhaExpression {
  const q = text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
  if (
    /melhorou|nao esta mais|ja nao|agora esta verde|mas.*(brot|folha nova)/.test(
      q,
    )
  )
    return "relieved";
  if (/morreu|nao resistiu|perdi minha planta/.test(q)) return "sad";
  if (
    /agua sanitaria|detergente|desinfetante/.test(q) &&
    !/nao (vou|coloco|usei)/.test(q)
  )
    return "angry";
  if (/cinco|5|dez|10/.test(q) && /vezes.*dia/.test(q)) return "surprised";
  if (/fofo|querido|adoro voce/.test(q)) return "shy";
  if (/boa noite|ainda esta acordado|ja esta tarde/.test(q)) return "sleepy";
  if (/primeira vez|de repente|varios brotos/.test(q)) return "surprised";
  if (/nao sei|nao faco ideia|identificar|qual planta/.test(q))
    return "curious";
  if (
    /nao (reguei|molhei)|esqueci de (regar|molhar)|murch|amarel|fungo|praga|manchas|toxic|venenos/.test(
      q,
    )
  )
    return "concerned";
  if (/obrigad|valeu|floresceu|deu certo|funcionou/.test(q)) return "happy";
  if (/^(oi|ola|bom dia|boa tarde)/.test(q)) return "welcome";
  return "neutral";
}
export const SOURCE_LABELS: Record<string, string> = {
  catalog: "Catálogo",
  web: "Pesquisa web",
  identification: "Identificação",
  care: "Cuidados",
  services: "Serviços",
  company: "Loja",
  general: "Conversa",
  connection: "Conexão",
  research_unavailable: "Orientação",
};
export const PHASE_LABELS: Record<string, string> = {
  context: "🌱 Deixa eu entender melhor…",
  catalog: "🌿 Estou consultando as informações da planta…",
  research: "🔎 Vou pesquisar isso para você…",
  model: "🌱 Deixa eu pensar…",
  writing: "🌿 Estou respondendo…",
  reply: "🌿 Já estou preparando sua orientação…",
};
