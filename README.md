# Oklahoma Sooners Dashboard

The **Oklahoma Sooners Dashboard** is a web application built with **Django** that uses the **CollegeFootballData API (CFBD)** to display real-time and seasonal statistics for the University of Oklahoma football team. It serves as a learning and practice project for integrating external APIs, managing live sports data, and implementing efficient caching mechanisms within the Django framework.

---

## Features

### Live Team Statistics
- Displays the current season’s overall and conference records.
- Automatically fetches and updates the latest data from the CollegeFootballData API.

### Upcoming and Previous Games
- Shows details for the next scheduled game (opponent, date, and time).
- Displays the most recent victory, including opponent and score information.

### Player Statistics
- Lists current offensive leaders for passing, rushing, and receiving yards.
- Displays each leader’s total yardage and corresponding touchdowns.
- Dynamically updates as new games are played.

### Caching System
- Implements per-team and per-season caching using Django’s built-in cache framework.
- Reduces API calls and improves load performance by storing fetched data in memory.
- Automatically refreshes data after a defined interval for real-time accuracy.

### Scalable Data Design
- Structured to support the inclusion of historical seasons.
- Designed for future persistence with long-term caching or database integration.

---

## Technologies Used

- **Backend:** Django (Python 3)
- **API:** CollegeFootballData API (CFBD)
- **Caching:** Django `LocMemCache` (with planned Redis integration)
- **Frontend:** Django Templates (HTML, CSS)
- **Environment:** Python virtual environment with `cfbd` and `pydantic`

---

## Setup and Installation

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/oklahoma-sooners-dashboard.git
cd oklahoma-sooners-dashboard
```
### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
### 4. Set Up Environment Variables
Create a `.env` file in the project root and add your CFBD API key:
```env
CFBD_API_KEY=your_api_key_here
```
### 5. Run the Development Server
```bash
python manage.py runserver
```
Open your browser and navigate to `http://127.0.0.1:8000/` to view the dashboard.

---

## Future Enhancements

- Historical season data storage and retrieval  
- Persistent caching using Redis or PostgreSQL  
- Enhanced box score breakdowns per game  
- Data visualization with charts and graphs  
- Automated daily cache refresh post-game  

---

## Project Goals

This project is built for educational purposes to:

- Practice consuming RESTful APIs in Python and Django.  
- Learn efficient data handling through caching and API integration.  
- Build scalable, maintainable web applications using a modular design approach.  



