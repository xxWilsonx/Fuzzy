import psycopg2
import secrets
import uuid
from random import choice, randint, random
from faker import Faker
from psycopg2.extras import execute_values

# Параметры подключения к PostgreSQL
CONFIG = {
    'database': 'fuzzy_search_lab',
    'user': 'postgres',
    'password': '7842590Ff',
    'address': 'localhost',
    'port': 5432
}

# Глобальные константы
PRODUCT_CATEGORIES = ['Gadgets', 'Apparel', 'Products', 'Books', 'Sport', 'Household', 'Playthings']
MANUFACTURERS = ['CircuitInnovate', 'UrbanThreadsCo', 'FreshHarvestGoods', 'InkwellPublishers', 'TitanActive', 'HearthCrafters', 'DreamPlayLabs']
SEARCH_TERMS = ['computer', 'monitor', 'keyboard', 'software', 'processor', 'adapter', 'mouse', 'windows']
RECORD_COUNT = 5000


def modify_text(input_str: str) -> str:
    """Вносит случайные изменения в строку для имитации опечаток"""
    if len(input_str) < 3:
        return input_str

    operations = {
        'transpose': lambda s, i: s[:i] + s[i + 1] + s[i] + s[i + 2:],
        'remove': lambda s, i: s[:i] + s[i + 1:],
        'add': lambda s, i: s[:i] + secrets.choice('abcdefghijklmnopqrstuvwxyz') + s[i:],
        'replace': lambda s, i: s[:i] + secrets.choice('abcdefghijklmnopqrstuvwxyz') + s[i + 1:]
    }

    operation = choice(list(operations.keys()))
    position = randint(0, len(input_str) - 2 if operation == 'transpose' else len(input_str) - 1)
    return operations[operation](input_str, position)


def create_product_records(quantity: int) -> list[tuple]:
    """Генерирует список продуктов со случайными данными"""
    dataset = []
    term_count = len(SEARCH_TERMS)

    for idx in range(quantity):
        term = SEARCH_TERMS[idx % term_count]
        company = choice(MANUFACTURERS)
        code = uuid.uuid4().hex[:6].upper()

        product_name = f"{company} {term.title()} {fake.word().title()} {code}"

        # Добавляем опечатки в 15% случаев
        if random() < 0.15:
            modified_term = modify_text(term)
            product_name = product_name.lower().replace(term, modified_term)

        dataset.append((
            product_name,
            f"Описание товара: {product_name}",
            choice(PRODUCT_CATEGORIES),
            company,
            f"ID-{uuid.uuid4().hex[:8]}"
        ))

    return dataset


def save_to_database(connection, records: list[tuple]):
    """Сохраняет сгенерированные данные в базу"""
    with connection.cursor() as cursor:
        insert_command = """
                         INSERT INTO products
                             (name, description, category, brand, sku)
                         VALUES %s \
                         """
        execute_values(cursor, insert_command, records)
        connection.commit()
        print(f"Добавлено записей: {len(records)}")


def initialize_database():
    """Основная функция инициализации данных"""
    db_conn = None
    try:
        db_conn = psycopg2.connect(
            dbname=CONFIG['database'],
            user=CONFIG['user'],
            password=CONFIG['password'],
            host=CONFIG['address'],
            port=CONFIG['port']
        )

        # Очистка существующих данных
        with db_conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE products RESTART IDENTITY;")
            db_conn.commit()

        # Генерация и сохранение данных
        print(f"Создание {RECORD_COUNT} товарных позиций...")
        product_data = create_product_records(RECORD_COUNT)
        save_to_database(db_conn, product_data)

    except Exception as error:
        print(f"Ошибка при работе с БД: {error}")
    finally:
        if db_conn:
            db_conn.close()
            print("Соединение с базой данных закрыто.")


if __name__ == "__main__":
    fake = Faker('ru_RU')
    initialize_database()