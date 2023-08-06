.venv:
	mkdir $@

.PHONY: deps
deps: .venv
	pipenv sync

.PHONY: clean
clean:
	# Remove the build
	sudo rm -rf build dist
	# And all of our pyc files
	find . -name '*.pyc' | xargs -n 100 -r rm {}
	# And lastly, .coverage files
	find . -name .coverage | xargs -r rm

.PHONY: test
test:
	rm -rf .coverage
	pipenv run nosetests --exe --cover-package=qless --with-coverage --cover-branches -v
