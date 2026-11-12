FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
COPY vendor /usr/share/nginx/html/vendor
COPY config /usr/share/nginx/html/config
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
