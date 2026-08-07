"""Public site chat — Rojgarmela.ai answers via Gemini, with FAQ fallback + smart option pills."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, List, Optional

from config import settings
from services.ai_service import get_ai

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {
    "english",
    "hindi",
    "hinglish",
    "tamil",
    "telugu",
    "marathi",
    "bengali",
    "punjabi",
}

DEFAULT_TOPIC_OPTIONS = {
    "english": [
        "What is Rojgarmela.ai?",
        "Register as Job Seeker",
        "How to apply for Training?",
        "Find Jobs & AI Matching",
        "Contact Support",
    ],
    "hindi": [
        "Rojgarmela.ai क्या है?",
        "Job Seeker के रूप में रजिस्टर",
        "Training के लिए कैसे apply करें?",
        "Jobs और AI Matching",
        "Support से संपर्क",
    ],
    "hinglish": [
        "Rojgarmela.ai kya hai?",
        "Job Seeker ke roop mein register",
        "Training ke liye kaise apply karun?",
        "Jobs aur AI Matching",
        "Contact Support",
    ],
    "punjabi": [
        "Rojgarmela.ai ਕੀ ਹੈ?",
        "Job Seeker ਵਜੋਂ ਰਜਿਸਟਰ",
        "Training ਲਈ ਕਿਵੇਂ apply ਕਰਾਂ?",
        "Jobs ਅਤੇ AI Matching",
        "Support ਨਾਲ ਸੰਪਰਕ",
    ],
    "tamil": [
        "Rojgarmela.ai என்றால் என்ன?",
        "Job Seeker ஆக பதிவு",
        "Training-க்கு எப்படி apply செய்வது?",
        "Jobs & AI Matching",
        "Contact Support",
    ],
    "telugu": [
        "Rojgarmela.ai అంటే ఏమిటి?",
        "Job Seeker గా నమోదు",
        "Training కి ఎలా apply చేయాలి?",
        "Jobs & AI Matching",
        "Contact Support",
    ],
    "marathi": [
        "Rojgarmela.ai म्हणजे काय?",
        "Job Seeker म्हणून नोंदणी",
        "Training साठी कसे apply करावे?",
        "Jobs & AI Matching",
        "Contact Support",
    ],
    "bengali": [
        "Rojgarmela.ai কী?",
        "Job Seeker হিসেবে রেজিস্টার",
        "Training-এ কীভাবে apply করব?",
        "Jobs & AI Matching",
        "Contact Support",
    ],
}

SYSTEM_PROMPT = """You are the official AI assistant for Rojgarmela.ai (Rojgar Mela) — an AI-powered job platform in India for job seekers, employers, training partners, and job fairs.

Answer ONLY about Rojgarmela.ai / Rojgar Mela:
- Platform overview and who it is for
- Registration, login, profiles, resumes
- Job search, AI matching, applications, job fairs
- Employer tools: post jobs, AI ranking, interviews, scheduling
- Seeker AI tools: resume builder, AI coach / mock interviews, career roadmap, assessments
- Training portal / courses — how to browse Training, open a course, and apply
- Support: Contact page, support@rojgarmela.com, phones +91-9915137531 / +91-9915130531

CRITICAL language rule:
- The user selected language is: {language}
- You MUST write the entire "reply" in that language only (including Hinglish if selected).
- Option pill labels (if any) should also be in that same language.

Option pills — YOU decide:
- If the user asked a clear, specific question and your answer fully covers it → set "options" to [] (empty). No pills.
- If the question is vague, broad, off-topic, or they may need related next steps → include 2–4 short option pills in the selected language.
- Never force pills after every answer. Prefer a direct answer when enough.
- If the user says thanks / thank you / bye / goodbye / ok thanks / dhanyavad / shukriya → reply with a warm short closing thank-you in {language}, wish them well on Rojgarmela.ai, and set "options" to [] (no pills).

