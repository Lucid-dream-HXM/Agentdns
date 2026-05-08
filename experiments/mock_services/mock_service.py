#!/usr/bin/env python3
"""Mock Service - 模拟实验市场中的服务"""

from flask import Flask, request, jsonify
import random
import time

app = Flask(__name__)

@app.route('/mock/<service_key>', methods=['POST'])
def mock_service(service_key):
    data = request.json or {}
    task = data.get('task', '')
    text = data.get('text', '')

    time.sleep(random.uniform(0.1, 0.3))

    return jsonify({
        'status': 'success',
        'result': f'[{service_key}] 处理完成: {text[:50]}...' if text else f'[{service_key}] 处理完成',
        'service_key': service_key,
        'processed': True
    })

@app.route('/mock', methods=['POST'])
def mock_default():
    data = request.json or {}
    task = data.get('task', '')

    return jsonify({
        'status': 'success',
        'result': f'Mock 处理完成: {task[:50] if task else "empty"}...',
        'processed': True
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9002, debug=False)