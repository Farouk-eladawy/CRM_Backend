const fs = require('fs');
const path = require('path');
const file = fs.readFileSync(path.join(__dirname, 'frontend_dashboard/new_frontend_dashboard/src/views/CustomersView.tsx'), 'utf8');

const texts = new Set();
let match;
const regex = />([^<>{]+)</g;
while ((match = regex.exec(file)) !== null) {
  const text = match[1].trim();
  if (text && /[A-Za-z]/.test(text)) {
    texts.add(text);
  }
}
console.log(Array.from(texts).slice(0, 50));
