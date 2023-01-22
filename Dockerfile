FROM python:alpine

# Set the config file location
ENV WOL_CONFIG_DIR=/wol_config


COPY wol.py /
ENTRYPOINT ["/wol.py"]

# Labels
LABEL org.opencontainers.image.url=https://github.com/bentasker/Wake-On-Lan-Python/
LABEL org.opencontainers.image.licenses=PSF-2.0
LABEL org.opencontainers.image.title="Wake On LAN utility"
