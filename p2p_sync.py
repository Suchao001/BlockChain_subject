import socket
import threading
import json
import sys
import os
import secrets

# นำเข้าโมดูลที่จำเป็น:
# socket: สำหรับการสื่อสารผ่านเครือข่าย
# threading: สำหรับการทำงานแบบหลายเธรด
# json: สำหรับการเข้าและถอดรหัสข้อมูล JSON
# sys: สำหรับการเข้าถึงตัวแปรและฟังก์ชันที่เกี่ยวข้องกับระบบ
# os: สำหรับการทำงานกับระบบปฏิบัติการ
# secrets: สำหรับการสร้างข้อมูลที่ปลอดภัยทางคริปโตกราฟี

""" การรันโปรแกรมบนสองเครื่อง:
บนเครื่องแรก: python p2p_node.py 5000
บนเครื่องที่สอง: python p2p_node.py 5001
ใช้ตัวเลือกที่ 1 บนเครื่องใดเครื่องหนึ่งเพื่อเชื่อมต่อกับอีกเครื่อง """




class Node:
    # constructor method
    def __init__(self, host, port):
        #กำหนดและสร้างตัวแปรต่างๆ ที่จำเป็น สำหรับการใช้งาน
        self.host = host
        self.port = port
        self.peers = []  # เก็บรายการ socket ของ peer ที่เชื่อมต่อ
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #สร้าง TCP socket สำหรับการสื่อสารผ่านเครือข่าย IPv4
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #อนุญาตให้ใช้ port ซ้ำได้ทันทีหลังจากปิดโปรแกรม
        self.transactions = []  # เก็บรายการ transactions
        self.transaction_file = f"transactions_{port}.json"  # ไฟล์สำหรับบันทึก transactions
        self.wallet_address = self.generate_wallet_address()  # สร้าง wallet address สำหรับโหนดนี้

    def generate_wallet_address(self):
        # สร้าง wallet address แบบง่ายๆ (ในระบบจริงจะซับซ้อนกว่านี้มาก)
        return '0x' + secrets.token_hex(20)       # ใช้ secrets.token_hex(20) เพื่อสร้างสตริงแบบสุ่มที่ปลอดภัย ยาว 40 ตัวอักษร (20 ไบต์)

    #function สำหรับ ...
    def start(self):
        # เริ่มต้นการทำงานของโหนด
        self.socket.bind((self.host, self.port))  # ผูก socket กับ host และ port ที่กำหนด
        self.socket.listen(1)  # เริ่มรับการเชื่อมต่อ (รับได้สูงสุด 1 การเชื่อมต่อที่รอคิวอยู่)
        print(f"Node listening on {self.host}:{self.port}")
        print(f"Your wallet address is: {self.wallet_address}")

        self.load_transactions()  # โหลด transactions จากไฟล์ (ถ้ามี)

        # เริ่ม thread สำหรับรับการเชื่อมต่อใหม่
        accept_thread = threading.Thread(target=self.accept_connections)
        accept_thread.start()

    def accept_connections(self):
        while True:
            # รอรับการเชื่อมต่อใหม่
            client_socket, address = self.socket.accept()
            print(f"New connection from {address}")

            # เริ่ม thread ใหม่สำหรับจัดการการเชื่อมต่อนี้
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.start()

    def handle_client(self, client_socket):
        while True:
            try:
                # รับข้อมูลจาก client
                data = client_socket.recv(1024)  # รับข้อมูลสูงสุด 1024 ไบต์
                if not data:
                    break  # ถ้าไม่มีข้อมูล แสดงว่าการเชื่อมต่อถูกปิด
                message = json.loads(data.decode('utf-8'))  # แปลงข้อมูลจาก JSON เป็น Python object
                
                self.process_message(message)

            except Exception as e:
                print(f"Error handling client: {e}")
                break

        client_socket.close()  # ปิดการเชื่อมต่อเมื่อเกิดข้อผิดพลาดหรือไม่มีข้อมูล

    def connect_to_peer(self, peer_host, peer_port):
        try:
            # สร้างการเชื่อมต่อไปยัง peer
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((peer_host, peer_port))
            self.peers.append(peer_socket)
            print(f"Connected to peer {peer_host}:{peer_port}")

            # เริ่ม thread สำหรับรับข้อมูลจาก peer นี้
            peer_thread = threading.Thread(target=self.handle_client, args=(peer_socket,))
            peer_thread.start()

        except Exception as e:
            print(f"Error connecting to peer: {e}")

    def broadcast(self, message):
        # ส่งข้อมูลไปยังทุก peer ที่เชื่อมต่ออยู่
        for peer_socket in self.peers:
            try:
                peer_socket.send(json.dumps(message).encode('utf-8'))
            except Exception as e:
                print(f"Error broadcasting to peer: {e}")
                self.peers.remove(peer_socket)  # ลบ peer ที่ไม่สามารถส่งข้อมูลได้

    def process_message(self, message):
        # ประมวลผลข้อความที่ได้รับ
        if message['type'] == 'transaction':
            print(f"Received transaction: {message['data']}")
            self.add_transaction(message['data'])
        else:
            print(f"Received message: {message}")

    def add_transaction(self, transaction):
        # เพิ่ม transaction ใหม่และบันทึกลงไฟล์
        self.transactions.append(transaction)
        self.save_transactions()
        print(f"Transaction added and saved: {transaction}")

    def create_transaction(self, recipient, amount):
        # สร้าง transaction ใหม่
        transaction = {
            'sender': self.wallet_address,
            'recipient': recipient,
            'amount': amount
        }
        self.add_transaction(transaction)
        self.broadcast({'type': 'transaction', 'data': transaction})

    def save_transactions(self):
        # บันทึก transactions ลงไฟล์
        with open(self.transaction_file, 'w') as f:
            json.dump(self.transactions, f)

    def load_transactions(self):
        # โหลด transactions จากไฟล์ (ถ้ามี)
        if os.path.exists(self.transaction_file):
            with open(self.transaction_file, 'r') as f:
                self.transactions = json.load(f)
            print(f"Loaded {len(self.transactions)} transactions from file.")

# เช็คการทำงานของโค้ด ด้วยการรันไฟล์นี้โดยตรง
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python p2p.py <port>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    node = Node("0.0.0.0", port)  # ใช้ "0.0.0.0" เพื่อรับการเชื่อมต่อจากภายนอก
    node.start()
    
    # คำสั่งหลักในการทำซ้ำ เพื่อเลือกคำสั่ง
    while True:
        print("\n1. Connect to a peer")
        print("2. Create a transaction")
        print("3. View all transactions")
        print("4. View my wallet address")
        print("5. Exit")
        choice = input("Enter your choice: ")
        
        # ตัวเลือกต่างๆ เพื่อทำงานในฟังก์ชันที่สร้างไว้
        if choice == '1':
            peer_host = input("Enter peer host to connect: ")
            peer_port = int(input("Enter peer port to connect: "))
            node.connect_to_peer(peer_host, peer_port)
        elif choice == '2':
            recipient = input("Enter recipient wallet address: ")
            amount = float(input("Enter amount: "))
            node.create_transaction(recipient, amount)
        elif choice == '3':
            print("All transactions:")
            for tx in node.transactions:
                print(tx)
        elif choice == '4':
            print(f"Your wallet address is: {node.wallet_address}")
        elif choice == '5':
            break
        else:
            print("Invalid choice. Please try again.")

    print("Exiting...")