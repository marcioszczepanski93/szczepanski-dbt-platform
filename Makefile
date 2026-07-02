.PHONY: up down restart logs ps init test dag-test lint fmt fernet dbt-build dbt-docs

# AIRFLOW_UID = UID do host: faz os containers escreverem nos volumes montados
# (logs/, dbt/target) com o dono certo, sem precisar de chmod manual.
export AIRFLOW_UID := $(shell id -u)

up:            ## Sobe a stack (build + detached)
	@mkdir -p logs
	docker compose up -d --build

down:          ## Derruba a stack (mantem os volumes)
	docker compose down

restart:
	docker compose restart airflow-scheduler airflow-dag-processor airflow-apiserver

logs:          ## Segue os logs do scheduler + dag-processor
	docker compose logs -f airflow-scheduler airflow-dag-processor

ps:
	docker compose ps

init:          ## Roda so o init (db migrate + cria admin)
	docker compose up airflow-init

# --entrypoint python pula o entrypoint do Airflow (que faz `airflow db check` e
# exigiria o postgres de metadata). Os testes so importam DAGs/modulos — nao usam o
# banco de metadata — entao rodam sem subir a stack (bom p/ DX e p/ CI).
test:          ## Roda a suite de testes dentro do container (airflow + pandera disponiveis)
	docker compose run --rm --no-deps --entrypoint python airflow-scheduler -m pytest -q

dag-test:      ## So o teste de integridade das DAGs
	docker compose run --rm --no-deps --entrypoint python airflow-scheduler -m pytest -q tests/test_dag_integrity.py

ci-integration: ## Usado pelo CI: build + dbt deps + testes (tudo com AIRFLOW_UID do runner)
	docker compose build airflow-scheduler
	docker compose run --rm --no-deps --entrypoint /opt/airflow/dbt-venv/bin/dbt \
		airflow-scheduler deps --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt
	docker compose run --rm --no-deps --entrypoint python airflow-scheduler -m pytest -q

lint:          ## ruff + mypy
	ruff check . && mypy include src

fmt:           ## Formata e auto-corrige
	ruff format . && ruff check --fix .

fernet:        ## Gera uma AIRFLOW_FERNET_KEY para o .env
	@python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

dbt-build:     ## Roda dbt build no venv isolado do container (warehouse precisa estar de pe)
	docker compose run --rm airflow-scheduler /opt/airflow/dbt-venv/bin/dbt build --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt

dbt-docs:      ## Gera a documentacao dbt
	docker compose run --rm airflow-scheduler /opt/airflow/dbt-venv/bin/dbt docs generate --project-dir /opt/airflow/dbt --profiles-dir /opt/airflow/dbt
