"""Catalog curriculum used to seed / refresh public career roadmaps."""


def _sub(title: str, subtitle: str, duration: str, level: str, tags: list[str]) -> dict:
    return {
        "title": title,
        "subtitle": subtitle,
        "duration": duration,
        "level": level,
        "skill_tags": tags,
        "resources": [],
    }


def _phase(title: str, duration: str, content: str, subs: list[dict]) -> dict:
    return {
        "title": title,
        "content": content,
        "duration": duration,
        "lessons_count": len(subs),
        "projects_count": 0,
        "quizzes_count": 0,
        "lessons": [],
        "sub_steps": subs,
    }


FULL_STACK_DEVELOPER = {
    "title": "Full Stack Developer",
    "slug": "full-stack-developer",
    "aliases": [],
    "category": "Software Engineering",
    "level": "Intermediate",
    "industries": ["IT", "Software", "Startup"],
    "short_description": "Build complete web applications from frontend to backend",
    "long_description": (
        "Master both frontend and backend development to build complete web applications from scratch."
    ),
    "skill_tags": ["React", "Node.js", "Databases", "APIs", "DevOps", "Git"],
    "duration_months": "12-18 months",
    "salary_lpa": "₹4L",
    "growth_percent": "+22%",
    "openings_count": "150000+",
    "is_published": True,
    "is_featured": True,
    "is_trending": True,
    "sort_order": 1,
    "career_insights": {
        "top_hiring_companies": ["Google", "Amazon", "Microsoft", "Meta", "Netflix"],
        "in_demand_skills": ["React", "Node.js", "TypeScript", "AWS", "Docker"],
        "related_career_paths": ["Frontend Developer", "Backend Developer", "DevOps Engineer"],
    },
    "faqs": [
        {
            "question": "Do I need a computer science degree?",
            "answer": "No! Many successful developers are self-taught. Focus on building projects and gaining practical experience.",
        },
        {
            "question": "How much time should I dedicate daily?",
            "answer": "Aim for 2-3 hours daily for consistent progress. Quality practice matters more than quantity.",
        },
    ],
    "steps": [
        _phase(
            "Foundation",
            "2-3 months",
            "Learn the building blocks of web development before moving to frameworks.",
            [
                _sub(
                    "HTML & CSS Fundamentals",
                    "Learn the building blocks of web development",
                    "2-3 weeks",
                    "Beginner",
                    ["HTML5", "CSS3", "Responsive Design", "Flexbox", "Grid"],
                ),
                _sub(
                    "JavaScript Basics",
                    "Master JavaScript fundamentals and ES6+ features",
                    "4-5 weeks",
                    "Beginner",
                    ["Variables", "Functions", "Arrays", "Objects", "ES6+", "DOM Manipulation"],
                ),
                _sub(
                    "Version Control with Git",
                    "Learn Git and GitHub for code management",
                    "1-2 weeks",
                    "Beginner",
                    ["Git", "GitHub", "Branching", "Pull Requests", "Collaboration"],
                ),
            ],
        ),
        _phase(
            "Frontend Development",
            "3-4 months",
            "Build interactive user interfaces with modern frontend tools.",
            [
                _sub(
                    "React Fundamentals",
                    "Components, JSX, props, and state for interactive UIs",
                    "4-5 weeks",
                    "Intermediate",
                    ["React", "JSX", "Props", "State", "Hooks"],
                ),
                _sub(
                    "Routing, Forms & API Calls",
                    "Client-side routing, forms, and fetching backend data",
                    "3-4 weeks",
                    "Intermediate",
                    ["React Router", "Forms", "Fetch", "REST APIs"],
                ),
                _sub(
                    "State Management & Tooling",
                    "Global state, TypeScript, and a production frontend workflow",
                    "3-4 weeks",
                    "Intermediate",
                    ["TypeScript", "Context API", "Vite", "Testing"],
                ),
            ],
        ),
        _phase(
            "Backend Development",
            "3-4 months",
            "Create APIs, databases, and authentication for real applications.",
            [
                _sub(
                    "Node.js & Express",
                    "Build REST APIs and server-side application logic",
                    "4-5 weeks",
                    "Intermediate",
                    ["Node.js", "Express", "REST", "Middleware"],
                ),
                _sub(
                    "Databases",
                    "Model and query relational and document data",
                    "3-4 weeks",
                    "Intermediate",
                    ["SQL", "PostgreSQL", "MongoDB", "ORMs"],
                ),
                _sub(
                    "Auth & Security",
                    "Protect APIs with auth, validation, and common security practices",
                    "2-3 weeks",
                    "Intermediate",
                    ["JWT", "OAuth", "Validation", "OWASP"],
                ),
            ],
        ),
        _phase(
            "Full Stack Integration",
            "2-3 months",
            "Connect frontend and backend into one shippable product.",
            [
                _sub(
                    "API Integration",
                    "Connect the UI to backend services with clean data flow",
                    "3-4 weeks",
                    "Intermediate",
                    ["REST", "Error Handling", "Loading States"],
                ),
                _sub(
                    "End-to-end Project",
                    "Build a complete web application from scratch",
                    "4-5 weeks",
                    "Intermediate",
                    ["Full Stack", "CRUD", "File Uploads"],
                ),
                _sub(
                    "Testing & Quality",
                    "Add tests and reviews so the app is ready to ship",
                    "2-3 weeks",
                    "Intermediate",
                    ["Jest", "Integration Tests", "Code Review"],
                ),
            ],
        ),
        _phase(
            "DevOps & Deployment",
            "2-3 months",
            "Ship and operate the application in production.",
            [
                _sub(
                    "Linux & CI/CD",
                    "Automate build, test, and release pipelines",
                    "3-4 weeks",
                    "Intermediate",
                    ["Linux", "GitHub Actions", "CI/CD"],
                ),
                _sub(
                    "Containers",
                    "Package the stack with Docker for consistent deploys",
                    "2-3 weeks",
                    "Intermediate",
                    ["Docker", "Images", "Compose"],
                ),
                _sub(
                    "Cloud Deployment",
                    "Host the app and monitor it in production",
                    "3-4 weeks",
                    "Intermediate",
                    ["AWS", "Nginx", "Monitoring"],
                ),
            ],
        ),
    ],
}

