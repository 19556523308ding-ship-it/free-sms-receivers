#!/bin/bash
# SMS Hub V2 部署：本地采集 -> 校验 -> 上传 -> 服务器刷新
set -euo pipefail
PY="python3"
cd /d/workspace/sms-hub 2>/dev/null || cd "$(dirname "$0")/.."

echo "[1/4] 本地采集..."
$PY scrapers/collect.py

echo "[2/4] 校验..."
$PY -c "
import json
d=json.load(open('scrapers/data/numbers.json',encoding='utf-8'))
t=d['totals']
assert t['records']>0 and t['uniquePhones']>0, '号码数为 0'
assert t['records']==len(d['numbers']), '记录数不符'
print('校验通过:',t)
"

echo "[3/4] 同步到 web 目录..."
mkdir -p web/data && cp scrapers/data/numbers.json web/data/numbers.json

echo "[4/4] 上传到服务器..."
scp -i /tmp/fjny.pem -o StrictHostKeyChecking=no web/index.html      ubuntu@170.106.38.62:/tmp/v2_index.html
scp -i /tmp/fjny.pem -o StrictHostKeyChecking=no web/guide.html     ubuntu@170.106.38.62:/tmp/v2_guide.html
scp -i /tmp/fjny.pem -o StrictHostKeyChecking=no web/sources.html   ubuntu@170.106.38.62:/tmp/v2_sources.html
scp -i /tmp/fjny.pem -o StrictHostKeyChecking=no web/sitemap.xml    ubuntu@170.106.38.62:/tmp/v2_sitemap.xml
scp -i /tmp/fjny.pem -o StrictHostKeyChecking=no web/robots.txt     ubuntu@170.106.38.62:/tmp/v2_robots.txt
scp -i /tmp/fjny.pem -o StrictHostKeyChecking=no web/data/numbers.json ubuntu@170.106.38.62:/tmp/v2_numbers.json
scp -i /tmp/fjny.pem -o StrictHostKeyChecking=no scrapers/collect.py   ubuntu@170.106.38.62:/tmp/v2_collect.py

# 官方素材包（brand/backgrounds/icons/sources）整体打包上传
tar -C web -czf /tmp/v2_assets.tgz assets
scp -i /tmp/fjny.pem -o StrictHostKeyChecking=no /tmp/v2_assets.tgz ubuntu@170.106.38.62:/tmp/v2_assets.tgz

ssh -i /tmp/fjny.pem -o StrictHostKeyChecking=no ubuntu@170.106.38.62 "
sudo cp /tmp/v2_index.html   /opt/sms-hub/web/index.html
sudo cp /tmp/v2_guide.html   /opt/sms-hub/web/guide.html
sudo cp /tmp/v2_sources.html /opt/sms-hub/web/sources.html
sudo cp /tmp/v2_sitemap.xml  /opt/sms-hub/web/sitemap.xml
sudo cp /tmp/v2_robots.txt   /opt/sms-hub/web/robots.txt
sudo mkdir -p /opt/sms-hub/web/data
sudo cp /tmp/v2_numbers.json /opt/sms-hub/web/data/numbers.json
sudo cp /tmp/v2_collect.py   /opt/sms-hub/scrapers/collect.py
sudo tar -C /opt/sms-hub/web -xzf /tmp/v2_assets.tgz
sudo chown -R ubuntu:ubuntu /opt/sms-hub
echo '--- 线上自检 ---'
for u in / /guide.html /sources.html /sitemap.xml /robots.txt /data/numbers.json /assets/brand/logo.svg /assets/backgrounds/world-map-bg.svg /assets/sources/quackr.svg; do
  printf '  %-46s -> %s\n' \"\$u\" \"\$(curl -sS -o /dev/null -w '%{http_code}' https://sms.jinzhai.icu\$u)\"
done
"
echo "部署完成"
