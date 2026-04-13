# socket

The `socket` module provides access to the BSD socket interface. It allows for
network communication using TCP and UDP.

Import with `use socket`.

---

## Constants

| Name | Description |
|------|-------------|
| `socket.AF_INET` | IPv4 address family |
| `socket.AF_INET6` | IPv6 address family |
| `socket.SOCK_STREAM` | TCP stream socket |
| `socket.SOCK_DGRAM` | UDP datagram socket |

---

## Functions

| Function | Returns | Description |
|----------|---------|-------------|
| `socket.create(family: Int, type: Int) -> Int` | Int | Create a new socket and return its ID |
| `socket.bind(sock: Int, address: String, port: Int) -> Nil` | Nil | Bind the socket to a local address and port |
| `socket.listen(sock: Int, backlog: Int) -> Nil` | Nil | Enable the socket to accept connections |
| `socket.accept(sock: Int) -> Record` | Record | Accept a new connection. Returns `{conn: Int, addr: String, port: Int}` |
| `socket.connect(sock: Int, address: String, port: Int) -> Nil` | Nil | Connect the socket to a remote address |
| `socket.send(sock: Int, data: String) -> Int` | Int | Send data through the socket. Returns number of bytes sent |
| `socket.recv(sock: Int, bufsize: Int) -> String` | String | Receive up to `bufsize` bytes from the socket |
| `socket.close(sock: Int) -> Nil` | Nil | Close the socket |
| `socket.gethostname() -> String` | String | Get the local hostname |
| `socket.gethostbyname(hostname: String) -> String` | String | Resolve a hostname to an IP address |

---

## Example: TCP Echo Server

```aster
use socket
use io

fn main():
    sock := socket.create(socket.AF_INET, socket.SOCK_STREAM)
    socket.bind(sock, "127.0.0.1", 8080)
    socket.listen(sock, 5)
    print("Listening on 127.0.0.1:8080...")

    res := socket.accept(sock)
    conn := res.conn
    print("Accepted connection from " + res.addr)

    data := socket.recv(conn, 1024)
    print("Received: " + data)

    socket.send(conn, "Echo: " + data)
    socket.close(conn)
    socket.close(sock)
```

## Example: TCP Client

```aster
use socket

fn main():
    sock := socket.create(socket.AF_INET, socket.SOCK_STREAM)
    socket.connect(sock, "127.0.0.1", 8080)
    socket.send(sock, "Hello, Server!")
    
    reply := socket.recv(sock, 1024)
    print("Server said: " + reply)
    
    socket.close(sock)
```
