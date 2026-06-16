import subprocess

pwd = "***"

# Fix charset - specify database name
cmds = [
    f'docker exec resume_mysql mysql -uroot -p{pwd} resume_db -e "ALTER DATABASE resume_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"',
    f'docker exec resume_mysql mysql -uroot -p{pwd} resume_db -e "ALTER TABLE resumes CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"',
    f'docker exec resume_mysql mysql -uroot -p{pwd} resume_db -e "ALTER TABLE users CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"',
    f'docker exec resume_mysql mysql -uroot -p{pwd} resume_db -e "SHOW CREATE TABLE resumes\\G"',
]

for cmd in cmds:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = result.stdout.strip()
    err = result.stderr.strip()
    # Filter out password warnings
    lines = [l for l in err.split('\n') if 'Warning' not in l and 'Insecure' not in l and l.strip()]
    if out:
        print(out[:800])
    if lines:
        print(f'ERR: {chr(10).join(lines)}')
    print()

print("Done! Charset fixed.")
