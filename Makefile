

tests:
	pytest

package:
	python setup.py sdist bdist_wheel

push_tags:
	git push --follow-tags