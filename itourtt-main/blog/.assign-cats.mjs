import { PrismaClient } from '/app/dist/generated/prisma/client.js';
import { PrismaPg } from '@prisma/adapter-pg';
import pg from 'pg';
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });
const prisma = new PrismaClient({ adapter: new PrismaPg(pool) });

const MAP = {
  'airport-transfers-in-egypt-cash-or-card-payment': ['travel-tips'],
  'can-i-book-an-airport-transfer-in-advance-online': ['airport-guides'],
  'can-i-book-hotel-airport-transfers-directly': ['airport-guides'],
  'do-uber-and-bolt-work-at-egyptian-airports': ['airport-guides'],
  'how-do-i-avoid-getting-scammed-on-airport-transfers': ['travel-tips'],
  'how-long-does-it-take-from-cairo-airport-to-downtown': ['airport-guides'],
  'how-much-does-a-private-transfer-cost-from-cairo-to-alexandria': ['egypt-trips'],
  'how-much-should-i-pay-for-airport-transfer-in-cairo': ['travel-tips'],
  'is-it-safe-to-take-a-taxi-from-cairo-airport-alone': ['travel-tips'],
  'private-driver-vs-uber-in-egypt-which-is-better': ['travel-tips'],
  'should-i-hire-a-driver-for-my-entire-egypt-trip': ['egypt-trips'],
  'what-time-should-i-book-my-airport-transfer': ['airport-guides'],
  'whats-the-best-way-to-get-from-cairo-airport-to-the-pyramids': ['egypt-trips'],
};

try {
  // Verify the 3 target categories exist (do NOT create new ones)
  const cats = await prisma.blogCategory.findMany({ select: { slug: true } });
  const have = new Set(cats.map(c => c.slug));
  for (const need of ['airport-guides', 'egypt-trips', 'travel-tips']) {
    if (!have.has(need)) throw new Error('Missing category: ' + need);
  }
  let updated = 0, missing = 0;
  for (const [slug, catSlugs] of Object.entries(MAP)) {
    const post = await prisma.blogPost.findUnique({ where: { slug }, select: { id: true } });
    if (!post) { console.log('MISSING POST:', slug); missing++; continue; }
    await prisma.blogPost.update({
      where: { slug },
      data: { categories: { set: catSlugs.map(s => ({ slug: s })) } },
    });
    console.log('OK  ', slug, '->', catSlugs.join(','));
    updated++;
  }
  console.log(`\nDONE: updated=${updated} missingPosts=${missing}`);
  // Final category counts
  const after = await prisma.blogCategory.findMany({ include: { _count: { select: { posts: true } } }, orderBy: { name: 'asc' } });
  console.log('=== CATEGORY COUNTS NOW ===');
  after.forEach(c => console.log(c.name, '|', c._count.posts));
} finally { await prisma.$disconnect(); await pool.end(); }
