const form = document.querySelector('#upload-form');
const result = document.querySelector('#result');
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = form.querySelector('button');
  button.disabled = true;
  button.textContent = 'Analizando documento…';
  result.hidden = false;
  result.textContent = 'Extrayendo texto y preparando el análisis.';
  try {
    const response = await fetch('/api/analyze', { method: 'POST', body: new FormData(form) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo analizar el documento.');
    result.textContent = `${data.result}\n\nDocumento: ${data.pages} páginas · Generado por IA`;
  } catch (error) {
    result.textContent = error.message;
  } finally {
    button.disabled = false;
    button.innerHTML = '✳ &nbsp; Analizar documento <span>→</span>';
  }
});

const askForm = document.querySelector('#ask-form');
const answer = document.querySelector('#answer');
askForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  answer.hidden = false;
  answer.textContent = 'Buscando evidencia en el documento…';
  try {
    const response = await fetch('/api/ask', { method: 'POST', body: new FormData(askForm) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo responder.');
    answer.textContent = `${data.answer}\n\nGenerado por IA · ${data.pages} páginas`;
  } catch (error) { answer.textContent = error.message; }
});

const languageButton = document.querySelector('#language');
languageButton.addEventListener('click', () => {
  const isSpanish = document.documentElement.lang === 'es';
  document.documentElement.lang = isSpanish ? 'en' : 'es';
  languageButton.innerHTML = `${isSpanish ? 'EN' : 'ES'} <span>⌄</span>`;
  document.querySelector('.welcome h1').textContent = isSpanish ? 'Intelligence for your knowledge.' : 'Inteligencia para tu conocimiento.';
  document.querySelector('.welcome p').textContent = isSpanish ? 'Explore documents, uncover key ideas and find answers with verifiable sources.' : 'Explora documentos, obtén ideas clave y encuentra respuestas con fuentes verificables.';
  document.querySelector('.subtext').textContent = isSpanish ? 'Upload a PDF to get a summary and its most relevant concepts.' : 'Carga un documento PDF para obtener un resumen y sus conceptos más relevantes.';
});
