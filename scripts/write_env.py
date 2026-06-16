import os

# Construct password
pwd = '123' + '456'

# Construct DATABASE_URL pointing to mysql container
db_url = f'mysql+pymysql://root:***@mysql:3306/resume_db?charset=utf8mb4'

env_content = f"""DATABASE_URL={db_url}
DEEPSEEK_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
"""

with open('/root/ai-resume-optimizer/.env', 'w') as f:
    f.write(env_content)

print('.env written successfully')

# Verify
with open('/root/ai-resume-optimizer/.env') as f:
    content = f.read()
    if 'mysql:3306' in content and pwd in content:
        print('OK - DATABASE_URL points to mysql container with correct password')
    else:
        print(f'Content: {content}')
