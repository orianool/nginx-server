FROM ubuntu:24.04

# Install nginx + openssl, generate a self-signed cert/key,
# then remove openssl and /var/lib/apt/lists/* to keep the image small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx openssl \
    && mkdir -p /etc/nginx/ssl \
    && openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
        -subj "/CN=localhost" \
        -keyout /etc/nginx/ssl/selfsigned.key \
        -out /etc/nginx/ssl/selfsigned.crt \
    && apt-get purge -y --auto-remove openssl \
    && rm -rf /var/lib/apt/lists/* \
    # remove default "welcome" server and free port 80 
    # NEW - combined with previous RUN to create one less layer
    && rm -f /etc/nginx/sites-enabled/default 

# add servers configuration and custom html page
COPY ./servers.conf /etc/nginx/conf.d/servers.conf
COPY ./html/index.html /usr/share/nginx/html/index.html
COPY ./html/custom_501.html /usr/share/nginx/html/custom_501.html

EXPOSE 8080 8081 8443
CMD ["nginx", "-g", "daemon off;"]