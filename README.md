# GreenTechHub
![Python version](https://img.shields.io/badge/python-3.12-blue.svg)
![GitHub release](https://img.shields.io/github/v/release/GreenMachine582/GreenTechHub?include_prereleases)
![GitHub deployments](https://img.shields.io/github/deployments/GreenMachine582/GreenTechHub/Production)

## Table of Contents
- [Introduction](#introduction)
- [Key Features](#key-features)
- [Milestones](#milestones)
- [Docker](#docker)
- [License](#license)

---

## Introduction
**GreenTechHub** is an interactive platform powered by **Python** and **Django**, designed to bring together technology 
enthusiasts, game developers, and creative minds. At its core, GreenTechHub serves as a hub for showcasing innovative 
projects, exploring a curated library of games, and accessing embedded services that enhance user experiences.

## Key Features
* **Project Showcase:** Highlight and share your creative endeavors, from game development projects to Python-powered 
tools, with a community of like-minded individuals.
* **Game Library:** A rich, organised collection of games ranging from indie creations to tech demos, all accessible 
through an intuitive interface.
* **Embedded Services:** Tools and APIs integrated seamlessly into the platform, offering users enhanced 
functionalities for projects and development workflows.

With GreenTechHub, users can explore, learn, and create in a vibrant ecosystem, making it a one-stop destination for 
showcasing innovation, sharing ideas, and building connections. Whether you're a seasoned developer or an aspiring 
creator, GreenTechHub is your space to thrive.

## Milestones
* **v1.0 (Initial Release):**
  - Launched core platform with project showcase, game library, and embedded services.
  - User authentication and profile management.
  - Responsive design with intuitive navigation.

* **v1.1 (Community Features):**
  - Added user comments and feedback on showcased projects.
  - Implemented project rating and upvote system.
  - Improved search and filter options in the game library.

* **v2.0 (API & Integration Expansion):**
  - Introduced API access for external integrations.
  - Enhanced embedded services with new tools for developers.
  - Implemented user dashboards for project analytics.

## Docker

To get started with running GreenTechHub in a Docker environment:

### 1. Build the Base Image

```bash
docker build -f Dockerfile.python -t pybase:3.11 .
```

### 2. Start the Application
This command will build and start all required services in detached mode:

```bash
docker-compose up --build -d
```

### 3. Stop and Remove Containers
To shut down the services and remove containers:

```bash
docker-compose down
```

### 4. Run Migrations & Create Superuser (Optional)
After the initial startup, you may want to run database migrations and create an admin user:

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

### 5. Rebuild Without Cache (If Needed)
```bash
docker-compose build --no-cache
```

### 6. View Logs
```bash
docker-compose logs -f
```
> **NOTE:** If you're using environment variables (e.g. .env), ensure that your docker-compose.yml is configured to use them properly.

## License
GreenTechHub is licensed under the MIT License, see [LICENSE](LICENSE) for more information.
