#!/bin/sh

# This script automates and standardizes how the linters are executed on the code base.
# Linter SETTINGS live in the linters' config files (pyproject.toml for Pylint, setup.cfg for
# Pycodestyle); this script only decides WHICH linters run and on WHAT.
# This script will execute all linters regardless of how many fail.
#
# Usage (from anywhere in the repo):
#   ./scripts/run_linters.sh
#
# This script uses the following exit codes:
#   0 on success
#   1 if any linter exits with a non-zero value or an expected directory is missing


# GLOBAL VARIABLES
EXIT_CODE=0                                # Value to exit with
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)  # Directory containing this script
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)    # Repo root: where the config files live
LINT_DIRS="src tools"                      # Directories to lint (add "test" once it exists)


# FUNCTIONS
# Verify every directory in LINT_DIRS exists.  A missing directory is a failure, not a skip, so a
# renamed or deleted directory can't silently drop out of linting.
check_lint_dirs()
{
    for LINT_DIR in $LINT_DIRS
    do
        if [ ! -d "$LINT_DIR" ]
        then
            echo "*** Missing lint directory: $LINT_DIR ***"
            EXIT_CODE=1
        fi
    done
}

# Run one linter.  Arguments: the linter's display name, then the command to run.
run_linter()
{
    LINTER_NAME=$1
    shift
    echo "Running $LINTER_NAME"
    "$@"
    if [ $? -ne 0 ]
    then
        echo "*** $LINTER_NAME Failed ***"
        EXIT_CODE=1
    fi
    echo ""
}


# SETUP
# Run from the repo root so the linters find their config files no matter where this was called
cd "$REPO_ROOT" || exit 1
check_lint_dirs

# LINTER COMMANDS
# LINT_DIRS is intentionally unquoted below so each directory becomes its own argument
# 1. Pycodestyle
run_linter "Pycodestyle" python3 -m pycodestyle $LINT_DIRS
# 2. Pylint
run_linter "Pylint" python3 -m pylint $LINT_DIRS

# DONE
if [ $EXIT_CODE -ne 0 ]
then
    echo "*** A Linter Failed ***"
fi
exit $EXIT_CODE
