import paramiko

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


# Create nginx config for resume optimizer
nginx_config = """
server {
    listen 80;
    server_name 47.96.254.198;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
"""

print('========== Creating Nginx Config ==========')
sftp = ssh.open_sftp()
with sftp.open('/www/server/panel/vhost/nginx/resume_optimizer.conf', 'w') as f:
    f.write(nginx_config)
sftp.close()
print('Config created: /www/server/panel/vhost/nginx/resume_optimizer.conf')

# Test nginx config
print('\n========== Testing Nginx Config ==========')
run('nginx -t 2>&1')

# Reload nginx
print('\n========== Reloading Nginx ==========')
run('nginx -s reload 2>&1')

# Test access
print('\n========== Testing Access ==========')
import time
time.sleep(2)
run('curl -s http://localhost/ | head -5')
run('curl -s http://localhost/history')
run('curl -s http://47.96.254.198/ | head -5')

ssh.close()
print('\n[DONE]')
