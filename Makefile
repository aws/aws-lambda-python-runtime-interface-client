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

.PHONY: test-integ
test-integ:
	@echo "Integration tests run via GitHub Actions (see .github/workflows/test-on-push-and-pr.yml)"
	@echo "To run a single combo locally:"
	@echo "  make test-integ-local DISTRO=alpine DISTRO_VERSION=3.20 RUNTIME_VERSION=3.13"

.PHONY: test-integ-local
test-integ-local:
	tests/integration/run-local.sh $(DISTRO) $(DISTRO_VERSION) $(RUNTIME_VERSION)

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
pr: init check-format check-security dev

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
