#!/bin/bash
# 接码号码聚合站 —— HTTPS 证书签发
# 前置：sms.jinzhai.icu 的 A 记录已指向本服务器（灰云或橙云均可）
# 执行：签证书 -> 切换 nginx 到 443 正式配置 -> reload -> 自检
set -euo pipefail

DOMAIN=sms.jinzhai.icu
EMAIL=190072239@qq.com
WEBROOT=/var/www/certbot
NGINX_SITE=/etc/nginx/sites-available/sms-hub

echo "[1/4] 签发证书（$DOMAIN）..."
sudo certbot certonly --webroot -w "$WEBROOT" \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos --no-eff-email \
    --keep-until-expiring

echo "[2/4] 切换 nginx 到 443 正式配置..."
sudo cp /opt/sms-hub/scripts/sms-hub.nginx.conf "$NGINX_SITE"

echo "[3/4] 检查配置并 reload..."
sudo nginx -t
sudo systemctl reload nginx
sleep 2

echo "[4/4] 自检..."
echo "--- 证书信息 ---"
sudo certbot certificates 2>/dev/null | grep -A3 "$DOMAIN" | head -6

HTTP=$(curl -sS -o /dev/null -w '%{http_code}' "http://$DOMAIN/" || echo "失败")
HTTPS=$(curl -sS -o /dev/null -w '%{http_code}' "https://$DOMAIN/" || echo "失败")
DATA=$(curl -sS -o /dev/null -w '%{http_code}' "https://$DOMAIN/data/numbers.json" || echo "失败")
echo "http://$DOMAIN/            -> $HTTP  (期望 301)"
echo "https://$DOMAIN/           -> $HTTPS (期望 200)"
echo "https://$DOMAIN/data/...   -> $DATA  (期望 200)"

echo ""
echo "完成。若上面三个值分别为 301 / 200 / 200，即可把 Cloudflare 的灰云切回橙云。"
