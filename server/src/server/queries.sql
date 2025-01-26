-- query:begin migrate
CREATE TABLE IF NOT EXISTS function (
    id CHAR(29) PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    live_deployment_id TEXT REFERENCES deployment (id) ON DELETE
    SET NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS deployment (
    id CHAR(29) PRIMARY KEY,
    function_id TEXT REFERENCES function (id) ON DELETE CASCADE NOT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);
-- query:end
-- query:begin create_function
INSERT INTO function (id, name)
VALUES (?, ?)
RETURNING id,
    name,
    created_at,
    updated_at;
-- query:end
-- query:begin foreign_keys_on
PRAGMA foreign_keys = ON;
-- query:end
-- query:begin create_deployment
INSERT INTO deployment (id, function_id, source)
VALUES (?, ?, ?)
RETURNING id,
    function_id,
    source;
-- query:end
-- query:begin update_live_deployment
UPDATE function
SET live_deployment_id = ?,
    updated_at = CURRENT_TIMESTAMP
WHERE id = ?;
-- query:end
-- query:begin get_live_deployment_for_function
SELECT dp.id AS deployment_id,
    function_id,
    source
FROM deployment dp
    JOIN function fn ON dp.function_id = fn.id
    AND fn.live_deployment_id = dp.id
WHERE fn.id = ?
LIMIT 1;
-- query:end
-- query:begin get_function
SELECT id,
    name,
    live_deployment_id,
    created_at,
    updated_at
FROM function
WHERE id = ?
LIMIT 1;
-- query:end
