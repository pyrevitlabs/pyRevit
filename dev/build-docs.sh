THISPATH=$(dirname "$0")
if [ "-r" = $1 ]; then
    rm -rf $THISPATH/../docs/_build
fi
sphinx-build -b html $THISPATH/../docs $THISPATH/../docs/_build