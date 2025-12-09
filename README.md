# VotoSecure 🗳️

A modern, accessible online voting platform designed for university clubs and student organizations.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Django](https://img.shields.io/badge/Django-4.2-green.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![WCAG](https://img.shields.io/badge/WCAG-2.1%20AA-purple.svg)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Database Setup](#database-setup)
  - [Running Locally](#running-locally)
- [User Roles](#user-roles)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Deployment](#deployment)
- [Accessibility](#accessibility)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Overview

VotoSecure addresses the lack of a dedicated, user-friendly voting platform for university student organizations. Traditional methods like paper ballots, show of hands, or generic survey tools (Google Forms) are inefficient, lack proper access controls, and fail to provide the trustworthiness that democratic processes deserve.

**Key Goals:**
- Make voting accessible, engaging, and trustworthy
- Provide role-based access control for different user types
- Ensure anonymous voting while preventing duplicate votes
- Deliver a modern, mobile-responsive user experience
- Meet WCAG 2.1 AA accessibility standards

---

## Features

### 🔐 Authentication & Authorization
- Secure user registration and login
- Three-tier role-based access control (Super Admin, Election Manager, Voter)
- Session management with Django's built-in security

### 🏛️ Club Management
- Create and manage university clubs/organizations
- One manager per club (1:1 relationship)
- Membership request and approval workflow
- Active/inactive club status

### 🗳️ Election System
- Create club-specific or global (campus-wide) elections
- Time-based election scheduling with timezone support
- Multiple candidates per election
- Early election termination with reason documentation

### ✅ Voting
- **Anonymous voting** - Vote table has no voter_id (ballot secrecy)
- **Vote receipts** - Unique receipt codes for participation verification
- **One vote per election** - Enforced at database level
- Real-time results visualization with Chart.js

### 📊 Dashboards
- **Super Admin Dashboard**: Manage all clubs, elections, users, and view audit logs
- **Election Manager Dashboard**: Manage assigned club, approve members, create elections
- **Voter View**: Browse clubs, request membership, vote, view results

### 📝 Audit Logging
- Comprehensive tracking of all administrative actions
- Records user, action, timestamp, IP address, and details
- Supports accountability and dispute resolution

### ♿ Accessibility
- WCAG 2.1 AA compliant
- Keyboard navigation support
- Screen reader compatible (ARIA labels)
- High contrast colors
- Reduced motion support
- Skip links for navigation

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Django 4.2 (Python 3.10+) |
| **Database** | PostgreSQL 14+ (Supabase) |
| **Frontend** | Django Templates, Custom CSS, Chart.js |
| **Deployment** | Render.com |
| **Static Files** | WhiteNoise |

### Dependencies

```
Django>=4.2
psycopg2-binary>=2.9.9
dj-database-url>=2.1.0
python-dotenv>=1.0.0
whitenoise>=6.6.0
gunicorn>=21.2.0
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Git
- PostgreSQL database (or Supabase account)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ishanpathak3/votosecure
   cd votosecure
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   ```bash
   # macOS/Linux
   source venv/bin/activate
   
   # Windows
   venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://username:password@host:port/database

# Django
SECRET_KEY=your-super-secret-key-here
DEBUG=True


```


**Getting your Supabase DATABASE_URL:**
1. Go to [supabase.com](https://supabase.com) and create a project
2. Navigate to Project Settings → Database
3. Copy the connection string (URI format)
4. Replace `[YOUR-PASSWORD]` with your database password

### Database Setup

```bash
# Run migrations
python manage.py migrate

# Create a superuser (Super Admin)
python manage.py createsuperuser
```

### Running Locally

```bash
# Start the development server
python manage.py runserver

# Access the application
# http://127.0.0.1:8000
```

---

## User Roles

| Role | Permissions |
|------|-------------|
| **Super Admin** | Create/manage all clubs, assign managers, create global elections, manage all users, view audit logs |
| **Election Manager** | Manage one club, approve/reject membership requests, create club elections, view club analytics |
| **Voter** | Register, request club membership, vote in elections, view results, access vote receipts |

### Role Assignment

- **Super Admin**: Set `is_superuser=True` on user account
- **Election Manager**: Assigned by Super Admin when creating/editing a club
- **Voter**: Default role for all registered users

---

## Project Structure

```
votosecure/
├── config/                 # Project configuration
│   ├── settings.py         # Django settings
│   ├── urls.py             # Root URL configuration
│   └── wsgi.py             # WSGI application
├── accounts/               # User authentication app
│   ├── views.py            # Login, register, logout views
│   └── urls.py
├── clubs/                  # Club management app
│   ├── models.py           # Club, ClubMembership, AuditLog
│   ├── views.py            # Club CRUD, membership workflows
│   ├── urls.py
│   └── templatetags/       # Custom template tags
├── elections/              # Election and voting app
│   ├── models.py           # Election, Candidate, Vote, VoteReceipt
│   ├── views.py            # Election CRUD, voting logic
│   └── urls.py
├── dashboard/              # Admin and manager dashboards
│   ├── views.py            # Dashboard views, forms
│   └── urls.py
├── templates/              # HTML templates
│   ├── base.html           # Base template with navigation
│   ├── accounts/           # Auth templates
│   ├── clubs/              # Club templates
│   ├── elections/          # Election templates
│   └── dashboard/          # Dashboard templates
│       ├── admin/          # Super Admin dashboard
│       └── manager/        # Election Manager dashboard
├── static/
│   └── css/
│       └── styles.css      # Custom CSS with design system
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌──────────────────┐
│  auth_user  │──────<│ clubs_club  │──────<│ elections_election│
│             │ 1:1   │             │  1:N  │                  │
│ - id (PK)   │manager│ - id (PK)   │       │ - id (PK)        │
│ - username  │       │ - name      │       │ - title          │
│ - email     │       │ - manager_id│       │ - start_time     │
│ - password  │       │ - is_active │       │ - end_time       │
└─────────────┘       └─────────────┘       │ - club_id (FK)   │
      │                     │               └──────────────────┘
      │ 1:N                 │ 1:N                  │ 1:N
      ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐
│clubs_clubmembership│  │elections_candidate│  │ elections_vote  │
│                  │  │                  │  │                 │
│ - club_id (FK)   │  │ - election_id(FK)│  │ - election_id   │
│ - user_id (FK)   │  │ - name           │  │ - candidate_id  │
│ - status         │  │ - description    │  │ - timestamp     │
│ - requested_at   │  └──────────────────┘  │ ⚠️ NO voter_id  │
└──────────────────┘                        └─────────────────┘
      │                                            │
      │                                            │ Separate!
      ▼                                            ▼
┌──────────────────┐                    ┌───────────────────┐
│ clubs_auditlog   │                    │elections_votereceipt│
│                  │                    │                   │
│ - user_id (FK)   │                    │ - voter_id (FK)   │
│ - action         │                    │ - election_id(FK) │
│ - timestamp      │                    │ - receipt_code    │
│ - ip_address     │                    │ - voted_at        │
└──────────────────┘                    └───────────────────┘
```

### Anonymous Voting Design

The `elections_vote` table intentionally has **no voter_id** to ensure ballot secrecy. The separate `elections_votereceipt` table tracks who voted (not what they voted for), enabling:
- Prevention of duplicate voting
- Voter verification via receipt codes
- Complete ballot anonymity

---

## Deployment

### Deploy to Render.com

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Create Render Web Service**
   - Connect your GitHub repository
   - Set environment: Python 3
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn config.wsgi:application`

3. **Add Environment Variables in Render**
   - `DATABASE_URL` - Your Supabase connection string
   - `SECRET_KEY` - Generate a secure key
   - `DEBUG` - Set to `False`
   - `ALLOWED_HOSTS` - Your Render URL

4. **Run Migrations**
   - Add to build command: `pip install -r requirements.txt && python manage.py migrate`

### Production Checklist

- [ ] `DEBUG=False`
- [ ] Secure `SECRET_KEY`
- [ ] `ALLOWED_HOSTS` configured
- [ ] Database backups enabled (automatic with Supabase)
- [ ] HTTPS enabled (automatic with Render)
- [ ] Static files collected (`python manage.py collectstatic`)

---

## Accessibility

VotoSecure is designed with accessibility as a core principle, following WCAG 2.1 AA guidelines:

| Feature | Implementation |
|---------|----------------|
| **Keyboard Navigation** | All interactive elements accessible via Tab, Enter, Arrow keys |
| **Screen Readers** | Semantic HTML, ARIA labels, proper heading hierarchy |
| **Color Contrast** | Minimum 4.5:1 contrast ratio for text |
| **Focus Indicators** | Visible 3px focus rings on all interactive elements |
| **Skip Links** | "Skip to main content" link for keyboard users |
| **Reduced Motion** | Respects `prefers-reduced-motion` media query |
| **Form Labels** | All inputs have associated labels with required indicators |
| **Error Messages** | Clear, descriptive error messages with icons |

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Write comments for complex logic

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Ishan Pathak

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Acknowledgments

- **Project Sponsor**: Dr. Ankit Shrestha, Assistant Professor, University of Mississippi
- **Course**: CSCI 487 - Senior Project, Fall 2025
- **Department**: Computer and Information Science, University of Mississippi

### Resources Used

- [Django Documentation](https://docs.djangoproject.com/)
- [Supabase Documentation](https://supabase.com/docs)
- [Render.com Documentation](https://render.com/docs)
- [Chart.js Documentation](https://www.chartjs.org/docs/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

## Contact

**Ishan Pathak**  
📧 ipathak@go.olemiss.edu  
🔗 [GitHub](https://github.com/ishanpathak3)

---

<p align="center">
  Made with ❤️ at the University of Mississippi
</p>