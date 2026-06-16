

## REGISTER


**Payload**:
```json
{
  "machine_id": "uuid",
  "building_id": "string",
  "room_id": "string",
  "seat_id": "string",
  "agent_version": "semver",
  "hw_fingerprint": "sha256-hex",
  "os_version": "string"
}
```
 machine_id, building_id, room_id, agent_version, hw_fingerprint

---

## HEARTBEAT

 каждые 30 секунд

**Payload**:
```json
{
  "cpu_pct": 0-100,
  "ram_pct": 0-100,
  "gpu_pct": 0-100,
  "disk_free_gb": float,
  "active_policy": "policy-id",
  "status": "online|offline|error"
}
```

---

## SCREENSHOT

при каждом изменении(по дефолту каждые 20 сек)

**Payload (changed=true)**:
```json
{
  "changed": true,
  "image_data": "base64-zstd-compressed",
  "width": 1920,
  "height": 1080,
  "phash": "hex-perceptual-hash"
}
```

**Payload (changed=false)**:
```json
{
  "changed": false
}
```

---

## TASK_RESULT



**Payload**:
```json
{
  "task_id": "uuid",
  "status": "ok|error|timeout",
  "output": "string",
  "error_code": null|int,
  "execution_time_ms": int
}
```

---

## EVENT



**Payload**:
```json
{
  "event_type": "USB_CONNECTED|P2P_DETECTED|...",
  "severity": "low|medium|high|critical",
  "details": { /* event-specific */ }
}
```


USB_CONNECTED  = {vendor_id, product_id, device_class, serial} 
P2P_DETECTED = {local_ip, remote_ip, local_port, remote_port, protocol}
 TAMPER_DETECTED = {expected_hash, actual_hash, file_path}
 PROCESS_KILLED = {pid, process_name, reason}

---

## METRICS

каждые 5 минут

**Payload**:
```json
{
  "period_start": "ISO8601",
  "period_end": "ISO8601",
  "dns_summary": [{"domain": "string", "query_count": int, "blocked": bool}],
  "app_focus_timeline": [{"app_name": "string", "window_title": "string", "duration_seconds": int}],
  "process_list": [{"pid": int, "name": "string", "cpu_pct": int, "memory_mb": int}],
  "unique_domains": int,
  "blocked_queries": int
}
```

---

## TASK



**Payload**:
```json
{
  "task_id": "uuid",
  "task_type": "SCREENSHOT|NET_POLICY|...",
  "payload": { /* в зависимости от таски */ },
  "priority": "normal|high",
  "deadline": "ISO8601"
}
```



SCREENSHOT = {quality: 1-100, force_capture: bool}
NET_POLICY = {whitelist: [], blacklist: [], whitelist_only: bool}
PROCESS_POLICY = {blocked_processes: [], gpu_threshold_pct: int, auto_kill: bool}
SCREEN_CONTROL = {action: "BLACKOUT|RESTORE|DPMS_OFF|DPMS_ON"}
 USB_POLICY = {blocked_classes: [], block_mass_storage: bool}
 TRAFFIC_LIMIT = {target_domain: string, limit_kbps: int, remove: bool}
 SHELL_EXEC = {command: string, timeout_ms: int}

---

## POLICY_UPDATE



**Payload**:
```json
{
  "policy_id": "uuid",
  "profile": "free|lesson|exam|lockdown",
  "rules": {
    "dns_whitelist": [],
    "dns_blacklist": [],
    "whitelist_only": false,
    "bandwidth_limit_kbps": null,
    "blocked_processes": [],
    "gpu_threshold_pct": 40,
    "auto_kill_violations": false,
    "block_mass_storage": false,
    "screenshot_interval_ms": 20000,
    "screenshot_quality": 80,
    "detect_p2p": false
  },
  "effective_from": "ISO8601",
  "effective_until": "ISO8601|null"
}
```

---

## PING / PONG



**PING (Relay -> Agent)**:
```json
{
  "sequence": int,
  "sent_at": "ISO8601"
}
```

**PONG (Agent -> Relay)**:
```json
{
  "sequence": int,
  "ping_sent_at": "ISO8601",
  "pong_sent_at": "ISO8601"
}
```

---

## AGENT_UPDATE


**Payload**:
```json
{
  "new_version": "semver",
  "download_url": "https://...",
  "sha256_hash": "hex",
  "file_size": int,
  "force": bool,
  "restart_required": bool
}
```

---

## ACK



**Payload**:
```json
{
  "acked_message_id": "uuid"
}
```

---

## ERROR

**Payload**:
```json
{
  "reference_id": "uuid",
  "code": "error-code",
  "message": "какой то текст ошибка",
  "details": "детали в json"
}
```
