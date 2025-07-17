.PHONY: target
target:
	$(info ${HELP_MESSAGE})
	@exit 0

.PHONY: init
init:
	poetry install

.PHONY: test
test: check-format
	poetry run pytest --cov awslambdaric --cov-report term-missing --cov-fail-under 90 tests

.PHONY: setup-codebuild-agent
setup-codebuild-agent:
	docker build -t codebuild-agent - < tests/integration/codebuild-local/Dockerfile.agent

.PHONY: test-smoke
test-smoke: setup-codebuild-agent
	CODEBUILD_IMAGE_TAG=codebuild-agent tests/integration/codebuild-local/test_one.sh tests/integration/codebuild/buildspec.os.alpine.yml alpine 3.15 3.9

.PHONY: test-integ
test-integ: setup-codebuild-agent
	CODEBUILD_IMAGE_TAG=codebuild-agent DISTRO="$(DISTRO)" tests/integration/codebuild-local/test_all.sh tests/integration/codebuild/.

.PHONY: check-security
check-security:
	poetry run bandit -r awslambdaric

.PHONY: format
format:
	poetry run black awslambdaric/ tests/

.PHONY: check-format
check-format:
	poetry run black --check awslambdaric/ tests/

.PHONY: dev
dev: init test

.PHONY: pr
pr: init check-format check-security dev

.PHONY: codebuild
codebuild: setup-codebuild-agent
	CODEBUILD_IMAGE_TAG=codebuild-agent DISTRO="$(DISTRO)" tests/integration/codebuild-local/test_all.sh tests/integration/codebuild

.PHONY: clean
clean:
	rm -rf dist
	rm -rf awslambdaric.egg-info
	find . -type d -name "__pycache__" -exec rm -r {} +

.PHONY: build
build: clean
	poetry build

define HELP_MESSAGE

Usage: $ make [TARGETS]

TARGETS
	check-security	Run bandit to find security issues.
	format       	Run black to automatically update your code to match formatting.
	build       	Builds the package with poetry.
	clean       	Cleans the working directory by removing built artifacts.
	dev         	Run all development tests after a change.
	init        	Install dependencies via Poetry.
	pr          	Perform all checks before submitting a Pull Request.
	test        	Run the unit tests.
	test-smoke  	Run smoke tests inside Docker.
	test-integ  	Run all integration tests.

endef
