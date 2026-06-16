import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.96.254.198', port=22, username='root', password='Hjz20050623', timeout=30)


def run(cmd, timeout=60):
    print(f'>>> {cmd}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out)
    if err:
        print(f'ERR: {err}')


sftp = ssh.open_sftp()

# 1. Fix .env - change IP to localhost
env_lines = [
    "DATABASE_URL=mysql+pymysql://root:***@localhost:3306/resume_db?charset=utf8mb4",
    "DEEPSEEK_API_KEY=***",
    "DEEPSEEK_BASE_URL=https://api.deepseek.com",
    "MODEL_NAME=deepseek-chat",
]
with sftp.open('/root/ai-resume-optimizer/.env', 'w') as f:
    f.write('\n'.join(env_lines) + '\n')
print('[OK] .env updated (IP -> localhost)')

# 2. Write docker-compose.yml with network_mode: host
compose_lines = [
    "services:",
    "  web:",
    "    build: .",
    "    container_name: resume_backend",
    "    restart: always",
    "    network_mode: host",
    "    env_file:",
    "      - .env",
    "    volumes:",
    "      - .:/app",
]
with sftp.open('/root/ai-resume-optimizer/docker-compose.yml', 'w') as f:
    f.write('\n'.join(compose_lines) + '\n')
print('[OK] docker-compose.yml updated (network_mode: host)')

sftp.close()

# 3. Restart
print('\n========== RESTART ==========')
run('cd /root/ai-resume-optimizer && docker compose down && docker compose up -d 2>&1')

time.sleep(5)

# 4. Check logs
print('\n========== LOGS ==========')
run('docker logs resume_backend 2>&1')

# 5. Test API
print('\n========== TEST ==========')
run('curl -s http://localhost:8000/history')
run('curl -s -o /dev/null -w "HTTP_CODE:%{http_code}" http://localhost:8000/')

ssh.close()
print('\n[DONE]')
