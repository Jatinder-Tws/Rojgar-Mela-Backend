# @router.post("/generate-description", response_model=JobDescriptionResponse)
# async def generate_description(payload: JobDescriptionRequest):
#     print(payload)
#     try:
#         return await generate_job_description(payload.title)

#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))

#     except Exception:
#         raise HTTPException(status_code=500, detail="Something went wrong")






# import asyncio

# @router.post("/generate-description", response_model=JobDescriptionOnlyResponse)
# async def generate_description(payload: JobTitleRequest):
#     try:
#         print("TITLE:", payload.title)

#         return await asyncio.to_thread(
#             generate_job_descriptions,
#             payload.title
#         )

#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))

#     except Exception as e:
#         print(" ERROR:", str(e))  
#         raise HTTPException(status_code=500, detail=str(e))

# import asyncio

# @router.post("/generate-description", response_model=JobDescriptionOnlyResponse)
# async def generate_description(payload: JobTitleRequest):
#     try:
#         print("TITLE:", payload.title)

#         return await asyncio.to_thread(
#             generate_job_descriptions,
#             payload.title
#         )

#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))

#     except Exception as e:
#         print(" ERROR:", str(e))   # 
#         raise HTTPException(status_code=500, detail=str(e))

# from google.genai import Client
# from google.genai.types import GenerateContentConfig
# import google.generativeai as genai
# from config import settings

# # if not settings.GOOGLE_API_KEY:
# #     raise RuntimeError("GOOGLE_API_KEY is not configured")


# # # Configure Gemini
# # genai.configure(api_key=settings.GOOGLE_API_KEY)


# # print("API KEY >>>>>>>> :", settings.GOOGLE_API_KEY)


# client = Client(api_key=settings.GOOGLE_API_KEY)


# def generate_job_descriptions(title: str):
#     print(title)
#     if not title:
#         raise ValueError("title is required")

#     prompt = f"""
#     Generate exactly 2 different job descriptions.

#     JOB_TITLE: {title}

#     Rules:
#     - Infer experience level (Junior / Mid / Senior)
#     - Each description should have 10–15 bullet points
#     - Keep them different in tone and tools

#     Return format:

#     DESCRIPTION_1:
#     * ...

#     DESCRIPTION_2:
#     * ...
#     """

#     print(client)

#     response =  client.models.generate_content(
#         model="gemini-2.5-flash-lite",
#         config=GenerateContentConfig(temperature=0.4),
#         contents=prompt
#     )
    
#     print(response)
#     text = response.text

#     if "DESCRIPTION_1:" not in text or "DESCRIPTION_2:" not in text:
#         raise ValueError("Invalid AI response format")

#     desc1_raw = text.split("DESCRIPTION_1:")[1].split("DESCRIPTION_2:")[0]
#     desc2_raw = text.split("DESCRIPTION_2:")[1]

#     def to_paragraph(desc):
#         lines = [
#             line.replace("*", "").strip()
#             for line in desc.split("\n")
#             if line.strip()
#         ]
#         return " ".join(lines)

#     return {
#         "description_1": to_paragraph(desc1_raw),
#         "description_2": to_paragraph(desc2_raw),
#     }

# def generate_job_skills(title: str):
#     if not title:
#         raise ValueError("title is required")

#     prompt = f"""
#     Generate a list of skills for the job:

#     JOB_TITLE: {title}

#     Rules:
#     - Only return comma-separated keywords
#     - No explanations
#     - Include tools, technologies, and soft skills
#     - Max 15 skills
#     """

#     response = client.models.generate_content(
#         model="gemini-2.5-flash-lite",
#         config=GenerateContentConfig(temperature=0.3),
#         contents=prompt
#     )

#     text = response.text.strip()

#     return {
#         "skills": [s.strip() for s in text.split(",") if s.strip()]
#     }

