import { test } from 'node:test';
import assert from 'node:assert/strict';
import { whatsappText } from '../src/whatsapp-text.js';
import { createPortfolioClient } from '../src/portfolio-client.js';

test('project tables become separate blocks while retaining descriptions and exact URLs', () => {
  const input = 'Proyectos de Nahuel\n\n| Proyecto | Qué hace | Demo | GitHub |\n' +
    '|----------|----------|------|--------|\n' +
    '| Clima | Pronósticos e IA. | https://clima.example/ | [Repositorio](https://github.com/example/clima) |\n' +
    '| Bot | Asistente de escritorio. | — | https://github.com/example/bot |\n\nMás información.';
  assert.equal(whatsappText(input), 'Proyectos de Nahuel\n\nClima\nQué hace: Pronósticos e IA.\n' +
    'Demo: https://clima.example/\nGitHub: Repositorio: https://github.com/example/clima\n\n' +
    'Bot\nQué hace: Asistente de escritorio.\nGitHub: https://github.com/example/bot\n\nMás información.');
});

test('technology tables keep categories and distinguish skills from work experience', () => {
  const input = '| Categoría | Habilidades | Experiencia laboral |\n|:---|---:|:---:|\n' +
    '| Frontend | Angular, TypeScript | WordPress |\n| Calidad | Playwright | — |';
  assert.equal(whatsappText(input), 'Frontend\nHabilidades: Angular, TypeScript\nExperiencia laboral: WordPress\n\nCalidad\nHabilidades: Playwright');
});

test('ordinary experience paragraphs and isolated pipes remain unchanged', () => {
  const input = 'Experiencia laboral\n\n- Desarrollo web — DGES\nJunio 2025\nTrabajo con WordPress.\n\nFrontend | Backend';
  assert.equal(whatsappText(input), input);
  assert.equal(whatsappText('| A | B |\n| valor | otro |'), '| A | B |\n| valor | otro |');
});

test('real API client formats a returned table before handing it to the conversation', async () => {
  const answer = createPortfolioClient({ apiUrl: 'https://portfolio.example/api/v1/chat/', timeoutMs: 1000,
    fetchImpl: async () => Response.json({ respuesta: '| Proyecto | Demo |\n|---|---|\n| Clima | https://clima.example/ |' }),
  });
  assert.equal(await answer('Proyectos'), 'Clima\nDemo: https://clima.example/');
});
