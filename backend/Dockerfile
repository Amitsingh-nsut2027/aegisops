FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY simulator.py incidents.py database.py persist_incidents.py alembic.ini ./
COPY queue_transport.py queue_worker.py queue_demo.py event_schema.py ./
COPY api.py api_schemas.py event_repository.py setup_api_role.py ./
COPY auth.py auth_cli.py ./
COPY llm_provider.py llm_demo.py ./
COPY bedrock_provider.py ./
COPY usage_accounting.py ./
COPY investigator.py investigator_cli.py ./
COPY run_repository.py ./
COPY evidence.py ./
COPY runbooks.py ./
COPY runbooks ./runbooks
COPY migrations ./migrations
USER 10001:10001
CMD ["python", "persist_incidents.py"]
