CREATE OR REPLACE FUNCTION analyze_query_plan(query_text TEXT)
RETURNS TABLE(
    node_type TEXT,
    index_name TEXT,
    startup_cost FLOAT,
    total_cost FLOAT,
    rows BIGINT
) AS $$
DECLARE
    plan_json JSON;
    plan_node JSON;
BEGIN
    EXECUTE 'EXPLAIN (FORMAT JSON) ' || query_text INTO plan_json;

    -- Парсинг JSON плана
    FOR plan_node IN SELECT * FROM json_array_elements(plan_json->0->'Plan'->'Plans' || jsonb_build_array(plan_json->0->'Plan'))
    LOOP
        node_type := plan_node->>'Node Type';
        index_name := COALESCE(plan_node->>'Index Name', '');
        startup_cost := (plan_node->>'Startup Cost')::FLOAT;
        total_cost := (plan_node->>'Total Cost')::FLOAT;
        rows := (plan_node->>'Plan Rows')::BIGINT;
        RETURN NEXT;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Функция для расчета метрик точности
CREATE OR REPLACE FUNCTION calculate_metrics(
    relevant_ids ANYARRAY,
    found_ids ANYARRAY
) RETURNS TABLE(
    "precision" FLOAT,
    recall FLOAT,
    f1_score FLOAT
) AS $$
DECLARE
    true_positives INT;
BEGIN
    SELECT COUNT(*) INTO true_positives
    FROM unnest(found_ids) AS f(id)
    WHERE f.id = ANY(relevant_ids);

    "precision" := CASE
        WHEN array_length(found_ids, 1) > 0
        THEN true_positives::FLOAT / array_length(found_ids, 1)
        ELSE 0
    END;

    recall := CASE
        WHEN array_length(relevant_ids, 1) > 0
        THEN true_positives::FLOAT / array_length(relevant_ids, 1)
        ELSE 0
    END;

    f1_score := CASE
        WHEN ("precision" + recall) > 0
        THEN 2 * ("precision" * recall) / ("precision" + recall)
        ELSE 0
    END;

    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;