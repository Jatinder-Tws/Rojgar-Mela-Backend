import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User
from models.portfolio import Portfolio
from datetime import datetime
from models.master import MasterState, MasterCity, MasterIndustry, MasterLanguage, MasterRole
from models.master_data import Department, DepartmentJob

null = None
true = True
false = False

# STATES_CITIES = {
#     "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik"],
#     "Karnataka": ["Bengaluru", "Mysuru", "Hubli", "Mangaluru"],
#     "Delhi": ["New Delhi", "Dwarka", "Rohini"],
#     "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai"],
#     "Telangana": ["Hyderabad", "Warangal"],
#     "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot"],
#     "West Bengal": ["Kolkata", "Howrah", "Durgapur"]
# }
# STATES_CITIES = {
#     "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Thane", "Aurangabad"],
#     "Karnataka": ["Bengaluru", "Mysuru", "Hubli", "Mangaluru", "Belagavi"],
#     "Delhi": ["New Delhi", "Dwarka", "Rohini", "Saket"],
#     "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli"],
#     "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar"],
#     "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar"],
#     "West Bengal": ["Kolkata", "Howrah", "Durgapur", "Siliguri", "Asansol"],
#     "Uttar Pradesh": ["Lucknow", "Kanpur", "Varanasi", "Agra", "Noida"],
#     "Rajasthan": ["Jaipur", "Udaipur", "Jodhpur", "Kota", "Ajmer"],
#     # "Madhya Pradesh": ["Bhopal", "Indore", "Gwalior", "Jabalpur"],
#     "Madhya Pradesh": ["Bhopal", "Indore", "Gwalior", "Jabalpur"],
#     "Kerala": ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur"],
#     "Punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala"],
#     "Haryana": ["Gurugram", "Faridabad", "Panipat", "Ambala"],
#     "Bihar": ["Patna", "Gaya", "Muzaffarpur", "Bhagalpur"],
#     "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela", "Puri"],
#     "Assam": ["Guwahati", "Dibrugarh", "Silchar"],
#     "Jharkhand": ["Ranchi", "Jamshedpur", "Dhanbad"],
#     "Chhattisgarh": ["Raipur", "Bhilai", "Bilaspur"],
#     "Uttarakhand": ["Dehradun", "Haridwar", "Nainital"],
#     "Himachal Pradesh": ["Shimla", "Manali", "Dharamshala"],
#     "Goa": ["Panaji", "Margao", "Vasco da Gama"],
#     "Tripura": ["Agartala"],
#     "Meghalaya": ["Shillong"],
#     "Manipur": ["Imphal"],
#     "Nagaland": ["Kohima", "Dimapur"],
#     "Mizoram": ["Aizawl"],
#     "Sikkim": ["Gangtok"],
#     "Arunachal Pradesh": ["Itanagar"]
# }

STATES_CITIES = {
    "Maharashtra": [
        "Mumbai", "Pune", "Nagpur", "Nashik", "Thane", "Aurangabad"
    ],

    "Karnataka": [
        "Bengaluru", "Mysuru", "Hubli", "Mangaluru", "Belagavi"
    ],

    "Delhi": [
        "New Delhi", "Dwarka", "Rohini", "Saket"
    ],

    "Tamil Nadu": [
        "Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli"
    ],

    "Telangana": [
        "Hyderabad", "Warangal", "Nizamabad", "Karimnagar"
    ],

    "Gujarat": [
        "Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar"
    ],

    "West Bengal": [
        "Kolkata", "Howrah", "Durgapur", "Siliguri", "Asansol"
    ],

    "Uttar Pradesh": [
        "Lucknow", "Kanpur", "Varanasi", "Agra", "Noida"
    ],

    "Rajasthan": [
        "Jaipur", "Udaipur", "Jodhpur", "Kota", "Ajmer"
    ],

    "Madhya Pradesh": [
        "Bhopal", "Indore", "Gwalior", "Jabalpur"
    ],

    "Kerala": [
        "Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur"
    ],

    "Punjab": [
        "Ludhiana", "Amritsar", "Jalandhar", "Patiala",
        "Bathinda", "Mohali", "Hoshiarpur", "Batala",
        "Pathankot", "Moga", "Abohar", "Malerkotla",
        "Khanna", "Phagwara"
    ],

    "Haryana": [
        "Gurugram", "Faridabad", "Panipat", "Ambala",
        "Hisar", "Karnal", "Rohtak", "Sonipat",
        "Yamunanagar", "Panchkula", "Bhiwani",
        "Sirsa", "Rewari", "Kurukshetra"
    ],

    "Bihar": [
        "Patna", "Gaya", "Muzaffarpur", "Bhagalpur",
        "Darbhanga", "Purnia", "Arrah", "Begusarai",
        "Katihar", "Munger", "Chapra", "Saharsa",
        "Samastipur", "Motihari"
    ],

    "Odisha": [
        "Bhubaneswar", "Cuttack", "Rourkela", "Puri",
        "Sambalpur", "Berhampur", "Balasore",
        "Jharsuguda", "Baripada", "Jeypore", "Bhadrak"
    ],

    "Assam": [
        "Guwahati", "Dibrugarh", "Silchar",
        "Jorhat", "Tezpur", "Nagaon",
        "Tinsukia", "Sivasagar", "Bongaigaon"
    ],

    "Jharkhand": [
        "Ranchi", "Jamshedpur", "Dhanbad",
        "Bokaro", "Hazaribagh", "Deoghar",
        "Giridih", "Ramgarh", "Chaibasa"
    ],

    "Chhattisgarh": [
        "Raipur", "Bhilai", "Bilaspur",
        "Korba", "Jagdalpur", "Rajnandgaon",
        "Raigarh", "Ambikapur", "Durg"
    ],

    "Uttarakhand": [
        "Dehradun", "Haridwar", "Nainital",
        "Rishikesh", "Roorkee", "Haldwani",
        "Rudrapur", "Almora", "Pithoragarh"
    ],

    "Himachal Pradesh": [
        "Shimla", "Manali", "Dharamshala",
        "Solan", "Mandi", "Kullu",
        "Hamirpur", "Bilaspur", "Chamba"
    ],

    "Goa": [
        "Panaji", "Margao", "Vasco da Gama",
        "Mapusa", "Ponda", "Bicholim", "Canacona"
    ],

    "Tripura": [
        "Agartala", "Udaipur", "Dharmanagar",
        "Kailasahar", "Belonia"
    ],

    "Meghalaya": [
        "Shillong", "Tura", "Jowai",
        "Nongpoh", "Baghmara"
    ],

    "Manipur": [
        "Imphal", "Thoubal", "Bishnupur",
        "Churachandpur", "Ukhrul"
    ],

    "Nagaland": [
        "Kohima", "Dimapur", "Mokokchung",
        "Tuensang", "Wokha", "Zunheboto"
    ],

    "Mizoram": [
        "Aizawl", "Lunglei", "Champhai",
        "Serchhip", "Kolasib"
    ],

    "Sikkim": [
        "Gangtok", "Namchi", "Gyalshing",
        "Mangan", "Singtam"
    ],

    "Arunachal Pradesh": [
        "Itanagar", "Naharlagun", "Tawang",
        "Pasighat", "Ziro", "Bomdila", "Roing"
    ]
}


