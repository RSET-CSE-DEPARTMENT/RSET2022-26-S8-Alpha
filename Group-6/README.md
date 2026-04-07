Here is a clean, professional **GitHub README (no emojis, proper formatting)** with your deployed link included:

---

# Zero Trust Micro-VPN for Campus Networks

## Overview

This project implements a Zero Trust-based Micro-VPN architecture integrated with a secure student management portal. It enforces identity-aware, role-based, and continuously verified access to campus resources.

Traditional VPNs grant broad access once connected. This system eliminates that risk by applying Zero Trust principles such as continuous authentication, least privilege access, and microsegmentation. 

---

## Live Deployment

Access the deployed application here:
[https://zero-trust-5hlq.onrender.com/verify_otp](https://zero-trust-5hlq.onrender.com/verify_otp)

---

## Features

### Security Features

* Zero Trust access control
* Trust score-based authorization
* Device fingerprinting
* Multi-factor authentication (Google Authenticator)
* Session monitoring with idle timeout
* Behavioral anomaly detection
* Account blocking on suspicious activity

### Student Portal

* View marks, attendance, and fees
* Submit grievances
* Request profile changes with OTP verification

### Faculty Portal

* Enter marks and attendance
* Post announcements
* Manage student data

### Admin Portal

* User management (create, update, delete)
* Approve/reject profile change requests
* View system logs and security events
* Resolve grievances

### Parent Portal

* View student academic details (read-only)
* Submit grievances

---

## Zero Trust Implementation

The system enforces key Zero Trust principles:

* Never trust, always verify
* Least privilege access
* Continuous authentication
* Microsegmentation

### Trust Score System

* Initial trust score: 100
* Decreases on:

  * Failed login attempts
  * OTP failures
  * Suspicious behavior
* Impacts:

  * Access permissions
  * MFA requirements
  * Session restrictions

---

## Tech Stack

### Backend

* Python (Flask)

### Database

* PostgreSQL 

### Security

* JWT-based authentication
* Hybrid encryption (AES + RSA)
* Device fingerprinting
* Trust scoring engine

### Frontend

* HTML, CSS, Jinja Templates

### Deployment

* Render Cloud

### Tools

* Postman
* GitHub

---

## Project Structure

```
project/
│── app.py                 # Main Flask application
│── templates/            # Role-based HTML templates
│── static/               # CSS and JavaScript
│── db/                   # Database files
│── logs/                 # Security logs
```

---

## Installation and Setup

### Clone the Repository

```
git clone https://github.com/your-repo-name.git
cd your-repo-name
```

### Install Dependencies

```
pip install flask
```

### Run the Application

```
python app.py
```

### Access the Application

```
http://127.0.0.1:5000
```

## Risks and Challenges

* VPN reliability and network dependency
* OTP delivery delays
* Role misconfiguration risks
* Integration complexity
* Scalability limitations

---

## Future Enhancements

* AI-based anomaly detection
* Containerized deployment with Kubernetes

---

## Team

* Aparna V Sunil
* Alan Suresh
* Abhirami C U
* Aryasree Nambiar

Guide: Mr. Sandy Joseph

---



If you want, I can also make a **short 1-page recruiter-friendly README** or add a **project architecture diagram section** for GitHub.
