// WhatsApp does not render Markdown tables. Keep their data as readable blocks.
function cells(line) {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim());
}

function tableLine(line) {
  return line.trim().startsWith('|') && cells(line).length >= 2;
}

export function whatsappText(text) {
  const lines = text.replace(/\r\n/g, '\n').split('\n');
  const result = [];
  for (let index = 0; index < lines.length; index++) {
    const header = cells(lines[index]);
    const separator = index + 1 < lines.length ? cells(lines[index + 1]) : [];
    if (!tableLine(lines[index]) || separator.length !== header.length ||
        !separator.every(cell => /^:?-{3,}:?$/.test(cell))) {
      result.push(lines[index]);
      continue;
    }
    index += 2;
    const blocks = [];
    for (; index < lines.length && tableLine(lines[index]); index++) {
      const row = cells(lines[index]);
      // Leave malformed rows intact rather than silently dropping their data.
      if (row.length !== header.length) { blocks.push(lines[index]); continue; }
      blocks.push(row.map((value, column) => {
        if (!value || /^[-–—]$/.test(value)) return '';
        const content = value.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '$1: $2');
        return column === 0 ? content : `${header[column]}: ${content}`;
      }).filter(Boolean).join('\n'));
    }
    result.push(blocks.join('\n\n'));
    index--;
  }
  return result.join('\n').trim();
}
