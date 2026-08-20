"""HTTP bridge so the PWA (phone/browser) can talk to the car over WiFi.

Architecture: this tool runs on a laptop/Raspberry Pi connected to the ELM327
(USB or Bluetooth). The PWA on your phone fetches http://<laptop>:<port>/api/*
on the same network. Stdlib only; CORS open for local use.

Endpoints:
  GET /api/health              bridge status
  GET /api/dtcs                PCM fault codes, decoded
  GET /api/scan                full module scan (slow — probes every module)
  GET /api/vehicles            installed KB list
  GET /api/kb?vehicle=<key>    one knowledge base
  GET /api/match?symptoms=...  KB matches (pass &dtcs=P2453,P2463 to include codes)

  python ford_recovery.py --serve 8765            (real adapter)
  python ford_recovery.py --serve 8765 --demo     (simulated, for PWA dev)
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import known_issues, modules, obd


def make_handler(ecu, vehicle):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, obj, status=200):
            body = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass  # quiet

        def do_GET(self):
            url = urlparse(self.path)
            q = parse_qs(url.query)
            try:
                if url.path == "/api/health":
                    self._json({"ok": True, "suite": "ford-tdci-recovery"})
                elif url.path == "/api/dtcs":
                    codes = obd.decode_dtcs(ecu.query("03"))
                    self._json({"dtcs": [
                        {"code": c, "description": obd.KNOWN_DTC.get(c, "")}
                        for c in codes]})
                elif url.path == "/api/scan":
                    results = modules.scan_modules(vehicle, log=lambda *a: None)
                    self._json({"modules": [
                        {"name": n, "present": p, "dtcs": d}
                        for n, (p, d) in results.items()]})
                elif url.path == "/api/vehicles":
                    self._json({"vehicles": known_issues.available_vehicles()})
                elif url.path == "/api/kb":
                    kb = known_issues.load_kb(q.get("vehicle", [None])[0])
                    self._json(kb)
                elif url.path == "/api/match":
                    kb = known_issues.load_kb(q.get("vehicle", [None])[0])
                    dtcs = q.get("dtcs", [""])[0].split(",") if q.get("dtcs") else []
                    hits = known_issues.match(kb, dtcs=dtcs,
                                              symptom_text=q.get("symptoms", [""])[0])
                    self._json({"matches": [
                        {"score": s, "issue": i, "dtc_hits": d, "symptom_hits": h}
                        for s, i, d, h in hits]})
                else:
                    self._json({"error": "unknown endpoint"}, 404)
            except Exception as e:
                self._json({"error": str(e)}, 500)

    return Handler


def serve(ecu, vehicle, port):
    httpd = ThreadingHTTPServer(("0.0.0.0", port), make_handler(ecu, vehicle))
    print(f"Bridge listening on http://0.0.0.0:{port}  "
          f"(phone must be on the same WiFi). Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nBridge stopped.")
