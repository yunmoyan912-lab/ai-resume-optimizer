import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('47.96.254.198', port=22, username='root', password='Hjz20050623', timeout=30)
sftp = ssh.open_sftp()

# Upload updated index.html
sftp.put('D:/Fastapi_base/ai-resume-optimizer/index.html', '/root/ai-resume-optimizer/index.html')
print('✓ index.html uploaded')

sftp.close()
ssh.close()
print('[DONE]')
