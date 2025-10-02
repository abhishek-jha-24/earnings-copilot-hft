run-api:
	uvicorn apps.api.main:app --reload --port 8000

run-ui:
	streamlit run apps/ui/app.py

init-db:
	python -c "from services.storage import init_db; init_db()"

test:
	pytest -q
