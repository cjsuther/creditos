# Dockerfile de desarrollo (Vite dev server con proxy a la API).
FROM node:20-alpine

WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .

EXPOSE 5173
ENV VITE_API_TARGET=http://backend:8000
CMD ["npm", "run", "dev"]
