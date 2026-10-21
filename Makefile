.PHONY: demo ask test compliance

PY ?= python

demo:
	$(PY) -m fitwise.cli size --underbust 78 --bust 90.5

ask:
	$(PY) -m fitwise.cli ask "75C 的姐妹尺码是什么"

test:
	$(PY) -m pytest

compliance:
	$(PY) scripts/compliance_check.py .
