# Zero Trust Student Management System: Comprehensive Feature Guide

This document provides an exhaustive technical breakdown of every feature implemented in the Zero Trust Student Management System. Each section covers the architectural logic, security implications, and specific code implementations.

---

## 1. Zero Trust Architecture (ZTA)

### [A] Policy Enforcement Point (PEP)
**How it works**: Every single request to the application (excluding basic public paths) is intercepted by a middleware layer. Before the request reaches its intended route, the application establishes a secure side-channel connection to the **Zero Trust Policy Server**.
- **Implementation**: `app.before_request` hook in [app.py](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/app.py#L1250-1311).
- **Logic**: It serializes the user's JWT and the target path, encrypts them, and sends them to the policy server at `127.0.0.1:5012`. If the server returns anything other than `ALLOWED`, the request is blocked or the session is terminated.

### [B] Policy Decision Point (PDP)
**How it works**: The standalone VPN server acts as the centralized brain for all access decisions. It maintains its own in-memory state of trust scores and RBAC policies, ensuring that even if the web server is compromised, the policy engine remains isolated.
- **Implementation**: `handle_client` in [vpn_server.py](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/zero_trust_vpn/vpn_server.py#L86-195).
- **Security Goal**: Separation of concerns. The web app (Data Plane) does not make security decisions; the VPN Server (Control Plane) does.

---

## 2. Hybrid Cryptographic Tunnel (RSA + AES)

The communication between the Flask App and the VPN Policy Server is protected by a high-performance hybrid encryption scheme.

### [A] RSA-2048 (Asymmetric)
- **Use Case**: Secure key exchange.
- **Implementation**: [crypto_utils.py](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/zero_trust_vpn/crypto_utils.py#L47-75).
- **Detail**: We use RSA-OAEP with SHA-256 for maximum resistance against chosen-ciphertext attacks. It is used to encrypt the one-time AES session key.

### [B] AES-256-CBC (Symmetric)
- **Use Case**: Bulk data encryption.
- **Implementation**: [crypto_utils.py](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/zero_trust_vpn/crypto_utils.py#L26-45).
- **Detail**: JSON payloads (JWT + Path) are encrypted using AES-256 in CBC mode with a unique IV (Initialization Vector) for every request.

---

## 3. Dynamic Trust Engine

The "Zero Trust" aspect is driven by a real-time trust scoring algorithm. Users do not just have "access"—they have a fluctuating "trust level."

### [A] Scoring & Penalties
- **Base Trust**: 100 points.
- **RBAC Violation**: Deducts 15 points (see [app.py:L1013](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/app.py#L1013)).
- **New Device Detection**: Deducts 10 points (see [app.py:L1198](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/app.py#L1198)).
- **Anomaly (Impossible Travel)**: Deducts 40 points.
- **Anomaly (Late Night Access)**: Deducts 10 points.

### [B] Automatic Session Termination
- **Threshold**: If trust falls below **40**, the user is restricted ([app.py:L1044](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/app.py#L1044)).
- **Critical Failure**: If trust falls below **10**, the VPN server instructs the client to terminate the session immediately ([vpn_server.py:L167](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/zero_trust_vpn/vpn_server.py#L167)).

### [C] Trust Recovery
- **Passive Recovery**: Users gain 2 points for every 5 minutes of "clean" behavior (no security violations) ([app.py:L859](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/app.py#L859)).
- **Self-Service Verification**: Users can "re-prove" their identity via an extra OTP check to gain a +20 point boost ([app.py:L1411](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/app.py#L1411)).

---

## 4. Advanced Security Mitigations

### [A] Replay Protection
- **Mechanism**: Every encrypted packet includes a high-resolution timestamp (`ts`) and a unique cryptographic `nonce`.
- **Enforcement**: [vpn_server.py:L122-137](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/zero_trust_vpn/vpn_server.py#L122-137).
- **Result**: Even if an attacker captures a valid "ALLOW" packet, they cannot "replay" it later to gain access.

### [B] Anomaly Detection Heuristics
- **Impossible Travel**: Calculates the geographical distance between the last login IP and current IP. If the speed required to travel that distance exceeds 500mph, it flags a breach ([app.py:L633-645](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/app.py#L633-645)).
- **Time-of-Day**: Flags access attempts made during unusual hours (e.g., 2 AM - 5 AM).

---

## 5. Functional SMS Features

### [A] Multi-Role Portal System
- **Student**: View marks, attendance, and notices.
- **Parent**: Track child progress, view grievances, and billing.
- **Faculty**: Manage marks, attendance, and assignments.
- **Admin**: Full system control including trust score manual overrides and audit logs.
- **RBAC Implementation**: `role_required` decorator in [app.py:L991-1131](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/app.py#L991-1131).

### [B] Secure Managed Auditing
- **Encrypted Logs**: Action logs are not stored in plain text. They are encrypted using the application's secret key.
- **Admin Decryption**: Only admins can view the logs, which are decrypted on-the-fly in memory ([app.py:L408-459](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/app.py#L408-459)).

---

## 6. Infrastructure & Reliability

- **Rate Limiting**: Custom decorator `rate_limit` ([app.py:L771-832](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/app.py#L771-832)) prevents brute-force and DoS attacks at the application level.
- **Idle Timeout**: Automatically terminates sessions after 5 minutes of inactivity ([app.py:L955-968](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/app.py#L955-968)).
- **Device Fingerprinting**: Uses browser/environment headers to generate a unique ID, preventing session hijacking from different machines ([app.py:L472-476](file:///c:/Users/alans/Downloads/Projects/Student_Management_System/app.py#L472-476)).
