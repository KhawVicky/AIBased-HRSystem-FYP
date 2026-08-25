FROM php:8.3-apache

RUN docker-php-ext-install mysqli \
    && (a2dismod mpm_event mpm_worker || true) \
    && a2enmod mpm_prefork headers \
    && apache2ctl configtest

COPY deploy/railway/candidate-api/php.ini /usr/local/etc/php/conf.d/uwc-uploads.ini
COPY deploy/railway/candidate-api/entrypoint.sh /usr/local/bin/uwc-api-entrypoint
COPY server/ /var/www/html/

RUN chmod +x /usr/local/bin/uwc-api-entrypoint \
    && sed -i 's/\r$//' /usr/local/bin/uwc-api-entrypoint \
    && mkdir -p /var/www/html/uploads

ENV API_SURFACE=full
ENV APPLICATION_ANALYSIS_WORKER_ENABLED=false

EXPOSE 80

ENTRYPOINT ["/bin/sh", "/usr/local/bin/uwc-api-entrypoint"]
