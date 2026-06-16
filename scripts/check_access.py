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


# 1. Check container status
print('========== Container Status ==========')
run('docker ps | grep resume')

# 2. Check if service is listening on 8000
print('\n========== Port Listening ==========')
run('ss -tlnp | grep 8000')

# 3. Check firewall status (iptables/ufw/firewalld)
print('\n========== Firewall Status ==========')
run('systemctl status firewalld 2>&1 | head -5')
run('ufw status 2>&1')
run('iptables -L INPUT -n | head -20')

# 4. Test local access
print('\n========== Local Test ==========')
run('curl -s http://127.0.0.1:8000/ | head -5')

# 5. Check if 8000 is accessible from public IP
print('\n========== Public IP Test ==========')
run('curl -s --connect-timeout 3 http://47.96.254.198:8000/ 2>&1 | head -5 || echo "Connection failed"')

ssh.close()
print('\n[DONE]')