DEPARTMENTS_DATA = {
    "Admissions": [],
    "Student Services": [],
    "Faculty Administration": [],
    "Underwriting": [],
    "Claims": [],
    "Loan Processing": [],
    "Credit Analysis": [],
    "Civil Engineering": [],
    "Site Operations": [],
    "Safety": [],
    "Project Management": [],
    "Physical Security": [],
    "Information Security": [],
    "Corporate Social Responsibility": [],
    "Environmental Health & Safety": [],
    "Sustainability": [],
    "Facilities": [],
    "Housekeeping": [],
    "Technical Writing": [],
    "Documentation": [],
    "Knowledge Management": [],
    "Management": [
        "Product Manager", "Team Lead", "Delivery Manager", 
        "Scrum Master", "Business Analyst"
    ],
    "Executive Office": [],
    "Strategy": [],
    "Corporate Planning": [],
    "Nursing": [],
    "Board Administration": [],
    "Software Development": [],
    "Custom Development": [
        "MERN Full Stack Developer", "Python Developer", "Mobile App Developer", 
        "Java Developer", "PHP Developer", "Node.js Developer", "React Native Developer"
    ],
    "Web Development": [],
    "Mobile Development": [],
    "DevOps": [],
    "Cloud Engineering": [],
    "Infrastructure": [],
    "Network Administration": [],
    "Database Administration": [],
    "Cybersecurity": [],
    "IT Support": [],
    "Technical Support": [
        "Customer Support Executive", "Technical Support Engineer", 
        "IT Support Specialist", "Desktop Support Engineer"
    ],
    "QA Team": [
        "QA Engineer", "Automation Tester", "Manual Tester", 
        "Performance Tester", "Security Analyst"
    ],
    "QA / Testing": [],
    "Data Engineering": [],
    "Artificial Intelligence / Machine Learning": [],
    "Business Intelligence": [],
    "Designing Team": [
        "UI/UX Designer", "Graphic Designer", "Web Designer", 
        "Motion Graphics Artist", "Product Designer"
    ],
    "UI/UX Design": [],
    "Graphic Design": [],
    "Product Design": [],
    "Video Production": [],
    "Content Creation": [],
    "Sales Team": [
        "Business Development Manager", "Sales Executive", "Account Manager", 
        "Inside Sales Specialist", "Pre-Sales Engineer"
    ],
    "Business Development": [],
    "Account Management": [],
    "Inside Sales": [],
    "Field Sales": [],
    "Pre-Sales": [],
    "Customer Acquisition": [],
    "Digital Marketing": [
        "SEO Specialist", "Content Writer", "Social Media Manager", 
        "PPC Expert", "Digital Marketing Executive", "Email Marketer"
    ],
    "Brand Marketing": [],
    "Performance Marketing": [],
    "SEO": [],
    "Social Media Marketing": [],
    "Product Marketing": [],
    "Public Relations": [],
    "Communications": [],
    "Human Resources": [],
    "HR Administration": [
        "HR Manager", "Talent Acquisition Specialist", "Admin Executive", 
        "Office Coordinator", "Employee Relations Specialist"
    ],
    "Talent Acquisition": [],
    "Recruitment": [],
    "Learning & Development": [],
    "Employee Relations": [],
    "Compensation & Benefits": [],
    "Payroll": [],
    "Operations": [
        "Operations Manager", "Project Coordinator", "Data Entry Operator", 
        "Logistics Coordinator", "Supply Chain Analyst"
    ],
    "Process Management": [],
    "Service Delivery": [],
    "Resource Management": [],
    "Administration": [],
    "Customer Support": [],
    "Customer Success": [],
    "Call Center": [],
    "Help Desk": [],
    "Finance": [],
    "Accounting": [],
    "Accounts Payable": [],
    "Accounts Receivable": [],
    "Treasury": [],
    "Taxation": [],
    "Audit": [],
    "Financial Planning & Analysis": [],
    "Legal": [],
    "Compliance": [],
    "Risk Management": [],
    "Corporate Governance": [],
    "Procurement": [],
    "Purchasing": [],
    "Supply Chain": [],
    "Logistics": [],
    "Inventory Management": [],
    "Vendor Management": [],
    "Warehouse": [],
    "Production": [],
    "Manufacturing": [],
    "Quality Control": [],
    "Maintenance": [],
    "Industrial Engineering": [],
    "Research and Development (R&D)": [],
    "Innovation Lab": [],
    "Product Engineering": [],
    "Data Science": [],
    "Analytics": [],
    "Reporting": [],
    "Data Governance": [],
    "Product Management": [],
    "Product Strategy": [],
    "Product Operations": [],
    "Medical Administration": [],
    "Laboratory": [],
    "Pharmacy": [],
    "Clinical Operations": [],
    "Academic Affairs": []
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
    "Marketing & Advertising",
    "E-commerce",
    "Logistics & Supply Chain",
    "Automotive",
    "Banking",
    "Insurance",
    "Pharmaceuticals",
    "Biotechnology",
    "Construction",
    "Energy & Utilities",
    "Oil & Gas",
    "Agriculture",
    "Food & Beverage",
    "Hospitality",
    "Travel & Tourism",
    "Media & Publishing",
    "Legal Services",
    "Government & Public Sector",
    "Non-Profit",
    "Human Resources",
    "Cybersecurity",
    "Artificial Intelligence & Machine Learning",
    "Cloud Computing",
    "Semiconductors",
    "Aerospace & Defense",
    "Mining & Metals",
    "Textiles & Apparel",
    "Consumer Goods",
    "Electronics",
    "Television & Broadcasting",
    "Sports & Fitness",
    "Environmental Services",
    "Waste Management",
    "Marine & Shipping",
    "Architecture & Planning",
    "Design Services",
    "Research & Development",
    "Event Management",
    "Gaming",
    "Animation & VFX",
    "EdTech",
    "FinTech",
    "HealthTech",
    "InsurTech",
    "PropTech",
    "AgriTech",
    "CleanTech",
    "Robotics",
    "IoT (Internet of Things)",
    "Blockchain",
    "Digital Marketing",
    "BPO & KPO",
    "Staffing & Recruitment",
    "Procurement",
    "Import & Export",
    "Luxury Goods",
    "Jewelry",
    "Furniture & Home Decor",
    "Printing & Packaging",
    "Music Industry",
    "Film Production",
    "Social Media",
    "Data Analytics",
    "Venture Capital & Private Equity",
    "Accounting & Auditing",
    "Corporate Training",
    "Security Services",
    "Facilities Management",
    "Pet Care",
    "Beauty & Cosmetics",
    "Wellness & Mental Health",
    "Translation & Localization",
    "Open Source Software",
    "Mobile Applications",
    "SaaS (Software as a Service)",
    "Hardware",
    "Networking",
    "Quantum Computing",
    "Space Technology",
    "Renewable Energy",
    "Drones",
    "3D Printing"
]

# INDUSTRIES = [
#     "Information Technology",
#     "Healthcare",
#     "Finance",
#     "Education",
#     "Manufacturing",
#     "Retail",
#     "Real Estate",
#     "Entertainment",
#     "Consulting",
#     "Telecommunications",
#     "Marketing & Advertising"
# ]

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


