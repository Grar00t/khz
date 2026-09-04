#!/bin/sh
export PATH=/home/a/.local/bin:/usr/local/bin:/usr/bin:/bin
if curl -sf http://127.0.0.1:8080/health > /dev/null; then
  echo ALIVE
  exit 0
fi
nohup /home/a/.local/bin/llama serve -m /home/a/models/Rawaseeng-14B-Oracle-Q4_K_M.gguf --alias Rawaseeng-14B-Oracle --jinja --chat-template-file /home/a/oracle/oracle.jinja --reasoning-format none -c 8192 -fa on --host 127.0.0.1 --port 8080 > /home/a/oracle/serve.log 2>&1 &
if timeout 240 sh -c 'until curl -sf http://127.0.0.1:8080/health > /dev/null; do sleep 3; done'; then
  echo STARTED
else
  echo TIMEOUT
  tail -6 /home/a/oracle/serve.log
fi
