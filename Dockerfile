FROM ubuntu:24.04

# --no-install-recommends & rm -rf /var/lib/apt/lists/* to reduce the final image size.
# if needed re-run apt-get update in later stages.
RUN apt-get update && apt-get install -y --no-install-recommends nginx ca-certificates \
    && rm -rf /var/lib/apt/lists/* 

# remove default "welcome" server and free port 80 
RUN rm -f /etc/nginx/sites-enabled/default

# add servers configuration and custom html page
COPY ./servers.conf /etc/nginx/conf.d/servers.conf
COPY ./html/index.html /usr/share/nginx/html/index.html
COPY ./html/custom_501.html /usr/share/nginx/html/custom_501.html

EXPOSE 8080 8081
CMD ["nginx", "-g", "daemon off;"]