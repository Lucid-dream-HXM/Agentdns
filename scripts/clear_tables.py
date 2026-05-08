#!/usr/bin/env python3
"""
清除PostgreSQL中的表
"""

import psycopg2

# 配置
PG_HOST = 'localhost'
PG_PORT = '5432'
PG_DB = 'agentdns'
PG_USER = 'agentdns'
PG_PASSWORD = 'agentdns123'

# 要删除的表
TABLES = [
    'async_tasks',
    'usage_records',
    'service_metadata',
    'agent_usage',
    'services',
    'agents',
    'billing_records',
    'organizations',
    'users'
]

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
        
        # 删除表（按依赖顺序）
        for table in reversed(TABLES):
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table};")
                print(f"Dropped table {table}")
            except Exception as e:
                print(f"Error dropping table {table}: {e}")
        
        conn.commit()
        print("\nAll tables dropped successfully")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
