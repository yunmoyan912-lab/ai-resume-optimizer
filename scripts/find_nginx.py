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


# 1. Find nginx config location
print('========== Finding Nginx Config ==========')
run('nginx -t 2>&1')
run('ls /www/server/panel/vhost/nginx/ 2>/dev/null')
run('ls /etc/nginx/conf.d/ 2>/dev/null')
run('cat /www/server/nginx/conf/nginx.conf 2>/dev/null | head -30')

ssh.close()
print('\n[DONE]')
