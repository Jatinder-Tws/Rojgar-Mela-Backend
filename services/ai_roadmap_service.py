import json
import logging
import re
import uuid
from typing import Dict, List, Optional
from json import JSONDecodeError
from models.user import User
from config import settings
from services.ai_service import get_ai, OpenAIAdapter

logger = logging.getLogger(__name__)


class AIRoadmapService:
    def __init__(self):
        self.prompt_version = "1.1"
        self._allowed_difficulties = {"beginner", "intermediate", "advanced"}
        self._allowed_resource_types = {"course", "article", "video", "project", "certification"}
        self._role_skill_map = {
            "devops": ["Linux", "Docker", "Kubernetes", "CI/CD", "Terraform", "AWS", "Monitoring", "GitOps"],
            "sre": ["Linux", "Kubernetes", "Prometheus", "Grafana", "SLI/SLO", "Incident Response", "Automation", "Python"],
            "frontend": ["JavaScript", "TypeScript", "React", "Next.js", "State Management", "Testing", "Accessibility", "Performance"],
            "backend": ["APIs", "Databases", "Authentication", "Caching", "Message Queues", "System Design", "Testing", "Security"],
            "data": ["SQL", "Python", "Pandas", "Data Modeling", "ETL", "Visualization", "Statistics", "Airflow"],
            "ml": ["Python", "Machine Learning", "Feature Engineering", "Model Evaluation", "Deep Learning", "MLOps", "Deployment", "Experiment Tracking"],
            "cloud": ["AWS", "Azure", "GCP", "Infrastructure as Code", "Kubernetes", "Networking", "Security", "Cost Optimization"],
            "full stack": ["JavaScript", "TypeScript", "React", "Node.js", "APIs", "Databases", "Testing", "Deployment"],
        }

    def _get_primary_ai_for_json(self):
        """
        Prefer OpenAI JSON mode for strict JSON reliability when key is present.
        """
        if settings.OPENAI_API_KEY:
            return OpenAIAdapter()
        return get_ai()
    
    async def suggest_roles(self, user: User) -> List[str]:
        """
        Suggest potential career roles based on user's current profile
        """
        # Try to get data from user or portfolio backref
        user_skills = getattr(user, 'skills', [])
        user_experience = getattr(user, 'experience', '0')
        user_industry = getattr(user, 'industry', '')
        user_current_role = (getattr(user, 'job_role', '') or '').strip()

        # Merge skills from user and portfolio for maximum context
        all_skills = set()
        if user_skills and isinstance(user_skills, list):
            for s in user_skills:
                if isinstance(s, str): all_skills.add(s.strip())
                elif isinstance(s, dict): all_skills.add(s.get('name', '').strip())

        portfolio = getattr(user, 'portfolio', None)
        if portfolio and hasattr(portfolio, 'skills'):
            portfolio_skills = portfolio.skills or []
            for s in portfolio_skills:
                if isinstance(s, str): all_skills.add(s.strip())
                elif isinstance(s, dict): all_skills.add(s.get('name', '').strip())
        
        user_skills = sorted([s for s in all_skills if s])
            
        # Prioritize headline if current_role/job_role is not specified or too generic
        portfolio_role = (getattr(portfolio, 'current_role', '') or '').strip()
        headline = (getattr(portfolio, 'headline', '') or '').strip()
        
        if not user_current_role:
            user_current_role = portfolio_role or headline
        
        if not user_industry:
            user_industry = headline or (getattr(portfolio, 'bio', None) or '')[:100]
        
        if hasattr(portfolio, 'total_experience_years') and portfolio.total_experience_years is not None:
            user_experience = str(portfolio.total_experience_years)

        # Extract brief work history for trajectory context
        work_history = []
        if portfolio and hasattr(portfolio, 'work_experiences'):
            experiences = portfolio.work_experiences or []
            for exp in experiences[:3]: # Last 3 roles
                role = exp.get('role', 'Unknown Role')
                company = exp.get('company', 'Unknown Company')
                work_history.append(f"{role} at {company}")
        
        user_bio = getattr(portfolio, 'bio', '') or ''

        system_prompt = """
        You are an expert career counselor and growth strategist. Based on a user's current skills, experience, and career trajectory, suggest 5-8 relevant target job roles they could progress into.
        Focus on "high-growth" roles that represent a logical step UP or a strategic pivot based on their background.
        
        Consider:
        1. Vertical progression (e.g., Developer -> Lead -> Architect)
        2. Horizontal pivots to high-demand niche roles (e.g., Backend -> DevOps/SRE)
        3. Management tracks (e.g., Senior Dev -> Engineering Manager)
        
        Return the response ONLY as a JSON object with a "suggested_roles" key containing a list of strings.
        Example: {"suggested_roles": ["Frontend Lead", "Full Stack Developer", "Software Architect"]}
        """

        user_prompt = f"""
        USER PROFILE:
        - Current Skills: {', '.join(user_skills) if user_skills else 'None specified'}
        - Total Experience: {user_experience} years
        - Current Role/Headline: {user_current_role or 'Not specified'}
        - Industry: {user_industry or 'Not specified'}
        - Recent Career Path: {', '.join(work_history) if work_history else 'Not specified'}
        - Professional Bio: {user_bio[:300] if user_bio else 'Not specified'}
        
        Suggest 5-8 strategic target roles for their next career move.
        """

        try:
            logger.info(f"Calling AI to suggest roles with focus: {user_current_role}, skills: {user_skills}")
            ai = get_ai()
            response = await ai.chat_completion(system_prompt, user_prompt)
            
            logger.debug(f"AI Response for suggested roles: {response}")
            
            # Clean up markdown
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            data = json.loads(response.strip())
            
            # Handle different possible JSON structures
            if isinstance(data, dict):
                roles = data.get("suggested_roles", [])
                if not roles and "roles" in data:
                    roles = data["roles"]
            elif isinstance(data, list):
                # AI might return a list of strings directly
                roles = data
            else:
                roles = []
            
            # Filter and clean roles
            roles = [str(r).strip() for r in roles if r]
            logger.info(f"AI suggested roles: {roles}")
            return roles
            
        except Exception as e:
            logger.error(f"Error suggesting roles in AIRoadmapService: {e}", exc_info=True)
            # Context-aware fallback roles
            role_lower = (user_current_role or "").lower()
            if "frontend" in role_lower:
                return ["Senior Frontend Developer", "Full Stack Developer", "Frontend Architect", "UI/UX Designer", "Product Designer"]
            elif "backend" in role_lower:
                return ["Senior Backend Developer", "Full Stack Developer", "System Architect", "DevOps Engineer", "Backend Lead"]
            elif "data" in role_lower:
                return ["Data Scientist", "Machine Learning Engineer", "Data Architect", "Senior Data Analyst", "AI Researcher"]
            elif "devops" in role_lower:
                return ["SRE Engineer", "Cloud Architect", "Senior DevOps Engineer", "Platform Engineer", "Security Engineer"]
            elif "ui" in role_lower or "ux" in role_lower or "design" in role_lower:
                return ["Senior UI/UX Designer", "Product Designer", "Design Lead", "Creative Director", "UX Architect"]
            
            # Generic tech fallback
            return [
                "Senior Software Engineer",
                "Tech Lead",
                "Software Architect",
                "Product Manager",
                "Engineering Manager"
            ]

    async def generate_roadmap(
        self,
        user: User,
        target_role: str,
        current_level: Optional[str] = None,
        target_level: Optional[str] = None,
        learning_preferences: Optional[Dict] = None,
        time_commitment: Optional[str] = None,
        focus_areas: Optional[List[str]] = None,
        current_skills: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate AI-powered roadmap based on user profile and preferences
        """
        
        # Extract user skills and experience
        user_skills = getattr(user, 'skills', [])
        user_experience = getattr(user, 'experience', '0')
        user_industry = getattr(user, 'industry', '')
        user_current_role = (getattr(user, 'job_role', '') or '').strip()
        current_skills = self._normalize_skills_input(current_skills)

        # Check portfolio if available
        portfolio = getattr(user, 'portfolio', None)
        if not current_skills:
            if not user_skills and portfolio and hasattr(portfolio, 'skills'):
                portfolio_skills = portfolio.skills or []
                user_skills = [s.get('name', '').strip() for s in portfolio_skills if isinstance(s, dict) and s.get('name')]
            current_skills = user_skills
        
        if portfolio:
            portfolio_role = (getattr(portfolio, 'current_role', '') or '').strip()
            headline = (getattr(portfolio, 'headline', '') or '').strip()

            if not user_current_role:
                user_current_role = portfolio_role or headline
            
            if not user_industry:
                user_industry = headline or (getattr(portfolio, 'bio', None) or '')[:100]
            
            if hasattr(portfolio, 'total_experience_years') and portfolio.total_experience_years is not None:
                user_experience = str(portfolio.total_experience_years)
        
        # Build the AI prompt
        role_context = self._build_role_context(target_role, current_skills or [])
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            current_skills=current_skills,
            experience_level=user_experience,
            target_role=target_role,
            current_level=current_level or self._infer_current_level(user_experience),
            target_level=target_level or "senior",
            industry=user_industry,
            learning_preferences=learning_preferences,
            time_commitment=time_commitment,
            focus_areas=focus_areas,
            role_context=role_context
        )
        
        try:
            # Call AI service
            ai = self._get_primary_ai_for_json()
            ai_response = await ai.chat_completion(system_prompt, user_prompt)
            
            # Parse and validate AI response
            try:
                roadmap_data = self._parse_ai_response(ai_response)
            except ValueError:
                # Attempt to repair the malformed JSON first.
                repaired_response = await self._repair_json_with_ai(ai, ai_response)
                try:
                    roadmap_data = self._parse_ai_response(repaired_response)
                except ValueError:
                    # Retry once with a stricter prompt if repair still fails.
                    retry_prompt = user_prompt + (
                        "\n\nIMPORTANT: Return strictly valid JSON only. "
                        "Do not include markdown fences, comments, or trailing text."
                    )
                    ai_response_retry = await ai.chat_completion(system_prompt, retry_prompt)
                    roadmap_data = self._parse_ai_response(ai_response_retry)
            
            # Normalize to backend/frontend contract and enhance resources
            roadmap_data = self._normalize_roadmap_payload(roadmap_data)
            roadmap_data = self._enforce_gap_alignment(roadmap_data, current_skills or [], role_context)
            roadmap_data = self._enhance_with_resources(roadmap_data, target_role)

            if self._needs_role_specific_regeneration(roadmap_data, target_role):
                logger.info("Roadmap quality gate triggered for target_role=%s. Regenerating with stricter role focus.", target_role)
                strict_role_prompt = user_prompt + (
                    f"\n\nCRITICAL QUALITY REQUIREMENTS:\n"
                    f"- This roadmap is specifically for '{target_role}'.\n"
                    f"- Include at least 8 milestones and at least 18 unique skills.\n"
                    f"- Do not use generic milestone titles like Foundation Skills/Practical Experience.\n"
                    f"- Each milestone title and skills should be role-specific for '{target_role}'.\n"
                    f"- Include these role-focus keywords naturally across milestones: "
                    f"{', '.join(self._role_focus_keywords(target_role))}.\n"
                    f"- Return valid JSON only."
                )
                strict_response = await ai.chat_completion(system_prompt, strict_role_prompt)
                strict_data = self._parse_ai_response(strict_response)
                roadmap_data = self._normalize_roadmap_payload(strict_data)
                roadmap_data = self._enforce_gap_alignment(roadmap_data, current_skills or [], role_context)
                roadmap_data = self._enhance_with_resources(roadmap_data, target_role)
            
            return roadmap_data
            
        except Exception as e:
            logger.error(f"Error generating roadmap: {e}")
            # Return fallback roadmap
            return self._normalize_roadmap_payload(
                self._generate_fallback_roadmap(target_role, current_skills or user_skills)
            )

    def _normalize_skills_input(self, current_skills: Optional[List[str]]) -> List[str]:
        """
        Normalize current_skills to a clean list of skill strings.
        Handles accidental string payloads like "{HTML,CSS,React}".
        """
        if current_skills is None:
            return []
        if isinstance(current_skills, list):
            cleaned = [str(s).strip() for s in current_skills if str(s).strip()]
            if cleaned and all(len(x) == 1 for x in cleaned):
                joined = "".join(cleaned).strip().strip("{}[]")
                if joined:
                    return [p.strip().strip("'\"") for p in joined.split(",") if p.strip().strip("'\"")]
            return cleaned
        if isinstance(current_skills, str):
            text = current_skills.strip().strip("{}[]")
            if not text:
                return []
            parts = [p.strip().strip("'\"") for p in text.split(",")]
            return [p for p in parts if p]
        return []
    
    def _build_system_prompt(self) -> str:
        return """
            You are an expert career counselor, senior technical mentor, and curriculum architect.

            Your task is to create a highly personalized, role-specific learning roadmap for a job seeker.

            CRITICAL INSTRUCTIONS:
            1. Every roadmap must be UNIQUE for the requested target role.
            2. Resources MUST be specifically chosen for the target role and milestone topic.
            3. NEVER reuse the same generic resources across unrelated roles.
            4. Do NOT repeat the same resource URL in multiple milestones unless absolutely necessary.
            5. Each milestone must contain resources that directly match the concepts taught in that milestone.
            6. If the target role changes (e.g., React Developer vs Python Developer vs DevOps Engineer), the resources must also change accordingly.
            7. Prefer official documentation, well-known free courses, and trusted learning platforms.
            8. Use only real and publicly accessible URLs.
            9. Avoid generic resources such as:
            - "Official Documentation"
            - "YouTube Tutorial"
            - "Udemy Course"
            without naming a specific course.
            10. Resource titles must be specific and descriptive.

            ROLE-SPECIFIC RESOURCE RULES:
            - React Developer → React Docs, Vite Docs, Redux Toolkit Docs, Next.js Docs.
            - Python Developer → Python Docs, FastAPI Docs, Django Docs, Real Python.
            - DevOps Engineer → Docker Docs, Kubernetes Docs, Terraform Docs, AWS Docs.
            - Data Scientist → Pandas Docs, NumPy Docs, Scikit-learn Docs, Kaggle.
            - Mobile Developer → Android Developers, React Native Docs, Flutter Docs.
            - Java Developer → Oracle Java Docs, Spring Docs, Hibernate Docs.
            - MERN Developer → MongoDB Docs, Express Docs, React Docs, Node.js Docs.
            - UI/UX Designer → Figma Learn, Nielsen Norman Group, Material Design.

            ROADMAP STRUCTURE:
            1. Create 8-10 highly detailed milestones.
            2. Group milestones into 4-5 logical stages:
            - Foundation
            - Core Development
            - Applied Engineering
            - Advanced Architecture
            - Career Acceleration
            3. Each phase (Beginner, Intermediate, Advanced) must contain at least 2 milestones.
            4. Tailor content to the user's current skills and avoid repeating known topics.
            5. Provide a complete career transformation plan.

            EACH MILESTONE MUST INCLUDE:
            - title
            - description (2-3 detailed sentences)
            - stage_title
            - stage_order
            - order_num
            - difficulty (beginner|intermediate|advanced)
            - skills (6-8 specific tools, frameworks, concepts)
            - estimated_time
            - dependencies
            - resources (3-4 unique, role-specific resources)

            RESOURCE REQUIREMENTS:
            Each resource must include:
            - title (specific course/article/project name)
            - type (course|article|video|project|certification)
            - url (real public URL)
            - platform
            - duration
            - difficulty
            - description
            - is_free
            - rating

            RESOURCE SELECTION RULES:
            1. At least one official documentation resource.
            2. At least one hands-on project or practical resource.
            3. At least one structured course or tutorial.
            4. No duplicate URLs within the roadmap.
            5. Titles must include exact course or documentation names.
            6. Resources must directly correspond to the milestone topic.

            EXAMPLES OF GOOD RESOURCES:
            - "React Official Documentation – Learn React"
            - "Full Stack Open Part 2 – Communicating with Server"
            - "Redux Toolkit Official Quick Start"
            - "FastAPI Official Tutorial"
            - "Docker Getting Started Guide"
            - "Kubernetes Basics Interactive Tutorial"

            EXAMPLES OF BAD RESOURCES:
            - "Official Documentation"
            - "YouTube Course"
            - "Online Tutorial"
            - "Example Course"

            TOP-LEVEL OUTPUT:
            - estimated_duration
            - market_based_salary (India, INR)
            - skills_to_develop (14-20 specific technologies and methodologies)
            - milestones

            SALARY FORMAT:
            {
            "currency": "INR",
            "entry_level": "INR 4,00,000 - 8,00,000 per year",
            "mid_level": "INR 8,00,000 - 18,00,000 per year",
            "senior_level": "INR 18,00,000 - 40,00,000 per year",
            "average": "INR 12,00,000 per year"
            }

            IMPORTANT:
            - Output VALID JSON only.
            - Do not include markdown.
            - Do not include explanations outside JSON.
            - Ensure each target role gets distinct and relevant resources.
            - Ensure no repeated generic resources across milestones.

            FORMAT:
            {
            "roadmap": {
                "estimated_duration": "X months",
                "market_based_salary": {
                "currency": "INR",
                "entry_level": "INR X - Y per year",
                "mid_level": "INR X - Y per year",
                "senior_level": "INR X - Y per year",
                "average": "INR X per year"
                },
                "skills_to_develop": ["skill1", "skill2"],
                "milestones": [
                {
                    "title": "Milestone Title",
                    "description": "Detailed description...",
                    "stage_title": "Foundation",
                    "stage_order": 1,
                    "order_num": 1,
                    "difficulty": "beginner",
                    "skills": ["skill1", "skill2"],
                    "estimated_time": "2-3 weeks",
                    "dependencies": [],
                    "resources": [
                    {
                        "title": "Specific Resource Name",
                        "type": "course",
                        "url": "https://real-url.com",
                        "platform": "Platform Name",
                        "duration": "10 hours",
                        "difficulty": "beginner",
                        "description": "Specific explanation of why this resource is useful.",
                        "is_free": true,
                        "rating": 4.8
                    }
                    ]
                }
                ]
            }
            }
            """
    
#     def _build_system_prompt(self) -> str:
#         return """
# You are an expert career counselor and technical trainer. Create a personalized learning roadmap for a job seeker.
# Generate a structured learning roadmap with the following requirements:

# 1. Create 8-10 highly detailed milestones, grouped into 4-5 logical "stages" (e.g., "Foundation", "Core Development", "Advanced Engineering", "Production Readiness", "Career Acceleration").
# 2. Each milestone must include:
#    - A clear, professional, and actionable title.
#    - A deep, 2-3 sentence description of exactly what concepts will be mastered.
#    - stage_title: The name of the group this milestone belongs to.
#    - stage_order: The sequence number of the stage (1, 2, 3...).
#    - difficulty: beginner|intermediate|advanced.
#    - Specific skills to develop: PROVIDE AT LEAST 6-8 SPECIFIC technical competencies or tools.
#    - Estimated time to complete (e.g., "2-3 weeks").
#    - 3-4 high-quality learning resources.
#    - Dependencies on previous milestones (if any).

# 3. IMPORTANT: Do NOT use generic terms like "Technical Skills", "Soft Skills", or "Portfolio Development". Every field must contain specific, industry-relevant information.
# 4. For the top-level "skills_to_develop", provide a comprehensive list of 14-20 specific tools, frameworks, and methodologies.
# 5. Tailor the roadmap based on the user's current skills to ensure they are learning new things, not repeating known concepts.
# 6. The roadmap should feel like a complete career transformation plan, not just a list of courses.
# 7. Include a top-level "market_based_salary" object for the target role with realistic market estimates in India.
# 8. Currency MUST be INR, format salary as monthly ranges like "INR 6,00,000 - 9,00,000 per year" or monthly where appropriate.
# 9. IMPORTANT for resources: provide real, publicly accessible URLs from trusted learning platforms (no placeholder URLs like example.com).
# 10. MANDATORY PROGRESSION: The roadmap must include all three career phases in sequence:
#    - Beginner phase (fundamentals)
#    - Intermediate phase (applied engineering)
#    - Advanced phase (architecture, optimization, leadership/project ownership)
# 11. Each phase must contain at least 2 milestones.

# FORMAT YOUR RESPONSE AS VALID JSON:
# {
#     "roadmap": {
#         "estimated_duration": "X months",
#         "market_based_salary": {
#             "currency": "INR",
#             "entry_level": "INR X - Y per year",
#             "mid_level": "INR X - Y per year",
#             "senior_level": "INR X - Y per year",
#             "average": "INR X per year"
#         },
#         "skills_to_develop": ["skill1", "skill2", ...],
#         "milestones": [
#             {
#                 "title": "Milestone Title",
#                 "description": "Detailed description...",
#                 "stage_title": "Stage Name (e.g. Foundation, Advanced)",
#                 "stage_order": 1,
#                 "order_num": 1,
#                 "difficulty": "intermediate",
#                 "skills": ["skill1", "skill2"],
#                 "estimated_time": "2-3 weeks",
#                 "dependencies": [],
#                 "resources": [
#                     {
#                         "title": "Resource Title",
#                         "type": "course|article|video|project|certification",
#                         "url": "https://real-course-link.example",
#                         "platform": "Platform Name",
#                         "duration": "X hours",
#                         "difficulty": "beginner|intermediate|advanced",
#                         "description": "Resource description",
#                         "is_free": true,
#                         "rating": 4.5
#                     }
#                 ]
#             }
#         ]
#     }
# }
# """

    def _build_user_prompt(
        self,
        current_skills: List[str],
        experience_level: str,
        target_role: str,
        current_level: str,
        target_level: str,
        industry: str,
        learning_preferences: Optional[Dict],
        time_commitment: Optional[str],
        focus_areas: Optional[List[str]],
        role_context: Optional[Dict] = None
    ) -> str:
        """
        Build the user prompt for roadmap generation
        """
        
        prompt = f"""
            USER PROFILE:
            - Current Skills: {', '.join(current_skills) if current_skills else 'None specified'}
            - Experience Level: {experience_level} years
            - Industry: {industry}
            - Target Role: {target_role}
            - Current Level: {current_level}
            - Target Level: {target_level}
            - Time Commitment: {time_commitment or 'Not specified'}
            - Focus Areas: {', '.join(focus_areas) if focus_areas else 'None specified'}

            LEARNING PREFERENCES:
            {json.dumps(learning_preferences or {}, indent=2)}

            ROLE GAP ANALYSIS:
            {json.dumps(role_context or {}, indent=2)}

            IMPORTANT:
            - Prioritize identified_skill_gaps over already known current skills.
            - Avoid repeating already-known skills unless required as a bridge.
            - Make roadmap content distinct for this target role.

            Generate the roadmap as JSON.
            Ensure salary figures are India-specific and in INR.
            """
        return prompt
    
    def _parse_ai_response(self, ai_response: str) -> Dict:
        """
        Parse and validate AI response
        """
        try:
            response = self._clean_ai_response(ai_response)
            roadmap_data = self._safe_json_load(response)
            
            # Validate structure
            if "roadmap" not in roadmap_data:
                # Sometimes the AI might return the object directly without the "roadmap" key
                if "milestones" in roadmap_data:
                    return roadmap_data
                raise ValueError("Invalid AI response structure")
            
            return roadmap_data["roadmap"]
            
        except JSONDecodeError as e:
            logger.error(f"Failed to parse AI response JSON: {e}")
            raise ValueError("Invalid JSON response from AI")

    def _clean_ai_response(self, ai_response: str) -> str:
        """
        Remove common wrapper formatting and isolate a JSON object payload.
        """
        response = ai_response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        return response.strip()

    def _safe_json_load(self, text: str) -> Dict:
        """
        Parse JSON robustly by first trying direct parse, then extracting the
        first top-level object in case of extra prose around JSON.
        """
        try:
            return json.loads(text)
        except JSONDecodeError:
            repaired = self._repair_common_json_issues(text)
            if repaired != text:
                try:
                    return json.loads(repaired)
                except JSONDecodeError:
                    pass

            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                sliced = text[start : end + 1]
                try:
                    return json.loads(sliced)
                except JSONDecodeError:
                    repaired_sliced = self._repair_common_json_issues(sliced)
                    return json.loads(repaired_sliced)
            raise

    def _repair_common_json_issues(self, text: str) -> str:
        """
        Best-effort cleanup for frequently malformed LLM JSON.
        """
        repaired = text
        # Normalize quotes frequently produced by rich text formatters.
        repaired = repaired.replace("“", "\"").replace("”", "\"").replace("’", "'")
        # Remove trailing commas before object/array close.
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        # Replace Python-like booleans/null with JSON literals.
        repaired = re.sub(r"\bNone\b", "null", repaired)
        repaired = re.sub(r"\bTrue\b", "true", repaired)
        repaired = re.sub(r"\bFalse\b", "false", repaired)
        return repaired

    async def _repair_json_with_ai(self, ai, malformed_response: str) -> str:
        """
        Ask the model to convert malformed JSON into valid JSON without changing
        the schema or meaning.
        """
        repair_system_prompt = """
You are a strict JSON repair tool.
You will receive malformed JSON that should follow this schema:
{
  "roadmap": {
    "estimated_duration": "string",
    "market_based_salary": {
      "currency": "INR",
      "entry_level": "string",
      "mid_level": "string",
      "senior_level": "string",
      "average": "string"
    },
    "skills_to_develop": ["string"],
    "milestones": [
      {
        "title": "string",
        "description": "string",
        "stage_title": "string",
        "stage_order": 1,
        "order_num": 1,
        "difficulty": "beginner|intermediate|advanced",
        "skills": ["string"],
        "estimated_time": "string",
        "dependencies": ["string"],
        "resources": [
          {
            "title": "string",
            "type": "course|article|video|project|certification",
            "url": "string",
            "platform": "string",
            "duration": "string",
            "difficulty": "beginner|intermediate|advanced",
            "description": "string",
            "is_free": true,
            "rating": 4.5
          }
        ]
      }
    ]
  }
}

Return ONLY valid JSON. No markdown. No explanation.
"""
        repair_user_prompt = (
            "Repair this malformed JSON and return valid JSON only:\n\n"
            f"{malformed_response}"
        )
        return await ai.chat_completion(repair_system_prompt, repair_user_prompt)
    
    def _enhance_with_resources(self, roadmap_data: Dict, target_role: str) -> Dict:
        """
        Enhance roadmap with additional resources if AI response is limited
        """
        # Add default resources for common skills if needed and replace invalid/off-topic URLs.
        used_urls = set()
        for milestone in roadmap_data.get("milestones", []):
            resources = milestone.get("resources", []) or []
            if not isinstance(resources, list):
                resources = []
            resources = [r for r in resources if isinstance(r, dict)]

            milestone_skills = milestone.get("skills", []) or []
            defaults = self._get_default_resources(milestone_skills, target_role)
            ranked_defaults = self._rank_resources_for_milestone(defaults, milestone_skills, target_role)

            for idx, resource in enumerate(list(resources)):
                url = resource.get("url")
                if (not self._is_valid_resource_url(url)) or (not self._is_relevant_resource(resource, milestone_skills, target_role)):
                    replacement = self._pick_next_resource(ranked_defaults, used_urls)
                    if replacement:
                        resource["title"] = replacement.get("title")
                        resource["type"] = replacement.get("type")
                        resource["url"] = replacement.get("url")
                        resource["platform"] = replacement.get("platform")
                        resource["duration"] = replacement.get("duration")
                        resource["difficulty"] = replacement.get("difficulty")
                        resource["description"] = replacement.get("description")
                        resource["is_free"] = replacement.get("is_free", True)
                        resource["rating"] = replacement.get("rating")
                        if replacement.get("url"):
                            used_urls.add(replacement.get("url"))
                    else:
                        resources.pop(idx)
                elif url:
                    used_urls.add(url)

            if len(resources) < 3:
                while len(resources) < 3:
                    candidate = self._pick_next_resource(ranked_defaults, used_urls)
                    if not candidate:
                        break
                    resources.append(candidate)
                    if candidate.get("url"):
                        used_urls.add(candidate.get("url"))

            # Hard role-alignment guard:
            # if resources still don't reflect target role, replace with role-first defaults.
            if not self._has_role_aligned_resource(resources, target_role):
                role_first_defaults = self._rank_resources_for_milestone(
                    self._get_default_resources([], target_role),
                    milestone_skills,
                    target_role
                )
                role_replaced = []
                for candidate in role_first_defaults:
                    if len(role_replaced) >= 3:
                        break
                    role_replaced.append(candidate)
                if role_replaced:
                    resources = role_replaced

            # Final de-dup within the same milestone
            deduped = []
            local_urls = set()
            for r in resources:
                r_url = r.get("url")
                if r_url and r_url in local_urls:
                    continue
                if r_url:
                    local_urls.add(r_url)
                deduped.append(r)
            resources = deduped

            milestone["resources"] = resources

        # Ensure top-level skills are role-aligned and not generic placeholders.
        roadmap_data["skills_to_develop"] = self._normalize_skills_to_develop(
            roadmap_data.get("skills_to_develop") or [],
            roadmap_data.get("milestones") or [],
            target_role
        )
        
        return roadmap_data

    def _has_role_aligned_resource(self, resources: List[Dict], target_role: str) -> bool:
        role = (target_role or "").lower()
        if not role:
            return True
        corpus = " ".join(
            f"{r.get('title','')} {r.get('platform','')} {r.get('description','')} {r.get('url','')}".lower()
            for r in resources
            if isinstance(r, dict)
        )
        markers = self._role_focus_keywords(target_role)
        return any(marker.lower() in corpus for marker in markers)

    def _rank_resources_for_milestone(self, resources: List[Dict], milestone_skills: List[str], target_role: str) -> List[Dict]:
        skills = [str(s).strip().lower() for s in (milestone_skills or []) if str(s).strip()]
        role_tokens = self._role_focus_keywords(target_role)

        def score(res: Dict) -> int:
            corpus = " ".join(
                [
                    str(res.get("title") or "").lower(),
                    str(res.get("platform") or "").lower(),
                    str(res.get("description") or "").lower(),
                    str(res.get("url") or "").lower(),
                ]
            )
            s = 0
            for token in skills:
                if token in corpus:
                    s += 3
            for token in role_tokens:
                if token in corpus:
                    s += 1
            return s

        return sorted(resources, key=score, reverse=True)

    def _pick_next_resource(self, ranked_resources: List[Dict], used_urls: set) -> Optional[Dict]:
        for res in ranked_resources:
            url = res.get("url")
            if not self._is_valid_resource_url(url):
                continue
            if url in used_urls:
                continue
            return res
        return None

    def _normalize_skills_to_develop(
        self,
        skills_to_develop: List[str],
        milestones: List[Dict],
        target_role: str
    ) -> List[str]:
        generic = {
            "technical skills",
            "soft skills",
            "portfolio development",
            "technical fundamentals",
            "project development",
        }

        cleaned = []
        for s in skills_to_develop:
            if not isinstance(s, str):
                continue
            skill = s.strip()
            if skill and skill.lower() not in generic:
                cleaned.append(skill)

        milestone_skills: List[str] = []
        for m in milestones:
            for s in (m.get("skills") or []):
                if isinstance(s, str) and s.strip() and s.strip().lower() not in generic:
                    milestone_skills.append(s.strip())

        if len(cleaned) < 10:
            merged = []
            seen = set()
            for s in cleaned + milestone_skills:
                key = s.lower()
                if key not in seen:
                    seen.add(key)
                    merged.append(s)
            cleaned = merged

        # Final role-based fallback when AI output is still weak.
        if len(cleaned) < 8:
            cleaned = self._role_focus_keywords(target_role)

        return cleaned[:20]

    def _normalize_roadmap_payload(self, roadmap_data: Dict) -> Dict:
        """
        Normalize AI roadmap response so DB write + frontend rendering are stable.
        """
        milestones = roadmap_data.get("milestones") or []
        if not isinstance(milestones, list):
            milestones = []

        normalized_milestones: List[Dict] = []

        for idx, raw in enumerate(milestones, start=1):
            if not isinstance(raw, dict):
                continue

            title = str(raw.get("title") or f"Milestone {idx}").strip()
            description = str(raw.get("description") or f"Complete {title}").strip()
            stage_title = str(raw.get("stage_title") or "General").strip() or "General"

            stage_order = raw.get("stage_order", 1)
            try:
                stage_order = int(stage_order)
            except (TypeError, ValueError):
                stage_order = 1
            if stage_order < 1:
                stage_order = 1

            order_num = raw.get("order_num", idx)
            try:
                order_num = int(order_num)
            except (TypeError, ValueError):
                order_num = idx
            if order_num < 1:
                order_num = idx

            difficulty = str(raw.get("difficulty") or "intermediate").strip().lower()
            if difficulty not in self._allowed_difficulties:
                difficulty = "intermediate"

            skills = raw.get("skills") or []
            if not isinstance(skills, list):
                skills = []
            skills = [str(s).strip() for s in skills if str(s).strip()]

            dependencies = raw.get("dependencies") or []
            if not isinstance(dependencies, list):
                dependencies = []
            dependencies = [
                str(dep).strip()
                for dep in dependencies
                if self._is_valid_uuid(str(dep).strip())
            ]

            resources = raw.get("resources") or []
            if not isinstance(resources, list):
                resources = []

            normalized_resources = []
            for r in resources:
                if not isinstance(r, dict):
                    continue
                r_type = str(r.get("type") or "article").strip().lower()
                if r_type not in self._allowed_resource_types:
                    r_type = "article"

                r_difficulty = str(r.get("difficulty") or difficulty).strip().lower()
                if r_difficulty not in self._allowed_difficulties:
                    r_difficulty = "intermediate"

                normalized_resources.append(
                    {
                        "title": str(r.get("title") or "Learning Resource").strip(),
                        "type": r_type,
                        "url": r.get("url"),
                        "platform": r.get("platform"),
                        "duration": r.get("duration"),
                        "difficulty": r_difficulty,
                        "description": r.get("description"),
                        "is_free": bool(r.get("is_free", True)),
                        "rating": r.get("rating"),
                    }
                )

            normalized_milestones.append(
                {
                    "title": title,
                    "description": description,
                    "stage_title": stage_title,
                    "stage_order": stage_order,
                    "order_num": order_num,
                    "difficulty": difficulty,
                    "skills": skills,
                    "estimated_time": str(raw.get("estimated_time") or "2-3 weeks").strip(),
                    "dependencies": dependencies,
                    "resources": normalized_resources,
                }
            )

        normalized_milestones.sort(key=lambda m: (m.get("stage_order", 1), m.get("order_num", 1)))
        normalized_milestones = self._enforce_level_progression(normalized_milestones)
        for i, milestone in enumerate(normalized_milestones, start=1):
            milestone["order_num"] = i

        skills_to_develop = roadmap_data.get("skills_to_develop") or []
        if not isinstance(skills_to_develop, list):
            skills_to_develop = []
        skills_to_develop = [str(s).strip() for s in skills_to_develop if str(s).strip()]

        return {
            "estimated_duration": str(roadmap_data.get("estimated_duration") or "3-6 months").strip(),
            "market_based_salary": self._normalize_market_salary(roadmap_data.get("market_based_salary")),
            "skills_to_develop": skills_to_develop,
            "milestones": normalized_milestones,
        }

    def _enforce_level_progression(self, milestones: List[Dict]) -> List[Dict]:
        """
        Ensure roadmap spans beginner -> intermediate -> advanced progression.
        """
        if not milestones:
            return milestones

        beginner_count = 0
        intermediate_count = 0
        advanced_count = 0
        for m in milestones:
            diff = str(m.get("difficulty") or "intermediate").strip().lower()
            if diff == "beginner":
                beginner_count += 1
            elif diff == "advanced":
                advanced_count += 1
            else:
                intermediate_count += 1

        # Guarantee minimum representation across all three phases.
        for m in milestones:
            if beginner_count >= 2:
                break
            if str(m.get("difficulty")).lower() == "intermediate":
                m["difficulty"] = "beginner"
                if not m.get("stage_title") or str(m.get("stage_title")).lower() == "general":
                    m["stage_title"] = "Beginner Foundation"
                beginner_count += 1
                intermediate_count = max(0, intermediate_count - 1)

        for m in reversed(milestones):
            if advanced_count >= 2:
                break
            if str(m.get("difficulty")).lower() == "intermediate":
                m["difficulty"] = "advanced"
                if not m.get("stage_title") or str(m.get("stage_title")).lower() == "general":
                    m["stage_title"] = "Advanced Engineering"
                advanced_count += 1
                intermediate_count = max(0, intermediate_count - 1)

        # Ensure the first milestone starts at beginner and last ends at advanced.
        milestones[0]["difficulty"] = "beginner"
        if not milestones[0].get("stage_title"):
            milestones[0]["stage_title"] = "Beginner Foundation"
        milestones[-1]["difficulty"] = "advanced"
        if not milestones[-1].get("stage_title"):
            milestones[-1]["stage_title"] = "Advanced Engineering"

        return milestones

    def _role_focus_keywords(self, target_role: str) -> List[str]:
        role = (target_role or "").lower()
        if "data" in role or "analyst" in role or "scientist" in role:
            return ["python", "sql", "pandas", "statistics", "machine learning", "data visualization"]
        if "devops" in role or "sre" in role or "cloud" in role:
            return ["docker", "kubernetes", "aws", "ci/cd", "terraform", "monitoring"]
        if "frontend" in role or "ui" in role or "ux" in role:
            return ["react", "typescript", "state management", "accessibility", "performance", "testing"]
        if "backend" in role or "api" in role:
            return ["api design", "database design", "authentication", "caching", "queue systems", "testing"]
        if "mobile" in role:
            return ["react native", "flutter", "app architecture", "state management", "api integration", "release pipeline"]
        if "product" in role:
            return ["product discovery", "roadmapping", "analytics", "experimentation", "stakeholder management", "prioritization"]
        return ["system design", "testing", "version control", "deployment", "problem solving", "architecture"]

    def _build_role_context(self, target_role: str, current_skills: List[str]) -> Dict:
        role_text = (target_role or "").lower().strip()
        required_skills: List[str] = []
        for role_key, role_skills in self._role_skill_map.items():
            if role_key in role_text:
                required_skills = role_skills
                break
        if not required_skills:
            required_skills = self._role_focus_keywords(target_role)

        current_norm = {str(s).strip().lower() for s in (current_skills or []) if str(s).strip()}
        skill_gaps = [s for s in required_skills if s.strip().lower() not in current_norm]
        return {
            "target_role": target_role,
            "required_role_skills": required_skills,
            "identified_skill_gaps": skill_gaps,
            "current_skills": current_skills or [],
        }

    def _enforce_gap_alignment(self, roadmap_data: Dict, current_skills: List[str], role_context: Dict) -> Dict:
        desired = role_context.get("identified_skill_gaps") or role_context.get("required_role_skills") or []
        desired = [str(s).strip() for s in desired if str(s).strip()]
        desired_norm = {s.lower() for s in desired}
        current_norm = {str(s).strip().lower() for s in (current_skills or []) if str(s).strip()}

        skills_to_develop = roadmap_data.get("skills_to_develop") or []
        if not isinstance(skills_to_develop, list):
            skills_to_develop = []
        existing_norm = {str(s).strip().lower() for s in skills_to_develop if str(s).strip()}

        for s in desired:
            sl = s.lower()
            if sl not in existing_norm and sl not in current_norm:
                skills_to_develop.append(s)
                existing_norm.add(sl)
        roadmap_data["skills_to_develop"] = skills_to_develop

        milestones = roadmap_data.get("milestones") or []
        for milestone in milestones:
            mskills = milestone.get("skills") or []
            if not isinstance(mskills, list):
                mskills = []
            mskill_norm = {str(s).strip().lower() for s in mskills if str(s).strip()}
            if not any(s in desired_norm for s in mskill_norm):
                for inject in desired[:2]:
                    if inject.lower() not in mskill_norm:
                        mskills.append(inject)
                        mskill_norm.add(inject.lower())
            milestone["skills"] = mskills
        roadmap_data["milestones"] = milestones
        return roadmap_data

    def _needs_role_specific_regeneration(self, roadmap_data: Dict, target_role: str) -> bool:
        milestones = roadmap_data.get("milestones") or []
        if len(milestones) < 6:
            return True

        unique_skills = set()
        for m in milestones:
            for s in (m.get("skills") or []):
                if isinstance(s, str) and s.strip():
                    unique_skills.add(s.strip().lower())
        if len(unique_skills) < 14:
            return True

        generic_titles = {"foundation skills", "practical experience", "technical skills", "portfolio development"}
        generic_title_count = 0
        for m in milestones:
            title = str(m.get("title") or "").strip().lower()
            if title in generic_titles:
                generic_title_count += 1
        if generic_title_count >= 2:
            return True

        role_tokens = [t for t in re.split(r"[^a-z0-9]+", (target_role or "").lower()) if len(t) > 2]
        if role_tokens:
            role_match_hits = 0
            for m in milestones:
                corpus = f"{m.get('title', '')} {m.get('description', '')} {' '.join(m.get('skills', []))}".lower()
                if any(tok in corpus for tok in role_tokens):
                    role_match_hits += 1
            if role_match_hits < max(2, len(milestones) // 4):
                return True

        return False

    def _normalize_market_salary(self, market_salary: Optional[Dict]) -> Dict:
        if not isinstance(market_salary, dict):
            return {
                "currency": "INR",
                "entry_level": "INR 4,00,000 - 7,00,000 per year",
                "mid_level": "INR 8,00,000 - 15,00,000 per year",
                "senior_level": "INR 16,00,000 - 30,00,000 per year",
                "average": "INR 12,00,000 per year",
            }
        def _to_inr_text(value: Optional[str], default_text: str) -> str:
            text = str(value or "").strip()
            if not text:
                return default_text
            if "inr" in text.lower() or "₹" in text:
                return text
            normalized = text.replace("$", "").replace("usd", "").replace("USD", "").strip(" -")
            if normalized:
                return f"INR {normalized}"
            return default_text

        return {
            "currency": "INR",
            "entry_level": _to_inr_text(market_salary.get("entry_level"), "INR 4,00,000 - 7,00,000 per year"),
            "mid_level": _to_inr_text(market_salary.get("mid_level"), "INR 8,00,000 - 15,00,000 per year"),
            "senior_level": _to_inr_text(market_salary.get("senior_level"), "INR 16,00,000 - 30,00,000 per year"),
            "average": _to_inr_text(market_salary.get("average"), "INR 12,00,000 per year"),
        }

    def _is_valid_resource_url(self, url: Optional[str]) -> bool:
        if not url or not isinstance(url, str):
            return False
        parsed = url.strip().lower()
        if not (parsed.startswith("http://") or parsed.startswith("https://")):
            return False
        if "example.com" in parsed or "placeholder" in parsed:
            return False
        return True

    def _is_relevant_resource(self, resource: Dict, milestone_skills: List[str], target_role: str) -> bool:
        role_tokens = self._role_focus_keywords(target_role)
        skill_tokens = [str(s).strip().lower() for s in (milestone_skills or []) if str(s).strip()]
        role = (target_role or "").lower()
        corpus = " ".join(
            [
                str(resource.get("title") or "").lower(),
                str(resource.get("platform") or "").lower(),
                str(resource.get("description") or "").lower(),
                str(resource.get("url") or "").lower(),
            ]
        )

        # Strong role guard: mobile roles must include mobile-specific markers.
        if "mobile" in role or "android" in role or "ios" in role:
            mobile_markers = ["react native", "flutter", "android", "ios", "swift", "kotlin", "xcode", "play store", "app store"]
            if not any(marker in corpus for marker in mobile_markers):
                return False

        if any(token.lower() in corpus for token in skill_tokens[:6]):
            return True
        if any(token.lower() in corpus for token in role_tokens):
            return True
        return False

    def _is_valid_uuid(self, value: str) -> bool:
        try:
            uuid.UUID(value)
            return True
        except (ValueError, TypeError):
            return False
    
    def _get_default_resources(self, skills: List[str], target_role: str) -> List[Dict]:
        """
        Get default resources for common skills
        """
        default_resources = []
        role_defaults: List[Dict] = []

        role = (target_role or "").lower()
        if "frontend" in role or "ui" in role or "ux" in role:
            role_defaults = [
                {"title": "React Official Learn", "type": "course", "url": "https://react.dev/learn", "platform": "React.dev", "duration": "20 hours", "difficulty": "intermediate", "description": "Core React concepts and patterns", "is_free": True, "rating": 4.9},
                {"title": "TypeScript Handbook", "type": "article", "url": "https://www.typescriptlang.org/docs/handbook/intro.html", "platform": "TypeScript", "duration": "12 hours", "difficulty": "intermediate", "description": "TypeScript fundamentals for frontend apps", "is_free": True, "rating": 4.8},
            ]
        elif "backend" in role or "api" in role:
            role_defaults = [
                {"title": "REST API Design Best Practices", "type": "article", "url": "https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design", "platform": "Microsoft Learn", "duration": "4 hours", "difficulty": "intermediate", "description": "Design scalable and consistent APIs", "is_free": True, "rating": 4.7},
                {"title": "PostgreSQL Tutorial", "type": "course", "url": "https://www.postgresqltutorial.com/", "platform": "PostgreSQL Tutorial", "duration": "15 hours", "difficulty": "beginner", "description": "Practical SQL and relational DB skills", "is_free": True, "rating": 4.6},
            ]
        elif "mobile" in role or "android" in role or "ios" in role:
            role_defaults = [
                {"title": "React Native Docs", "type": "article", "url": "https://reactnative.dev/docs/getting-started", "platform": "React Native", "duration": "10 hours", "difficulty": "beginner", "description": "Official guide for building cross-platform mobile apps", "is_free": True, "rating": 4.8},
                {"title": "Flutter Codelabs", "type": "course", "url": "https://docs.flutter.dev/codelabs", "platform": "Flutter", "duration": "12 hours", "difficulty": "beginner", "description": "Hands-on Flutter learning labs", "is_free": True, "rating": 4.8},
                {"title": "Android Developers Training", "type": "course", "url": "https://developer.android.com/courses", "platform": "Android Developers", "duration": "14 hours", "difficulty": "intermediate", "description": "Official Android training pathways", "is_free": True, "rating": 4.7},
            ]
        elif "data" in role or "analyst" in role or "scientist" in role:
            role_defaults = [
                {"title": "Kaggle Learn", "type": "course", "url": "https://www.kaggle.com/learn", "platform": "Kaggle", "duration": "30 hours", "difficulty": "intermediate", "description": "Hands-on data science micro-courses", "is_free": True, "rating": 4.8},
                {"title": "Pandas User Guide", "type": "article", "url": "https://pandas.pydata.org/docs/user_guide/index.html", "platform": "Pandas", "duration": "10 hours", "difficulty": "intermediate", "description": "Essential data manipulation with pandas", "is_free": True, "rating": 4.7},
            ]
        elif "devops" in role or "sre" in role or "cloud" in role:
            role_defaults = [
                {"title": "Docker Curriculum", "type": "course", "url": "https://docker-curriculum.com/", "platform": "Docker Curriculum", "duration": "10 hours", "difficulty": "beginner", "description": "Docker from basics to practical usage", "is_free": True, "rating": 4.7},
                {"title": "Kubernetes Basics", "type": "course", "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/", "platform": "Kubernetes", "duration": "8 hours", "difficulty": "intermediate", "description": "Official Kubernetes interactive tutorial", "is_free": True, "rating": 4.8},
            ]

        # Common resources for different skill categories
        skill_resources = {
            "python": [
                {
                    "title": "Python for Everybody",
                    "type": "course",
                    "url": "https://www.coursera.org/learn/python",
                    "platform": "Coursera",
                    "duration": "20 hours",
                    "difficulty": "beginner",
                    "description": "Comprehensive Python course for beginners",
                    "is_free": True,
                    "rating": 4.8
                }
            ],
            "javascript": [
                {
                    "title": "JavaScript.info",
                    "type": "article",
                    "url": "https://javascript.info",
                    "platform": "JavaScript.info",
                    "duration": "30 hours",
                    "difficulty": "beginner",
                    "description": "Modern JavaScript tutorial",
                    "is_free": True,
                    "rating": 4.7
                }
            ],
            "react": [
                {
                    "title": "React Tutorial",
                    "type": "video",
                    "url": "https://react.dev/learn",
                    "platform": "React.dev",
                    "duration": "15 hours",
                    "difficulty": "intermediate",
                    "description": "Official React tutorial",
                    "is_free": True,
                    "rating": 4.9
                }
            ],
            "docker": [
                {
                    "title": "Docker Curriculum",
                    "type": "course",
                    "url": "https://docker-curriculum.com/",
                    "platform": "Docker Curriculum",
                    "duration": "10 hours",
                    "difficulty": "beginner",
                    "description": "Hands-on Docker fundamentals",
                    "is_free": True,
                    "rating": 4.7
                }
            ],
            "kubernetes": [
                {
                    "title": "Kubernetes Basics",
                    "type": "course",
                    "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/",
                    "platform": "Kubernetes",
                    "duration": "8 hours",
                    "difficulty": "intermediate",
                    "description": "Official Kubernetes interactive tutorials",
                    "is_free": True,
                    "rating": 4.8
                }
            ],
            "aws": [
                {
                    "title": "AWS Cloud Practitioner Essentials",
                    "type": "course",
                    "url": "https://explore.skillbuilder.aws/learn/course/external/view/elearning/134/aws-cloud-practitioner-essentials",
                    "platform": "AWS Skill Builder",
                    "duration": "6 hours",
                    "difficulty": "beginner",
                    "description": "Official AWS cloud fundamentals",
                    "is_free": True,
                    "rating": 4.6
                }
            ],
            "terraform": [
                {
                    "title": "Terraform Associate Tutorials",
                    "type": "course",
                    "url": "https://developer.hashicorp.com/terraform/tutorials",
                    "platform": "HashiCorp",
                    "duration": "12 hours",
                    "difficulty": "intermediate",
                    "description": "Official Terraform guided tutorials",
                    "is_free": True,
                    "rating": 4.8
                }
            ],
            "react native": [
                {
                    "title": "React Native Docs",
                    "type": "course",
                    "url": "https://reactnative.dev/docs/getting-started",
                    "platform": "React Native",
                    "duration": "16 hours",
                    "difficulty": "intermediate",
                    "description": "Official React Native guide",
                    "is_free": True,
                    "rating": 4.8
                }
            ],
            "flutter": [
                {
                    "title": "Flutter Codelabs",
                    "type": "course",
                    "url": "https://docs.flutter.dev/codelabs",
                    "platform": "Flutter",
                    "duration": "14 hours",
                    "difficulty": "beginner",
                    "description": "Official Flutter hands-on labs",
                    "is_free": True,
                    "rating": 4.7
                }
            ],
            "android": [
                {
                    "title": "Android Developer Guides",
                    "type": "article",
                    "url": "https://developer.android.com/guide",
                    "platform": "Android Developers",
                    "duration": "18 hours",
                    "difficulty": "intermediate",
                    "description": "Official Android docs and guides",
                    "is_free": True,
                    "rating": 4.8
                }
            ],
            "ios": [
                {
                    "title": "SwiftUI Tutorials",
                    "type": "course",
                    "url": "https://developer.apple.com/tutorials/swiftui",
                    "platform": "Apple Developer",
                    "duration": "12 hours",
                    "difficulty": "intermediate",
                    "description": "Official SwiftUI tutorials",
                    "is_free": True,
                    "rating": 4.8
                }
            ]
        }
        
        for skill in skills:
            skill_lower = skill.lower().strip()
            for key, resources in skill_resources.items():
                if key == skill_lower or key in skill_lower or skill_lower in key:
                    default_resources.extend(resources)

        merged = []
        seen_urls = set()
        for item in role_defaults + default_resources:
            url = item.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                merged.append(item)

        return merged[:5]  # Limit to 5 resources
    
    def _infer_current_level(self, experience: str) -> str:
        """
        Infer current level from experience
        """
        try:
            exp_years = float(experience)
            if exp_years < 1:
                return "beginner"
            elif exp_years < 3:
                return "junior"
            elif exp_years < 5:
                return "mid-level"
            else:
                return "senior"
        except (ValueError, TypeError):
            return "beginner"
    
    def _generate_fallback_roadmap(self, target_role: str, user_skills: List[str]) -> Dict:
        """
        Generate a basic fallback roadmap if AI fails
        """
        role_keywords = self._role_focus_keywords(target_role)
        role_lower = (target_role or "").lower()
        if "mobile" in role_lower:
            fallback_skills = [
                "React Native", "Flutter", "Dart", "Android", "iOS", "State Management",
                "Mobile API Integration", "Offline Storage", "Push Notifications", "App Deployment"
            ]
            milestone_title_1 = "Mobile App Development Foundations"
            milestone_title_2 = "Cross-Platform Mobile Engineering"
            desc_1 = "Build core mobile development concepts including app lifecycle, navigation, state handling, and API communication."
            desc_2 = "Develop production-ready mobile apps with performance optimization, offline-first patterns, and platform-specific integrations."
            milestone_title_3 = "Mobile Production Readiness"
            desc_3 = "Focus on release pipelines, store deployment, crash monitoring, analytics, and performance tuning for production mobile apps."
            milestone_3_skills = ["Release Management", "Crash Analytics", "Push Notifications", "App Security", "Performance Tuning", "Store Deployment"]
        elif "cloud" in role_lower or "devops" in role_lower or "sre" in role_lower:
            fallback_skills = [
                "Linux Administration", "AWS Core Services", "Infrastructure as Code",
                "Terraform", "Docker", "Kubernetes", "CI/CD Pipelines", "Observability",
                "Cloud Security", "Networking", "Cost Optimization", "Disaster Recovery"
            ]
            milestone_title_1 = "Cloud & Infrastructure Foundations"
            milestone_title_2 = "Cloud Platform Architecture & Operations"
            desc_1 = "Build strong cloud fundamentals in compute, networking, IAM, and infrastructure automation with Terraform."
            desc_2 = "Design resilient cloud architectures with Kubernetes, CI/CD, observability, security controls, and cost governance."
            milestone_title_3 = "Production Cloud Operations"
            desc_3 = "Implement secure deployment pipelines, workload monitoring, incident response workflows, and high availability patterns in cloud-native environments."
            milestone_3_skills = ["CI/CD", "Cloud Security", "Incident Response", "SLO/SLI", "Autoscaling", "Disaster Recovery"]
        elif "ai" in role_lower or "ml" in role_lower or "machine learning" in role_lower or "data scientist" in role_lower:
            fallback_skills = [
                "Python", "NumPy", "Pandas", "SQL", "Statistics", "Probability",
                "Machine Learning Algorithms", "Feature Engineering", "Model Evaluation",
                "Scikit-learn", "Deep Learning", "PyTorch", "MLOps", "Model Deployment"
            ]
            milestone_title_1 = "AI/ML Mathematical & Python Foundations"
            milestone_title_2 = "Machine Learning Modeling & Evaluation"
            desc_1 = "Build a strong AI/ML base with Python for data work, statistics, probability, and structured exploratory analysis."
            desc_2 = "Train, tune, and evaluate ML models, then operationalize them with reproducible pipelines and deployment fundamentals."
            milestone_title_3 = "MLOps & Model Deployment"
            desc_3 = "Productionize ML workloads using experiment tracking, model versioning, monitoring, and deployment pipelines."
            milestone_3_skills = ["Model Serving", "Experiment Tracking", "Feature Pipelines", "Drift Monitoring", "A/B Testing", "Model Governance"]
        else:
            fallback_skills = [
                "Data Structures & Algorithms", "Problem Solving Patterns", "JavaScript/TypeScript",
                "React & State Management", "Node.js API Development", "SQL & Database Design",
                "System Design Basics", "Testing (Unit/Integration)", "Git/GitHub Workflow",
                "CI/CD Fundamentals", "Docker Basics", "Cloud Deployment", "Performance Optimization",
                "Interview Preparation"
            ]
            milestone_title_1 = "Programming & Problem-Solving Foundation"
            milestone_title_2 = "Role-Specific Core Engineering"
            desc_1 = f"Establish strong programming basics, clean coding habits, and algorithmic thinking required for {target_role}."
            desc_2 = f"Build production-grade capabilities focused on {target_role} with practical implementation and debugging depth."
            milestone_title_3 = "Production Engineering & Delivery"
            desc_3 = "Strengthen testing, deployment, observability, and scalability practices to deliver reliable production systems."
            milestone_3_skills = ["Testing", "CI/CD", "Deployment", "Monitoring", "Performance", "System Reliability"]

        resource_pool = self._get_default_resources(fallback_skills, target_role)
        if len(resource_pool) < 3:
            resource_pool = [
                {
                    "title": "Roadmap Learning Resource",
                    "type": "article",
                    "url": "https://roadmap.sh",
                    "platform": "roadmap.sh",
                    "duration": "6 hours",
                    "difficulty": "beginner",
                    "description": "Role-based technology roadmap references",
                    "is_free": True,
                    "rating": 4.6,
                }
            ] + resource_pool

        m1_resources = resource_pool[:3]
        m2_resources = resource_pool[1:4] if len(resource_pool) >= 4 else resource_pool[:3]
        m3_resources = resource_pool[2:5] if len(resource_pool) >= 5 else resource_pool[:3]

        return {
            "estimated_duration": "3-6 months",
            "market_based_salary": {
                "currency": "INR",
                "entry_level": "INR 4,00,000 - 7,00,000 per year",
                "mid_level": "INR 8,00,000 - 15,00,000 per year",
                "senior_level": "INR 16,00,000 - 30,00,000 per year",
                "average": "INR 12,00,000 per year"
            },
            "skills_to_develop": fallback_skills,
            "milestones": [
                {
                    "title": milestone_title_1,
                    "description": desc_1,
                    "stage_title": "Foundation",
                    "stage_order": 1,
                    "order_num": 1,
                    "difficulty": "beginner",
                    "skills": role_keywords[:6] if role_keywords else ["Problem Solving", "Foundations"],
                    "estimated_time": "4-6 weeks",
                    "dependencies": [],
                    "resources": m1_resources
                },
                {
                    "title": milestone_title_2,
                    "description": desc_2,
                    "stage_title": "Core Development",
                    "stage_order": 2,
                    "order_num": 2,
                    "difficulty": "intermediate",
                    "skills": role_keywords[:6] if role_keywords else ["Core Engineering"],
                    "estimated_time": "6-8 weeks",
                    "dependencies": [],
                    "resources": m2_resources
                },
                {
                    "title": milestone_title_3,
                    "description": desc_3,
                    "stage_title": "Advanced Engineering",
                    "stage_order": 2,
                    "order_num": 3,
                    "difficulty": "intermediate",
                    "skills": milestone_3_skills,
                    "estimated_time": "6-8 weeks",
                    "dependencies": [],
                    "resources": m3_resources
                }
            ]
        }


# Global instance
ai_roadmap_service = AIRoadmapService()
