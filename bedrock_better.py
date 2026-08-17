import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- CONFIG & FAST PONG TEMPLATE ---
SERVERS_FILE = "servers.json"
RAKNET_MAGIC = b"\x00\xff\xff\x00\xfe\xfe\xfe\xfe\xfd\xfd\xfd\xfd\x12\x34\x56\x78"

DEFAULT_MOTD = (
    b"MCPE;Bedrock Better;800;1.20.80;1;100;13371337;\xc2\xaa! Join"
    b" me!\xc2\xab;Survival;1;19132;19132;"
)
MOTD_LEN_BYTES = len(DEFAULT_MOTD).to_bytes(2, byteorder="big")

proxy_running = False
proxy_socket = None
active_server_id = None


# --- DATA STORAGE ---
def load_servers():
    if os.path.exists(SERVERS_FILE):
        try:
            with open(SERVERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_servers(servers):
    with open(SERVERS_FILE, "w") as f:
        json.dump(servers, f, indent=2)


# --- ULTRA-FAST UDP ROUTER ---
def create_pong(ping_id):
    return (
        b"\x1c"
        + ping_id
        + b"\x00\x00\x00\x00\x00\x00\x00\x00"
        + RAKNET_MAGIC
        + MOTD_LEN_BYTES
        + DEFAULT_MOTD
    )


def udp_proxy(target_ip, target_port):
    global proxy_running, proxy_socket
    try:
        resolved_ip = socket.gethostbyname(target_ip)
    except Exception as e:
        print(f"[Error] DNS Lookup failed for {target_ip}: {e}")
        return

    server_addr = (resolved_ip, int(target_port))
    client_addr = None

    try:
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        proxy_socket.bind(("0.0.0.0", 19132))
        proxy_socket.settimeout(0.2)

        magic = RAKNET_MAGIC

        while proxy_running:
            try:
                data, addr = proxy_socket.recvfrom(2048)

                if (
                    data[0] in (0x01, 0x02)
                    and len(data) >= 25
                    and magic in data
                ):
                    proxy_socket.sendto(create_pong(data[1:9]), addr)
                    continue

                if addr != server_addr:
                    client_addr = addr
                    proxy_socket.sendto(data, server_addr)
                elif client_addr:
                    proxy_socket.sendto(data, client_addr)

            except socket.timeout:
                continue
            except Exception:
                pass
    finally:
        if proxy_socket:
            try:
                proxy_socket.close()
            except Exception:
                pass


# --- COOL SLATE THEME UI ---
HTML_UI = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bedrock Better</title>
    <link href="https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #1e2430;
            --card-bg: #2a3140;
            --card-border: #3d4659;
            --input-bg: #161a23;
            --accent-blue: #3b82f6;
            --accent-blue-hover: #2563eb;
            --accent-red: #ef4444;
            --accent-red-hover: #dc2626;
            --accent-green: #10b981;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Silkscreen', sans-serif; }
        body { background: var(--bg); color: var(--text-main); min-height: 100vh; padding: 24px 16px; display: flex; justify-content: center; }

        .container { width: 100%; max-width: 460px; }

        /* HEADER */
        .top-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 22px; }
        .logo-area { display: flex; align-items: center; gap: 10px; }
        .icon-box { width: 34px; height: 34px; background: var(--accent-blue); border-radius: 8px; display: grid; place-items: center; color: #fff; font-size: 16px; font-weight: 700; }
        .app-title { font-size: 15px; color: #fff; letter-spacing: 0.5px; }

        .status-pill { display: flex; align-items: center; gap: 8px; background: var(--card-bg); border: 1px solid var(--card-border); padding: 6px 12px; border-radius: 20px; font-size: 10px; color: var(--text-sub); }
        .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-sub); }
        .dot.running { background: var(--accent-green); }

        /* MAIN CONNECT CARD */
        .connect-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); }
        .card-label { font-size: 10px; color: var(--text-sub); text-transform: uppercase; margin-bottom: 14px; display: block; }

        .input-group { margin-bottom: 12px; }
        .input-group label { display: block; font-size: 9px; color: var(--text-sub); margin-bottom: 5px; }
        .input-group input { width: 100%; padding: 12px; background: var(--input-bg); border: 1px solid var(--card-border); border-radius: 8px; color: #fff; font-size: 11px; outline: none; transition: border-color 0.15s; }
        .input-group input:focus { border-color: var(--accent-blue); }

        .port-row { display: flex; gap: 10px; }
        .port-row .input-group { flex: 1; }

        .btn-run { width: 100%; padding: 14px; background: var(--accent-blue); color: #fff; border: none; border-radius: 8px; font-size: 12px; cursor: pointer; font-weight: 700; margin-top: 6px; transition: background 0.15s; }
        .btn-run:hover { background: var(--accent-blue-hover); }
        .btn-run.stop { background: var(--accent-red); }
        .btn-run.stop:hover { background: var(--accent-red-hover); }

        /* SAVED SERVERS SECTION */
        .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .section-title { font-size: 10px; color: var(--text-sub); text-transform: uppercase; }
        .btn-save-current { background: var(--card-bg); border: 1px solid var(--card-border); color: var(--text-main); padding: 6px 12px; border-radius: 6px; font-size: 9px; cursor: pointer; transition: background 0.15s; }
        .btn-save-current:hover { background: var(--card-border); }

        .saved-list { display: flex; flex-direction: column; gap: 10px; }
        .server-item { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 10px; padding: 12px 14px; display: flex; align-items: center; justify-content: space-between; }
        .server-item.active { border-color: var(--accent-blue); }

        .item-info { display: flex; flex-direction: column; gap: 3px; }
        .item-name { font-size: 12px; color: #fff; }
        .item-addr { font-size: 9px; color: var(--text-sub); }

        .item-actions { display: flex; gap: 6px; }
        .btn-sm { padding: 6px 10px; border-radius: 6px; border: 1px solid var(--card-border); background: var(--input-bg); color: var(--text-main); font-size: 9px; cursor: pointer; }
        .btn-sm:hover { border-color: var(--text-sub); }
        .btn-sm.del { color: var(--accent-red); }

        .empty-hint { text-align: center; padding: 24px; color: var(--text-sub); font-size: 10px; border: 1px dashed var(--card-border); border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <!-- TOP NAVIGATION -->
        <div class="top-bar">
            <div class="logo-area">
                <div class="icon-box">B</div>
                <div class="app-title">Bedrock Better</div>
            </div>
            <div class="status-pill">
                <div class="dot" id="statusDot"></div>
                <span id="statusText">STOPPED</span>
            </div>
        </div>

        <!-- MAIN RUN BOX -->
        <div class="connect-card">
            <span class="card-label">Target Connection</span>
            
            <div class="input-group">
                <label>Server Name</label>
                <input type="text" id="targetName" placeholder="e.g. Anarchy Server">
            </div>

            <div class="port-row">
                <div class="input-group" style="flex:2;">
                    <label>IP Address</label>
                    <input type="text" id="targetIp" placeholder="play.example.com">
                </div>
                <div class="input-group" style="flex:1;">
                    <label>Port</label>
                    <input type="number" id="targetPort" value="19132">
                </div>
            </div>

            <button class="btn-run" id="runBtn" onclick="handleRunClick()">RUN</button>
        </div>

        <!-- SAVED SERVERS LIST -->
        <div class="section-header">
            <span class="section-title">Saved Servers</span>
            <button class="btn-save-current" onclick="saveCurrent()">+ Save Entry</button>
        </div>

        <div class="saved-list" id="savedList"></div>
    </div>

    <script>
        let servers = [];
        let activeId = null;

        async function fetchState() {
            const res = await fetch('/api/servers');
            const data = await res.json();
            servers = data.servers;
            activeId = data.activeId;

            if (activeId) {
                const current = servers.find(s => s.id === activeId);
                if (current) {
                    document.getElementById('targetName').value = current.name;
                    document.getElementById('targetIp').value = current.ip;
                    document.getElementById('targetPort').value = current.port;
                }
            }

            render();
        }

        function render() {
            const dot = document.getElementById('statusDot');
            const statusText = document.getElementById('statusText');
            const runBtn = document.getElementById('runBtn');

            if (activeId) {
                dot.classList.add('running');
                statusText.textContent = 'RUNNING';
                statusText.style.color = '#10b981';
                runBtn.textContent = 'STOP';
                runBtn.classList.add('stop');
            } else {
                dot.classList.remove('running');
                statusText.textContent = 'STOPPED';
                statusText.style.color = '#94a3b8';
                runBtn.textContent = 'RUN';
                runBtn.classList.remove('stop');
            }

            const list = document.getElementById('savedList');
            if (!servers.length) {
                list.innerHTML = `<div class="empty-hint">No saved servers.<br>Fill the form above and click "+ Save Entry".</div>`;
                return;
            }

            list.innerHTML = servers.map(s => {
                const isActive = s.id === activeId;
                return `
                    <div class="server-item ${isActive ? 'active' : ''}">
                        <div class="item-info">
                            <span class="item-name">${s.name}</span>
                            <span class="item-addr">${s.ip}:${s.port}</span>
                        </div>
                        <div class="item-actions">
                            <button class="btn-sm" onclick="useServer('${s.id}')">Select</button>
                            <button class="btn-sm del" onclick="deleteServer('${s.id}')">Del</button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        async function handleRunClick() {
            if (activeId) {
                await fetch('/api/toggle', { method: 'POST', body: JSON.stringify({ id: activeId }) });
            } else {
                const name = document.getElementById('targetName').value.trim() || 'Custom Server';
                const ip = document.getElementById('targetIp').value.trim();
                const port = parseInt(document.getElementById('targetPort').value) || 19132;

                if (!ip) return alert('Please enter an IP address!');

                let existing = servers.find(s => s.ip === ip && s.port === port);
                let targetId = existing ? existing.id : 'temp_' + Date.now();

                if (!existing) {
                    await fetch('/api/save', {
                        method: 'POST',
                        body: JSON.stringify({ id: targetId, name, ip, port })
                    });
                }

                await fetch('/api/toggle', { method: 'POST', body: JSON.stringify({ id: targetId }) });
            }
            fetchState();
        }

        async function saveCurrent() {
            const name = document.getElementById('targetName').value.trim();
            const ip = document.getElementById('targetIp').value.trim();
            const port = parseInt(document.getElementById('targetPort').value) || 19132;

            if (!name || !ip) return alert('Please enter both a Server Name and IP.');

            await fetch('/api/save', {
                method: 'POST',
                body: JSON.stringify({ id: String(Date.now()), name, ip, port })
            });

            fetchState();
        }

        function useServer(id) {
            const s = servers.find(x => x.id === id);
            if (!s) return;
            document.getElementById('targetName').value = s.name;
            document.getElementById('targetIp').value = s.ip;
            document.getElementById('targetPort').value = s.port;
        }

        async function deleteServer(id) {
            await fetch('/api/delete', { method: 'POST', body: JSON.stringify({ id }) });
            fetchState();
        }

        fetchState();
    </script>
</body>
</html>
"""


# --- HTTP API SERVER ---
class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_UI.encode("utf-8"))
        elif self.path == "/api/servers":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            res = {"servers": load_servers(), "activeId": active_server_id}
            self.wfile.write(json.dumps(res).encode("utf-8"))

    def do_POST(self):
        global proxy_running, active_server_id
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}

        servers = load_servers()

        if self.path == "/api/save":
            s_id = body.get("id") or str(int(time.time() * 1000))
            existing = next((x for x in servers if x["id"] == s_id), None)

            if existing:
                existing["name"] = body["name"]
                existing["ip"] = body["ip"]
                existing["port"] = body["port"]
            else:
                servers.append({
                    "id": s_id,
                    "name": body["name"],
                    "ip": body["ip"],
                    "port": body["port"],
                })

            save_servers(servers)

        elif self.path == "/api/delete":
            s_id = body.get("id")
            if active_server_id == s_id:
                proxy_running = False
                active_server_id = None
            servers = [x for x in servers if x["id"] != s_id]
            save_servers(servers)

        elif self.path == "/api/toggle":
            s_id = body.get("id")
            if active_server_id == s_id:
                proxy_running = False
                active_server_id = None
            else:
                proxy_running = False
                time.sleep(0.2)
                target = next((x for x in servers if x["id"] == s_id), None)
                if target:
                    proxy_running = True
                    active_server_id = s_id
                    threading.Thread(
                        target=udp_proxy,
                        args=(target["ip"], target["port"]),
                        daemon=True,
                    ).start()

        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    print("=========================================")
    print(" BEDROCK BETTER - LAN ROUTER ENGINE")
    print("=========================================")
    print("👉 Control Panel: http://127.0.0.1:8080")

    server = HTTPServer(("0.0.0.0", 8080), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        proxy_running = False
        server.server_close()