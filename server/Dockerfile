FROM php:8.3-apache

RUN docker-php-ext-install mysqli \
    && (a2dismod mpm_event mpm_worker || true) \
    && a2enmod mpm_prefork headers \
    && apache2ctl configtest

RUN printf '%s\n' \
      'upload_max_filesize=10M' \
      'post_max_size=32M' \
      'memory_limit=256M' \
      '; Submission orchestration can run parser and scoring sequentially after the application/resume have already been persisted.' \
      'max_execution_time=420' \
    > /usr/local/etc/php/conf.d/uwc-uploads.ini

COPY entrypoint.sh /usr/local/bin/uwc-api-entrypoint
COPY . /var/www/html/

RUN chmod +x /usr/local/bin/uwc-api-entrypoint \
    && mkdir -p /var/www/html/uploads

ENV API_SURFACE=candidate

EXPOSE 80

ENTRYPOINT ["uwc-api-entrypoint"]
