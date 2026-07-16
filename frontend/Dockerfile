# 前端镜像：Node 构建 + Nginx 托管
# 构建（在 frontend 目录）：docker build -t legal-rag-frontend .
FROM node:24-alpine AS build

# 国内网络可取消注释使用 npmmirror 加速
# RUN npm config set registry https://registry.npmmirror.com

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
