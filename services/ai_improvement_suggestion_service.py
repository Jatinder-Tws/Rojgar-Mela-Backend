import json
import asyncio
from config import settings
import google.genai as genai


def get_gemini_client():
    return genai.Client(api_key=settings.GOOGLE_API_KEY)


def build_prompt(job_title, job_description, technologies, resume_text):
    return f"""
        Act as a senior technical recruiter.

        Analyze the resume against the job.

        JOB TITLE:
        {job_title}

        JOB DESCRIPTION:
        {job_description}

        TECH STACK:
        {", ".join(technologies)}

        RESUME:
        {resume_text}

        Return ONLY valid JSON with:
        - missing_skills (list)
        - improvements (list)
        - rewritten_bullets (list)
        - ats_keywords (list)
        - score (0-10)
        - futureTechToLearn (list)
        """


async def analyze_resume_multi(data, resume_text):

 
    prompt = build_prompt(
        data["job_title"], data["job_description"], data["technologies"], resume_text
    )


    system_instruction = "You are a professional resume reviewer."

    client =  get_gemini_client()

    # return
    response =  client.models.generate_content(
        model=settings.GEMINI_CHAT_MODEL,
        contents=[system_instruction, prompt],
        config={"response_mime_type": "application/json"},
    )
    return json.loads(response.text)


def merge_results(results):
    final = {
        "missing_skills": [],
        "improvements": [],
        "rewritten_bullets": [],
        "ats_keywords": [],
        "score": 0,
        "futureTechToLearn": [],
    }

    scores = []

    for r in results:
        final["missing_skills"] += r.get("missing_skills", [])
        final["improvements"] += r.get("improvements", [])
        final["rewritten_bullets"] += r.get("rewritten_bullets", [])
        final["ats_keywords"] += r.get("ats_keywords", [])
        final["futureTechToLearn"] += r.get("futureTechToLearn", [])

        if "score" in r:
            scores.append(r["score"])

    for key in final:
        if isinstance(final[key], list):
            final[key] = list(set(final[key]))

    final["score"] = sum(scores) / len(scores) if scores else 0

    return final


# import json
# from config import settings
# from openai import AsyncOpenAI

# def get_openai_client():
#     return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# def build_prompt(job_title, job_description, technologies, resume_text):
#     return f"""
#         Act as a senior technical recruiter.

#         Analyze the resume against the job.

#         JOB TITLE:
#         {job_title}

#         JOB DESCRIPTION:
#         {job_description}

#         TECH STACK:
#         {", ".join(technologies)}

#         RESUME:
#         {resume_text}

#         Return ONLY valid JSON with:
#         - missing_skills (list)
#         - improvements (list)
#         - rewritten_bullets (list)
#         - ats_keywords (list)
#         - score (0-10)
#         - futureTechToLearn (list)
#         """

# # async def analyze_resume(data, resume_text):
# #     client = get_openai_client()

# #     prompt = build_prompt(
# #         data["job_title"],
# #         data["job_description"],
# #         data["technologies"],
# #         resume_text
# #     )

# #     # ✅ FIX: add await
# #     response = await client.chat.completions.create(
# #         model="gpt-4o-mini",
# #         messages=[
# #             {"role": "system", "content": "You are a professional resume reviewer."},
# #             {"role": "user", "content": prompt}
# #         ],
# #         response_format={"type": "json_object"}
# #     )

# #     content = response.choices[0].message.content

# #     try:
# #         return json.loads(content)
# #     except Exception:
# #         return {
# #             "missing_skills": [],
# #             "improvements": [content],
# #             "rewritten_bullets": [],
# #             "ats_keywords": [],
# #             "score": 0,
# #             "futureTechToLearn":[]
# #         }
    
# async def analyze_resume_multi(data, resume_text):
#     client = get_openai_client()

#     prompt = build_prompt(
#         data["job_title"],
#         data["job_description"],
#         data["technologies"],
#         resume_text
#     )

#     # 🚀 Run both models in parallel
#     import asyncio

#     tasks = [
#         client.chat.completions.create(
#             model="gpt-4o-mini",
#             messages=[
#                 {"role": "system", "content": "You are a resume reviewer."},
#                 {"role": "user", "content": prompt}
#             ],
#             response_format={"type": "json_object"}
#         ),
#         client.chat.completions.create(
#             model="gpt-4o",
#             messages=[
#                 {"role": "system", "content": "You are a strict senior recruiter."},
#                 {"role": "user", "content": prompt}
#             ],
#             response_format={"type": "json_object"}
#         )
#     ]

#     responses = await asyncio.gather(*tasks)

#     results = []
#     for res in responses:
#         try:
#             results.append(json.loads(res.choices[0].message.content))
#         except:
#             pass

#     return merge_results(results)

# def merge_results(results):
#     final = {
#         "missing_skills": [],
#         "improvements": [],
#         "rewritten_bullets": [],
#         "ats_keywords": [],
#         "score": 0,
#         "futureTechToLearn": []
#     }

#     scores = []

#     for r in results:
#         final["missing_skills"] += r.get("missing_skills", [])
#         final["improvements"] += r.get("improvements", [])
#         final["rewritten_bullets"] += r.get("rewritten_bullets", [])
#         final["ats_keywords"] += r.get("ats_keywords", [])
#         final["futureTechToLearn"] += r.get("futureTechToLearn", [])

#         if "score" in r:
#             scores.append(r["score"])

#     # ✅ Remove duplicates
#     for key in final:
#         if isinstance(final[key], list):
#             final[key] = list(set(final[key]))

#     # ✅ Average score
#     final["score"] = sum(scores) / len(scores) if scores else 0

#     return final