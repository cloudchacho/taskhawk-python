PROJECT:=taskhawk-python
DATE:=$(shell date +"%Y.%m.%d.%H.%M.%S")
TENDRIL_PREFIX='/usr/local/tendril/tendril'
NEEDS_DATABASE=True
MAIN_APP:=${PROJECT}
APP_TYPE:=python-lib
AUTO_VERSION:=false
PYTHON_VERSION:=3.6.4

export PROJECT
export DATE
export TENDRIL_PREFIX
export NEEDS_DATABASE
export MAIN_APP
export APP_TYPE
export AUTO_VERSION
export PYTHON_VERSION

.PHONY: test update_deps

test_setup: update_deps
	echo "don't need test setup"

test: clean test_setup
	./scripts/run-tests.sh

update_deps:
	./scripts/update-deps.sh

jenkins_diff_setup: update_deps
	./scripts/jenkins/diff-git-setup.sh

jenkins_diff_build: jenkins_diff_setup
	./scripts/jenkins/diff-build.sh

jenkins_ci_setup: test_setup
	./scripts/jenkins/ci-git-setup.sh

jenkins_ci_build: jenkins_ci_setup
	./scripts/jenkins/ci-build.sh

jenkins_ci_condition:
	./scripts/jenkins/ci-condition.py

jenkins_release_setup: clean
	git clean -ffdx

jenkins_release: jenkins_release_setup update_deps
	./scripts/jenkins/release.sh

clean:
	rm -rf usr/ etc/ *.deb build dist
	find . -name "*.pyc" -delete
