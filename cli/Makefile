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
	@uv run cli invoke examples/basic.js
example-function-invoke:
	@uv run cli functions invoke hello-world
example-function-deploy:
	@uv run cli functions deploy hello-world examples/basic.js
