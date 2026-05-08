#!/usr/bin/env python3
"""
数据库迁移脚本
将SQLite数据库中的数据迁移到PostgreSQL数据库
"""

import sqlite3
import psycopg2
from psycopg2 import extras
import os
import sys

# 配置
SQLITE_DB = 'agentdns-backend/agentdns.db'
PG_HOST = 'localhost'
PG_PORT = '5432'
PG_DB = 'agentdns'
PG_USER = 'agentdns'
PG_PASSWORD = 'agentdns123'

def get_sqlite_tables(conn):
    """获取SQLite中的所有表"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables

def get_table_columns(conn, table_name):
    """获取表的列信息"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = [(row[1], row[2]) for row in cursor.fetchall()]
    cursor.close()
    return columns

def get_sqlite_data(conn, table_name):
    """获取表中的所有数据"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name};")
    data = cursor.fetchall()
    cursor.close()
    return data

def create_postgresql_table(pg_conn, table_name, columns):
    """在PostgreSQL中创建表"""
    cursor = pg_conn.cursor()
    
    # 映射SQLite类型到PostgreSQL类型
    type_mapping = {
        'INTEGER': 'INTEGER',
        'TEXT': 'TEXT',
        'REAL': 'FLOAT',
        'BLOB': 'BYTEA',
        'BOOLEAN': 'BOOLEAN',
        'DATETIME': 'TIMESTAMP'
    }
    
    # 构建CREATE TABLE语句
    columns_sql = []
    for col_name, col_type in columns:
        pg_type = type_mapping.get(col_type.upper(), 'TEXT')
        columns_sql.append(f"{col_name} {pg_type}")
    
    create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns_sql)});"
    
    try:
        cursor.execute(create_sql)
        pg_conn.commit()
        print(f"Created table {table_name}")
    except Exception as e:
        print(f"Error creating table {table_name}: {e}")
        pg_conn.rollback()
    finally:
        cursor.close()

def convert_boolean_values(data, columns):
    """将SQLite的整数布尔值转换为PostgreSQL的布尔值"""
    converted_data = []
    for row in data:
        converted_row = []
        for i, value in enumerate(row):
            col_name, col_type = columns[i]
            # 检查是否为布尔类型列
            if col_type.upper() == 'BOOLEAN' and isinstance(value, int):
                converted_row.append(bool(value))
            else:
                converted_row.append(value)
        converted_data.append(converted_row)
    return converted_data

def insert_data_to_postgresql(pg_conn, table_name, columns, data):
    """将数据插入到PostgreSQL表中"""
    if not data:
        print(f"No data to insert for table {table_name}")
        return
    
    # 转换布尔值
    data = convert_boolean_values(data, columns)
    
    cursor = pg_conn.cursor()
    col_names = [col[0] for col in columns]
    placeholders = ','.join(['%s'] * len(col_names))
    insert_sql = f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({placeholders});"
    
    try:
        extras.execute_batch(cursor, insert_sql, data)
        pg_conn.commit()
        print(f"Inserted {len(data)} rows into table {table_name}")
    except Exception as e:
        print(f"Error inserting data into {table_name}: {e}")
        pg_conn.rollback()
    finally:
        cursor.close()

def main():
    """主函数"""
    # 连接SQLite数据库
    try:
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        print(f"Connected to SQLite database: {SQLITE_DB}")
    except Exception as e:
        print(f"Error connecting to SQLite: {e}")
        return
    
    # 连接PostgreSQL数据库
    try:
        pg_conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD
        )
        print(f"Connected to PostgreSQL database: {PG_DB}")
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        sqlite_conn.close()
        return
    
    try:
        # 获取SQLite中的所有表
        tables = get_sqlite_tables(sqlite_conn)
        print(f"Found tables: {tables}")
        
        # 排除SQLite系统表
        tables = [table for table in tables if not table.startswith('sqlite_')]
        
        # 迁移每个表
        for table in tables:
            print(f"\nProcessing table: {table}")
            
            # 获取表结构
            columns = get_table_columns(sqlite_conn, table)
            print(f"Columns: {columns}")
            
            # 创建PostgreSQL表
            create_postgresql_table(pg_conn, table, columns)
            
            # 获取数据
            data = get_sqlite_data(sqlite_conn, table)
            
            # 插入数据
            insert_data_to_postgresql(pg_conn, table, columns, data)
        
        print("\n=== Migration completed ===")
        
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        # 关闭连接
        sqlite_conn.close()
        pg_conn.close()
        print("Connections closed")

if __name__ == "__main__":
    main()
