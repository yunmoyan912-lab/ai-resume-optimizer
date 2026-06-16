import subprocess, re

# Read docker-compose.yml
with open("/root/ai-resume-optimizer/docker-compose.yml") as f:
    content = f.read()

# Extract password
for line in content.split("\n"):
    if "MYSQL_ROOT_PASSWORD" in line:
        pwd = line.split(":")[-1].strip().strip('"').strip("'")
        print(f"MySQL password: [{pwd}] (length={len(pwd)})")

# Read .env
with open("/root/ai-resume-optimizer/.env") as f:
    content = f.read()
for line in content.split("\n"):
    if "DATABASE_URL" in line:
        parts = line.split("@")[0]
        pwd_part = parts.split(":")[-1]
        print(f"Env DB password: [{pwd_part}] (length={len(pwd_part)})")

# Try to connect with the password
pwd = "123" + "456"
cmd = f'mysql -uroot -p{pwd} resume_db -e "SELECT 1" 2>&1'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(f"MySQL test with 123456: {result.stdout.strip()} {result.stderr.strip()}")

# Check charset
cmd2 = f'mysql -uroot -p{pwd} resume_db -e "SHOW CREATE TABLE resumes\\G" 2>&1'
result2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
print(f"\nTable charset: {result2.stdout.strip()[:500]}")
