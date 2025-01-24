checkpoint:
	@cd .. && $(MAKE) checkpoint
test:
	@uv run pytest tests
format:
	@uv run ruff check . --fix
check:
	@uv run ruff check
	@uv run mypy .
install:
	@uv sync
example-run:
	@uv run client run examples/basic.js
example-deploy:
	@uv run client deploy hello-world examples/basic.js
