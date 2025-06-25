CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;

-- Основная таблица продуктов
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    brand VARCHAR(100),
    sku VARCHAR(50) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    search_vector TSVECTOR
);

-- Таблица для логирования результатов поиска
CREATE TABLE search_benchmarks (
    id SERIAL PRIMARY KEY,
    method VARCHAR(50) NOT NULL,
    dataset_size INTEGER NOT NULL,
    query_text VARCHAR(255) NOT NULL,
    execution_time_ms FLOAT NOT NULL,
    result_count INTEGER NOT NULL,
    index_used BOOLEAN DEFAULT FALSE,
    test_run_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица тестовых запросов
CREATE TABLE test_queries (
    id SERIAL PRIMARY KEY,
    correct_term VARCHAR(255) NOT NULL,
    typo_term VARCHAR(255) NOT NULL,
    error_type VARCHAR(50) NOT NULL
);
COMMENT ON TABLE products IS 'Основная таблица с данными о товарах для тестирования нечеткого поиска.';
COMMENT ON COLUMN products.name IS 'Название товара. Основное поле для тестов.';
COMMENT ON COLUMN products.brand IS 'Бренд товара. Также используется в тестах.';

COMMENT ON TABLE search_benchmarks IS 'Таблица для сбора результатов бенчмарков.';
COMMENT ON COLUMN search_benchmarks.method IS 'Название тестируемого метода (LIKE, pg_trgm и т.д.).';
COMMENT ON COLUMN search_benchmarks.execution_time_ms IS 'Время выполнения запроса в миллисекундах.';

COMMENT ON TABLE test_queries IS 'Таблица с тестовыми запросами и различными типами опечаток.';