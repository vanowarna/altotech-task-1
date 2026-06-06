FROM nginx:1.25-alpine
COPY services/dashboard/nginx.conf /etc/nginx/conf.d/default.conf
COPY services/dashboard/index.html /usr/share/nginx/html/index.html
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=4s --retries=5 \
  CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1
