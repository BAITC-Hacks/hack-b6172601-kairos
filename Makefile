.PHONY: install key seed run docker test smoke check commit lock

install:
	python3 -m venv .venv
	@if [ -s requirements.lock.txt ]; then \
		.venv/bin/pip install -r requirements.lock.txt; \
	else \
		.venv/bin/pip install -r requirements.txt; \
	fi

lock:
	.venv/bin/pip freeze > requirements.lock.txt
	@echo "Wrote requirements.lock.txt - commit it."

key:
	bash scripts/setup_key.sh

seed:
	python3 scripts/seed_data.py

run:
	uvicorn app.main:app --reload --port 8000

docker:
	docker compose up --build

test:
	pytest -q

smoke:
	bash scripts/smoke_test.sh

check:
	bash scripts/check_language.sh

commit:
	bash scripts/hourly_commit.sh