ROLES = {
    "Information Technology": [
        "Software Engineer",
        "Frontend Developer",
        "Backend Developer",
        "Full Stack Developer",
        "DevOps Engineer",
        "UI/UX Designer",
        "Data Analyst",
        "Data Scientist",
        "Business Analyst",
        "Product Manager",
        "Project Manager",
        "QA Engineer",
        "Mobile App Developer",
        "Cloud Engineer"
    ],
    "Healthcare": [
        "Healthcare Data Analyst",
        "Clinical Research Associate",
        "Medical Writer",
        "Regulatory Affairs Specialist",
        "Pharmacovigilance Specialist",
        "Healthcare Project Manager",
        "Healthcare Business Analyst",
        "Hospital Administrator",
        "Medical Coder"
    ],
    "Finance": [
        "Financial Analyst",
        "Investment Analyst",
        "Risk Analyst",
        "Compliance Officer",
        "Accountant",
        "Auditor",
        "Finance Data Analyst",
        "Finance Business Analyst",
        "Treasury Analyst"
    ],
    "Education": [
        "Teacher",
        "Professor",
        "Instructional Designer",
        "Curriculum Developer",
        "Education Product Manager",
        "EdTech Software Engineer",
        "Academic Coordinator"
    ],
    "Manufacturing": [
        "Industrial Engineer",
        "Mechanical Engineer",
        "Manufacturing Engineer",
        "Quality Assurance Engineer",
        "Supply Chain Analyst",
        "Procurement Specialist",
        "Operations Manager",
        "Plant Manager"
    ],
    "Retail": [
        "Sales Executive",
        "Store Manager",
        "Merchandiser",
        "Inventory Manager",
        "Retail Marketing Manager",
        "Retail Data Analyst",
        "Retail Product Manager",
        "Category Manager"
    ],
    "Real Estate": [
        "Real Estate Consultant",
        "Property Manager",
        "Real Estate Sales Executive",
        "Real Estate Marketing Manager",
        "Real Estate Business Analyst"
    ],
    "Entertainment": [
        "Graphic Designer",
        "Animator",
        "Video Producer",
        "Film Editor",
        "Entertainment UI/UX Designer",
        "Entertainment Marketing Manager",
        "Content Creator"
    ],
    "Consulting": [
        "Consultant",
        "Management Consultant",
        "Strategy Consultant",
        "Consulting Business Analyst",
        "Consulting Data Analyst",
        "Consulting Project Manager"
    ],
    "Telecommunications": [
        "Network Engineer",
        "Telecommunications Engineer",
        "Telecom Backend Developer",
        "Telecom DevOps Engineer",
        "Telecom Data Analyst",
        "RF Engineer"
    ],
    "Marketing & Advertising": [
        "Marketing Manager",
        "Digital Marketing Specialist",
        "SEO Specialist",
        "Social Media Manager",
        "Copywriter",
        "Graphic Designer",
        "Advertising Sales Executive",
        "Brand Manager"
    ],
    "E-commerce": [
        "E-commerce Manager",
        "Catalog Manager",
        "E-commerce Product Manager",
        "E-commerce Data Analyst",
        "E-commerce Frontend Developer",
        "Marketplace Specialist"
    ],
    "Logistics & Supply Chain": [
        "Logistics Coordinator",
        "Warehouse Manager",
        "Supply Chain Manager",
        "Procurement Specialist",
        "Operations Executive",
        "Transportation Manager"
    ],
    "Automotive": [
        "Automotive Engineer",
        "Vehicle Design Engineer",
        "Automotive Quality Engineer",
        "Automotive Project Manager",
        "Service Engineer"
    ],
    "Banking": [
        "Banking Operations Executive",
        "Relationship Manager",
        "Credit Analyst",
        "Banking Risk Analyst",
        "Loan Officer"
    ],
    "Insurance": [
        "Insurance Advisor",
        "Claims Analyst",
        "Underwriter",
        "Actuary",
        "Policy Administrator"
    ],
    "Pharmaceuticals": [
        "Pharmacist",
        "Pharmaceutical Research Scientist",
        "Drug Safety Associate",
        "Regulatory Affairs Manager",
        "Quality Control Analyst"
    ],
    "Biotechnology": [
        "Biotechnologist",
        "Research Scientist",
        "Lab Technician",
        "Clinical Data Manager",
        "Bioinformatics Analyst"
    ],
    "Construction": [
        "Civil Engineer",
        "Architect",
        "Site Engineer",
        "Quantity Surveyor",
        "Construction Project Manager"
    ],
    "Energy & Utilities": [
        "Energy Analyst",
        "Power Systems Engineer",
        "Utility Operations Manager",
        "Electrical Engineer",
        "Renewable Energy Engineer"
    ],
    "Oil & Gas": [
        "Petroleum Engineer",
        "Drilling Engineer",
        "Reservoir Engineer",
        "HSE Officer",
        "Process Engineer"
    ],
    "Agriculture": [
        "Agronomist",
        "Agricultural Engineer",
        "Farm Manager",
        "Soil Scientist",
        "Crop Analyst"
    ],
    "Food & Beverage": [
        "Food Technologist",
        "Quality Assurance Manager",
        "Production Supervisor",
        "Food Safety Officer",
        "Supply Chain Manager"
    ],
    "Hospitality": [
        "Hotel Manager",
        "Front Office Executive",
        "Housekeeping Manager",
        "Restaurant Manager",
        "Guest Relations Executive"
    ],
    "Travel & Tourism": [
        "Travel Consultant",
        "Tour Manager",
        "Reservation Executive",
        "Destination Specialist",
        "Operations Coordinator"
    ],
    "Media & Publishing": [
        "Editor",
        "Journalist",
        "Content Writer",
        "Publishing Manager",
        "Proofreader"
    ],
    "Legal Services": [
        "Lawyer",
        "Legal Associate",
        "Paralegal",
        "Compliance Officer",
        "Contract Specialist"
    ],
    "Government & Public Sector": [
        "Policy Analyst",
        "Public Administrator",
        "Program Officer",
        "Government Project Manager",
        "Research Officer"
    ],
    "Non-Profit": [
        "Program Manager",
        "Fundraising Manager",
        "Community Outreach Coordinator",
        "Grant Writer",
        "Volunteer Coordinator"
    ],
    "Human Resources": [
        "HR Executive",
        "HR Manager",
        "Recruiter",
        "Talent Acquisition Specialist",
        "Learning and Development Specialist"
    ],
    "Cybersecurity": [
        "Cybersecurity Analyst",
        "Security Engineer",
        "Penetration Tester",
        "SOC Analyst",
        "Incident Response Specialist"
    ],
    "Artificial Intelligence & Machine Learning": [
        "AI Engineer",
        "Machine Learning Engineer",
        "Prompt Engineer",
        "Research Scientist",
        "MLOps Engineer"
    ],
    "Cloud Computing": [
        "Cloud Engineer",
        "Cloud Architect",
        "Site Reliability Engineer",
        "DevOps Engineer",
        "Infrastructure Engineer"
    ],
    "Semiconductors": [
        "Semiconductor Engineer",
        "Chip Design Engineer",
        "Verification Engineer",
        "Process Engineer",
        "Test Engineer"
    ],
    "Aerospace & Defense": [
        "Aerospace Engineer",
        "Avionics Engineer",
        "Systems Engineer",
        "Defense Analyst",
        "Quality Engineer"
    ],
    "Mining & Metals": [
        "Mining Engineer",
        "Metallurgical Engineer",
        "Geologist",
        "Safety Officer",
        "Operations Manager"
    ],
    "Textiles & Apparel": [
        "Textile Engineer",
        "Fashion Designer",
        "Production Merchandiser",
        "Quality Inspector",
        "Sourcing Manager"
    ],
    "Consumer Goods": [
        "Brand Manager",
        "Category Manager",
        "Sales Manager",
        "Supply Chain Analyst",
        "Product Manager"
    ],
    "Electronics": [
        "Electronics Engineer",
        "Embedded Systems Engineer",
        "Hardware Design Engineer",
        "PCB Design Engineer",
        "Electronics Test Engineer"
    ],
    "Television & Broadcasting": [
        "Broadcast Engineer",
        "Video Editor",
        "TV Producer",
        "Camera Operator",
        "Broadcast Technician"
    ],
    "Sports & Fitness": [
        "Fitness Trainer",
        "Sports Coach",
        "Sports Nutritionist",
        "Gym Manager",
        "Sports Analyst"
    ],
    "Environmental Services": [
        "Environmental Engineer",
        "Sustainability Analyst",
        "Environmental Consultant",
        "Ecologist",
        "Compliance Specialist"
    ],
    "Waste Management": [
        "Waste Management Specialist",
        "Recycling Coordinator",
        "Environmental Compliance Officer",
        "Operations Supervisor",
        "Safety Officer"
    ],
    "Marine & Shipping": [
        "Marine Engineer",
        "Ship Operations Manager",
        "Logistics Coordinator",
        "Port Manager",
        "Naval Architect"
    ],
    "Architecture & Planning": [
        "Architect",
        "Urban Planner",
        "Landscape Architect",
        "Draftsman",
        "Planning Consultant"
    ],
    "Design Services": [
        "Graphic Designer",
        "UI/UX Designer",
        "Product Designer",
        "Interior Designer",
        "Creative Director"
    ],
    "Research & Development": [
        "Research Scientist",
        "R&D Engineer",
        "Innovation Manager",
        "Lab Technician",
        "Prototype Engineer"
    ],
    "Event Management": [
        "Event Manager",
        "Event Coordinator",
        "Wedding Planner",
        "Production Manager",
        "Sponsorship Manager"
    ],
    "Gaming": [
        "Game Developer",
        "Game Designer",
        "Game Artist",
        "Level Designer",
        "QA Tester"
    ],
    "Animation & VFX": [
        "Animator",
        "VFX Artist",
        "3D Modeler",
        "Compositor",
        "Motion Graphics Designer"
    ],
    "EdTech": [
        "EdTech Product Manager",
        "Instructional Designer",
        "Learning Experience Designer",
        "Education Software Engineer",
        "Academic Content Developer"
    ],
    "FinTech": [
        "FinTech Product Manager",
        "Financial Software Engineer",
        "Payments Analyst",
        "Risk Analyst",
        "Compliance Officer"
    ],
    "HealthTech": [
        "HealthTech Product Manager",
        "Healthcare Software Engineer",
        "Clinical Data Analyst",
        "Medical Informatics Specialist",
        "Healthcare UX Designer"
    ],
    "InsurTech": [
        "InsurTech Product Manager",
        "Insurance Data Analyst",
        "Insurance Software Engineer",
        "Underwriting Analyst",
        "Claims Automation Specialist"
    ],
    "PropTech": [
        "PropTech Product Manager",
        "Real Estate Software Engineer",
        "Property Data Analyst",
        "GIS Analyst",
        "Real Estate UX Designer"
    ],
    "AgriTech": [
        "AgriTech Product Manager",
        "Agricultural Data Analyst",
        "Precision Agriculture Engineer",
        "Farm Automation Specialist",
        "Agronomist"
    ],
    "CleanTech": [
        "CleanTech Product Manager",
        "Renewable Energy Engineer",
        "Carbon Analyst",
        "Sustainability Consultant",
        "Energy Data Analyst"
    ],
    "Robotics": [
        "Robotics Engineer",
        "Automation Engineer",
        "Control Systems Engineer",
        "ROS Developer",
        "Mechatronics Engineer"
    ],
    "IoT (Internet of Things)": [
        "IoT Engineer",
        "Embedded Systems Engineer",
        "Firmware Engineer",
        "IoT Solutions Architect",
        "Sensor Integration Engineer"
    ],
    "Blockchain": [
        "Blockchain Developer",
        "Smart Contract Engineer",
        "Web3 Developer",
        "Cryptography Engineer",
        "Tokenomics Analyst"
    ],
    "Digital Marketing": [
        "Digital Marketing Manager",
        "SEO Specialist",
        "PPC Specialist",
        "Content Strategist",
        "Email Marketing Specialist"
    ],
    "BPO & KPO": [
        "Customer Support Executive",
        "Process Associate",
        "Operations Analyst",
        "Quality Analyst",
        "Team Leader"
    ],
    "Staffing & Recruitment": [
        "Recruiter",
        "Talent Acquisition Specialist",
        "Sourcing Specialist",
        "Recruitment Manager",
        "HR Consultant"
    ],
    "Procurement": [
        "Procurement Specialist",
        "Category Buyer",
        "Vendor Manager",
        "Strategic Sourcing Manager",
        "Contract Manager"
    ],
    "Import & Export": [
        "Import Export Manager",
        "Customs Compliance Specialist",
        "Trade Analyst",
        "Documentation Executive",
        "International Logistics Coordinator"
    ],
    "Luxury Goods": [
        "Luxury Brand Manager",
        "Visual Merchandiser",
        "Retail Sales Consultant",
        "Product Specialist",
        "Store Manager"
    ],
    "Jewelry": [
        "Jewelry Designer",
        "Gemologist",
        "Production Manager",
        "Sales Consultant",
        "Quality Inspector"
    ],
    "Furniture & Home Decor": [
        "Furniture Designer",
        "Interior Designer",
        "Product Development Manager",
        "Visual Merchandiser",
        "Sales Consultant"
    ],
    "Printing & Packaging": [
        "Packaging Engineer",
        "Print Production Manager",
        "Prepress Specialist",
        "Graphic Designer",
        "Quality Control Inspector"
    ],
    "Music Industry": [
        "Music Producer",
        "Sound Engineer",
        "Artist Manager",
        "Music Marketing Manager",
        "A&R Manager"
    ],
    "Film Production": [
        "Film Producer",
        "Director",
        "Screenwriter",
        "Cinematographer",
        "Production Coordinator"
    ],
    "Social Media": [
        "Social Media Manager",
        "Content Creator",
        "Community Manager",
        "Influencer Marketing Specialist",
        "Social Media Analyst"
    ],
    "Data Analytics": [
        "Data Analyst",
        "Business Intelligence Analyst",
        "Analytics Engineer",
        "Data Visualization Specialist",
        "Reporting Analyst"
    ],
    "Venture Capital & Private Equity": [
        "Investment Associate",
        "Due Diligence Analyst",
        "Portfolio Manager",
        "Deal Sourcing Analyst",
        "Financial Modeling Analyst"
    ],
    "Accounting & Auditing": [
        "Accountant",
        "Auditor",
        "Tax Consultant",
        "Forensic Accountant",
        "Internal Audit Manager"
    ],
    "Corporate Training": [
        "Corporate Trainer",
        "Learning and Development Specialist",
        "Training Manager",
        "Instructional Designer",
        "Facilitator"
    ],
    "Security Services": [
        "Security Officer",
        "Security Supervisor",
        "Risk Consultant",
        "Surveillance Operator",
        "Security Manager"
    ],
    "Facilities Management": [
        "Facilities Manager",
        "Maintenance Supervisor",
        "Building Operations Manager",
        "Asset Manager",
        "Space Planner"
    ],
    "Pet Care": [
        "Veterinary Assistant",
        "Pet Groomer",
        "Pet Trainer",
        "Veterinary Technician",
        "Pet Care Manager"
    ],
    "Beauty & Cosmetics": [
        "Cosmetologist",
        "Beauty Consultant",
        "Makeup Artist",
        "Skincare Specialist",
        "Cosmetic Product Manager"
    ],
    "Wellness & Mental Health": [
        "Mental Health Counselor",
        "Psychologist",
        "Wellness Coach",
        "Therapist",
        "Clinical Program Manager"
    ],
    "Translation & Localization": [
        "Translator",
        "Interpreter",
        "Localization Specialist",
        "Localization Project Manager",
        "Language Quality Analyst"
    ],
    "Open Source Software": [
        "Open Source Developer",
        "Community Manager",
        "Maintainer",
        "Developer Advocate",
        "Technical Writer"
    ],
    "Mobile Applications": [
        "Mobile App Developer",
        "Android Developer",
        "iOS Developer",
        "React Native Developer",
        "Flutter Developer"
    ],
    "SaaS (Software as a Service)": [
        "SaaS Product Manager",
        "Customer Success Manager",
        "Software Engineer",
        "DevOps Engineer",
        "Solutions Architect"
    ],
    "Hardware": [
        "Hardware Engineer",
        "Embedded Systems Engineer",
        "Firmware Engineer",
        "PCB Design Engineer",
        "Hardware Test Engineer"
    ],
    "Networking": [
        "Network Engineer",
        "Network Administrator",
        "Network Architect",
        "Systems Engineer",
        "NOC Engineer"
    ],
    "Quantum Computing": [
        "Quantum Researcher",
        "Quantum Software Engineer",
        "Quantum Algorithm Developer",
        "Quantum Physicist",
        "Research Scientist"
    ],
    "Space Technology": [
        "Space Systems Engineer",
        "Aerospace Engineer",
        "Satellite Engineer",
        "Mission Operations Engineer",
        "Propulsion Engineer"
    ],
    "Renewable Energy": [
        "Renewable Energy Engineer",
        "Solar Engineer",
        "Wind Energy Technician",
        "Energy Analyst",
        "Project Manager"
    ],
    "Drones": [
        "Drone Operator",
        "UAV Engineer",
        "Flight Test Engineer",
        "Drone Software Developer",
        "Payload Integration Engineer"
    ],
    "3D Printing": [
        "Additive Manufacturing Engineer",
        "3D Printing Technician",
        "CAD Designer",
        "Prototype Engineer",
        "Materials Engineer"
    ]
}



