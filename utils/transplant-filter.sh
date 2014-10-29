#!/bin/sh
set -eux

# This is a hg transplant filter for filtering out unittest changes from within
# the main CPython commits.
# Run like:
# hg transplant -v -s ../cpython.hg --filter utils/transplant-filter.sh 0f1619e539fb:
# If it fails, examine the .rej files and fix the commit up then run
# hg transplant -v -s ../cpython.hg --filter utils/transplant-filter.sh 0f1619e539fb: --continue
# To resume.  If the fixup involves not applying the patch, see
# http://bz.selenic.com/show_bug.cgi?id=4423 for a patch which you can apply
# locally to make 'empty delta' cause a skip rather than an error.
msg_path=$1
patch_path=$2

# Firstly select only unittest changes (and not mock changes)
filterdiff --clean --strip 3 --addprefix=a/unittest2/ -i 'a/Lib/unittest/*' -x 'a/Lib/unittest/mock.py' -x 'a/Lib/unittest/test/testmock/*' $2 > $2.unittest
# Secondly we want to pick up any NEWS entries.
filterdiff --strip 2 --addprefix=a/ -i a/Misc/NEWS $2 > $2.NEWS
cat $2.unittest $2.NEWS > $2
filtered=$(cat $2.unittest)
rm $2.unittest $2.NEWS
set +x
if [ -z "${filtered}" ]; then
  set -x
  # Don't include NEWS entries when there were no unittest changes.
  rm $2
  touch $2
else
  set -x
  cat $1
fi
