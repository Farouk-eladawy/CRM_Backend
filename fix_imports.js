const fs = require('fs');
const path = require('path');

const targetFiles = [
  'frontend_dashboard/new_frontend_dashboard/src/views/ReligiousOperationView.tsx',
  'frontend_dashboard/new_frontend_dashboard/src/views/AIOperationView.tsx'
];

for (const relPath of targetFiles) {
  const p = path.join(__dirname, relPath);
  let content = fs.readFileSync(p, 'utf8');

  const uiDictRegex = /const UI_DICT: Record<string, string> = \{[\s\S]*?\};\nconst _t = \(str: string, lang: string\) => lang === "ar"\ \? \(UI_DICT\[str\] \|\| str\) : str;\n\n/;
  const match = uiDictRegex.exec(content);
  if (match) {
    content = content.replace(match[0], '');
    
    // find last import by looking for the last "from '...';" or "from \"...\";"
    let lastImportIndex = 0;
    const lines = content.split('\n');
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].includes('import ') || lines[i].includes('from ')) {
        // Just find the last import block
      }
    }
    // A simpler way: Find the last "from 'lucide-react';" or similar.
    const lastFrom = content.lastIndexOf("from 'lucide-react';");
    if (lastFrom !== -1) {
      lastImportIndex = content.indexOf('\n', lastFrom) + 1;
    } else {
      // Fallback
      lastImportIndex = content.lastIndexOf(';') + 1;
    }

    content = content.slice(0, lastImportIndex) + '\n' + match[0] + content.slice(lastImportIndex);
    fs.writeFileSync(p, content);
  }
}
console.log('Fixed import order again');
