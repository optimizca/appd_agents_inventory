from getpass import getpass

from cryptography.fernet import Fernet


inputPwd = getpass("Enter your password")
controllerPassword = inputPwd
key = Fernet.generate_key()
print("key: ",key.decode('utf-8'))

fernet = Fernet(key)
encString = fernet.encrypt(inputPwd.encode())

print("encrypted string: ", encString.decode('utf-8'))
decMessage = fernet.decrypt(encString).decode()


