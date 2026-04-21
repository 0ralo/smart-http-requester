create table roles
(
    id          serial
        primary key,
    title       text,
    permissions integer
);

create table users
(
    id            serial
        primary key,
    username      varchar(50) not null
        unique,
    password_hash bytea       not null,
    role_id       integer
        references roles
);

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INT REFERENCES users(id),
    url TEXT NOT NULL,
    method VARCHAR(10) DEFAULT 'GET',
    headers JSONB,
    body TEXT,
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, done, failed
    attempt_count INT DEFAULT 0,
    max_attempts INT DEFAULT 3,
    result JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);