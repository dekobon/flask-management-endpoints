#!/usr/bin/env bash

python3 -m build --sdist
python3 -m build --wheel

# To upload
# twine upload dist/*