USERS_DATA = [
    {
        "id": "504d4b5f-52a0-43a7-8899-c794009ba421",
        "first_name": "SUNIL",
        "last_name": "KUMAR SHARMA",
        "email": "sharma.vandana830@gmail.com",
        "phone": "9855518686",
        "hashed_password": "$2b$12$Y8GZi.3tuulJmv5o7vccRubnYoqVRJYeKCXQIWbRCRZEe3ajOM4U.",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": null,
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": "GARMENTS",
        "job_type": null,
        "salary_range": null,
        "experience": "5+ Years",
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-02 10:56:49.9602",
        "updated_at": "2026-06-02 10:56:49.960202",
        "father_or_mother_name": "SH. ROSHAN LAL SHARMA",
        "gender": "Male",
        "address": "HOUSE NO. 88-B STREET NO. 02, LANE NO. 02 RAMAN ENCLAVE NEAR RISHI NAGAR LUDHIANA-141001",
        "highest_qualification": "Graduation",
        "stream_specialization": "DISPATCHING OF GOODS IN GARMENT SECTOR",
        "college_institute_name": "GOVT. COLLEGE",
        "preferred_job_sector": "GARMENTS",
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "250b8c44-8b8b-40f6-9c4d-28eb8bb5707e",
        "first_name": "Dharminder",
        "last_name": "singh",
        "email": "dharminders737@gmail.com",
        "phone": "9872809263",
        "hashed_password": "$2b$12$fG6t8h30Ht.Lc9DT/8qrs.BlvQK4kSsv5GniOr0Yg0ojmm0X2oLXS",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": null,
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": "Billing Executive",
        "job_type": null,
        "salary_range": null,
        "experience": "3\u20135 Years",
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-02 10:56:53.423518",
        "updated_at": "2026-06-02 10:56:53.42352",
        "father_or_mother_name": "Naib singh",
        "gender": "Male",
        "address": "Village-Rania,p.o-sangowal,ludhiana",
        "highest_qualification": "Graduation",
        "stream_specialization": "B.A",
        "college_institute_name": "Karamsar college Rara sahib",
        "preferred_job_sector": "Billing Executive",
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "ba876ee6-d642-448e-a05c-f22c31f5aeec",
        "first_name": "Jashpreet",
        "last_name": "singh",
        "email": "4kjashan@gmail.com",
        "phone": "9888887837",
        "hashed_password": "$2b$12$zse413X7bvbDGZBTO0paxeJA.AbTNAnbnYohIe9quYPi4IfzCVi/u",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": null,
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": "Management",
        "job_type": null,
        "salary_range": null,
        "experience": "3\u20135 Years",
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-02 10:57:02.341163",
        "updated_at": "2026-06-02 10:57:02.341166",
        "father_or_mother_name": "Gurdeep",
        "gender": "Male",
        "address": "Model town",
        "highest_qualification": "Post Graduation",
        "stream_specialization": "MBA",
        "college_institute_name": "CU and PCTE",
        "preferred_job_sector": "Management",
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "a0c16b1a-e982-4d41-b948-ad0acfe1c6d9",
        "first_name": "Kuldeep",
        "last_name": "Kumar",
        "email": "kuldeepkumar3729@gmail.com",
        "phone": "7508302822",
        "hashed_password": "$2b$12$lovX2kG9LSrL0Es.76Asw.FOTllcGzt.V98vKlRkAr9ppBNn25svK",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": null,
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": "Metallurgy Lab",
        "job_type": null,
        "salary_range": null,
        "experience": "5+ Years",
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-02 10:57:05.476311",
        "updated_at": "2026-06-02 10:57:05.476313",
        "father_or_mother_name": "Ram kesh",
        "gender": "Male",
        "address": "St.4 jai gurudev nagar Mundian Kalan Ludhiana, Punjab",
        "highest_qualification": "10th, Diploma, Graduation",
        "stream_specialization": "Mechanical Engineering",
        "college_institute_name": "Ludhiana Group of College",
        "preferred_job_sector": "Metallurgy Lab",
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "8a6058a0-0595-4eff-8d17-94a4bc26449a",
        "first_name": "PUNEET",
        "last_name": "HARRY",
        "email": "puneetharry99@gmail.com",
        "phone": "7696135224",
        "hashed_password": "$2b$12$uRgeWugbMylo.caosmHUVOK/hdAPtCGQ2zuOsDV5JYdTmIy3JBYDq",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": null,
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": "Public sector, interacting others",
        "job_type": null,
        "salary_range": null,
        "experience": "Fresher",
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-02 10:57:11.439478",
        "updated_at": "2026-06-02 10:57:11.439481",
        "father_or_mother_name": "MR. JASWINDER PAL",
        "gender": "Male",
        "address": "Hno. 541, Keharwali,  DASUYA HOSHIARPUR",
        "highest_qualification": "Diploma",
        "stream_specialization": "NON MEDICAL, [ PCM ]",
        "college_institute_name": "PT. JR POLYTECHNIC GOVERNMENT COLLEG E, HOSHIARPUR",
        "preferred_job_sector": "Public sector, interacting others",
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "27a962d5-1a11-4602-a813-d48937e29e2e",
        "first_name": "Deepak Singh",
        "last_name": "Negi",
        "email": "deepaksnegi2008@gmail.com",
        "phone": "0842766091",
        "hashed_password": "$2b$12$UzDLJ.di47Y5ZsJaWrLd4.1MkKerjTR/Sm8ZW/RPUNQv5uUnX/BrG",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": "SYC6RRRE6IXFJYGXXWADBNQ3H3PV335L",
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": null,
        "job_type": "in_office",
        "salary_range": "3 - 6 LPA",
        "experience": null,
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": [
            "Ludhiana, Punjab"
        ],
        "profile_embedding": null,
        "created_at": "2026-06-02 11:58:35.283106",
        "updated_at": "2026-06-02 12:00:24.367353",
        "father_or_mother_name": null,
        "gender": null,
        "address": null,
        "highest_qualification": null,
        "stream_specialization": null,
        "college_institute_name": null,
        "preferred_job_sector": null,
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "492c7c2c-5697-4fc4-9946-fb5776521ca2",
        "first_name": "Aman",
        "last_name": "Mishra",
        "email": "amanmishra253698@gmail.com",
        "phone": "9041241722",
        "hashed_password": "$2b$12$kYaTBB3GPp.THmVinMIUOOpxoXIoWS6MRGWbZAHBLicTEtwcwJupq",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": null,
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": "Supply chain",
        "job_type": null,
        "salary_range": null,
        "experience": "0\u20131 Year",
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-02 10:46:57.063437",
        "updated_at": "2026-06-02 10:46:57.063439",
        "father_or_mother_name": "Arbind Kumar Mishra",
        "gender": "Male",
        "address": "141014, post, Deep Colony, Dhandari Khurd, Dhandari Kalan, Ludhiana, Punjab 141003, India",
        "highest_qualification": "12th, Other",
        "stream_specialization": "Humanities /2nd year BA",
        "college_institute_name": "SCD GOVT COLLEGE",
        "preferred_job_sector": "Supply chain",
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "1f354c80-80fb-40a3-8884-77996e1c415c",
        "first_name": "Rahul",
        "last_name": "Choudhary",
        "email": "rhul29435@gmail.com",
        "phone": "8837753473",
        "hashed_password": "$2b$12$4tKKAKexqkunVesNgvMfTe1YjZqe9fRgmf.XcCsL77ftyWxVkTY5S",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": null,
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": "Digital marketing",
        "job_type": null,
        "salary_range": null,
        "experience": "1\u20133 Years",
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-02 10:56:56.400839",
        "updated_at": "2026-06-02 10:56:56.400842",
        "father_or_mother_name": "Rakesh Kumar",
        "gender": "Male",
        "address": "Old sundar nagar mundian kalan ludhiana",
        "highest_qualification": "Post Graduation",
        "stream_specialization": "MBA digital marketing",
        "college_institute_name": "Chandigarh University",
        "preferred_job_sector": "Digital marketing",
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "115662ad-e519-456e-8088-85b99d6a7b6a",
        "first_name": "Naveen",
        "last_name": "kumar",
        "email": "2384naveen@gmail.com",
        "phone": "9815953675",
        "hashed_password": "$2b$12$F6wrztdRehkfV6U3mxDtY.9dhCV0wfqtMAb8KS7Fn2x7a.c2vZW6a",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": null,
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": "Industries",
        "job_type": null,
        "salary_range": null,
        "experience": "3\u20135 Years",
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-02 10:56:59.335002",
        "updated_at": "2026-06-02 10:56:59.335004",
        "father_or_mother_name": "Sukhdev",
        "gender": "Male",
        "address": "Hno 2561 st no 7/11 Prem vihar tiba road Ludhiana",
        "highest_qualification": "ITI",
        "stream_specialization": "Electrician",
        "college_institute_name": "Gurukul iti",
        "preferred_job_sector": "Industries",
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "bfec53ed-3f72-431d-8d39-08ee15cbe6a3",
        "first_name": "Harvinder",
        "last_name": "Singh",
        "email": "harry1xgdu@gmail.com",
        "phone": "9464445446",
        "hashed_password": "$2b$12$Sn4Ox4cASXNm2.Rq85CJa.w0qHqGktG8Tq.svSMqBZpcKyPHTSpMy",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": null,
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": "No",
        "job_type": null,
        "salary_range": null,
        "experience": "Fresher",
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-02 10:57:08.389555",
        "updated_at": "2026-06-02 10:57:08.389557",
        "father_or_mother_name": "Sukhvir Singh",
        "gender": "Male",
        "address": "Village:- Bhungarni , District:- Hoshiarpur",
        "highest_qualification": "10th, 12th, Diploma",
        "stream_specialization": "Electrical engineering",
        "college_institute_name": "Pt.jr Polotecnical college hoshiarpu r",
        "preferred_job_sector": "No",
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "7ec050a9-034c-4ea2-8994-876c844faa3d",
        "first_name": "Gurbaj",
        "last_name": "Singh",
        "email": "gurbajsandhuan@gmail.com",
        "phone": "9592162110",
        "hashed_password": "$2b$12$Cb83FvJpCR1eJXdxBq.AN.wpC5N9qwAPcrA4uy3RY34pPYQGFFa6W",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": null,
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": "Quality",
        "job_type": null,
        "salary_range": null,
        "experience": "Fresher",
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-02 10:57:14.408889",
        "updated_at": "2026-06-02 10:57:14.408894",
        "father_or_mother_name": "Narinder Singh",
        "gender": "Male",
        "address": "vpo Sandhuan -140112",
        "highest_qualification": "10th, 12th, Diploma, ITI",
        "stream_specialization": "Mechanical engineering",
        "college_institute_name": "S.G.H.S.G.P.C.RANWAN",
        "preferred_job_sector": "Quality",
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "bb6756db-5e87-4fab-beae-24e6af48e26d",
        "first_name": "Ramanjeet",
        "last_name": "Singh",
        "email": "ramanjeetsingh440@gmail.com",
        "phone": "8146431035",
        "hashed_password": "$2b$12$A0SFbHD0NlXCXhqZJo/o9um8zh33xctxNtA7zo.rBZ0ZDTTpCDqWq",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": null,
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": "Cnc machine operator",
        "job_type": null,
        "salary_range": null,
        "experience": "0\u20131 Year",
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-02 10:57:17.679872",
        "updated_at": "2026-06-02 10:57:17.679875",
        "father_or_mother_name": "Parmjeet kaur",
        "gender": "Male",
        "address": "Lohari kalan district fatehgarh sahib",
        "highest_qualification": "Diploma",
        "stream_specialization": "Mechanical Engineering",
        "college_institute_name": "Shri guru hargobind sahib polytechni c college Ranwan",
        "preferred_job_sector": "Cnc machine operator",
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "94de26a3-3115-433c-ad54-c80c09d4e897",
        "first_name": "Vanshika",
        "last_name": "Malhotra",
        "email": "vanshika.malhotra80@gmail.com",
        "phone": "9815270499",
        "hashed_password": "$2b$12$z9kOfyOCqkpOEP.MV737/uAoO2kiCurUx4o83NaOg9ua1er9ZU.Ke",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": "4VYRLYICGWVG2SXCKNUXOLFG5UWN74KA",
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": null,
        "job_type": "in_office",
        "salary_range": "3 - 6 LPA",
        "experience": null,
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": [
            "Mohali, Punjab"
        ],
        "profile_embedding": null,
        "created_at": "2026-06-02 12:14:40.220291",
        "updated_at": "2026-06-02 12:15:55.334136",
        "father_or_mother_name": null,
        "gender": null,
        "address": null,
        "highest_qualification": null,
        "stream_specialization": null,
        "college_institute_name": null,
        "preferred_job_sector": null,
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "b8257d42-26cc-4345-b225-1081b7706259",
        "first_name": "AKASH",
        "last_name": "SINGH",
        "email": "singhakash1995a@gmail.com",
        "phone": "6394617864",
        "hashed_password": "$2b$12$6S9J3c2he0ugn8gxnBYBi.v0pBBJI5hIkN.M3wfZ0U4Guemib3wl.",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": "CSLDGDXVZXRZ6S6EAOZYR4WM725MFABW",
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": null,
        "job_type": "in_office",
        "salary_range": "3 - 6 LPA",
        "experience": null,
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": [
            "Lucknow, Uttar Pradesh"
        ],
        "profile_embedding": null,
        "created_at": "2026-06-02 11:47:19.805408",
        "updated_at": "2026-06-02 11:48:12.809601",
        "father_or_mother_name": null,
        "gender": null,
        "address": null,
        "highest_qualification": null,
        "stream_specialization": null,
        "college_institute_name": null,
        "preferred_job_sector": null,
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "6adffb4d-7db5-4ed5-88c1-2da3b405900b",
        "first_name": "Samparn",
        "last_name": "Sahani",
        "email": "samparnsahani@gmail.com",
        "phone": "9876114287",
        "hashed_password": "$2b$12$/tefBOF2TLVKgfkT2f48ae3gsXOX5D8uCx6itOpGT2/1m2/3nFBF6",
        "profile_pic_url": "/api/uploads/profile_6adffb4d-7db5-4ed5-88c1-2da3b4059 00b_5657769cc35d4d8698be9d25fbf17a8d.png",
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": false,
        "totp_secret": "ECZ5AXXH6ZOYYHUKGAA7QF5HPUVMEWY2",
        "totp_enabled": false,
        "is_first_login": true,
        "role": "provider",
        "industry": "Manufacturing",
        "job_role": null,
        "job_type": null,
        "salary_range": null,
        "experience": null,
        "auto_apply_enabled": false,
        "company_type": "company",
        "company_name": "Mitter Fasteners",
        "company_location": "Ludhiana, Punjab",
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-01 04:49:29.030681",
        "updated_at": "2026-06-02 05:57:26.600149",
        "father_or_mother_name": null,
        "gender": null,
        "address": null,
        "highest_qualification": null,
        "stream_specialization": null,
        "college_institute_name": null,
        "preferred_job_sector": null,
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": "3184/2, Street No: 14, New Janta Nagar, Gill Road, Ludhiana-141003. (INDIA).",
        "is_super_admin": false
    },
    {
        "id": "eaae3590-f758-41e9-8b58-98e8d6b44db7",
        "first_name": "VIKRAMJEET",
        "last_name": "SINGH",
        "email": "vikramjeetsingh007@gmail.com",
        "phone": "9855185000",
        "hashed_password": "$2b$12$WlgjFp0LPQa4pxlKz7H/EOlB08DifDDhEbw7Q1vdnop9LmNs0gBwa",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": "H45NA4QCZVGOV65N7F2VSW73VJ4KZXZR",
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": null,
        "job_type": "in_office",
        "salary_range": "0 - 3 LPA",
        "experience": null,
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": [
            "Ludhiana, Punjab"
        ],
        "profile_embedding": null,
        "created_at": "2026-06-02 06:14:31.566117",
        "updated_at": "2026-06-02 06:16:20.416185",
        "father_or_mother_name": null,
        "gender": null,
        "address": null,
        "highest_qualification": null,
        "stream_specialization": null,
        "college_institute_name": null,
        "preferred_job_sector": null,
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "25c85fd1-edf9-43f9-9887-60698b38941d",
        "first_name": "Super",
        "last_name": "Admin",
        "email": "superadmin@hirely.com",
        "phone": "9999999999",
        "hashed_password": "$2b$12$jSUJdXVW4Tdii05jGnMcZ.s6t1B1RaFlH2we8HKG9tpAP0geh26Ki",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": false,
        "totp_secret": null,
        "totp_enabled": false,
        "is_first_login": true,
        "role": null,
        "industry": null,
        "job_role": null,
        "job_type": null,
        "salary_range": null,
        "experience": null,
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-02 07:14:30.086305",
        "updated_at": "2026-06-02 07:14:30.086307",
        "father_or_mother_name": null,
        "gender": null,
        "address": null,
        "highest_qualification": null,
        "stream_specialization": null,
        "college_institute_name": null,
        "preferred_job_sector": null,
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": true
    },
    {
        "id": "f744c5a1-f3fa-4591-bde2-aa2a681986ca",
        "first_name": "Suresh",
        "last_name": "Kumar",
        "email": "pradeepkumarcse126@gmail.com",
        "phone": "9876543298",
        "hashed_password": "$2b$12$6xoEQ9HM4w9gpUB1QRimL.pet/ON7eAxt98qTRpJpZXqxJIKq/BdW",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": false,
        "is_assessment_done": false,
        "totp_secret": null,
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": "IT / SaaS",
        "job_role": "Content Writer",
        "job_type": null,
        "salary_range": null,
        "experience": "2 - 3 Year",
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-02 07:34:43.523024",
        "updated_at": "2026-06-02 07:34:43.523027",
        "father_or_mother_name": null,
        "gender": "Male",
        "address": "Ludhiana, Punjab",
        "highest_qualification": null,
        "stream_specialization": null,
        "college_institute_name": null,
        "preferred_job_sector": null,
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "3b709be7-cce9-4464-b4b6-5d63ce6f816b",
        "first_name": "Dhiraj",
        "last_name": "Sharma",
        "email": "learnpath79@gmail.com",
        "phone": "9876678998",
        "hashed_password": "$2b$12$tBVJVFKeVqgAlbEFkUmcBe9hkEYNZW9N5fsfA7j27PLJ35DK5dmvi",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": false,
        "is_assessment_done": false,
        "totp_secret": null,
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": "IT / SaaS",
        "job_role": "Flutter Developer",
        "job_type": null,
        "salary_range": null,
        "experience": "1 - 2 Year",
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": null,
        "profile_embedding": null,
        "created_at": "2026-06-02 07:46:41.75579",
        "updated_at": "2026-06-02 07:46:41.755793",
        "father_or_mother_name": null,
        "gender": "Male",
        "address": "Ludhiana, Punjab",
        "highest_qualification": null,
        "stream_specialization": null,
        "college_institute_name": null,
        "preferred_job_sector": null,
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    },
    {
        "id": "6693ac2c-c3b5-4fbc-8066-15dd28bf1d8b",
        "first_name": "SHIVAM",
        "last_name": "VERMA",
        "email": "shivam22182@gmail.com",
        "phone": "8739029266",
        "hashed_password": "$2b$12$z5mgIT91LaUDKwwurGlK7eeJDHxpGxUv7s6Pup9yp.Yk3Ff5lt2ja",
        "profile_pic_url": null,
        "is_verified": true,
        "onboarding_complete": true,
        "is_assessment_done": true,
        "totp_secret": "VNX7QQDCX6VFOF6636M3J74DPIHVQHDG",
        "totp_enabled": false,
        "is_first_login": true,
        "role": "seeker",
        "industry": null,
        "job_role": null,
        "job_type": "in_office",
        "salary_range": "3 - 6 LPA",
        "experience": null,
        "auto_apply_enabled": false,
        "company_type": null,
        "company_name": null,
        "company_location": null,
        "company_size": null,
        "preferred_locations": [
            "Mohali, Punjab"
        ],
        "profile_embedding": null,
        "created_at": "2026-06-02 12:23:05.141613",
        "updated_at": "2026-06-02 12:25:04.635775",
        "father_or_mother_name": null,
        "gender": null,
        "address": null,
        "highest_qualification": null,
        "stream_specialization": null,
        "college_institute_name": null,
        "preferred_job_sector": null,
        "job_roles_offering": null,
        "specific_requirements": null,
        "company_address": null,
        "is_super_admin": false
    }
]



