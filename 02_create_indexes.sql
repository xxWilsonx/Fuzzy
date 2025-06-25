CREATE INDEX idx_products_name ON products(name);
CREATE INDEX idx_products_name_lower ON products(LOWER(name));
CREATE INDEX idx_products_name_trgm ON products USING gin (name gin_trgm_ops);
CREATE INDEX idx_products_name_soundex ON products(soundex(name));
CREATE INDEX idx_products_fts ON products USING gin(search_vector);