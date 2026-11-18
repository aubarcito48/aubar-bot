const SECTIONS = [
  { labels: { es: 'Sobre Nahuel', en: 'About Nahuel' }, aliases: ['sobre mi', 'about'],
    query: { es: 'Contame sobre el perfil de Nahuel según su portfolio publicado.', en: "Tell me about Nahuel's profile from his published portfolio." } },
  { labels: { es: 'Proyectos', en: 'Projects' }, aliases: [],
    query: { es: 'Mostrame los proyectos publicados de Nahuel, cada uno en un bloque separado por una línea en blanco: nombre, breve descripción, Demo: URL y GitHub: URL solo si esos enlaces están publicados para ese proyecto. Usá enlaces completos, no tablas ni enlaces Markdown. No inventes enlaces ni mezcles repositorios entre proyectos.', en: "Show Nahuel's published projects, each in a separate block with a blank line between projects: name, short description, Demo: URL and GitHub: URL only when published for that project. Use full URLs, no tables or Markdown links. Never invent links or mix repositories between projects." } },
  { labels: { es: 'Experiencia', en: 'Experience' }, aliases: [],
    query: { es: 'Contame sobre la experiencia laboral publicada de Nahuel.', en: "Tell me about Nahuel's published work experience." } },
  { labels: { es: 'Educación', en: 'Education' }, aliases: ['formacion'],
    query: { es: 'Contame sobre la educación y formación publicada de Nahuel.', en: "Tell me about Nahuel's published education and training." } },
  { labels: { es: 'Tecnologías', en: 'Technologies' }, aliases: ['skills'],
    query: { es: '¿Qué tecnologías figuran en el portfolio de Nahuel? Diferenciá habilidades de experiencia laboral. Agrupalas por categoría en bloques separados por una línea en blanco, sin tablas.', en: "Which technologies are listed in Nahuel's portfolio? Distinguish skills from work experience. Group by category in blocks separated by blank lines, without tables." } },
  { labels: { es: 'Contacto', en: 'Contact' }, aliases: ['contactanos'],
    query: { es: '¿Cómo puedo contactar a Nahuel usando los medios publicados en su portfolio?', en: 'How can I contact Nahuel using the contact methods published in his portfolio?' } },
];

export function normalizeChoice(text) {
  return text.trim().toLowerCase().normalize('NFD').replace(/\p{M}/gu, '');
}

export function isMenuRequest(text) {
  return ['menu', '/menu', 'menú principal'].map(normalizeChoice).includes(normalizeChoice(text));
}

export function menuText(language) {
  const items = SECTIONS.map((section, index) => `${index + 1}. ${section.labels[language]}`).join('\n');
  return language === 'es'
    ? `¿Qué te gustaría conocer?\n\n${items}\n\nRespondé con el número, el nombre de una sección o tu propia pregunta. Escribí MENÚ cuando quieras volver a estas opciones.`
    : `What would you like to explore?\n\n${items}\n\nReply with a number, a section name or your own question. Send MENU whenever you want to see these options again.`;
}

export function sectionQuestion(text, language) {
  const choice = normalizeChoice(text);
  const section = SECTIONS.find((item, index) => choice === String(index + 1) ||
    [...Object.values(item.labels), ...item.aliases].some(label => normalizeChoice(label) === choice));
  return section?.query[language];
}
