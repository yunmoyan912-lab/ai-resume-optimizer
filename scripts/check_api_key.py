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


# Check what API key is actually stored
run('grep DEEPSEEK_API_KEY /root/ai-resume-optimizer/.env')

# Check length of the key
run('python3 -c "with open(\'/root/ai-resume-optimizer/.env\') as f: lines = f.readlines(); [print(f\'Key length: {len(line.split(\"=\",1)[1].strip())}\') for line in lines if \"DEEPSEEK_API_KEY\" in line]"')

ssh.close()
print('[DONE]')
