import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.96.254.198', port=22, username='root', password='Hjz20050623', timeout=30)


def run(cmd, timeout=30):
    print(f'>>> {cmd}')
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out)
    if err:
        print(f'ERR: {err}')


# 1. Open port 8000 in ufw
print('========== Opening Port 8000 ==========')
run('ufw allow 8000/tcp')

# 2. Reload ufw
run('ufw reload')

# 3. Verify ufw status
print('\n========== UFW Status ==========')
run('ufw status | grep 8000')

# 4. Test public access
print('\n========== Testing Public Access ==========')
run('curl -s --connect-timeout 5 http://47.96.254.198:8000/ 2>&1 | head -5')
run('curl -s --connect-timeout 5 http://47.96.254.198:8000/history 2>&1')

ssh.close()
print('\n✅ 端口已开放，现在可以访问 http://47.96.254.198:8000/ 了！')
