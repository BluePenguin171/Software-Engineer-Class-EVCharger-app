# Software-Engineer-Class-EVCharger-app
# ⚡ EV Charger Application

An **academic Software Engineering project** for finding and reserving electric vehicle (EV) charging stations.

The application uses the user's location to identify nearby charging stations and displays them on a map. Users can view available chargers, create reservations, and cancel existing reservations.

The system is composed of a **Flutter frontend** and a **FastAPI backend**, with additional CLI and documentation components.

---

## 📌 Project Overview

The goal of this project is to demonstrate the design and implementation of a full-stack location-based application.

The application provides a simple workflow:

```text
User
 │
 ▼
Flutter Frontend
 │
 │ REST API
 ▼
FastAPI Backend
 │
 ▼
Application Data
 │
 ├── Charging Stations
 └── Reservations
```

The frontend communicates with the backend through a REST API.

---

## ✨ Features

### 📍 Charging Station Search

* Uses the user's location to find nearby EV charging stations.
* Displays charging stations on a map.
* Allows users to explore available charging locations.


### 🔌 Charging Station Information

Users can view information about available charging stations and use the application to determine which station is suitable for their needs.

### 📅 Reservations

Users can:

* Create a reservation for a charging station.
* View their reservation.
* Cancel an existing reservation.

### 🔄 Frontend / Backend Communication

The Flutter application communicates with the FastAPI backend through REST API requests.

---

## 🏗️ Technologies

| Component       | Technology              |
| --------------- | ----------------------- |
| Frontend        | Flutter / Dart          |
| Backend         | Python / FastAPI        |
| API             | REST                    |
| Maps            | Location & map services |
| API Testing     | Postman                 |
| Version Control | Git / GitHub            |

---

## 📂 Project Structure

```text
Software-Engineer-Class-EVCharger-app/
│
├── back-end/
│   └── FastAPI backend
│
├── front-end/
│   └── Flutter application
│
├── cli-client/
│   └── CLI client
│
├── documentation/
│   └── Project documentation
│
├── .gitignore
├── LICENSE
└── README.md
```

---

# 🧪 API Testing with Postman

The backend API can be tested independently from the Flutter application using **Postman**.

Postman allows the API endpoints to be tested directly by sending HTTP requests to the FastAPI backend.


# 🔄 Application Workflow

A typical user workflow is:

```text
1. Open Application
        │
        ▼
2. Get User Location
        │
        ▼
3. Find Nearby Charging Stations
        │
        ▼
4. Display Stations on Map
        │
        ▼
5. Select Charging Station
        │
        ▼
6. Create Reservation
        │
        ▼
7. Manage Reservation
        │
        └──────► Cancel Reservation
```

---

# 🧩 System Architecture

The application follows a client-server architecture.

```text
┌─────────────────────────┐
│      Flutter App        │
│                         │
│  • User Interface       │
│  • Map                  │
│  • Location             │
│  • Reservations         │
└────────────┬────────────┘
             │
             │ REST API
             ▼
┌─────────────────────────┐
│      FastAPI API        │
│                         │
│  • API Endpoints        │
│  • Business Logic       │
│  • Reservation Logic    │
│  • Charging Stations    │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│       Data Layer        │
│                         │
│  • Stations             │
│  • Reservations         │
│  • Users / Data         │
└─────────────────────────┘
```

---


# 📚 Documentation

Additional project documentation can be found in:

```text
documentation/
```

This section contains supporting material related to the design and development of the project.

---


## 👨‍🎓 Academic Project

**EV Charger Application**

Developed as part of a Software Engineering academic project.

Built with ❤️ using **Flutter** and **FastAPI**.