PORTFOLIOS_DATA = [
    {
        "id": "184c499f-b818-4346-a819-07a18825e2dc",
        "user_id": "b8257d42-26cc-4345-b225-1081b7706259",
        "headline": "Job Seeker",
        "bio": "As a Beginner,I want to build my career in a creative environment where I can learn and expand my knowledge which can help to contribute to the success of the organization",
        "date_of_birth": "1995-07-15",
        "gender": "Male",
        "city": "Lucknow",
        "state": "Uttar Pradesh",
        "linkedin_url": null,
        "github_url": null,
        "website_url": null,
        "total_experience_years": 1,
        "current_company": null,
        "current_role": null,
        "skills": [
            {
                "name": "Positive Attitude",
                "level": "Intermediate"
            },
            {
                "name": "Punctuality, Hardworking, Honesty & Sincerely",
                "level": "Intermediate"
            },
            {
                "name": "Ability to work in team as well as individual ",
                "level": "Intermediate"
            },
            {
                "name": " Problem Solving",
                "level": "Intermediate"
            }
        ],
        "work_experiences": [
            {
                "company": "Yamaha Motor PVT. LTD",
                "role": "Sales",
                "start_date": "2024-01",
                "end_date": "2025-01",
                "description": "",
                "is_current": false
            },
            {
                "company": "LG Electronics Pvt. LTD",
                "role": "Sales",
                "start_date": "2025-01",
                "end_date": "2026-01",
                "description": "",
                "is_current": false
            }
        ],
        "education": [
            {
                "institution": "NCTV",
                "degree": "ITI",
                "field": "Fitter",
                "start_year": "2015",
                "end_year": "2017"
            }
        ],
        "certifications": [],
        "languages": [
            {
                "language": "Hindi",
                "proficiency": "Conversational"
            },
            {
                "language": "English",
                "proficiency": "Conversational"
            }
        ],
        "projects": [],
        "intro_video_path": null,
        "intro_video_filename": null,
        "intro_audio_path": null,
        "intro_audio_filename": null,
        "created_at": "2026-06-02 11:48:12.823915",
        "updated_at": "2026-06-02 11:53:50.39572"
    },
    {
        "id": "9f4aec3e-0a92-47c6-8ec3-b6dc1448269c",
        "user_id": "eaae3590-f758-41e9-8b58-98e8d6b44db7",
        "headline": null,
        "bio": "Master of Computer Applications with 10 years plus experience in ,backend operations,MIS EDP, Data Entry, File Management, Data Handling, ERP (Sale support, Purchase & Inventory support) & Backend Support area & Data entry in manufacturing Limited Company. Extensive experience with Sale Inventory & Purchase ERP Modules & its process",
        "date_of_birth": null,
        "gender": "Male",
        "city": "Ludhiana",
        "state": "Punjab",
        "linkedin_url": null,
        "github_url": null,
        "website_url": null,
        "total_experience_years": 16,
        "current_company": null,
        "current_role": null,
        "skills": [
            {
                "name": " Data Entry & Data management",
                "level": "Intermediate"
            },
            {
                "name": "Advance Excel ",
                "level": "Intermediate"
            },
            {
                "name": "Office Applications",
                "level": "Intermediate"
            },
            {
                "name": "SQL Programming, Database Management System",
                "level": "Intermediate"
            },
            {
                "name": "Crystal Reports 9",
                "level": "Intermediate"
            },
            {
                "name": "MS Acces",
                "level": "Intermediate"
            },
            {
                "name": "Nuron",
                "level": "Intermediate"
            },
            {
                "name": "Tally erp9",
                "level": "Intermediate"
            }
        ],
        "work_experiences": [
            {
                "company": "M/S Deepak Fasteners Limited Unbrako",
                "role": "Sr MIS cum back office executive",
                "start_date": "2010-08",
                "end_date": "2018-03",
                "description": "File & Documents Management. \nPreparation/Data punching of Sale orders, Invoicing, packing slip IN ERP.\nPreparation/Data Punching of Purchase Orders, Purchase Invoices, Purchase indent.\nResponsible for Good receipts data entry of /MRN (Material Receipt Note) for Import material.\nStock adjustments & Stock Movement according to user requirements in ERP.\nStock Valuation.\nPreparing power point slides related with different business aspects & processes.\n Mail drafting& mail correspondence.\n Responsible for all Data Entry Tasks",
                "is_current": false
            },
            {
                "company": "J F I - Dhardari Kalan, LDH",
                "role": "Back office executive",
                "start_date": "2018-05",
                "end_date": "",
                "description": "Preparation of Sale Order, Invoicing/Billing in ERP.\n\uf0a7 MIS Reports like Bill wise due statement & Agent/Party wise due statement, daily, weekly, \nmonthly, intercompany sale, yearly sale, domestic & export Sale Report agent/party wise \n\uf0a7 Pending Back orders & Pending Purchase order reports.\n\uf0a7 Preparation of MIS reports for the user and management.\n\uf0a7 Maintaining Stock & Creating Stock adjustment & stock movement in ERP.\n\uf0a7 All File & Document Management.\n\uf0a7 Creating Sales & Purchase registers for end users.\n\uf0a7 Creation of New price list timely & maintain it in the ERP. \n\uf0a7 Ensuring all inquiries are dealt with accurately, timely & professionally.\n\uf0a7 Tracing sale order to ensure that they are scheduled and sent out on time.",
                "is_current": true
            }
        ],
        "education": [
            {
                "institution": "A.V.M, Punjab School Education Board ",
                "degree": "10",
                "field": "matriculation",
                "start_year": "2000",
                "end_year": "2001"
            },
            {
                "institution": "S.C.D Govt. Collage, P.S.E.B ",
                "degree": "12",
                "field": "Commerce",
                "start_year": "2002",
                "end_year": "2003"
            },
            {
                "institution": "Arya Collage, Punjab University ",
                "degree": "BCA",
                "field": "Computer",
                "start_year": "2003",
                "end_year": "2006"
            },
            {
                "institution": "Quest Infosis, P.T.U",
                "degree": "MCA",
                "field": "Computer",
                "start_year": "2007",
                "end_year": "2010"
            }
        ],
        "certifications": [],
        "languages": [
            {
                "language": "Hindi",
                "proficiency": "Conversational"
            },
            {
                "language": "English",
                "proficiency": "Conversational"
            },
            {
                "language": "Punjabi",
                "proficiency": "Conversational"
            }
        ],
        "projects": [],
        "intro_video_path": null,
        "intro_video_filename": null,
        "intro_audio_path": null,
        "intro_audio_filename": null,
        "created_at": "2026-06-02 06:16:20.423001",
        "updated_at": "2026-06-02 06:48:35.39626"
    },
    {
        "id": "21fd80b7-8df7-46a1-bbd7-e9f20c7aa0c0",
        "user_id": "492c7c2c-5697-4fc4-9946-fb5776521ca2",
        "headline": null,
        "bio": null,
        "date_of_birth": null,
        "gender": null,
        "city": null,
        "state": null,
        "linkedin_url": null,
        "github_url": null,
        "website_url": null,
        "total_experience_years": null,
        "current_company": null,
        "current_role": null,
        "skills": null,
        "work_experiences": null,
        "education": null,
        "certifications": null,
        "languages": null,
        "projects": null,
        "intro_video_path": null,
        "intro_video_filename": null,
        "intro_audio_path": null,
        "intro_audio_filename": null,
        "created_at": "2026-06-02 10:48:17.325928",
        "updated_at": "2026-06-02 10:48:17.325931"
    },
    {
        "id": "877f74e3-77c9-423c-85f7-1383a5417fd3",
        "user_id": "6693ac2c-c3b5-4fbc-8066-15dd28bf1d8b",
        "headline": "AI/ML Engineer",
        "bio": null,
        "date_of_birth": "1999-07-13",
        "gender": "Male",
        "city": "Mohali",
        "state": "Punjab",
        "linkedin_url": null,
        "github_url": null,
        "website_url": null,
        "total_experience_years": 4,
        "current_company": null,
        "current_role": null,
        "skills": [
            {
                "name": "Python3",
                "level": "Intermediate"
            },
            {
                "name": "OpenCV",
                "level": "Intermediate"
            },
            {
                "name": "TensorFlow",
                "level": "Intermediate"
            },
            {
                "name": "PyTorch",
                "level": "Intermediate"
            },
            {
                "name": "Flask",
                "level": "Intermediate"
            },
            {
                "name": "BeautifulSoup",
                "level": "Intermediate"
            },
            {
                "name": "LangChain",
                "level": "Intermediate"
            },
            {
                "name": "GitHub",
                "level": "Intermediate"
            },
            {
                "name": "Git",
                "level": "Intermediate"
            }
        ],
        "work_experiences": "[{\"company\": \"Anviam Solutions Pvt Ltd\", \"role\": \"AI/ML Engineer\", \"start_date\": \"2025-04\", \"end_date\": \"\", \"description\": \"\u2022\tDeveloped \u201cTalking Bird,\u201d a multi-agent Conversational AI system featuring an \u201cAsk_AI\u201d module powered by SQL Agent and RAG Agent, integrated with Weaviate Cloud. Utilized OpenAI LLMs and embedding models to generate contextual responses from both structured and unstructured data.\\n\u2022\tImplemented scalable, vector-based semantic search with Weaviate, enhancing retrieval accuracy across hybrid data sources for natural language queries.\\n\u2022\tBuilt a Previsit Assessment module using ElevenLabs API and a conversational agent. Applied prompt engineering to simulate\\nhuman-like dialogue, improving user understanding, experience, and downstream task efficiency.\\n\", \"is_current\": true}, {\"company\": \"The Kraftors Web Solution Pvt Ltd\", \"role\": \"Software Engineer - AI\", \"start_date\": \"2025-01\", \"end_date\": \"2025-03\", \"description\": \"\u2022\tFine-tuned the Google T5-Large model for question answering (QA) and text summarization, optimizing performance for\\nOxane Partners to enhance content extraction and response accuracy.\\n\u2022\tDeveloped an AI-powered mass calling system using Realtime OpenAI GPT-4o Mini API and Twillio for Bluesales, enabling:\\n100 concurrent AI-driven calls with a single click, improving operational efficiency.\\nConversational AI capabilities, ensuring human-like interactions for enhanced user experience.\\nCost optimization, reducing call expenses to $0.10 per minute, significantly lowering operational costs\\nReplacement for VAPI AI and other TTS/STT solutions, offering a scalable and cost-effective alternative\\n\", \"is_current\": false}, {\"company\": \"The Kraftors Web Solution Pvt Ltd\", \"role\": \"Associate Software Engineer\", \"start_date\": \"2024-04\", \"end_date\": \"2024-12\", \"description\": \"\u2022\tDesigned and developed a multimodal AI aggregation platform, integrating top LLMs from OpenAI, Google, Anthropic, Stability AI, Haiper, and Cohere, providing users with a seamless, unified AI experience.\\n\u2022\tEnhanced platform functionalities by implementing:\\nImage Generation using advanced open-source Stability AI models for high-quality visual content creation.\\nAI-Powered Resume Generation leveraging LLaMA 13B, enabling automated and customized resume building.\\nDomain-Specific Chatbots for health and finance, utilizing Mistral 7B and LLaMA 13B to deliver context-aware interactions\\n\", \"is_current\": false}]",
        "education": "[{\"institution\": \"Rameshwaram Institute of Technology and Management (AKTU)\t\", \"degree\": \"B.Tech\", \"field\": \"Computer Science\", \"start_year\": \"2020\", \"end_year\": \"2023\"}, {\"institution\": \"Feroze Gandhi Polytechnic , Raebareli (BTEUP)\", \"degree\": \"Diploma\", \"field\": \"Computer Science\", \"start_year\": \"2017\", \"end_year\": \"2020\"}]",
        "certifications": [],
        "languages": [
            {
                "language": "Hindi",
                "proficiency": "Conversational"
            },
            {
                "language": "English",
                "proficiency": "Conversational"
            }
        ],
        "projects": [],
        "intro_video_path": null,
        "intro_video_filename": null,
        "intro_audio_path": null,
        "intro_audio_filename": null,
        "created_at": "2026-06-02 12:25:04.642004",
        "updated_at": "2026-06-02 12:30:57.336329"
    },
    {
        "id": "3e50020f-6abd-4cb3-8199-0734e39e799c",
        "user_id": "27a962d5-1a11-4602-a813-d48937e29e2e",
        "headline": "Finance & Accounts",
        "bio": "\u2022       Highly efficient in prioritising invoices with purchase orders, utilities, bills, expense reports, check requests, etc. in order to process payments accurately and timely \u2022       Gained expertise in ensuring a timely and accurate invoicing of customers, recording of revenue, application of receipts \u2022       Proficient in assisting the senior leadership with audit requests, quarter end close, and other demands as they arise",
        "date_of_birth": "1983-04-10",
        "gender": "Male",
        "city": "Ludhiana",
        "state": "Punjab",
        "linkedin_url": null,
        "github_url": null,
        "website_url": null,
        "total_experience_years": 16,
        "current_company": null,
        "current_role": null,
        "skills": [
            {
                "name": "AP & AR Management ",
                "level": "Intermediate"
            },
            {
                "name": "Cash & Bank Reconciliations ",
                "level": "Intermediate"
            },
            {
                "name": "Channel Accounting",
                "level": "Intermediate"
            },
            {
                "name": "Vendor Payment Lifecycle Management ",
                "level": "Intermediate"
            },
            {
                "name": "MIS Reporting & Documentation",
                "level": "Intermediate"
            },
            {
                "name": "Team Coordination ",
                "level": "Intermediate"
            },
            {
                "name": "Office Administration Supply Chain",
                "level": "Intermediate"
            }
        ],
        "work_experiences": "[{\"company\": \"Saatvik Solar Industries Private Limited \", \"role\": \"Deputy Manager - SCM\", \"start_date\": \"2025-04\", \"end_date\": \"\", \"description\": \"\u2022\tProcess and verify sales orders and invoices with accuracy, ensuring timely billing and minimal discrepancies.\\n\u2022\tCoordinate with finance and sales departments to resolve invoicing issues and streamline billing workflows.\\n\u2022\tMaintain accurate records of invoicing, credit notes, and customer accounts in SAP.\\n\\n\u2022\tManage daily dispatch schedules for local and national shipments, ensuring on-time delivery to customers.\\n\u2022\tCoordinate with warehouse and transport teams to align dispatch priorities with customer delivery timelines.\\n\", \"is_current\": true}, {\"company\": \"Dish Infra Services Private Limited (DISH TV) \", \"role\": \"Lead Accounts \", \"start_date\": \"2018-04\", \"end_date\": \"2025-03\", \"description\": \"\u2022\tMonitor and kept track of payment schedules\\n\u2022\tRecording of collection & sale/purchase transactions in SAP\\n\u2022\tFinalizing & processing the claims for the Distributors / Direct Dealers of the company against the schemes / Service payouts\\n\u2022\tEmployee travel & Imprest Claim booking and payment processing\\n\u2022\tVendor & employee Payments\\n\u2022\tPreparation of Cash & Bank Reconciliation Statements\\n\u2022\tVendor & Customer Account Reconciliation\\n\u2022\tCoordinate with sales and customer service departments to resolve billing disputes and maintain positive client relationships.\\n\u2022\tWarehouse Audit & coordination with warehouse team regarding stock related issues\\n\u2022\tPreparing of various types of MIS as per schedule and reporting to top level management\\n\u2022\tAssist outside auditors at year-end to include preparing schedules, providing explanation of supporting materials and procedures and preparing any other necessary data\\n\u2022\tProcessed human resources paperwork for new employees\\n\u2022\tHandled day to day office admin activities.\\n\", \"is_current\": false}]",
        "education": [
            {
                "institution": "Punjab University, Chandigarh ",
                "degree": "B.Com",
                "field": "commerce",
                "start_year": "2003",
                "end_year": "2006"
            }
        ],
        "certifications": [],
        "languages": [
            {
                "language": "English",
                "proficiency": "Conversational"
            },
            {
                "language": "Hindi",
                "proficiency": "Conversational"
            }
        ],
        "projects": [],
        "intro_video_path": null,
        "intro_video_filename": null,
        "intro_audio_path": null,
        "intro_audio_filename": null,
        "created_at": "2026-06-02 12:00:24.370659",
        "updated_at": "2026-06-02 12:09:09.173995"
    },
    {
        "id": "6e3e9cbc-1c6a-4174-9e1a-018167fe791a",
        "user_id": "94de26a3-3115-433c-ad54-c80c09d4e897",
        "headline": "UI/UX Designer",
        "bio": "UI/UX Designer with 5 years of experience creating seamless, user-focused digital products. Skilled in transforming user research into responsive, accessible, and pixel-perfect designs. Collaborative team player who thrives in Agile environments, committed to delivering intuitive and high-impact user experiences across web and mobile platforms",
        "date_of_birth": null,
        "gender": "Female",
        "city": "Mohali",
        "state": "Punjab",
        "linkedin_url": null,
        "github_url": null,
        "website_url": null,
        "total_experience_years": 6,
        "current_company": null,
        "current_role": null,
        "skills": "[{\"name\": \" \tResponsive UI/UX\", \"level\": \"Intermediate\"}, {\"name\": \" \tDesign Systems\", \"level\": \"Intermediate\"}, {\"name\": \" \tAccessibility & Inclusion\", \"level\": \"Intermediate\"}, {\"name\": \" \tWireframing & Prototyping\", \"level\": \"Intermediate\"}, {\"name\": \" \tUser-Centered Design\", \"level\": \"Intermediate\"}, {\"name\": \" \tFigma & FigJam\", \"level\": \"Intermediate\"}, {\"name\": \" \tPhotoshop\", \"level\": \"Intermediate\"}, {\"name\": \" \tIllustrator\", \"level\": \"Intermediate\"}]",
        "work_experiences": "[{\"company\": \"Cubeinfotech, Mohali\", \"role\": \"UI/UX Designer\", \"start_date\": \"2022-06\", \"end_date\": \"2024-05\", \"description\": \" \tBoosted brand engagement by 30% through compelling UI design and marketing visuals.\\n \tImproved project delivery by 20% by refining design processes and systems.\\n \tCreated high-conversion landing pages and assets for diverse digital campaigns.\\n\", \"is_current\": false}, {\"company\": \"Alkye Services Pty Ltd., Mohali \", \"role\": \"Sr. UI/UX Designer\", \"start_date\": \"2024-05\", \"end_date\": \"\", \"description\": \" \tLead designer for web and dashboard platforms, improving user engagement and task success.\\n \tReduced drop-off rates by 30% through optimized workflows and data-driven design.\\n \tCollaborated with developers and stakeholders to align design solutions with business objectives.\\n\", \"is_current\": true}]",
        "education": [
            {
                "institution": "Apeejay College of Fine Arts, Jalandhar ",
                "degree": "Bachelor of Fine Arts (BFA)",
                "field": "Arts",
                "start_year": "2019",
                "end_year": "2022"
            }
        ],
        "certifications": [],
        "languages": [
            {
                "language": "English",
                "proficiency": "Conversational"
            },
            {
                "language": "Hindi",
                "proficiency": "Conversational"
            }
        ],
        "projects": [],
        "intro_video_path": null,
        "intro_video_filename": null,
        "intro_audio_path": null,
        "intro_audio_filename": null,
        "created_at": "2026-06-02 12:15:55.338803",
        "updated_at": "2026-06-02 12:20:24.605548"
    }
]

