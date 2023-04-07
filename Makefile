.venv:
	mkdir $@

.PHONY: deps
deps: .venv
	pipenv sync --dev

.PHONY: clean
clean:
	# Remove the build
	rm -rf build dist
	# And all of our pyc files
	find . -path ./.venv -prune -o -name '*.pyc' -print | xargs -n 100 -r rm
	# And lastly, .coverage files
	find . -path ./.venv -prune -o -name .coverage -print | xargs -r rm

.PHONY: test
test:
	rm -rf .coverage
	pipenv run coverage run --branch --source=qless -m unittest discover -s test -t test -v
