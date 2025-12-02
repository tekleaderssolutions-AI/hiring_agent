from django.core.management.base import BaseCommand
from db import db_cursor


INIT_SQL = '''
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memories (
  id UUID PRIMARY KEY,
  type TEXT NOT NULL,
  title TEXT,
  text TEXT,
  embedding vector(1536),
  metadata JSONB,
  canonical_json JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS resumes (
  id UUID PRIMARY KEY,
  candidate_name TEXT,
  email TEXT,
  phone TEXT,
  type TEXT NOT NULL,
  title TEXT,
  text TEXT,
  embedding vector(1536),
  metadata JSONB,
  canonical_json JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resumes_embedding ON resumes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
'''


class Command(BaseCommand):
    help = 'Initialize Postgres vector extension and create memories/resumes tables (idempotent)'

    def handle(self, *args, **options):
        with db_cursor() as cur:
            cur.execute(INIT_SQL)
        self.stdout.write(self.style.SUCCESS('DB initialized (vector extension, tables, indexes).'))
