#!/bin/bash
# Rebuild the python 3 code from the python 2 sources, and run tests.

set -eu
IFS=$'\n\t'

# These are items in the boto source we want to copy into the build directory, and apply with 2to3.
items=(
    boto
    tests
)

BASE=$(dirname "${BASH_SOURCE[0]}")
BUILD_DIR="${BASE}/build"
SRC_DIR="${BASE}/.."

# Prep build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# If /usr/bin/realpath is installed, we can make the path names more clear.
which realpath >/dev/null && {
    BUILD_DIR=$(realpath "$BUILD_DIR")
    SRC_DIR=$(realpath "$SRC_DIR")
}

echo "Using source directory: $SRC_DIR"
echo "Re-created build directory: $BUILD_DIR"

for item in ${items[@]}; do
    cp -a "${SRC_DIR}/${item}" "${BUILD_DIR}/${item}"
done

echo "Applying 2to3..."
cd "${BUILD_DIR}"

2to3 -n -w . > 2to3.out 2> 2to3.err
# Note that if 2to3 has an error (i.e. exits with a nonzero exit
# code), this script will exit because it uses uses the set -e option
# above. man bash for details.

echo "2to3 successful! Running tests... (with verbose output)"

set -x
python tests/test.py tests/unit

