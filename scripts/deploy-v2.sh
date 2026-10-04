#!/bin/bash
# SMS Hub 2.0 部署（腾讯云美国 170.106.38.62）
# 上传静态站点 + 采集器 + nginx 配置，并做线上自检
set -euo pipefail
cd /d/workspace/sms-hub 2>/dev/null || cd "$(dirname "$0")/.."

KEY="${KEY:-/tmp/fjny.pem}"
HOST="${HOST:-ubuntu@170.106.38.62}"
SSH="ssh -i $KEY -o StrictHostKeyChecking=no"
SCP="scp -i $KEY -o StrictHostKeyChecking=no"

echo "[1/4] 打包前端..."
tar -C web -czf /tmp/smshub-web.tgz \
  index.html numbers.html number.html country.html admin.html guide.html faq.html \
  sitemap.xml robots.txt favicon.ico assets data
ls -lh /tmp/smshub-web.tgz

echo "[2/4] 上传..."
$SCP /tmp/smshub-web.tgz "$HOST:/tmp/smshub-web.tgz"
$SCP scrapers/collect.py "$HOST:/tmp/v2_collect.py"
$SCP scrapers/probe_numbers.py "$HOST:/tmp/v2_probe_numbers.py"
$SCP scripts/sms-hub.nginx.conf "$HOST:/tmp/smshub.nginx.conf"

echo "[3/4] 应用..."
$SSH "$HOST" '
set -e
sudo mkdir -p /opt/sms-hub/web
sudo tar -C /opt/sms-hub/web -xzf /tmp/smshub-web.tgz
sudo cp /tmp/v2_collect.py /opt/sms-hub/scrapers/collect.py
sudo cp /tmp/v2_probe_numbers.py /opt/sms-hub/scrapers/probe_numbers.py
sudo cp /tmp/smshub.nginx.conf /etc/nginx/sites-available/sms-hub
sudo chown -R ubuntu:ubuntu /opt/sms-hub
sudo nginx -t && sudo systemctl reload nginx
echo "--- nginx reloaded ---"
'

echo "[4/4] 线上自检..."
$SSH "$HOST" '
for u in / /index.html /numbers /numbers.html /number.html /country.html /admin.html /guide.html /faq.html \
         /assets/app.css /assets/app.js /assets/brand/favicon.svg /favicon.ico /data/numbers.json /sitemap.xml /robots.txt; do
  printf "  %-32s -> %s\n" "$u" "$(curl -sS -o /dev/null -w "%{http_code}" https://sms.jinzhai.icu$u)"
done
echo "--- 干净 URL 检查 ---"
curl -sS -o /dev/null -w "  /numbers      -> %{http_code}\n" https://sms.jinzhai.icu/numbers
curl -sS -o /dev/null -w "  /country/us   -> %{http_code}\n" https://sms.jinzhai.icu/country/us
'
echo "部署完成"
