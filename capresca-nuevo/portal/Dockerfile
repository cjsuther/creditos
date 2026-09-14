# Dockerfile de desarrollo del portal.
# Reutiliza la imagen del frontend como base: ya trae node + node_modules con los MISMOS
# paquetes (react, react-dom, vite, @vitejs/plugin-react, typescript, @types). Así el portal
# levanta sin pull del registry ni npm install (el node_modules llega por el volumen anónimo).
FROM capresca-nuevo-frontend:latest

WORKDIR /app
COPY . .

EXPOSE 5174
ENV VITE_API_TARGET=http://backend:8000
CMD ["npm", "run", "dev"]
