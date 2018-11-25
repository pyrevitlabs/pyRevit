THISPATH=$(dirname "$0")
rm -rf $THISPATH/../docs/_build
sphinx-build -b html $THISPATH/../docs $THISPATH/../docs/_build