async def seed_master_data(session: AsyncSession):
    # Seed Departments and Jobs
    for dept_name, job_names in DEPARTMENTS_DATA.items():
        existing = await session.execute(select(Department).where(Department.name == dept_name))
        dept = existing.scalars().first()
        if not dept:
            dept = Department(name=dept_name)
            session.add(dept)
            await session.flush()
        
        for job_name in job_names:
            existing_job = await session.execute(
                select(DepartmentJob).where(DepartmentJob.name == job_name, DepartmentJob.department_id == dept.id)
            )
            if not existing_job.scalars().first():
                session.add(DepartmentJob(name=job_name, department_id=dept.id))
                
    await session.flush()

    # Seed Industries
    for ind in INDUSTRIES:
        existing = await session.execute(select(MasterIndustry).where(MasterIndustry.name == ind))
        if not existing.scalars().first():
            session.add(MasterIndustry(name=ind))
    await session.flush()
    
    # Seed Languages
    for lang in LANGUAGES:
        existing = await session.execute(select(MasterLanguage).where(MasterLanguage.name == lang))
        if not existing.scalars().first():
            session.add(MasterLanguage(name=lang))
    await session.flush()
            
    # Seed Roles
    seen_roles = set()
    for ind_name, roles in ROLES.items():
        ind = await session.execute(select(MasterIndustry).where(MasterIndustry.name == ind_name))
        ind_obj = ind.scalars().first()
        if ind_obj:
            for role in roles:
                if role in seen_roles:
                    continue
                existing = await session.execute(select(MasterRole).where(MasterRole.name == role))
                if not existing.scalars().first():
                    session.add(MasterRole(name=role, industry_id=ind_obj.id))
                    seen_roles.add(role)
    await session.flush()
            
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
        await session.flush()
                
        # Seed Users
    for u_data in USERS_DATA:
        if 'created_at' in u_data and u_data['created_at']:
            u_data['created_at'] = datetime.fromisoformat(u_data['created_at'])
        if 'updated_at' in u_data and u_data['updated_at']:
            u_data['updated_at'] = datetime.fromisoformat(u_data['updated_at'])
        
        # Don't try to insert role or other enums directly as strings if they need mapping, 
        # but SQLAlchemy usually handles Enum strings gracefully if they match.
        existing_user = await session.execute(select(User).where(User.email == u_data.get('email')))
        if not existing_user.scalars().first():
            user_obj = User(**u_data)
            session.add(user_obj)
            
    
    # Seed Portfolios
    for p_data in PORTFOLIOS_DATA:
        if 'created_at' in p_data and p_data['created_at']:
            p_data['created_at'] = datetime.fromisoformat(p_data['created_at'])
        if 'updated_at' in p_data and p_data['updated_at']:
            p_data['updated_at'] = datetime.fromisoformat(p_data['updated_at'])
                
        existing_port = await session.execute(select(Portfolio).where(Portfolio.id == p_data.get('id')))
        if not existing_port.scalars().first():
            port_obj = Portfolio(**p_data)
            session.add(port_obj)
            
    await session.commit()

if __name__ == "__main__":
    import asyncio
    from database import AsyncSessionLocal
    
    async def run_seed():
        async with AsyncSessionLocal() as session:
            await seed_master_data(session)
            
    asyncio.run(run_seed())
    print("Seeding completed successfully!")
