.PHONY: target
target:
	$(info ${HELP_MESSAGE})
	@exit 0

.PHONY: init
init:
	pip3 install -r requirements/base.txt -r requirements/dev.txt

.PHONY: test
test: check-format
	pytest --cov awslambdaric --cov-report term-missing --cov-fail-under 90 tests

.PHONY: setup-codebuild-agent
setup-codebuild-agent:
	docker build -t codebuild-agent - < tests/integration/codebuild-local/Dockerfile.agent

.PHONY: test-smoke
test-smoke: setup-codebuild-agent
	CODEBUILD_IMAGE_TAG=codebuild-agent tests/integration/codebuild-local/test_one.sh tests/integration/codebuild/buildspec.os.alpine.1.yml alpine 3.12 3.8

.PHONY: test-integ
test-integ: setup-codebuild-agent
	CODEBUILD_IMAGE_TAG=codebuild-agent tests/integration/codebuild-local/test_all.sh tests/integration/codebuild/.

.PHONY: check-security
check-security:
	bandit -r awslambdaric

.PHONY: format
format:
	black setup.py awslambdaric/ tests/

.PHONY: check-format
check-format:
	black --check setup.py awslambdaric/ tests/

# Command to run everytime you make changes to verify everything works
.PHONY: dev
dev: init test

# Verifications to run before sending a pull request
.PHONY: pr
pr: init check-format check-security dev test-smoke

.PHONY: clean
clean:
	rm -rf dist
	rm -rf awslambdaric.egg-info

.PHONY: build
build: clean
	BUILD=true python3 setup.py sdist

define HELP_MESSAGE

Usage: $ make [TARGETS]

TARGETS
	check-security	Run bandit to find security issues.
	format       	Run black to automatically update your code to match our formatting.
	build       	Builds the package.
	clean       	Cleans the working directory by removing built artifacts.
	dev         	Run all development tests after a change.
	init        	Initialize and install the requirements and dev-requirements for this project.
	pr          	Perform all checks before submitting a Pull Request.
	test        	Run the Unit tests.

endef
