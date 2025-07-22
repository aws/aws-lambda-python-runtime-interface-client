.PHONY: target
target:
	$(info ${HELP_MESSAGE})
	@exit 0

.PHONY: init
init:
	python scripts/dev.py init

.PHONY: test
test:
	python scripts/dev.py test

.PHONY: lint
lint:
	python scripts/dev.py lint

.PHONY: clean
clean:
	python scripts/dev.py clean

.PHONY: build
build: clean
ifeq ($(shell uname),Linux)
	BUILD=true python scripts/dev.py build
else
	python scripts/dev.py build
endif

.PHONY: local-test
local-test:
	python scripts/dev.py local-test

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

define HELP_MESSAGE

Usage: $ make [TARGETS]

TARGETS
	check-security	Run bandit to find security issues.
	format       	Run black to automatically update your code to match formatting.
	build       	Build the package using scripts/dev.py.
	clean       	Cleans the working directory using scripts/dev.py.
	dev         	Run all development tests using scripts/dev.py.
	init        	Install dependencies via scripts/dev.py.
	pr          	Perform all checks before submitting a Pull Request.
	test        	Run unit tests using scripts/dev.py.
	lint        	Run all linters via scripts/dev.py.
	test-smoke  	Run smoke tests inside Docker.
	test-integ  	Run all integration tests.
	local-test		Run the Lambda handler locally using AWS RIE.

endef