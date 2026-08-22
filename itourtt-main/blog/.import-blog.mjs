// Runs INSIDE the pod (cwd /app). Imports blog posts as DRAFT (English only).
import { readFileSync } from 'node:fs';
import { PrismaClient } from '/app/dist/generated/prisma/client.js';
import { PrismaPg } from '@prisma/adapter-pg';
import pg from 'pg';

const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });
const prisma = new PrismaClient({ adapter: new PrismaPg(pool) });

const posts = JSON.parse(readFileSync('/app/blog-posts.json', 'utf8'));
// Canonical category registry (slug -> display name), shared with the build step.
const CATEGORIES = JSON.parse(readFileSync('/app/blog-categories.json', 'utf8'));

// Build a `connectOrCreate` list for a post's category slugs.
// Only canonical categories (present in the registry) are created/connected; unknown slugs are skipped with a warning.
function categoryConnect(categorySlugs) {
  return (categorySlugs ?? [])
    .filter((slug) => {
      if (CATEGORIES[slug]) return true;
      console.log(`  WARN: skipping unknown category "${slug}" (not in registry)`);
      return false;
    })
    .map((slug) => ({
      where: { slug },
      create: { slug, name: CATEGORIES[slug] },
    }));
}

let created = 0;
let skipped = 0;
try {
  for (const p of posts) {
    const existing = await prisma.blogPost.findUnique({ where: { slug: p.slug } });
    if (existing) {
      console.log(`SKIP (exists): ${p.slug}`);
      skipped++;
      continue;
    }
    await prisma.blogPost.create({
      data: {
        slug: p.slug,
        title: p.title,
        excerpt: p.excerpt,
        contentHtml: p.contentHtml,
        status: 'DRAFT',
        publishedAt: null,
        tags: p.tags ?? [],
        metaTitle: p.metaTitle,
        metaDescription: p.metaDescription,
        categories: { connectOrCreate: categoryConnect(p.categorySlugs) },
      },
    });
    console.log(`CREATE (draft): ${p.slug} [${(p.categorySlugs ?? []).join(',') || 'no category'}]`);
    created++;
  }
  const total = await prisma.blogPost.count();
  console.log(`\nDONE: created=${created} skipped=${skipped} | total blogPost rows now=${total}`);
} finally {
  await prisma.$disconnect();
  await pool.end();
}
