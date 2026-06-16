import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.96.254.198', port=22, username='root', password='Hjz20050623', timeout=30)

# Read current .env
sftp = ssh.open_sftp()
with sftp.open('/root/ai-resume-optimizer/.env', 'r') as f:
    content = f.read().decode()
print('Current .env:')
for line in content.strip().split('\n'):
    if 'DATABASE' in line:
        # Show password safely
        parts = line.split('://')[1] if '://' in line else line
        user_part = parts.split('@')[0]
        host_part = parts.split('@')[1]
        print(f'  DATABASE_URL: user_part={user_part}, host_part={host_part}')
    else:
        print(f'  {line}')

# Check: extract password from DATABASE_URL line
for line in content.strip().split('\n'):
    if 'DATABASE_URL' in line:
        url = line.split('=', 1)[1]
        # format: mysql+pymysql://root:PASSWORD@host:3306/db
        after_user = url.split('root:')[1]
        pwd = after_user.split('@')[0]
        print(f'\nActual password in .env: [{pwd}] (length={len(pwd)})')
        print(f'Expected password: [2feddf5af11ed648] (length=16)')
        if pwd != '2feddf5af11ed648':
            print('>>> PASSWORD MISMATCH! Fixing...')
            new_url = url.replace(pwd, '2feddf5af11ed648')
            new_content = content.replace(url, new_url)
            with sftp.open('/root/ai-resume-optimizer/.env', 'w') as f:
                f.write(new_content)
            print('>>> .env fixed!')
        else:
            print('>>> Password is correct.')

sftp.close()


def run(cmd, timeout=60):
    print(f'>>> {cmd}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out)
    if err:
        print(f'ERR: {err}')


# Restart container
print('\n========== RESTART ==========')
run('cd /root/ai-resume-optimizer && docker compose down && docker compose up -d 2>&1')

import time
time.sleep(5)

# Check logs
print('\n========== LOGS ==========')
run('docker logs resume_backend 2>&1')

# Test
print('\n========== TEST ==========')
run('curl -s http://localhost:8000/history')
run('curl -s -o /dev/null -w "HTTP_CODE:%{http_code}" http://localhost:8000/')

ssh.close()
print('\n[DONE]')
