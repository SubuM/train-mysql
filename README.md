# 🧪 SQL Lab

SQL Lab is a web-based SQL learning and database experimentation platform built with Streamlit.  
It allows users to securely interact with isolated MySQL containers through a browser-based SQL editor, while administrators can manage users, containers, and logs via an admin dashboard.  

The application is deployed on Streamlit Cloud and accessed via a web URL. No local installation or configuration is required for end users.

## ✨ Core Functionality

### 👤 User Features
- **User registration and authentication** via backend API
- **One isolated MySQL container per user**
- **Browser-based SQL editor** (ACE Editor)
- **Execute SQL queries** against a personal MySQL database
- **Automatic creation of a personal database**
- **Database schema explorer** (databases, tables, columns)
- **Query history tracking** (session-based)
- **Table previews** with configurable row limits
- **Protection** against destructive actions on system databases

### 🛡️ Admin Features
- **Secure admin login**
- **List users** (basic and detailed views)
- **Manage containers** (start, stop, restart, suspend, or delete user containers)
- **View container logs** per user
- **Centralized backend-controlled container lifecycle management**

## 🧑‍💻 Usage

### User Workflow
1. Access the SQL Lab application via the provided URL
2. Register a new account or log in
3. Start a personal MySQL container
4. After successful start of MySQL container, logout and login with the new user account
5. If needed, choose the SQL editor theme from the dropdown
6. Write and execute SQL queries in the browser
7. Explore schemas and preview tables
8. All query history are listed

### Admin Workflow
1. Log in using admin credentials
2. View registered users
3. Manage user containers (start, stop, suspend, delete)
4. Inspect container logs when required

## ⚠️ Limitations
- Intended for **educational and lab environments only**
- Not designed for **production workloads**
- SQL execution is **unrestricted** within the user’s container
- Query history is stored in **session memory only**
- No built-in **rate limiting** or **brute-force protection**
- No automatic **container cleanup** beyond admin actions
- No built-in **database backups**
- Overall security depends on **hosting** and **backend configuration**

## 🔐 Data Security & Privacy (EU / GDPR Considerations)

This application is designed following **privacy-by-design** principles, but full **GDPR compliance** depends on deployment and operational practices.

### Personal Data Processed
- **Username**
- **Authentication credentials** (passwords are securely hashed, never stored in plaintext)
- **User container metadata**
- **Container logs** (accessible to administrators)
- **SQL queries** (processed transiently; not persistently stored by the frontend)

### Data Storage
- Authentication data is handled by a **backend service**
- **Passwords** are stored using **secure one-way hashing**
- **Database content** is isolated per user container
- No client-side persistent storage of **personal data**

### Data Minimization
- Only data necessary for **authentication** and functionality is processed
- No **analytics**, **profiling**, or **tracking**
- No **third-party data sharing**

### User Rights
Administrators can:
- **Delete users** and associated containers (**Right to Erasure**)
- **Suspend** or **restore access**
- **Remove all user-associated database data**

### Operator Responsibilities
The deploying organization is responsible for:
- Providing a **privacy notice**
- Handling **data subject requests**
- Ensuring **secure hosting** and **HTTPS**
- Defining **retention** and **deletion policies**
- Maintaining **access controls** and **audit practices**

## 📄 License

This project is licensed under the **Apache License, Version 2.0**.

You may:
- Use, modify, and distribute the software
- Use it for **commercial** or **non-commercial** purposes

You must:
- Include the original **copyright notice**
- Include a copy of the **Apache 2.0 license**

See the LICENSE file for full details.

## 📌 Intended Use

- **SQL education and training**
- **Controlled lab environments**
- **Workshops and demonstrations**
- **Internal learning platforms**

Not suitable for:
- **Production databases**
- Processing **sensitive personal** or **regulated data**
- **High-availability** or **compliance-critical systems**
