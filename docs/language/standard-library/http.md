# http

The `http` module provides a basic HTTP/1.1 client and server, built on top of the
`net` and `socket` modules.

Import with `use http`.

---

## HTTP Client

| Function | Returns | Description |
|----------|---------|-------------|
| `http.get(url: String) -> Record` | Record | Send an HTTP GET request and return the response |

### Response Record

- `status`: Int (e.g. 200)
- `body`: String

---

## HTTP Server

| Function | Returns | Description |
|----------|---------|-------------|
| `http.listen(port: Int, handler: Function)` | Nil | Start an HTTP server on the given port |

### Request Record (passed to handler)

- `method`: String
- `path`: String
- `body`: String

### Handler Function

The handler should accept a `Request` record and return a `Response` record.

```aster
fn my_handler(req):
    return {
        status: 200,
        body: "Hello, " + req.path
    }
```

---

## Example: HTTP Client

```aster
use http

fn main():
    res := http.get("http://example.com/")
    print("Status: " + str(res.status))
    print("Body: " + res.body)
```

## Example: HTTP Server

```aster
use http

fn main():
    http.listen(8080, fn(req) -> :
        return {
            status: 200,
            body: "<h1>Aster HTTP Server</h1><p>You requested: " + req.path + "</p>"
        }
    )
```
