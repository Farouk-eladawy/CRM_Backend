/* Build posts.json from /opt/itour/blog/*.md for CMS import (DRAFT, English). */
const fs = require('fs');
const path = require('path');
const MarkdownIt = require('/opt/itour/frontend/node_modules/markdown-it');
const md = new MarkdownIt({ html: false, linkify: true, typographer: false });

const dir = '/opt/itour/blog';
const files = fs.readdirSync(dir).filter((f) => f.endsWith('.md'));

// Canonical category registry (slug -> display name), shared with the importer.
const CATEGORIES = JSON.parse(fs.readFileSync(path.join(dir, '.categories.json'), 'utf8'));
const CAT_SLUGS = new Set(Object.keys(CATEGORIES));
const NAME_TO_SLUG = new Map(
  Object.entries(CATEGORIES).map(([slug, name]) => [slugify(name), slug]),
);

function slugify(s) {
  return s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

// Resolve a frontmatter `category` value to a canonical category slug.
// Accepts either a slug ("travel-tips") or a display name ("Travel Tips"), case-insensitive.
function resolveCategory(value, slug) {
  const norm = slugify(value);
  if (CAT_SLUGS.has(norm)) return norm;
  if (NAME_TO_SLUG.has(norm)) return NAME_TO_SLUG.get(norm);
  console.warn(`  WARN: unknown category "${value}" in ${slug} -> using "${norm}" (add it to .categories.json)`);
  return norm;
}

function parseFrontmatter(raw) {
  const m = raw.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!m) throw new Error('no frontmatter');
  const fm = {};
  for (const line of m[1].split('\n')) {
    const mm = line.match(/^(\w+):\s*(.*)$/);
    if (!mm) continue;
    let v = mm[2].trim().replace(/^"(.*)"$/, '$1');
    fm[mm[1]] = v;
  }
  return { fm, body: m[2] };
}

const posts = files.sort().map((file) => {
  const raw = fs.readFileSync(path.join(dir, file), 'utf8');
  const { fm, body } = parseFrontmatter(raw);
  const slug = file.replace(/\.md$/, '');
  // Drop the leading H1 (the CMS renders `title` separately).
  const bodyNoH1 = body.replace(/^\s*#\s+.*\n+/, '');
  const contentHtml = md.render(bodyNoH1).trim();
  // `category` frontmatter may be a single value or comma-separated list.
  const categorySlugs = (fm.category ? fm.category.split(',') : [])
    .map((c) => c.trim())
    .filter(Boolean)
    .map((c) => resolveCategory(c, slug));
  if (categorySlugs.length === 0) {
    console.warn(`  WARN: no category for ${slug}`);
  }
  return {
    slug,
    title: fm.title,
    excerpt: fm.description,
    metaTitle: fm.title,
    metaDescription: fm.description,
    tags: fm.topic ? [fm.topic] : [],
    categorySlugs,
    contentHtml,
  };
});

fs.writeFileSync(path.join(dir, 'posts.json'), JSON.stringify(posts, null, 2));
console.log(`built posts.json with ${posts.length} posts`);
console.log('sample slug:', posts[0].slug);
console.log('sample categories:', posts[0].categorySlugs.join(',') || '(none)');
console.log('sample html head:', posts[0].contentHtml.slice(0, 160).replace(/\n/g, ' '));
