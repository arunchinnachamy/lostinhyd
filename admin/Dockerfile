FROM node:20-alpine

WORKDIR /app

# Install dependencies
RUN apk add --no-cache wget

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the React Admin SPA
RUN npm run build

# Expose port
EXPOSE 3001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:3001/health || exit 1

# Start the Express server
CMD ["node", "src/server.js"]
