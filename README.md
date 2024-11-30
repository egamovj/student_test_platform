# Student Test Platform

A web-based platform for conducting online tests with student authentication and result tracking.

## Features

- Student authentication with first and last name
- Interactive test-taking interface
- Immediate test results with correct/incorrect answers
- Admin panel for managing questions and viewing results
- Secure admin authentication

## Installation

1. Clone the repository
2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
- Windows:
```bash
venv\Scripts\activate
```
- Unix/MacOS:
```bash
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Create admin account:
```bash
python create_admin.py
```

6. Run the application:
```bash
python app.py
```

## Admin Access

- URL: /admin/login
- Default credentials:
  - Username: admin
  - Password: admin123

## License

MIT
