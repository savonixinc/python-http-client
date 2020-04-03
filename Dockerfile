FROM ubuntu:xenial
ENV PYTHON_VERSIONS='python3.7' \
    OAI_SPEC_URL="https://raw.githubusercontent.com/sendgrid/sendgrid-oai/master/oai_stoplight.json"

# install testing versions of python from deadsnakes
RUN set -x \
    && apt-get update \
    && apt-get install -y --no-install-recommends software-properties-common \
    && apt-add-repository -y ppa:fkrull/deadsnakes \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends $PYTHON_VERSIONS \
        curl \
        git \
    && apt-get install -y python3-pip \
    && apt-get purge -y --auto-remove software-properties-common \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /root

# install Prism
ADD https://raw.githubusercontent.com/stoplightio/prism/master/install install.sh
RUN chmod +x ./install.sh && \
    ./install.sh && \
    rm ./install.sh

# set up default Twilio SendGrid env
WORKDIR /root/sources
RUN git clone https://github.com/kur1zu/python-http-client.git && \
    git clone https://github.com/kur1zu/sendgrid-python.git

WORKDIR /root/sources/sendgrid-python
RUN git checkout dev

WORKDIR /root/sources/python-http-client
RUN git checkout dev

WORKDIR /root
RUN python3.7 -m pip install -e "/root/sources/python-http-client[async]"
RUN ln -s /root/sources/sendgrid-python/sendgrid && \
    ln -s /root/sources/python-http-client/python_http_client

COPY . .
CMD sh run.sh
