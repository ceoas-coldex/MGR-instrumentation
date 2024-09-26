#!/bin/sh
cd C:\\Users\\ceoas_coldex\\Documents\\GitHub\\MGR-instrumentation
git add --all
timestamp() {
  date +"at %H:%M:%S on %d/%m/%Y"
}
git commit -m "Regular auto-commit $(timestamp)"
git push origin main