FROM node:24-bookworm-slim
ENV NODE_ENV=production HEALTH_HOST=0.0.0.0 AUTH_DIR=/app/.data PORT=3000
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY src ./src
RUN mkdir -p .data && chown -R node:node /app
USER node
EXPOSE 3000
CMD ["node", "src/index.js"]
