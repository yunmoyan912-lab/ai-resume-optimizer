import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.96.254.198', port=22, username='root', password='Hjz20050623', timeout=30)

# Stop the current container
def run(cmd, timeout=60):
    print(f'>>> {cmd}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out)
    if err:
        print(f'ERR: {err}')

# 1. Check if anything is using port 80
print('========== Checking Port 80 ==========')
run('ss -tlnp | grep ":80 "')

# 2. Stop container, change to port 80
print('\n========== Stopping Container ==========')
run('cd /root/ai-resume-optimizer && docker compose down 2>&1')

# 3. Update main.py CMD to use port 80
print('\n========== Updating Dockerfile to Port 80 ==========')
sftp = ssh.open_sftp()

# Read current Dockerfile
with sftp.open('/root/ai-resume-optimizer/Dockerfile', 'r') as f:
    df = f.read().decode()
print('Current Dockerfile:')
print(df)

# Update port 8000 -> 80
new_df = df.replace('--port 8000', '--port 80').replace('EXPOSE 8000', 'EXPOSE 80')
with sftp.open('/root/ai-resume-optimizer/Dockerfile', 'w') as f:
    f.write(new_df)
print('\nUpdated Dockerfile:')
print(new_df)

sftp.close()

# 4. Rebuild and start
print('\n========== Rebuilding ==========')
run('cd /root/ai-resume-optimizer && docker compose build --no-cache 2>&1 | tail -5')

print('\n========== Starting ==========')
run('cd /root/ai-resume-optimizer && docker compose up -d 2>&1')

import time
time.sleep(5)

# 5. Check
print('\n========== Status ==========')
run('docker ps | grep resume')
run('docker logs resume_backend 2>&1 | tail -10')
run('curl -s http://localhost:80/ | head -3')
run('curl -s http://localhost:80/history')

ssh.close()
print('\n[DONE]')
