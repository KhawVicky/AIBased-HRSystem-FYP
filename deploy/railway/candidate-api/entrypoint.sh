#!/bin/sh
set -eu

a2dismod mpm_event mpm_worker >/dev/null 2>&1 || true
a2enmod mpm_prefork >/dev/null
apache2ctl configtest

mkdir -p \
  /var/www/html/uploads/candidate-defaults \
  /var/www/html/uploads/resumes
chown -R www-data:www-data /var/www/html/uploads

analysis_worker_pid=""
if [ "${APPLICATION_ANALYSIS_WORKER_ENABLED:-false}" = "true" ]; then
  if ! command -v php >/dev/null 2>&1; then
    echo "PHP CLI is required for the application analysis worker" >&2
    exit 1
  fi

  (
    while true; do
      if ! php /var/www/html/application_analysis_worker.php --once; then
        echo "Application analysis worker cycle failed; retrying" >&2
      fi
      sleep "${APPLICATION_ANALYSIS_WORKER_POLL_SECONDS:-2}"
    done
  ) &
  analysis_worker_pid=$!
fi

apache2-foreground &
apache_pid=$!
trap 'if [ -n "$analysis_worker_pid" ]; then kill "$analysis_worker_pid" 2>/dev/null || true; fi; kill "$apache_pid" 2>/dev/null || true; exit 143' TERM INT

if wait "$apache_pid"; then
  apache_status=0
else
  apache_status=$?
fi

if [ -n "$analysis_worker_pid" ]; then
  kill "$analysis_worker_pid" 2>/dev/null || true
fi
exit "$apache_status"
