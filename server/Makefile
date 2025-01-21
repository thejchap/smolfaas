checkpoint:
	@cd .. && $(MAKE) checkpoint
dev:
	@uv run fastapi dev src/server
test:
	@uv run pytest tests
format:
	@uv run ruff check . --fix
check:
	@uv run ruff check
	@uv run mypy .
docker:
	@docker compose up --build
install:
	@brew install v8
	@uv sync --reinstall