DATA_SCIENTIST = {
    "title": "Data Scientist",
    "slug": "data-scientist",
    "aliases": ["ai-data-scientist"],
    "category": "AI & Data",
    "level": "Advanced",
    "industries": ["IT", "Fintech", "Analytics"],
    "short_description": "Turn data into actionable insights with ML and analytics",
    "long_description": (
        "Analyze complex data, build machine learning models, and drive data-driven decisions."
    ),
    "skill_tags": [
        "Python",
        "Machine Learning",
        "Statistics",
        "SQL",
        "Data Visualization",
        "Deep Learning",
    ],
    "duration_months": "15-20 months",
    "salary_lpa": "₹6L",
    "growth_percent": "+36%",
    "openings_count": "80000+",
    "is_published": True,
    "is_featured": True,
    "is_trending": True,
    "sort_order": 2,
    "career_insights": {
        "top_hiring_companies": ["Google", "Amazon", "Meta", "Netflix", "Apple"],
        "in_demand_skills": ["Python", "Machine Learning", "TensorFlow", "SQL", "Statistics"],
        "related_career_paths": ["Machine Learning Engineer", "Data Analyst", "AI Researcher"],
    },
    "faqs": [
        {
            "question": "Is a PhD required for data science?",
            "answer": "No, most data science roles require a bachelor's or master's degree. Focus on building a strong portfolio.",
        },
        {
            "question": "Should I learn R or Python?",
            "answer": "Python is more versatile and widely used in industry. Focus on Python first.",
        },
    ],
    "steps": [
        _phase(
            "Mathematics & Statistics",
            "3-4 months",
            "Build the math foundation used in machine learning and inference.",
            [
                _sub(
                    "Linear Algebra",
                    "Master vectors, matrices, and transformations",
                    "4-5 weeks",
                    "Intermediate",
                    ["Vectors", "Matrices", "Eigenvalues", "Transformations"],
                ),
                _sub(
                    "Calculus & Optimization",
                    "Learn derivatives, gradients, and optimization",
                    "4-5 weeks",
                    "Intermediate",
                    ["Derivatives", "Gradients", "Optimization", "Partial Derivatives"],
                ),
                _sub(
                    "Probability & Statistics",
                    "Understand distributions, hypothesis testing, and inference",
                    "4-6 weeks",
                    "Intermediate",
                    ["Probability", "Distributions", "Hypothesis Testing", "Bayesian Statistics"],
                ),
            ],
        ),
        _phase(
            "Programming & Tools",
            "3-4 months",
            "Write analysis code and work with real datasets.",
            [
                _sub(
                    "Python for Data Science",
                    "Write clean Python for analysis and modeling",
                    "4-5 weeks",
                    "Intermediate",
                    ["Python", "NumPy", "Pandas"],
                ),
                _sub(
                    "SQL & Data Wrangling",
                    "Query, clean, and join data from multiple sources",
                    "3-4 weeks",
                    "Intermediate",
                    ["SQL", "Joins", "Cleaning", "ETL"],
                ),
                _sub(
                    "Data Visualization",
                    "Communicate insights with charts and dashboards",
                    "3-4 weeks",
                    "Intermediate",
                    ["Matplotlib", "Seaborn", "Tableau"],
                ),
            ],
        ),
        _phase(
            "Machine Learning",
            "4-5 months",
            "Train, evaluate, and explain classical ML models.",
            [
                _sub(
                    "Supervised Learning",
                    "Regression and classification for labeled problems",
                    "5-6 weeks",
                    "Advanced",
                    ["Regression", "Classification", "scikit-learn"],
                ),
                _sub(
                    "Unsupervised Learning",
                    "Clustering, dimensionality reduction, and pattern finding",
                    "4-5 weeks",
                    "Advanced",
                    ["Clustering", "PCA", "Feature Engineering"],
                ),
                _sub(
                    "Model Evaluation",
                    "Choose metrics, validate models, and avoid leakage",
                    "3-4 weeks",
                    "Advanced",
                    ["Cross-validation", "Metrics", "Bias-Variance"],
                ),
            ],
        ),
        _phase(
            "Deep Learning & AI",
            "3-4 months",
            "Move from classical ML into neural networks and modern AI.",
            [
                _sub(
                    "Neural Networks",
                    "Understand layers, loss, and backpropagation",
                    "4-5 weeks",
                    "Advanced",
                    ["Neural Networks", "PyTorch", "TensorFlow"],
                ),
                _sub(
                    "Computer Vision & Sequence Models",
                    "Apply CNNs and sequence models to real tasks",
                    "4-5 weeks",
                    "Advanced",
                    ["CNN", "RNN", "Transformers"],
                ),
                _sub(
                    "Generative AI",
                    "Work with large language models and applied GenAI",
                    "3-4 weeks",
                    "Advanced",
                    ["LLMs", "Prompting", "RAG"],
                ),
            ],
        ),
        _phase(
            "Production & MLOps",
            "2-3 months",
            "Take models from notebook to production.",
            [
                _sub(
                    "Model Deployment",
                    "Serve models through APIs and batch jobs",
                    "3-4 weeks",
                    "Advanced",
                    ["FastAPI", "Docker", "Batch Inference"],
                ),
                _sub(
                    "Pipelines & Monitoring",
                    "Automate training and watch for drift",
                    "3-4 weeks",
                    "Advanced",
                    ["MLOps", "Airflow", "Monitoring"],
                ),
                _sub(
                    "Portfolio Projects",
                    "Ship case studies that hiring managers can review",
                    "2-3 weeks",
                    "Advanced",
                    ["Portfolio", "Storytelling", "GitHub"],
                ),
            ],
        ),
    ],
}

CATALOG_ROADMAPS = [FULL_STACK_DEVELOPER, DATA_SCIENTIST]
