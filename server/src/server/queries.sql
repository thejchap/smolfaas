-- query:begin migrate
PRAGMA foreign_keys = ON;
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
    name;
-- query:end