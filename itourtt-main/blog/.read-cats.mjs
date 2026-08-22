import { PrismaClient } from '/app/dist/generated/prisma/client.js';
import { PrismaPg } from '@prisma/adapter-pg';
import pg from 'pg';
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });
const prisma = new PrismaClient({ adapter: new PrismaPg(pool) });
try {
  const cats = await prisma.blogCategory.findMany({ include: { _count: { select: { posts: true } } }, orderBy: { name: 'asc' } });
  console.log('=== EXISTING CATEGORIES (' + cats.length + ') ===');
  cats.forEach(c => console.log(c.slug, '|', c.name, '| posts:', c._count.posts));
  const drafts = await prisma.blogPost.findMany({ where: { status: 'DRAFT' }, select: { slug: true, categories: { select: { slug: true } } } });
  console.log('=== DRAFTS (' + drafts.length + ') ===');
  drafts.forEach(d => console.log(d.slug, '->', d.categories.map(c => c.slug).join(',') || '(none)'));
} finally { await prisma.$disconnect(); await pool.end(); }
