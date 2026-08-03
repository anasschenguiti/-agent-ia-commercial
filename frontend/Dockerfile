# Dockerfile — Frontend Next.js
FROM node:20-alpine

WORKDIR /app

# Installe les dépendances npm
COPY package*.json ./
RUN npm install --legacy-peer-deps

# Copie le reste du code frontend
COPY . .

# Build Next.js
RUN npm run build

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["npm", "run", "start"]
