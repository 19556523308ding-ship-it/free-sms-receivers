# 短信渲染服务部署（腾讯云 170.106.38.62）
# 前置：服务器已装 google-chrome（实测 /usr/bin/google-chrome 存在）
set -euo pipefail
BASE=/opt/sms-hub/api
# 优先用同机已上传的 /tmp/api_deploy（scp -r 会多套一层 api/，两种路径都兼容）
if [ -d /tmp/api_deploy/api ]; then
  SRC=/tmp/api_deploy/api
elif [ -d /tmp/api_deploy ]; then
  SRC=/tmp/api_deploy
else
  SRC="$(cd "$(dirname "$0")/.." && pwd)/api"
fi
echo "源码目录: $SRC"

echo "[1/5] 创建目录..."
sudo mkdir -p "$BASE" /opt/sms-hub/logs

echo "[2/5] 复制代码..."
sudo cp "$SRC/reader.js" "$BASE/reader.js"
sudo cp "$SRC/package.json" "$BASE/package.json"

echo "[3/5] 安装依赖（puppeteer-core 复用系统 Chrome，不下载 Chromium）..."
cd "$BASE"
sudo npm install --omit=dev --no-audit --no-fund 2>&1 | tail -3

echo "[4/5] 写入 systemd unit..."
sudo tee /etc/systemd/system/sms-reader.service >/dev/null <<'UNIT'
[Unit]
Description=SMS Hub 短信渲染服务（puppeteer-core + 系统 Chrome）
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/sms-hub/api
ExecStart=/usr/bin/node /opt/sms-hub/api/reader.js
ExecStop=/bin/kill -TERM $MAINPID
Restart=always
RestartSec=5
Environment=NODE_ENV=production
Environment=SMS_READER_PORT=18620
Environment=SMS_READER_BIND=127.0.0.1
Environment=CHROME_PATH=/usr/bin/google-chrome
Environment=NODE_OPTIONS=--max-old-space-size=512
# 资源上限：防止 Chrome 异常膨胀拖垮整机
MemoryMax=1200M
TasksMax=512
StandardOutput=append:/opt/sms-hub/logs/reader.log
StandardError=append:/opt/sms-hub/logs/reader.log

[Install]
WantedBy=multi-user.target
UNIT
sudo systemd-analyze verify /etc/systemd/system/sms-reader.service 2>&1 | grep -i "sms-reader" || true

echo "[5/5] 启动并设置开机自启..."
sudo mkdir -p /opt/sms-hub/logs
sudo systemctl daemon-reload
sudo systemctl enable sms-reader >/dev/null
sudo systemctl restart sms-reader
sleep 6

echo "--- 服务状态 ---"
sudo systemctl is-active sms-reader
curl -s --noproxy '*' http://127.0.0.1:18620/healthz | head -c 400
echo
