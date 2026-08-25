#!/bin/sh
set -eu

a2dismod mpm_event mpm_worker >/dev/null 2>&1 || true
a2enmod mpm_prefork >/dev/null
apache2ctl configtest

mkdir -p \
  /var/www/html/uploads/candidate-defaults \
  /var/www/html/uploads/resumes
chown -R www-data:www-data /var/www/html/uploads

exec apache2-foreground
