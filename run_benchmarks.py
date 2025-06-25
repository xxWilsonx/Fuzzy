import psycopg2
import time
import uuid
from psycopg2 import sql

DB_CONFIG = {
    'database': 'fuzzy_search_lab',
    'user': 'postgres',
    'password': '7842590Ff',
    'host': 'localhost',
    'port': '5432'
}


class SearchPerformanceAnalyzer:
    def __init__(self, db_config):
        self.db_conn = psycopg2.connect(**db_config)
        self.session_id = uuid.uuid4().hex
        print(f"Начало тестовой сессии: {self.session_id}")
        self._setup_fulltext_search()
        self._install_extensions()

    def _install_extensions(self):
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
                cursor.execute("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;")
                self.db_conn.commit()
        except Exception as error:
            print(f"Ошибка установки расширений: {error}")
            self.db_conn.rollback()

    def _setup_fulltext_search(self):
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                               ALTER TABLE products
                                   ADD COLUMN IF NOT EXISTS search_vector tsvector;

                               UPDATE products
                               SET search_vector = to_tsvector('english', name || ' ' || description);
                               """)
                self.db_conn.commit()
        except Exception as error:
            print(f"Ошибка настройки полнотекстового поиска: {error}")
            self.db_conn.rollback()

    def _compute_metrics(self, retrieved, relevant):
        if not relevant:
            return (0.0, 0.0, 0.0) if retrieved else (1.0, 1.0, 1.0)

        true_positives = len(retrieved & relevant)
        precision = true_positives / len(retrieved) if retrieved else 0
        recall = true_positives / len(relevant)
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0
        return (precision, recall, f1)

    def _save_results(self, method, size, query, duration, count, indexed):
        insert_query = """
                       INSERT INTO search_benchmarks (method, dataset_size, query_text, \
                                                      execution_time_ms, result_count, \
                                                      index_used, test_run_id) \
                       VALUES (%s, %s, %s, %s, %s, %s, %s) \
                       """
        with self.db_conn.cursor() as cursor:
            cursor.execute(insert_query, (
                method, size, query,
                duration, count, indexed, self.session_id
            ))
            self.db_conn.commit()

    def _execute_search(self, query_template, search_term):
        start_time = time.perf_counter()
        results = set()
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(query_template, (search_term,))

                # Явно получаем описание столбцов
                col_names = [desc[0] for desc in cursor.description]

                for row in cursor.fetchall():
                    if row and len(row) > 0:  # Двойная проверка
                        results.add(row[0])

        except Exception as e:
            print(f"Ошибка выполнения запроса: {e}")
            return (0, 0, set())

        return (
            (time.perf_counter() - start_time) * 1000,
            len(results),
            results
        )

    def _get_dataset_size(self):
        with self.db_conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(id) FROM products;")
            return cursor.fetchone()[0]

    def _get_reference_items(self, correct_term):
        with self.db_conn.cursor() as cursor:
            cursor.execute(
                "SELECT name FROM products WHERE name ILIKE %s;",
                ('%' + correct_term + '%',)
            )
            return {row[0] for row in cursor.fetchall() if row}

    def execute_tests(self):
        print("\nЗапуск тестов производительности...")
        data_size = self._get_dataset_size()

        test_scenarios = [
            ('computer', 'copmuter', 'перестановка'),
            ('monitor', 'mointor', 'перестановка'),
            ('keyboard', 'keybord', 'пропуск буквы'),
            ('software', 'sofware', 'пропуск буквы'),
            ('processor', 'processsor', 'добавление буквы'),
            ('adapter', 'adappter', 'добавление буквы'),
            ('mouse', 'mouce', 'замена буквы'),
            ('windows', 'windovs', 'замена буквы')
        ]

        search_methods = {
            'ILIKE': sql.SQL("SELECT name FROM products WHERE name ILIKE '%' || {} || '%'"),
            'Trigram': sql.SQL("SELECT name FROM products WHERE name %% {}"),
            'Levenshtein': sql.SQL("SELECT name FROM products WHERE levenshtein(name, {}) <= 3"),
            'Soundex': sql.SQL("SELECT name FROM products WHERE soundex(name) = soundex({})"),
            'FTS': sql.SQL("SELECT name FROM products WHERE search_vector @@ plainto_tsquery('english', {})")
        }

        for correct, typo, error_type in test_scenarios:
            print(f"\nТестирование: '{typo}' (Ошибка: {error_type})")
            reference = self._get_reference_items(correct)

            if not reference:
                print(f"  Эталонные данные для '{correct}' не найдены")
                continue

            for method_name, query_template in search_methods.items():
                try:
                    compiled_query = query_template.format(sql.Placeholder())
                    duration, count, results = self._execute_search(compiled_query, typo)
                    prec, rec, f1 = self._compute_metrics(results, reference)

                    self._save_results(
                        method=method_name,
                        size=data_size,
                        query=typo,
                        duration=duration,
                        count=count,
                        indexed=method_name in ['Trigram', 'FTS']
                    )

                    print(
                        f"  {method_name:<12} | "
                        f"Время: {duration:>6.1f} мс | "
                        f"Результаты: {count:<3} | "
                        f"Точность: {prec:.2f} | "
                        f"Полнота: {rec:.2f} | "
                        f"F1: {f1:.2f}"
                    )
                except Exception as e:
                    print(f"  Ошибка в методе {method_name}: {e}")

    def close_connection(self):
        if self.db_conn:
            self.db_conn.close()


if __name__ == '__main__':
    tester = SearchPerformanceAnalyzer(DB_CONFIG)
    try:
        tester.execute_tests()
    except Exception as e:
        print(f"Критическая ошибка выполнения тестов: {e}")
    finally:
        tester.close_connection()