# http

The `http` module provides a basic HTTP/1.1 client and server, built on top of the
`net` and `socket` modules.

Import with `use http`.

---

## Type aliases

| Alias | Fields | Description |
|-------|--------|-------------|
| `http.Request` | `method`, `path`, `body` | Incoming HTTP request |
| `http.Response` | `status`, `body` | HTTP response to send |

---

## HTTP Client

| Function | Returns | Description |
|----------|---------|-------------|
| `http.get(url: String) -> http.Response` | Record | Send an HTTP GET request and return the response |

### Response fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | Int | HTTP status code (e.g. `200`) |
| `body` | String | Response body |

---

## HTTP Server

| Function | Returns | Description |
|----------|---------|-------------|
| `http.listen(port: Int, handler: Fn(Request) -> Response)` | Nil | Start an HTTP server; blocks forever |

### Request fields (passed to handler)

| Field | Type | Description |
|-------|------|-------------|
| `method` | String | HTTP method (`"GET"`, `"POST"`, …) |
| `path` | String | Request path (e.g. `"/"`) |
| `body` | String | Request body |

### Handler function

The handler receives a `Request` record and must return a `Response` record.
Pass a named function — inline `fn` literals as arguments are not yet supported.

```aster
fn my_handler(req) -> http.Response:
    return { status: 200, body: "Hello from Aster!" }

fn main():
    http.listen(8080, my_handler)
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

fn handle(req) -> http.Response:
    return { status: 200, body: "<h1>Hello from Aster!</h1><p>Path: " + req.path + "</p>" }

fn main():
    print("Starting HTTP server on port 8080...")
    http.listen(8080, handle)
```
