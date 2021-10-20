FROM klakegg/hugo:0.88.0-ext-alpine

RUN apk add --no-cache git

RUN mkdir -p /themes && \
    cd /themes && \
    git clone -n https://github.com/google/docsy.git && \
    cd docsy && \
    git checkout f8d5a5e && \
    git submodule update --init && \
    rm -rf userguide && \
    find . -name .git -print0 | xargs -0 rm -rf

ENTRYPOINT
