-- TenderGuard Database Schema
-- Run this in PostgreSQL after creating the 'tenderguard' database

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rfp_filename VARCHAR(255),
    rfp_text TEXT,
    proposal_filename VARCHAR(255),
    proposal_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE requirements (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    requirement_id VARCHAR(50),
    text TEXT NOT NULL,
    category VARCHAR(255),
    confidence FLOAT,
    keywords_found TEXT,
    status VARCHAR(50),
    matched_proposal_text TEXT,
    match_confidence FLOAT,
    validation_status VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_requirements_project_id ON requirements(project_id);
