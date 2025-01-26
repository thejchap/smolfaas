default: brew install
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
clean:
	@docker system prune --volumes --force
brew:
	@brew install v8 cmake
install:
	@uv sync --reinstall
