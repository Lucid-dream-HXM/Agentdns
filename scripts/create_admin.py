#!/usr/bin/env python3
"""
创建管理员用户
"""

import psycopg2
from passlib.context import CryptContext

# 配置
PG_HOST = 'localhost'
PG_PORT = '5432'
PG_DB = 'agentdns'
PG_USER = 'agentdns'
PG_PASSWORD = 'agentdns123'

# 管理员用户信息
ADMIN_USERNAME = 'admin'
ADMIN_EMAIL = 'admin@agentdns.com'
ADMIN_PASSWORD = 'admin123'
ADMIN_FULL_NAME = 'System Administrator'

# 密码哈希配置（与FastAPI应用相同）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password):
    """密码哈希"""
    # 限制密码长度为72字节以避免bcrypt错误
    if len(password.encode('utf-8')) > 72:
        password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)

def main():
    """主函数"""
    try:
        # 连接PostgreSQL
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD
        )
        cursor = conn.cursor()
        
        # 检查管理员用户是否存在
        cursor.execute("SELECT id FROM users WHERE username = %s;", (ADMIN_USERNAME,))
        if cursor.fetchone():
            print(f"Admin user {ADMIN_USERNAME} already exists")
        else:
            # 创建管理员用户
            hashed_pwd = hash_password(ADMIN_PASSWORD)
            cursor.execute("""
                INSERT INTO users (
                    username, email, full_name, hashed_password, role, 
                    is_active, is_verified, balance, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, 'admin', 
                    true, true, 1000.0, NOW(), NOW()
                )
            """, (ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_FULL_NAME, hashed_pwd))
            
            conn.commit()
            print(f"Admin user {ADMIN_USERNAME} created successfully")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
