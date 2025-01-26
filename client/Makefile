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
example-invoke:
	@uv run client invoke examples/basic.js
example-function-invoke:
	@uv run client functions invoke hello-world
example-function-deploy:
	@uv run client functions deploy hello-world examples/basic.js
