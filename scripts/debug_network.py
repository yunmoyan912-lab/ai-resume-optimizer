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


# 1. Check container and service
print('========== Service Status ==========')
run('docker ps | grep resume')
run('ss -tlnp | grep 8000')

# 2. Test local access
print('\n========== Local Test ==========')
run('curl -s http://localhost:8000/ | head -3')
run('curl -s http://localhost:8000/history')

# 3. Check iptables for 8000
print('\n========== Iptables Rules for 8000 ==========')
run('iptables -L -n | grep 8000')
run('iptables -L INPUT -n -v | grep 8000')

# 4. Check if there's any DROP rule blocking
print('\n========== UFW Detailed Status ==========')
run('ufw status verbose')

# 5. Check network interfaces
print('\n========== Network Interfaces ==========')
run('ip addr show | grep inet | grep -v 127.0.0.1')

ssh.close()
