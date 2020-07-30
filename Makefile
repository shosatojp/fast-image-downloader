all:
	rm -rf dist/* build/*
	python3 setup.py bdist_wheel
	twine upload --repository pypi dist/*