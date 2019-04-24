#!/usr/bin/env python
# -*- coding:utf-8 -*-
#@Time  : 2019/4/3 20:00
#@Author: ouyangshuyin
#@File  : demo.py
import struct
import threading
import hashlib
import socket
import base64
import logging

# 客户端列表字典
global clients
clients = {}


# 通知客户端
# （编码格式很复杂，debug哭了QAQ）
def wirte_mes(message):
    data = struct.pack('B', 129)
    msg_len = len(message)
    if msg_len <= 125:
        data += struct.pack('B', msg_len)
    elif msg_len <= (2 ** 16 - 1):
        data += struct.pack('!BH', 126, msg_len)
    elif msg_len <= (2 ** 64 - 1):
        data += struct.pack('!BQ', 127, msg_len)
    else:
        logging.error('Message is too long!')
        return
    data += bytes(message, encoding='utf-8')
    logging.debug(data)
    print(data)
    for connection in clients.values():
        # a = '%c%c%s' % (0x81, len(data), data)
        connection.send(data)
        # connection.send(str.encode(a))

# 处理线程
class websocket_thread(threading.Thread):
    # 初始化函数
    def __init__(self, connection, username):
        super(websocket_thread, self).__init__()
        self.connection = connection
        self.username = username
    # 运行业务逻辑
    def run(self):
        print('new websocket client joined!')
        data = self.connection.recv(1024)
        data = bytes.decode(data)
        print(data)
        print(type(data))
        headers = self.parse_headers(data)
        token = self.generate_token(headers['Sec-WebSocket-Key'])
        self.connection.send(b'\
HTTP/1.1 101 WebSocket Protocol Hybi-10\r\n\
Upgrade: WebSocket\r\n\
Connection: Upgrade\r\n\
Sec-WebSocket-Accept: %s\r\n\r\n' % token)
        print("-----服务器返回,表示已经接收到请求-----")
        print('\
HTTP/1.1 101 WebSocket Protocol Hybi-10\r\n\
Upgrade: WebSocket\r\n\
Connection: Upgrade\r\n\
Sec-WebSocket-Accept: %s\r\n\r\n' % token)
        print("-----服务器返回,表示已经接收到请求-----")
        while True:
            try:
                data = self.connection.recv(1024)
            except Exception as e:
                print("unexpected error: ", e)
                clients.pop(self.username)
                break
            data = self.parse_data(data)
            if len(data) == 0:
                continue
            message = self.username + ": " + data
            print(message)
            wirte_mes(message)

    # 信息处理
    def parse_data(self, msg):
        v = msg[1] & 0x7f
        if v == 0x7e:
            p = 4
        elif v == 0x7f:
            p = 10
        else:
            p = 2
        mask = msg[p:p + 4]
        data = msg[p + 4:]
        return ''.join([chr(v ^ mask[k % 4]) for k, v in enumerate(data)])

    # 请求头处理
    def parse_headers(self, msg):
        headers = {}
        header, data = msg.split('\r\n\r\n', 1)
        for line in header.split('\r\n')[1:]:
                # print("hello")
                # print(line)
                key, value = line.split(': ', 1)
                headers[key] = value
                # print(key)
                # print(value)
        headers['data'] = data
        return headers

    # 产生token
    def generate_token(self, msg):
        key = msg + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        key = str.encode(key)
        # 使用hashlib的sha1加密
        ser_key = hashlib.sha1(key).digest()
        # 使用base64编码
        return base64.b64encode(ser_key)


# 服务端
class websocket_server(threading.Thread):
    def __init__(self, port):
        super(websocket_server, self).__init__()
        self.port = port

    def run(self):
        # 建立链接（握手阶段）
        # 配置socket对象
        # socket（a,b） a:地址簇 默认为ipv4  b:类型 默认为流式socket（tcp） 还有数据报式socket(udp)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', self.port))
        # 可以挂起的最大连接数
        sock.listen(5)
        print('websocket server started!')
        while True:
            # 循环监听
            # 接受连接并返回（connection,address）//(新的套接字对象，来接受和发送数据     客户端地址)
            connection, address = sock.accept()
            print("++++++++++++++++++++++++++++++++++++++++++++++")
            print(connection)
            print(address)
            print("++++++++++++++++++++++++++++++++++++++++++++++")
            try:
                username = "ID" + str(address[1])
                thread = websocket_thread(connection, username)
                thread.start()
                clients[username] = connection
            except socket.timeout:
                print('websocket connection timeout!')

# main函数
if __name__ == '__main__':
    server = websocket_server(9000)
    server.start()