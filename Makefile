test:
	coverage run --include='gcp_doctor/*' -m pytest

coverage-report:
	coverage report -m
