checkpoint:
	@git add -A
	@git commit -m "checkpoint $$(date '+%Y-%m-%dT%H:%M:%S%z')"
	@git push

