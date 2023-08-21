.PHONY: all \
		help \
		build \
		up \
		down \
		logs \
		clean \
		reload \
		format \
		lint \
		run \
		bash \

RUN_IN_DEVTOOLS_CONTAINER=docker-compose run --rm -u `id -u`:`id -u` api
RUN_IN_DEVTOOLS_CONTAINER_PYTEST=docker-compose run --rm -u `id -u`:`id -u` -e "TEST_RUNNER=pytest" api

# target: all - Default target. Does nothing.
all:
	@echo "Hello $(LOGNAME), nothing to do by default"
	@echo "Try 'make help'"

# target: help - Display callable targets.
help:
	@egrep "^# target:" [Mm]akefile

# Docker commands
# target: build - build images.
build:
	COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 docker-compose build

# target: up - up services.
up:
	docker-compose up -d

# target: down - destroy services.
down:
	docker-compose down

# target: logs - show logs from services.
logs:
	docker-compose logs -f

# target: clean - remove all dangling images and old volumes data.
clean:
	docker system prune -f

# target: stop - stop some services services.
stop:
	docker-compose stop

# target: reload - restart api service.
reload:
	docker-compose restart api

# Linting and formatting
# target: format - run isort for style formatting on project python code.
format:
	$(RUN_IN_DEVTOOLS_CONTAINER) isort .

# target: lint - run flake8 linter for validation.
lint:
	$(RUN_IN_DEVTOOLS_CONTAINER) flake8 --show-source


# target: bash - run bash in container
bash:
	$(RUN_IN_DEVTOOLS_CONTAINER) bash