Other rules:
1. Stay on Rojgarmela.ai topics.
2. Do not invent prices, partnerships, or features you are unsure about.
3. Keep answers concise (2–5 short sentences).
4. Never ask for passwords, OTPs, or payment card details.
5. Do not claim you can create accounts or apply yourself — guide users to the website flows.

Respond with valid JSON only:
{{
  "reply": "helpful answer ONLY in {language}",
  "options": []
}}
or with pills when useful:
{{
  "reply": "helpful answer ONLY in {language}",
  "options": ["Option 1", "Option 2"]
}}
"""


def _parse_ai_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {"reply": text or "How can I help you with Rojgarmela.ai?", "options": []}


def _normalize_language(language: Optional[str]) -> str:
    lang = (language or "english").strip().lower()
    return lang if lang in SUPPORTED_LANGUAGES else "english"


def _topic_options(language: str) -> List[str]:
    return list(DEFAULT_TOPIC_OPTIONS.get(language) or DEFAULT_TOPIC_OPTIONS["english"])


# topic -> language -> reply
_FAQ: dict[str, dict[str, str]] = {
    "about": {
        "english": (
            "Rojgarmela.ai is an AI-powered job platform that connects job seekers, employers, "
            "and training partners across India. It offers AI job matching, resume tools, "
            "interview prep, career roadmaps, training courses, and job fairs."
        ),
        "hindi": (
            "Rojgarmela.ai भारत का AI-powered job platform है जो job seekers, employers और training partners को जोड़ता है। "
            "यहाँ AI job matching, resume tools, interview prep, career roadmap, training courses और job fairs उपलब्ध हैं।"
        ),
        "hinglish": (
            "Rojgarmela.ai India ka AI-powered job platform hai jo job seekers, employers aur training partners ko jodta hai. "
            "Yahan AI matching, resume tools, interview prep, training courses aur job fairs milte hain."
        ),
        "punjabi": (
            "Rojgarmela.ai ਭਾਰਤ ਦਾ AI-powered job platform ਹੈ ਜੋ job seekers, employers ਅਤੇ training partners ਨੂੰ ਜੋੜਦਾ ਹੈ। "
            "ਇੱਥੇ AI matching, resume tools, interview prep, training courses ਅਤੇ job fairs ਉਪਲਬਧ ਹਨ।"
        ),
        "tamil": (
            "Rojgarmela.ai என்பது இந்தியாவின் AI-powered job platform. Job seekers, employers மற்றும் training partners-ஐ இணைக்கிறது. "
            "AI matching, resume tools, interview prep, training courses மற்றும் job fairs கிடைக்கும்."
        ),
        "telugu": (
            "Rojgarmela.ai భారతదేశంలోని AI-powered job platform. Job seekers, employers మరియు training partnersను కలుపుతుంది. "
            "AI matching, resume tools, interview prep, training courses మరియు job fairs అందుబాటులో ఉన్నాయి."
        ),
        "marathi": (
            "Rojgarmela.ai हे भारतातील AI-powered job platform आहे जे job seekers, employers आणि training partners जोडते. "
            "येथे AI matching, resume tools, interview prep, training courses आणि job fairs उपलब्ध आहेत."
        ),
        "bengali": (
            "Rojgarmela.ai ভারতের AI-powered job platform যা job seekers, employers এবং training partnersকে যুক্ত করে। "
            "এখানে AI matching, resume tools, interview prep, training courses এবং job fairs পাওয়া যায়।"
        ),
    },
    "training": {
        "english": (
            "To apply for training on Rojgarmela.ai: open Training from the menu, browse courses, "
            "open the course you want, then click Apply. Sign in as a Job Seeker if prompted, "
            "complete any required profile details, and submit your application."
        ),
        "hindi": (
            "Training के लिए apply करने हेतु: मेनू से Training खोलें, courses देखें, "
            "पसंदीदा course खोलें और Apply पर क्लिक करें। ज़रूरत पड़ने पर Job Seeker के रूप में login करें, "
            "profile details पूरा करें और application submit करें।"
        ),
        "hinglish": (
            "Training ke liye apply karne ke liye: menu se Training kholo, courses browse karo, "
            "jo course chahiye usko open karo aur Apply click karo. Agar pooche to Job Seeker se login karo, "
            "profile details complete karke application submit kar do."
        ),
        "punjabi": (
            "Training ਲਈ apply ਕਰਨ ਲਈ: ਮੀਨੂ ਤੋਂ Training ਖੋਲ੍ਹੋ, courses ਵੇਖੋ, "
            "ਚਾਹੀਦਾ course ਖੋਲ੍ਹੋ ਅਤੇ Apply ’ਤੇ ਕਲਿੱਕ ਕਰੋ। ਲੋੜ ਪੈਣ ’ਤੇ Job Seeker ਵਜੋਂ login ਕਰੋ, "
            "profile details ਪੂਰੀ ਕਰੋ ਅਤੇ application submit ਕਰੋ।"
        ),
        "tamil": (
            "Training-க்கு apply செய்ய: மெனுவில் Training திறந்து courses பாருங்கள், "
            "விருப்பமான course திறந்து Apply அழுத்தவும். தேவைப்பட்டால் Job Seeker ஆக login செய்து "
            "profile details முடித்து application சமர்ப்பிக்கவும்."
        ),
        "telugu": (
            "Training కి apply చేయడానికి: మెనూలో Training తెరిచి courses చూడండి, "
            "కావాల్సిన course తెరిచి Apply నొక్కండి. అవసరమైతే Job Seeker గా login చేసి "
            "profile details పూర్తి చేసి application submit చేయండి."
        ),
        "marathi": (
            "Training साठी apply करण्यासाठी: मेनूमधून Training उघडा, courses पहा, "
            "हवे असलेले course उघडा आणि Apply क्लिक करा. गरज असल्यास Job Seeker म्हणून login करा, "
            "profile details पूर्ण करून application submit करा."
        ),
        "bengali": (
            "Training-এ apply করতে: মেনু থেকে Training খুলুন, courses দেখুন, "
            "পছন্দের course খুলে Apply ক্লিক করুন। প্রয়োজনে Job Seeker হিসেবে login করে "
            "profile details পূরণ করে application জমা দিন।"
        ),
    },
    "seeker": {
        "english": (
            "To register as a Job Seeker, open Register, choose Job Seeker, verify your email, "
            "then complete your profile and upload a resume. You can then browse jobs, get AI matches, "
            "apply for training, and apply to jobs."
        ),
        "hindi": (
            "Job Seeker के रूप में Register खोलें, Job Seeker चुनें, email verify करें, "
            "profile पूरा करें और resume upload करें। फिर jobs, training और AI matches इस्तेमाल कर सकते हैं।"
        ),
        "hinglish": (
            "Job Seeker ke liye Register kholo, Job Seeker choose karo, email verify karo, "
            "profile complete karke resume upload karo. Phir jobs, training aur AI matches use kar sakte ho."
        ),
        "punjabi": (
            "Job Seeker ਵਜੋਂ Register ਖੋਲ੍ਹੋ, Job Seeker ਚੁਣੋ, email verify ਕਰੋ, "
            "profile ਪੂਰੀ ਕਰੋ ਅਤੇ resume upload ਕਰੋ। ਫਿਰ jobs, training ਅਤੇ AI matches ਵਰਤੋ।"
        ),
    },
    "employer": {
        "english": (
            "Employers can register as a Provider, complete the company profile, and post jobs. "
            "You get AI candidate ranking, applicant pipelines, interview scheduling, and job fair tools."
        ),
        "hindi": (
            "Employers Provider के रूप में register करके company profile पूरा कर सकते हैं और jobs post कर सकते हैं। "
            "AI candidate ranking, applicant pipeline, interview scheduling और job fair tools मिलते हैं।"
        ),
        "hinglish": (
            "Employers Provider ke roop mein register karke company profile complete kar sakte hain aur jobs post kar sakte hain. "
            "AI ranking, pipeline, interview scheduling aur job fair tools milte hain."
        ),
        "punjabi": (
            "Employers Provider ਵਜੋਂ register ਕਰਕੇ company profile ਪੂਰੀ ਕਰ ਸਕਦੇ ਹਨ ਅਤੇ jobs post ਕਰ ਸਕਦੇ ਹਨ। "
            "AI ranking, pipeline, interview scheduling ਅਤੇ job fair tools ਮਿਲਦੇ ਹਨ।"
        ),
    },
    "jobs": {
        "english": (
            "Use Find Jobs / Browse Jobs to search openings. Complete your profile for better AI matches. "
            "Track applications under Applied Jobs after you apply."
        ),
        "hindi": (
            "Find Jobs / Browse Jobs से openings खोजें। बेहतर AI matches के लिए profile पूरा रखें। "
            "Apply करने के बाद Applied Jobs में track करें।"
        ),
        "hinglish": (
            "Find Jobs / Browse Jobs se openings khojo. Better AI matches ke liye profile complete rakho. "
            "Apply ke baad Applied Jobs mein track karo."
        ),
        "punjabi": (
            "Find Jobs / Browse Jobs ਤੋਂ openings ਲੱਭੋ। ਵਧੀਆ AI matches ਲਈ profile ਪੂਰੀ ਰੱਖੋ। "
            "Apply ਤੋਂ ਬਾਅਦ Applied Jobs ਵਿੱਚ track ਕਰੋ।"
        ),
    },
    "ai": {
        "english": (
            "Seeker AI tools include Resume Builder, AI Coach (mock interviews), Career Roadmap, "
            "and Rojgar Assessment. Employers can use AI job descriptions, candidate ranking, and AI interviews."
        ),
        "hindi": (
            "Seeker AI tools: Resume Builder, AI Coach (mock interviews), Career Roadmap और Rojgar Assessment। "
            "Employers के लिए AI job descriptions, candidate ranking और AI interviews उपलब्ध हैं।"
        ),
        "hinglish": (
            "Seeker AI tools: Resume Builder, AI Coach (mock interviews), Career Roadmap aur Rojgar Assessment. "
            "Employers ke liye AI job descriptions, candidate ranking aur AI interviews milte hain."
        ),
        "punjabi": (
            "Seeker AI tools: Resume Builder, AI Coach (mock interviews), Career Roadmap ਅਤੇ Rojgar Assessment। "
            "Employers ਲਈ AI job descriptions, candidate ranking ਅਤੇ AI interviews ਉਪਲਬਧ ਹਨ।"
        ),
    },
    "fair": {
        "english": (
            "Job Fairs let seekers and companies register for events, explore fair-specific openings, "
            "and share registration links. Browse Job Fairs from the main navigation."
        ),
        "hindi": (
            "Job Fairs में seekers और companies events के लिए register कर सकते हैं, "
            "fair-specific openings देख सकते हैं और registration links share कर सकते हैं।"
        ),
        "hinglish": (
            "Job Fairs mein seekers aur companies events ke liye register kar sakte hain, "
            "fair openings dekh sakte hain aur registration links share kar sakte hain."
        ),
        "punjabi": (
            "Job Fairs ਵਿੱਚ seekers ਅਤੇ companies events ਲਈ register ਕਰ ਸਕਦੇ ਹਨ, "
            "fair openings ਵੇਖ ਸਕਦੇ ਹਨ ਅਤੇ registration links share ਕਰ ਸਕਦੇ ਹਨ।"
        ),
    },
    "contact": {
        "english": (
            "Reach us via the Contact page, email support@rojgarmela.com, "
            "or call +91-9915137531 / +91-9915130531. You can also join our WhatsApp community."
        ),
        "hindi": (
            "Contact page, email support@rojgarmela.com, या +91-9915137531 / +91-9915130531 पर संपर्क करें। "
            "WhatsApp community भी join कर सकते हैं।"
        ),
        "hinglish": (
            "Contact page, email support@rojgarmela.com, ya +91-9915137531 / +91-9915130531 par contact karo. "
            "WhatsApp community bhi join kar sakte ho."
        ),
        "punjabi": (
            "Contact page, email support@rojgarmela.com, ਜਾਂ +91-9915137531 / +91-9915130531 ’ਤੇ ਸੰਪਰਕ ਕਰੋ। "
            "WhatsApp community ਵੀ join ਕਰ ਸਕਦੇ ਹੋ।"
        ),
    },
    "register": {
        "english": (
            "Click Register, pick Job Seeker or Employer, fill your details, verify email, "
            "then finish onboarding. Seekers should upload a resume; employers should complete the company profile."
        ),
        "hindi": (
            "Register पर क्लिक करें, Job Seeker या Employer चुनें, details भरें, email verify करें, "
            "फिर onboarding पूरा करें।"
        ),
        "hinglish": (
            "Register pe click karo, Job Seeker ya Employer choose karo, details bharo, email verify karo, "
            "phir onboarding complete karo."
        ),
        "punjabi": (
            "Register ’ਤੇ ਕਲਿੱਕ ਕਰੋ, Job Seeker ਜਾਂ Employer ਚੁਣੋ, details ਭਰੋ, email verify ਕਰੋ, "
            "ਫਿਰ onboarding ਪੂਰਾ ਕਰੋ।"
        ),
    },
    "default": {
        "english": (
            "I can help with Rojgarmela.ai — registration, jobs, training, AI tools, job fairs, and support. "
            "Pick an option below or type your question."
        ),
        "hindi": (
            "मैं Rojgarmela.ai से जुड़े सवालों में मदद कर सकता हूँ — registration, jobs, training, AI tools, job fairs और support। "
            "नीचे option चुनें या अपना सवाल लिखें।"
        ),
        "hinglish": (
            "Main Rojgarmela.ai se related sawalon mein help kar sakta hoon — registration, jobs, training, AI tools, job fairs aur support. "
            "Option select karo ya question likho."
        ),
        "punjabi": (
            "ਮੈਂ Rojgarmela.ai ਨਾਲ ਸਬੰਧਤ ਸਵਾਲਾਂ ਵਿੱਚ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ — registration, jobs, training, AI tools, job fairs ਅਤੇ support। "
            "ਹੇਠਾਂ option ਚੁਣੋ ਜਾਂ ਆਪਣਾ ਸਵਾਲ ਲਿਖੋ।"
        ),
        "tamil": (
            "Rojgarmela.ai தொடர்பான கேள்விகளுக்கு உதவ முடியும் — registration, jobs, training, AI tools, job fairs மற்றும் support. "
            "கீழே option தேர்வு செய்யுங்கள் அல்லது கேள்வி எழுதுங்கள்."
        ),
        "telugu": (
            "Rojgarmela.ai సంబంధిత ప్రశ్నలకు సహాయం చేయగలను — registration, jobs, training, AI tools, job fairs మరియు support. "
            "క్రింద option ఎంచుకోండి లేదా ప్రశ్న రాయండి."
        ),
        "marathi": (
            "मी Rojgarmela.ai संबंधित प्रश्नांमध्ये मदत करू शकतो — registration, jobs, training, AI tools, job fairs आणि support. "
            "खाली option निवडा किंवा प्रश्न लिहा."
        ),
        "bengali": (
            "আমি Rojgarmela.ai সম্পর্কিত প্রশ্নে সাহায্য করতে পারি — registration, jobs, training, AI tools, job fairs এবং support। "
            "নিচে option বেছে নিন বা প্রশ্ন লিখুন।"
        ),
    },
    "thanks": {
        "english": (
            "You're welcome! Thank you for chatting with Rojgarmela.ai. "
            "Wishing you the best — come back anytime if you need help."
        ),
        "hindi": (
            "आपका स्वागत है! Rojgarmela.ai से बात करने के लिए धन्यवाद। "
            "आपकी सफलता की शुभकामनाएँ — ज़रूरत पड़ने पर फिर पूछिए।"
        ),
        "hinglish": (
            "You're welcome! Rojgarmela.ai se baat karne ke liye thank you. "
            "All the best — zarurat pade to kabhi bhi wapas aana."
        ),
        "punjabi": (
            "ਜੀ ਆਇਆਂ ਨੂੰ! Rojgarmela.ai ਨਾਲ ਗੱਲ ਕਰਨ ਲਈ ਧੰਨਵਾਦ। "
            "ਤੁਹਾਡੀ ਸਫਲਤਾ ਲਈ ਸ਼ੁਭਕਾਮਨਾਵਾਂ — ਲੋੜ ਪਏ ਤਾਂ ਫਿਰ ਪੁੱਛੋ।"
        ),
        "tamil": (
            "வரவேற்கிறோம்! Rojgarmela.ai உடன் பேசியதற்கு நன்றி. "
            "உங்களுக்கு வாழ்த்துகள் — தேவைப்பட்டால் மீண்டும் கேளுங்கள்."
        ),
        "telugu": (
            "స్వాగతం! Rojgarmela.ai తో మాట్లాడినందుకు ధన్యవాదాలు. "
            "మీ విజయానికి శుభాకాంక్షలు — అవసరమైతే మళ్లీ అడగండి."
        ),
        "marathi": (
            "आपले स्वागत आहे! Rojgarmela.ai शी बोलल्याबद्दल धन्यवाद. "
            "यशस्वी व्हा — गरज असल्यास पुन्हा विचारा."
        ),
        "bengali": (
            "স্বাগতম! Rojgarmela.ai-এর সাথে কথা বলার জন্য ধন্যবাদ। "
            "শুভকামনা — দরকার হলে আবার জিজ্ঞাসা করুন।"
        ),
    },
}


def _topic_key(message: str) -> str:
    q = (message or "").lower().strip()
    # Closing / thanks — handle before other topics
    if any(
        k in q
        for k in (
            "thank",
            "thanks",
            "thx",
            "ty",
            "bye",
            "goodbye",
            "good bye",
            "see you",
            "dhanyavad",
            "dhanyavaad",
            "shukriya",
            "शुक्रिया",
            "धन्यवाद",
            "धन्यवाद्",
            "ਧੰਨਵਾਦ",
            "நன்றி",
            "ధన్యవాద",
            "धन्यवाद",
            "ধন্যবাদ",
        )
    ) or q in {"ok", "okay", "ok thanks", "ok thank you", "done", "great", "nice"}:
        return "thanks"
    # Training before generic "apply" / jobs
    if any(
        k in q
        for k in (
            "training",
            "course",
            "courses",
            "ट्रेनिंग",
            "कोर्स",
            "ਟ੍ਰੇਨਿੰਗ",
            "பயிற்சி",
            "శిక్షణ",
        )
    ):
        return "training"
    if any(
        k in q
        for k in (
            "what is rojgar",
            "about rojgar",
            "rojgarmela.ai?",
            "rojgarmela.ai क्या",
            "rojgarmela.ai kya",
            "rojgarmela.ai ਕੀ",
            "platform kya",
            "what is rojgarmela",
        )
    ) or (
        ("rojgar" in q or "rojgarmela" in q)
        and any(k in q for k in ("what", "kya", "क्या", "ਕੀ", "என்ன", "ఏమి", "কী", "काय"))
    ):
        return "about"
    if any(k in q for k in ("seeker", "candidate", "job seeker")):
        return "seeker"
    if any(k in q for k in ("employer", "provider", "company", "hire", "post job")):
        return "employer"
    if any(k in q for k in ("resume", "interview", "coach", "roadmap", "assessment", "ai tool", "ai matching")):
        return "ai"
    if any(k in q for k in ("job fair", "job fairs")) or (
        "fair" in q and "job" in q
    ):
        return "fair"
    if any(k in q for k in ("contact", "support", "phone", "email", "संपर्क", "ਸੰਪਰਕ")):
        return "contact"
    if any(k in q for k in ("register", "sign up", "signup", "create account", "रजिस्टर", "नोंदणी", "ਰਜਿਸਟਰ")):
        return "register"
    if any(k in q for k in ("find job", "browse job", "search job", "applied job")) or (
        "jobs" in q and "training" not in q
    ):
        return "jobs"
    if "apply" in q and "training" not in q and "course" not in q:
        return "jobs"
    return "default"


def _faq_reply(topic: str, language: str) -> str:
    by_lang = _FAQ.get(topic) or _FAQ["default"]
    if language in by_lang:
        return by_lang[language]
    # Prefer hinglish bridge for missing regional translations of specific topics
    if language in ("tamil", "telugu", "marathi", "bengali") and "english" in by_lang:
        # Still answer; use english content only if no native — prefer hinglish if present else english
        return by_lang.get(language) or by_lang.get("hinglish") or by_lang["english"]
    return by_lang.get("english") or _FAQ["default"]["english"]


def _faq_fallback(message: str, language: str) -> dict[str, Any]:
    """Knowledge answers when Gemini is unavailable. Pills only when helpful."""
    key = _topic_key(message)
    reply = _faq_reply(key, language)

    # Direct answers + thanks/closing → no pills. Vague/default → offer pills.
    if key in ("default",):
        options = _topic_options(language)
    else:
        options = []

    return {"reply": reply, "options": options}


def _normalize_options(raw_options: Any, language: str) -> List[str]:
    if raw_options is None:
        return []
    if not isinstance(raw_options, list):
        return []
    cleaned = [str(o).strip() for o in raw_options if str(o).strip()]
    return cleaned[:4]


async def generate_landing_reply(
    message: str,
    history: Optional[List[dict]] = None,
    language: Optional[str] = None,
) -> dict[str, Any]:
    """Return {reply, options}. Empty options means no pill tabs."""
    msg = (message or "").strip()
    lang = _normalize_language(language)

    if not msg:
        return {
            "reply": _faq_reply("default", lang),
            "options": _topic_options(lang),
        }

    if len(msg) > 2000:
        msg = msg[:2000]

    # Closing thanks — reply immediately in selected language (no pills)
    if _topic_key(msg) == "thanks":
        return {"reply": _faq_reply("thanks", lang), "options": []}

    if (not settings.GOOGLE_API_KEY and not settings.OPENAI_API_KEY) or settings.AI_MODE == "mock":
        return _faq_fallback(msg, lang)

    history = history or []
    convo_lines = []
    for turn in history[-8:]:
        role = (turn.get("role") or "").strip().lower()
        text = (turn.get("content") or "").strip()
        if not text:
            continue
        label = "User" if role == "user" else "Assistant"
        convo_lines.append(f"{label}: {text}")

    user_prompt = (
        f"Selected language (MANDATORY for reply + options): {lang}\n"
        f"Conversation so far:\n{chr(10).join(convo_lines) if convo_lines else '(none)'}\n\n"
        f"User: {msg}\n\n"
        "Decide yourself whether options pills are needed. "
        "If the answer is complete and specific, return options as []. "
        "Respond with JSON only."
    )

    try:
        ai = get_ai()
        raw = await asyncio.wait_for(
            ai.chat_completion(SYSTEM_PROMPT.format(language=lang), user_prompt),
            timeout=12,
        )
        parsed = _parse_ai_json(raw)
        reply = (parsed.get("reply") or "").strip()
        options = _normalize_options(parsed.get("options"), lang)
        if not reply:
            return _faq_fallback(msg, lang)
        return {"reply": reply, "options": options}
    except Exception as exc:
        logger.warning("Landing chat AI error, using FAQ fallback: %s", exc)
        return _faq_fallback(msg, lang)
