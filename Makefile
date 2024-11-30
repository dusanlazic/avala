.PHONY: check

PY_PROJECTS = server client shared

check-python:
	@for dir in $(PY_PROJECTS); do \
		echo "Running make check in $$dir"; \
		$(MAKE) -C $$dir check || exit 1; \
	done
