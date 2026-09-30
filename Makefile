up: ; cp -n .env.example .env; docker compose up -d
down: ; docker compose down
reset: ; docker compose down -v
ps: ; docker compose ps
