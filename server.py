import socket
import threading
import json
import time
import uuid
import base64

CHAT_SERVER_NAME = 'server'

HOST = '127.0.0.1'  # 主机地址
PORT = 8888  # 端口号
BUFFSIZE = 1024  # 缓存区大小，单位是字节，这里设定了2K的缓冲区
ADDR = (HOST, PORT)  # 链接地址

grouplist = {}  # 群聊列表

image_fold_path = '/Users/rodrick/Documents/python/Chatroom/server_temp/img/'


# 公用函数
def get_keys(list, value_list):
    return [k for k, v in list.items() if v in value_list]


class User:
    def __init__(self, address, tcpCliSock):
        self.address = address
        self.tcpCliSock = tcpCliSock


class Handle:
    userlist = {}  # 用户列表,User对象
    usernames = []  # 用户名列表

    def __init__(self, user):
        self.user = user

    def login(self, data):
        """处理登录信息包"""
        if data["username"] in Handle.userlist.values() or self.user in Handle.userlist.keys():
            data["status"] = False
            data["info"] = "该用户名已被占用"
        else:
            data["status"] = True
            Handle.userlist[self.user] = data["username"]
            Handle.usernames.append(data["username"])
            self.user.username = data["username"]
            self.refresh_list(data)
        self.send_socket_to_self(data)

    def refresh_list(self, data):
        """刷新在线用户列表"""
        nameList = Handle.usernames
        data["list"] = nameList
        userlist = [user for user in Handle.userlist]
        self.send_socket_to_all(userlist, data)

    def init_list(self, data):
        """获取在线用户列表"""
        data["type"] = "login"
        nameList = Handle.usernames
        data["list"] = nameList
        self.send_socket_to_self(data)

    def group_chat(self, data):
        """群聊"""
        userlist = [user for user in Handle.userlist]
        self.send_socket_to_all(userlist, data)

    def private_chat(self, data):
        """私聊"""
        send_to_namelist = data['to']
        send_to_userlist = get_keys(Handle.userlist, send_to_namelist)
        self.send_socket_to_users(send_to_userlist, data)

    def create_group(self, data):
        """用户创建了群聊"""
        group_dic = data['group']
        grouplist.update(group_dic)
        print(grouplist)

    def group_pic(self, data):
        """群聊图片"""
        userlist = [user for user in Handle.userlist]
        self.send_socket_to_all(userlist, data)

    @staticmethod
    def send_socket_to_users(send_to_userlist, data):
        """向用户列表发送信息包"""
        json_data = json.dumps(data)
        json_data = str.encode(json_data)
        for user in send_to_userlist:
            user.tcpCliSock.send(json_data)
        print("Send to users: " + str(json_data))

    @staticmethod
    def send_socket_to_all(userlist, data):
        """给所有用户发送信息包"""
        json_data = json.dumps(data)
        json_data = str.encode(json_data)
        for user in userlist:
            user.tcpCliSock.send(json_data)
        print("Send to all users: " + str(json_data))

    def send_socket_to_self(self, data):
        """给本用户发送信息包"""
        json_data = json.dumps(data)
        json_data = str.encode(json_data)
        self.user.tcpCliSock.send(json_data)
        print('Send to user self: ' + str(json_data))

    @staticmethod
    def remove_user(user):
        try:
            handle = Handle(user)
            Handle.userlist.pop(user)
            Handle.usernames.remove(user.username)
            data = {"type": "remove_user", "username": user.username}
            handle.refresh_list(data)
        except Exception as err:
            print(err)

    def recv_pic(self, socket):
        name = str(uuid.uuid1())  # 获取文件名
        file_path = image_fold_path + name  # 将文件夹和图片名连接起来
        print(file_path)
        print('Start saving!')
        f = open(file_path+'.png', 'wb+')
        while True:
            data = socket.recv(BUFFSIZE)
            if data == 'EOF'.encode():
                print('Saving completed!')
                break
            f.write(data)

    def __main__(self, data):
        """处理信息包"""
        type = data["type"]
        switch = {
            "login": self.login,
            "init_list": self.init_list,
            "group_chat": self.group_chat,
            "private_chat": self.private_chat,
            "create_group": self.create_group,
            "group_pic": self.group_pic,
        }
        try:
            switch[type](data)
        except Exception as e:
            print(e)
            data["status"] = False
            data["info"] = "未知错误"
            return data


class ClientThread(threading.Thread):
    def __init__(self, user):
        threading.Thread.__init__(self)
        self.user = user

    def run(self):
        handle = Handle(self.user)  # handle input
        try:
            while True:
                json_data = self.user.tcpCliSock.recv(BUFFSIZE)
                data = json.loads(json_data, strict=False)
                print("receive data from: " + data['username'])
                if data['type'] == 'logout':
                    break
                elif data['type'] == 'group_pic':
                    while True:
                        data = self.user.tcpCliSock.recv(BUFFSIZE)
                        print(data)
                        data = data.decode()
                        print("begin receive picture")
                        if data == 'quit':
                            break
                        handle.recv_pic(self.user.tcpCliSock)
                else:
                    handle.__main__(data)
        except Exception as err:
            print("连接中断")
            print(err)
        finally:
            name = Handle.userlist[self.user]
            print(str(name) + "退出聊天室")
            Handle.remove_user(self.user)
            self.user.tcpCliSock.close()

    def stop(self):
        try:
            self.user.tcpCliSock.shutdown(2)
            self.user.tcpCliSock.close()
        except Exception as err:
            print("连接中断")
            print(err)


class ChatServer:
    def __main__(self):
        tcpSerSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpSerSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 在绑定前调用setsockopt让套接字允许地址重用
        tcpSerSock.bind(ADDR)
        tcpSerSock.listen(5)

        threads = []

        while True:
            try:
                print('Waiting for connection...')
                tcpCliSock, addr = tcpSerSock.accept()
                print('...connected from:', addr)

                user = User(addr, tcpCliSock)
                clientThread = ClientThread(user)
                threads += [clientThread]
                clientThread.start()
            except KeyboardInterrupt:
                print('KeyboardInterrupt:')
                for t in threads:
                    t.stop()
                break

        tcpSerSock.close()


if __name__ == '__main__':
    print("\t\tChat Room Server\n")

    server = ChatServer()
    server.__main__()
