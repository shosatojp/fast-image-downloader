all:
	rm -rf dist/* build/*
	python3 setup.py bdist_wheel
	twine upload --repository pypi dist/*

clean:
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -r '{}' \;