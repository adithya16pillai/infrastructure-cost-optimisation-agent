# Dev-mode container: runs the Vite dev server with the /api proxy so the whole
# stack works with `docker compose up` and no build step.
FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
