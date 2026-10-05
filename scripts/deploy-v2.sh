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
  index.html numbers.html number.html country.html admin.html guide.html faq.html 404.html \
  sitemap.xml robots.txt favicon.ico assets data country en
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
         /assets/app.css /assets/app.js /assets/brand/favicon.svg /favicon.ico /data/numbers.json /sitemap.xml /robots.txt /404.html; do
  printf "  %-32s -> %s\n" "$u" "$(curl -sS -o /dev/null -w "%{http_code}" https://sms.jinzhai.icu$u)"
done
echo "--- 干净 URL 检查 ---"
curl -sS -o /dev/null -w "  /numbers      -> %{http_code}\n" https://sms.jinzhai.icu/numbers
echo "--- SEO 静态国家页（必须 200 且源码含 H1）---"
for iso in us gb ua de; do
  CODE=$(curl -sS -o /tmp/cp_$iso.html -w "%{http_code}" https://sms.jinzhai.icu/country/$iso)
  H1=$(grep -o "<h1>[^<]*</h1>" /tmp/cp_$iso.html | head -1)
  SZ=$(wc -c < /tmp/cp_$iso.html)
  printf "  /country/%-3s -> %s  size=%sB  %s\n" "$iso" "$CODE" "$SZ" "$H1"
done
echo "--- 英文版（/en/ 全部必须 200，且源码含英文正文）---"
for u in /en/ /en/numbers /en/guide /en/faq /en/country /en/number \
         /en/country/us /en/country/gb /en/country/de \
         /en/assets/app.css /en/assets/app.js /en/assets/i18n.js; do
  CODE=$(curl -sS -o /dev/null -w "%{http_code}" "https://sms.jinzhai.icu$u")
  printf "  %-24s -> %s\n" "$u" "$CODE"
done
echo "--- 英文页 Googlebot 视角（源码必须含英文 H1，无需 JS）---"
for iso in us gb de; do
  curl -sS -A "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" \
    -o /tmp/en_$iso.html "https://sms.jinzhai.icu/en/country/$iso"
  H1=$(grep -o "<h1[^>]*>[^<]*</h1>" /tmp/en_$iso.html | head -1)
  HL=$(grep -c 'hreflang=' /tmp/en_$iso.html)
  SZ=$(wc -c < /tmp/en_$iso.html)
  printf "  /en/country/%-3s size=%sB  hreflang=%s  %s\n" "$iso" "$SZ" "$HL" "$H1"
done
echo "--- 中文国家页 hreflang 双向配对抽查 ---"
curl -sS -o /tmp/zh_us.html https://sms.jinzhai.icu/country/us
grep -o '<link rel="alternate"[^>]*>' /tmp/zh_us.html | sed 's/^/  /'
'
echo "部署完成"
