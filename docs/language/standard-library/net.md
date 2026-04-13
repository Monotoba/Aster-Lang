# net

The `net` module provides higher-level abstractions for network communication,
built on top of the raw `socket` native module.

Import with `use net`.

---

## TCP Client

| Function | Returns | Description |
|----------|---------|-------------|
| `net.dial(addr: String, port: Int) -> List` | List | Connect to a remote TCP server |
| `net.send(client: List, data: String) -> Int` | Int | Send data to the remote server |
| `net.recv(client: List, bufsize: Int) -> String` | String | Receive data from the remote server |
| `net.close(client: List) -> Nil` | Nil | Close the client connection |

### TcpClient (List)

- `[0]`: Int (raw socket ID)
- `[1]`: String (address)
- `[2]`: Int (port)

---

## TCP Server

| Function | Returns | Description |
|----------|---------|-------------|
| `net.listen(addr: String, port: Int) -> List` | List | Start a TCP server |
| `net.accept(server: List) -> List` | List | Accept a new connection from a client |
| `net.stop(server: List) -> Nil` | Nil | Stop the server and close its listening socket |

### TcpServer (List)

- `[0]`: Int (raw socket ID)
- `[1]`: String (address)
- `[2]`: Int (port)

---

## Example: Echo Client

```aster
use net

fn main():
    print("Connecting to 127.0.0.1:8080...")
    client := net.dial("127.0.0.1", 8080)
    
    net.send(client, "Hello, Server!")
    reply := net.recv(client, 1024)
    print("Server says: " + reply)
    
    net.close(client)
```
