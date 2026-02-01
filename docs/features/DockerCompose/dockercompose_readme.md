## Purpose

This file defines and manages multi-container Docker applications. It specifies services, networks, and volumes so you can run your entire stack with a single command.

## Usage

1. Ensure Docker and Docker Compose are installed.
2. Place the `docker-compose.yml` file in your project root.
3. Run:
    
    `docker-compose up -d`
    
    for executing after changes in the code run:
    
    `docker-compose up -d —build`
    
    This starts all services in detached mode.
    
4. To stop services:
    
    `docker-compose down`
    

## Structure

A typical `docker-compose.yml` file contains:

`version: "3.9"

services:
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: mydb
    volumes:
      - db_data:/var/lib/postgresql/data

volumes:
  db_data:`

### Sections

- **version**: Compose file format version.
- **services**: Defines containers (e.g., `web`, `db`).
- **volumes**: Persistent storage for data.
- **networks** (optional): Custom networking between services.

## Common Commands

- `docker-compose ps` → List running services.
- `docker-compose logs -f` → Stream logs.
- `docker-compose exec -it <service> bash` → Open shell inside a container.