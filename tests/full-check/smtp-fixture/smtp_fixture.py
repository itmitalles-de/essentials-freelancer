import base64
import email
import json
import threading
from email import policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import StreamRequestHandler, ThreadingTCPServer


lock = threading.Lock()
state = {"mode": "success", "messages": []}


def message_summary(content: bytes) -> dict:
    message = email.message_from_bytes(content, policy=policy.default)
    attachments = []
    for part in message.iter_attachments():
        payload = part.get_payload(decode=True) or b""
        attachments.append(
            {
                "filename": part.get_filename(),
                "content_type": part.get_content_type(),
                "size": len(payload),
                "content_base64": base64.b64encode(payload).decode("ascii"),
            }
        )
    return {
        "subject": str(message.get("Subject", "")),
        "from": str(message.get("From", "")),
        "to": [address.strip() for address in str(message.get("To", "")).split(",")],
        "attachments": attachments,
    }


class SMTPHandler(StreamRequestHandler):
    def send(self, text: str) -> None:
        self.wfile.write((text + "\r\n").encode("ascii"))
        self.wfile.flush()

    def handle(self) -> None:
        with lock:
            mode = state["mode"]
        if mode == "disconnect":
            return
        if mode == "timeout":
            threading.Event().wait(5)
            return
        self.send("220 synthetic-smtp ESMTP")
        recipients = []
        sender = ""
        data_mode = False
        content = bytearray()
        while True:
            raw = self.rfile.readline(1024 * 1024)
            if not raw:
                return
            line = raw.rstrip(b"\r\n")
            if data_mode:
                if line == b".":
                    with lock:
                        state["messages"].append(
                            {
                                **message_summary(bytes(content)),
                                "envelope_from": sender,
                                "envelope_to": recipients,
                            }
                        )
                    self.send("250 2.0.0 synthetic queued")
                    data_mode = False
                    content.clear()
                else:
                    content.extend(line[1:] if line.startswith(b"..") else line)
                    content.extend(b"\r\n")
                continue
            command = line.decode("utf-8", "replace")
            upper = command.upper()
            if upper.startswith(("EHLO ", "HELO ")):
                self.send("250-synthetic-smtp")
                self.send("250 SIZE 10485760")
            elif upper.startswith("MAIL FROM:"):
                sender = command[10:].strip(" <>")
                self.send("250 2.1.0 sender accepted")
            elif upper.startswith("RCPT TO:"):
                with lock:
                    current_mode = state["mode"]
                if current_mode == "reject":
                    self.send("550 5.1.1 synthetic recipient rejection")
                else:
                    recipients.append(command[8:].strip(" <>"))
                    self.send("250 2.1.5 recipient accepted")
            elif upper == "DATA":
                self.send("354 End data with <CR><LF>.<CR><LF>")
                data_mode = True
            elif upper == "RSET":
                recipients.clear()
                content.clear()
                self.send("250 reset")
            elif upper == "NOOP":
                self.send("250 ok")
            elif upper == "QUIT":
                self.send("221 bye")
                return
            else:
                self.send("502 command not implemented")


class SMTPServer(ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class HTTPHandler(BaseHTTPRequestHandler):
    def response(self, status: int, body: object) -> None:
        content = json.dumps(body, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        if self.path == "/health":
            self.response(200, {"status": "ok"})
        elif self.path == "/api/messages":
            with lock:
                self.response(200, list(state["messages"]))
        elif self.path == "/api/state":
            with lock:
                self.response(200, {"mode": state["mode"], "count": len(state["messages"])})
        else:
            self.response(404, {"error": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/mode":
            mode = body.get("mode")
            if mode not in {"success", "reject", "timeout", "disconnect"}:
                self.response(400, {"error": "invalid mode"})
                return
            with lock:
                state["mode"] = mode
            self.response(200, {"mode": mode})
        elif self.path == "/api/reset":
            with lock:
                state["mode"] = "success"
                state["messages"].clear()
            self.response(200, {"status": "reset"})
        else:
            self.response(404, {"error": "not found"})

    def log_message(self, format: str, *args) -> None:
        return


smtp_server = SMTPServer(("0.0.0.0", 1025), SMTPHandler)
http_server = ThreadingHTTPServer(("0.0.0.0", 8025), HTTPHandler)
threading.Thread(target=smtp_server.serve_forever, daemon=True).start()
http_server.serve_forever()
