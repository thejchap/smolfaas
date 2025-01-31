default: brew install check test
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
	@brew install v8 cmake flyctl
	@brew info v8 | grep "stable 12.7" && echo "correct brew version" || echo "incorrect brew version" && exit 1
install:
	@uv sync --reinstall
deploy:
	@fly deploy
