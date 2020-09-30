#======================================================================
# Copyright (c) 2020, Arm Limited. All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
#======================================================================

#======================================================================
# FILE: Dockerfile
#
# DESCRIPTION: This is used for containerised deployment of the quality
#  metrics broker component.
#======================================================================

FROM alpine:3.11

RUN apk update && \
    apk upgrade && \
    apk add --no-cache python3-dev && \
    pip3 install --upgrade pip

WORKDIR /metrics_server
COPY . /metrics_server

RUN pip3 --no-cache-dir install -r requirements.txt

EXPOSE 5000

CMD python3 quality_metrics_server.py
