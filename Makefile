.PHONY: up down restart logs check test backend frontend backup restore secret

up:
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=200

check:
	./scripts/check.sh

test:
	cd backend && pytest -q

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev -- --host 0.0.0.0

backup:
	./scripts/backup.sh

restore:
	@test -n "$(FILE)" || (echo "Usage: make restore FILE=backups/xxx.dump" && exit 2)
	RESTORE_CONFIRM=YES ./scripts/restore.sh "$(FILE)"

secret:
	./scripts/generate-secret.sh
