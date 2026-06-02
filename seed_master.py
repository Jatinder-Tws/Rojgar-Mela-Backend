import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.master import MasterState, MasterCity, MasterIndustry, MasterLanguage, MasterRole

# STATES_CITIES = {
#     "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik"],
#     "Karnataka": ["Bengaluru", "Mysuru", "Hubli", "Mangaluru"],
#     "Delhi": ["New Delhi", "Dwarka", "Rohini"],
#     "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai"],
#     "Telangana": ["Hyderabad", "Warangal"],
#     "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot"],
#     "West Bengal": ["Kolkata", "Howrah", "Durgapur"]
# }
STATES_CITIES = {
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Thane", "Aurangabad"],
    "Karnataka": ["Bengaluru", "Mysuru", "Hubli", "Mangaluru", "Belagavi"],
    "Delhi": ["New Delhi", "Dwarka", "Rohini", "Saket"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli"],
    "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar"],
    "West Bengal": ["Kolkata", "Howrah", "Durgapur", "Siliguri", "Asansol"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Varanasi", "Agra", "Noida"],
    "Rajasthan": ["Jaipur", "Udaipur", "Jodhpur", "Kota", "Ajmer"],
    # "Madhya Pradesh": ["Bhopal", "Indore", "Gwalior", "Jabalpur"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Gwalior", "Jabalpur"],
    "Kerala": ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur"],
    "Punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala"],
    "Haryana": ["Gurugram", "Faridabad", "Panipat", "Ambala"],
    "Bihar": ["Patna", "Gaya", "Muzaffarpur", "Bhagalpur"],
    "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela", "Puri"],
    "Assam": ["Guwahati", "Dibrugarh", "Silchar"],
    "Jharkhand": ["Ranchi", "Jamshedpur", "Dhanbad"],
    "Chhattisgarh": ["Raipur", "Bhilai", "Bilaspur"],
    "Uttarakhand": ["Dehradun", "Haridwar", "Nainital"],
    "Himachal Pradesh": ["Shimla", "Manali", "Dharamshala"],
    "Goa": ["Panaji", "Margao", "Vasco da Gama"],
    "Tripura": ["Agartala"],
    "Meghalaya": ["Shillong"],
    "Manipur": ["Imphal"],
    "Nagaland": ["Kohima", "Dimapur"],
    "Mizoram": ["Aizawl"],
    "Sikkim": ["Gangtok"],
    "Arunachal Pradesh": ["Itanagar"]
}

INDUSTRIES = [
    "Information Technology",
    "Healthcare",
    "Finance",
    "Education",
    "Manufacturing",
    "Retail",
    "Real Estate",
    "Entertainment",
    "Consulting",
    "Telecommunications",
    "Marketing & Advertising"
]

# LANGUAGES = [
#     "English",
#     "Hindi",
#     "Marathi",
#     "Kannada",
#     "Telugu",
#     "Tamil",
#     "Gujarati",
#     "Bengali",
#     "Spanish",
#     "French",
#     "German",
#     "Japanese",
#     "Mandarin"
# ]
LANGUAGES = [
    "Hindi",
    "English",
    "Assamese",
    "Bengali",
    "Bodo",
    "Dogri",
    "Gujarati",
    "Kannada",
    "Kashmiri",
    "Konkani",
    "Maithili",
    "Malayalam",
    "Manipuri (Meitei)",
    "Marathi",
    "Nepali",
    "Odia",
    "Punjabi",
    "Sanskrit",
    "Santali",
    "Sindhi",
    "Tamil",
    "Telugu",
    "Urdu"
]


ROLES = [
    "Software Engineer",
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "Data Scientist",
    "Data Analyst",
    "Product Manager",
    "Project Manager",
    "Sales Executive",
    "Marketing Manager",
    "HR Manager",
    "Business Analyst",
    "UI/UX Designer",
    "DevOps Engineer"
]

async def seed_master_data(session: AsyncSession):
    # Seed Industries
    for ind in INDUSTRIES:
        existing = await session.execute(select(MasterIndustry).where(MasterIndustry.name == ind))
        if not existing.scalars().first():
            session.add(MasterIndustry(name=ind))
    
    # Seed Languages
    for lang in LANGUAGES:
        existing = await session.execute(select(MasterLanguage).where(MasterLanguage.name == lang))
        if not existing.scalars().first():
            session.add(MasterLanguage(name=lang))
            
    # Seed Roles
    for role in ROLES:
        existing = await session.execute(select(MasterRole).where(MasterRole.name == role))
        if not existing.scalars().first():
            session.add(MasterRole(name=role))
            
    # Seed States and Cities
    for state_name, cities in STATES_CITIES.items():
        existing_state_res = await session.execute(select(MasterState).where(MasterState.name == state_name))
        state_db = existing_state_res.scalars().first()
        
        if not state_db:
            code = state_name.replace(" ", "").upper()[:10]
            state_db = MasterState(name=state_name, code=code)
            session.add(state_db)
            await session.flush()
            
        for city_name in cities:
            existing_city = await session.execute(
                select(MasterCity).where(MasterCity.name == city_name, MasterCity.state_id == state_db.id)
            )
            if not existing_city.scalars().first():
                session.add(MasterCity(name=city_name, state_id=state_db.id))
                
    await session.commit()
