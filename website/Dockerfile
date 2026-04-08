FROM node:20-alpine

WORKDIR /app

# Install dependencies for build
RUN apk add --no-cache wget

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Expose port
EXPOSE 3000

# Health check endpoint will be handled by Astro
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:3000/health || exit 1

# Start the server
ENV HOST=0.0.0.0 PORT=3000
CMD ["node", "./dist/server/entry.mjs"]
