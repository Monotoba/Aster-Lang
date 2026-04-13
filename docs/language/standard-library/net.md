# net

The `net` module provides higher-level abstractions for network communication,
built on top of the raw `socket` native module.

Import with `use net`.

---

## TCP Client

| Function | Returns | Description |
|----------|---------|-------------|
| `net.dial(addr: String, port: Int) -> TcpClient` | Record | Connect to a remote TCP server |
| `net.send(client: TcpClient, data: String) -> Int` | Int | Send data to the remote server |
| `net.recv(client: TcpClient, bufsize: Int) -> String` | String | Receive data from the remote server |
| `net.close(client: TcpClient) -> Nil` | Nil | Close the client connection |

### TcpClient record fields

| Field | Type | Description |
|-------|------|-------------|
| `sock` | Int | Raw socket file descriptor |
| `addr` | String | Remote address |
| `port` | Int | Remote port |

---

## TCP Server

| Function | Returns | Description |
|----------|---------|-------------|
| `net.listen(addr: String, port: Int) -> TcpServer` | Record | Start a TCP server |
| `net.accept(server: TcpServer) -> TcpClient` | Record | Accept a new connection from a client |
| `net.stop(server: TcpServer) -> Nil` | Nil | Stop the server and close its listening socket |

### TcpServer record fields

| Field | Type | Description |
|-------|------|-------------|
| `sock` | Int | Raw socket file descriptor |
| `addr` | String | Bound address |
| `port` | Int | Bound port |

---

## Example: Echo Client

```aster
use net

fn main():
    client := net.dial("127.0.0.1", 8080)
    net.send(client, "Hello, Server!")
    reply := net.recv(client, 1024)
    print("Server says: " + reply)
    net.close(client)
```

## Example: Echo Server

```aster
use net

fn main():
    server := net.listen("0.0.0.0", 8080)
    print("Listening on port 8080...")
    while true:
        client := net.accept(server)
        data := net.recv(client, 1024)
        net.send(client, data)
        net.close(client)
```
