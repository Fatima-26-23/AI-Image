-- Phase 1 schema. pgvector optional at ~50 images; embedding stored as float array
-- for now — swap to VECTOR type later if you add the pgvector extension.

CREATE TABLE IF NOT EXISTS images (
    id           SERIAL PRIMARY KEY,
    filepath     TEXT NOT NULL,
    subject      TEXT,
    category     TEXT,
    attributes   TEXT[] DEFAULT '{}',
    caption      TEXT,
    confidence   REAL,
    flagged      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_images_category ON images (category);
CREATE INDEX IF NOT EXISTS idx_images_flagged ON images (flagged);

CREATE TABLE IF NOT EXISTS image_vectors (
    id           SERIAL PRIMARY KEY,
    image_id     INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    embedding    REAL[] NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_image_vectors_image_id ON image_vectors (image_id);

CREATE TABLE IF NOT EXISTS posts (
    id           SERIAL PRIMARY KEY,
    title        TEXT NOT NULL,
    content      TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS post_vectors (
    id           SERIAL PRIMARY KEY,
    post_id      INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    embedding    REAL[] NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_post_vectors_post_id ON post_vectors (post_id);

CREATE TABLE IF NOT EXISTS suggestions (
    id               SERIAL PRIMARY KEY,
    post_id          INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    image_id         INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    similarity_score REAL,
    guard_decision   TEXT NOT NULL CHECK (guard_decision IN ('accepted', 'rejected')),
    guard_reason     TEXT,
    status           TEXT NOT NULL DEFAULT 'pending'
                       CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_suggestions_post_id ON suggestions (post_id);
CREATE INDEX IF NOT EXISTS idx_suggestions_status ON suggestions (status);

CREATE TABLE IF NOT EXISTS cost_log (
    id           SERIAL PRIMARY KEY,
    call_type    TEXT NOT NULL CHECK (call_type IN ('vision', 'embedding')),
    reference_id INTEGER,           -- image_id or post_id, depending on call_type
    cost_usd     REAL NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
