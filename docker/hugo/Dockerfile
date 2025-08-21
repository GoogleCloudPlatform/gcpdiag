# Use the official extended Hugo image. The versioned tag provides the extended build.
FROM ghcr.io/gohugoio/hugo:v0.148.2

# Switch to the root user to install global npm packages.
USER root

# Install postcss-cli and autoprefixer globally.
# These are required by the docsy theme for processing CSS.
RUN npm install -g postcss-cli autoprefixer

# Set the NODE_PATH environment variable so that Hugo's PostCSS processor
# can find the globally installed modules.
ENV NODE_PATH=/usr/local/lib/node_modules

# Switch back to the default, non-privileged hugo user.
USER hugo

# Set the working directory to /src, where the website source will be mounted.
WORKDIR /src
