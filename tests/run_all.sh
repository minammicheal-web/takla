#!/bin/sh
# Runs every headless-Chrome test against ../index.html. Needs python3 + playwright and Google Chrome at /usr/bin/google-chrome.
# Screenshots go to $SHOTS (default /tmp/shots). The sync tests talk to a local fake Firebase on port 8765.
cd "$(dirname "$0")"
python3 mock_firebase.py >/tmp/mock_firebase.log 2>&1 & MOCK=$!
sleep 1
for t in pharmacy_units core payments_reset v7_features customers_layout language activities home invoices exchange sync_basic sync_customers sync_photos; do
  echo "== $t"; python3 $t.py 2>&1 | grep -iE "err|fail|traceback|assert|left visible" | head -8
done
kill $MOCK
