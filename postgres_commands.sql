<!-- docker exec -it jobseekerbackend-postgres-1  psql -U jobmatch -d jobmatch_db -->
-- docker exec -it combined_backend-postgres-1  psql -U jobmatch -d jobmatch_db
<!-- \dt --> -- to view tables 


<!-- Alter command changes  -->

<!-- ALTER TABLE job_postings ADD COLUMN post_count INTEGER DEFAULT 0; -->

<!-- Added new state and cities in master_state>
INSERT INTO master_states (name, code) VALUES
('Andhra Pradesh', 'AP'),
('Arunachal Pradesh', 'AR'),
('Assam', 'AS'),
('Bihar', 'BR'),
('Chhattisgarh', 'CG'),
('Goa', 'GA'),
('Haryana', 'HR'),
('Himachal Pradesh', 'HP'),
('Jharkhand', 'JH'),
('Kerala', 'KL'),
('Madhya Pradesh', 'MP'),
('Manipur', 'MN'),
('Meghalaya', 'ML'),
('Mizoram', 'MZ'),
('Nagaland', 'NL'),
('Odisha', 'OD'),
('Punjab', 'PB'),
('Rajasthan', 'RJ'),
('Sikkim', 'SK'),
('Tripura', 'TR'),
('Uttar Pradesh', 'UP'),
('Uttarakhand', 'UK');

INSERT INTO master_cities (id, name, state_id) VALUES
(173, 'Chandigarh', 37),
(174, 'Mohali', 37);

jobmatch_db=# ALTER TABLE job_postings DROP COLUMN embedding;
ALTER TABLE
jobmatch_db=# ALTER TABLE job_postings ADD COLUMN embedding vector(3072);
ALTER TABLE

jobmatch_db=# ALTER TABLE users DROP COLUMN profile_embedding;
ALTER TABLE
jobmatch_db=# ALTER TABLE users ADD COLUMN profile_embedding vector(3072);
ALTER TABLE
jobmatch_db=#

jobmatch_db=# ALTER TABLE resumes DROP COLUMN embedding;
ALTER TABLE
jobmatch_db=# ALTER TABEL resumes ADD COLUMN embedding vector(3072);
ERROR:  syntax error at or near "TABEL"
LINE 1: ALTER TABEL resumes ADD COLUMN embedding vector(3072);
              ^
jobmatch_db=# ALTER TABLE resumes ADD COLUMN embedding vector(3072);
ALTER TABLE


http://192.168.100.15:8000/api/assessment/check-phone/7896543211
INSERT INTO master_cities (name, state_id) VALUES
('Patiala', 37),
('Bathinda', 37),
('Pathankot', 37),
('Hoshiarpur', 37),
('Batala', 37),
('Moga', 37),
('Abohar', 37),
('Malerkotla', 37),
('Khanna', 37),
('Phagwara', 37),
('Muktsar', 37),
('Barnala', 37),
('Rajpura', 37),
('Firozpur', 37),
('Kapurthala', 37),
('Zirakpur', 37),
('Faridkot', 37),
('Sunam', 37),
('Sangrur', 37),
('Fazilka', 37),
('Gurdaspur', 37),
('Tarn Taran', 37),
('Nawanshahr', 37),
('Mansa', 37),
('Rupnagar', 37),
('Kharar', 37),
('Gobindgarh', 37),
('Kotkapura', 37),
('Jagraon', 37),
('Nakodar', 37),
('Talwandi Sabo', 37),
('Zira', 37),
('Dera Bassi', 37);

INSERT INTO master_cities (name, state_id) VALUES
-- Andhra Pradesh (21)
('Visakhapatnam',21),('Vijayawada',21),('Guntur',21),

-- Arunachal Pradesh (22)
('Itanagar',22),('Naharlagun',22),

-- Assam (23)
('Guwahati',23),('Silchar',23),('Dibrugarh',23),

-- Bihar (24)
('Patna',24),('Gaya',24),('Muzaffarpur',24),

-- Chhattisgarh (25)
('Raipur',25),('Bhilai',25),('Bilaspur',25),

-- Goa (26)
('Panaji',26),('Margao',26),('Vasco da Gama',26),

-- Himachal Pradesh (28)
('Shimla',28),('Manali',28),('Dharamshala',28),

-- Jharkhand (29)
('Ranchi',29),('Jamshedpur',29),('Dhanbad',29),

-- Manipur (32)
('Imphal',32),

-- Meghalaya (33)
('Shillong',33),

-- Mizoram (34)
('Aizawl',34),

-- Nagaland (35)
('Kohima',35),('Dimapur',35),

-- Odisha (36)
('Bhubaneswar',36),('Cuttack',36),('Rourkela',36),

-- Sikkim (39)
('Gangtok',39),

-- Tripura (40)
('Agartala',40),

-- Uttarakhand (42)
('Dehradun',42),('Haridwar',42),('Rishikesh',42);

FIX DUPLICATE CITIES ISSUE 
SELECT id, name, ROW_NUMBER() OVER (PARTITION BY name ORDER BY id) AS rn FROM master_cities ORDER BY name;
DELETE FROM master_cities WHERE id IN (SELECT id FROM (SELECT id,ROW_NUMBER() OVER (PARTITION BY name ORDER BY id) AS rn FROM master_cities) t WHERE rn > 1;
ALTER TABLE master_cities ADD CONSTRAINT unique_city UNIQUE (name);

-- Add remaining major cities to master_cities table
INSERT INTO master_cities (name, state_id) VALUES

-- Punjab (state_id = 22)
('Bathinda', 22),
('Mohali', 22),
('Hoshiarpur', 22),
('Batala', 22),
('Pathankot', 22),
('Moga', 22),
('Abohar', 22),
('Malerkotla', 22),
('Khanna', 22),
('Phagwara', 22),

-- Haryana (state_id = 23)
('Hisar', 23),
('Karnal', 23),
('Rohtak', 23),
('Sonipat', 23),
('Yamunanagar', 23),
('Panchkula', 23),
('Bhiwani', 23),
('Sirsa', 23),
('Rewari', 23),
('Kurukshetra', 23),

-- Bihar (state_id = 24)
('Darbhanga', 24),
('Purnia', 24),
('Arrah', 24),
('Begusarai', 24),
('Katihar', 24),
('Munger', 24),
('Chapra', 24),
('Saharsa', 24),
('Samastipur', 24),
('Motihari', 24),

-- Odisha (state_id = 25)
('Sambalpur', 25),
('Berhampur', 25),
('Balasore', 25),
('Jharsuguda', 25),
('Baripada', 25),
('Jeypore', 25),
('Bhadrak', 25),

-- Assam (state_id = 26)
('Jorhat', 26),
('Tezpur', 26),
('Nagaon', 26),
('Tinsukia', 26),
('Sivasagar', 26),
('Bongaigaon', 26),

-- Jharkhand (state_id = 27)
('Bokaro', 27),
('Hazaribagh', 27),
('Deoghar', 27),
('Giridih', 27),
('Ramgarh', 27),
('Chaibasa', 27),

-- Chhattisgarh (state_id = 28)
('Korba', 28),
('Jagdalpur', 28),
('Rajnandgaon', 28),
('Raigarh', 28),
('Ambikapur', 28),
('Durg', 28),

-- Uttarakhand (state_id = 29)
('Rishikesh', 29),
('Roorkee', 29),
('Haldwani', 29),
('Rudrapur', 29),
('Almora', 29),
('Pithoragarh', 29),

-- Himachal Pradesh (state_id = 30)
('Solan', 30),
('Mandi', 30),
('Kullu', 30),
('Hamirpur', 30),
('Bilaspur', 30),
('Chamba', 30),

-- Goa (state_id = 31)
('Mapusa', 31),
('Ponda', 31),
('Bicholim', 31),
('Canacona', 31),

-- Tripura (state_id = 32)
('Udaipur', 32),
('Dharmanagar', 32),
('Kailasahar', 32),
('Belonia', 32),

-- Meghalaya (state_id = 33)
('Tura', 33),
('Jowai', 33),
('Nongpoh', 33),
('Baghmara', 33),

-- Manipur (state_id = 34)
('Thoubal', 34),
('Bishnupur', 34),
('Churachandpur', 34),
('Ukhrul', 34),

-- Nagaland (state_id = 35)
('Mokokchung', 35),
('Tuensang', 35),
('Wokha', 35),
('Zunheboto', 35),

-- Mizoram (state_id = 36)
('Lunglei', 36),
('Champhai', 36),
('Serchhip', 36),
('Kolasib', 36),

-- Sikkim (state_id = 37)
('Namchi', 37),
('Gyalshing', 37),
('Mangan', 37),
('Singtam', 37),

-- Arunachal Pradesh (state_id = 38)
('Naharlagun', 38),
('Tawang', 38),
('Pasighat', 38),
('Ziro', 38),
('Bomdila', 38),
('Roing', 38);

-- master industries insert command
INSERT INTO master_industries (name) VALUES
('Information Technology'),
('Healthcare'),
('Finance'),
('Education'),
('Manufacturing'),
('Retail'),
('Real Estate'),
('Entertainment'),
('Consulting'),
('Telecommunications'),
('Marketing & Advertising'),
('E-commerce'),
('Logistics & Supply Chain'),
('Automotive'),
('Banking'),
('Insurance'),
('Pharmaceuticals'),
('Biotechnology'),
('Construction'),
('Energy & Utilities'),
('Oil & Gas'),
('Agriculture'),
('Food & Beverage'),
('Hospitality'),
('Travel & Tourism'),
('Media & Publishing'),
('Legal Services'),
('Government & Public Sector'),
('Non-Profit'),
('Human Resources'),
('Cybersecurity'),
('Artificial Intelligence & Machine Learning'),
('Cloud Computing'),
('Semiconductors'),
('Aerospace & Defense'),
('Mining & Metals'),
('Textiles & Apparel'),
('Consumer Goods'),
('Electronics'),
('Television & Broadcasting'),
('Sports & Fitness'),
('Environmental Services'),
('Waste Management'),
('Marine & Shipping'),
('Architecture & Planning'),
('Design Services'),
('Research & Development'),
('Event Management'),
('Gaming'),
('Animation & VFX'),
('EdTech'),
('FinTech'),
('HealthTech'),
('InsurTech'),
('PropTech'),
('AgriTech'),
('CleanTech'),
('Robotics'),
('IoT (Internet of Things)'),
('Blockchain'),
('Digital Marketing'),
('BPO & KPO'),
('Staffing & Recruitment'),
('Procurement'),
('Import & Export'),
('Luxury Goods'),
('Jewelry'),
('Furniture & Home Decor'),
('Printing & Packaging'),
('Music Industry'),
('Film Production'),
('Social Media'),
('Data Analytics'),
('Venture Capital & Private Equity'),
('Accounting & Auditing'),
('Corporate Training'),
('Security Services'),
('Facilities Management'),
('Pet Care'),
('Beauty & Cosmetics'),
('Wellness & Mental Health'),
('Translation & Localization'),
('Open Source Software'),
('Mobile Applications'),
('SaaS (Software as a Service)'),
('Hardware'),
('Networking'),
('Quantum Computing'),
('Space Technology'),
('Renewable Energy'),
('Drones'),
('3D Printing');




-- master roles insert command

-- Drop the old unique constraint/index on name only
DROP INDEX IF EXISTS ix_master_roles_name;

-- Create a composite unique index so the same role name
-- can exist in multiple industries
CREATE UNIQUE INDEX IF NOT EXISTS ix_master_roles_name_industry
ON master_roles (name, industry_id);


INSERT INTO master_roles (name, industry_id) VALUES

-- Information Technology (23)
('Software Engineer', 23),
('Frontend Developer', 23),
('Backend Developer', 23),
('Full Stack Developer', 23),
('DevOps Engineer', 23),
('UI/UX Designer', 23),
('Data Analyst', 23),
('Data Scientist', 23),
('Business Analyst', 23),
('Product Manager', 23),
('Project Manager', 23),
('QA Engineer', 23),
('Mobile App Developer', 23),
('Cloud Engineer', 23),

-- Healthcare (24)
('Healthcare Data Analyst', 24),
('Clinical Research Associate', 24),
('Medical Writer', 24),
('Regulatory Affairs Specialist', 24),
('Pharmacovigilance Specialist', 24),
('Healthcare Project Manager', 24),
('Healthcare Business Analyst', 24),
('Hospital Administrator', 24),
('Medical Coder', 24),

-- Finance (25)
('Financial Analyst', 25),
('Investment Analyst', 25),
('Risk Analyst', 25),
('Compliance Officer', 25),
('Accountant', 25),
('Auditor', 25),
('Finance Data Analyst', 25),
('Finance Business Analyst', 25),
('Treasury Analyst', 25),

-- Education (26)
('Teacher', 26),
('Professor', 26),
('Instructional Designer', 26),
('Curriculum Developer', 26),
('Education Product Manager', 26),
('EdTech Software Engineer', 26),
('Academic Coordinator', 26),

-- Manufacturing (27)
('Industrial Engineer', 27),
('Mechanical Engineer', 27),
('Manufacturing Engineer', 27),
('Quality Assurance Engineer', 27),
('Supply Chain Analyst', 27),
('Procurement Specialist', 27),
('Operations Manager', 27),
('Plant Manager', 27),

-- Retail (28)
('Sales Executive', 28),
('Store Manager', 28),
('Merchandiser', 28),
('Inventory Manager', 28),
('Retail Marketing Manager', 28),
('Retail Data Analyst', 28),
('Retail Product Manager', 28),
('Category Manager', 28),

-- Real Estate (29)
('Real Estate Consultant', 29),
('Property Manager', 29),
('Real Estate Sales Executive', 29),
('Real Estate Marketing Manager', 29),
('Real Estate Business Analyst', 29),

-- Entertainment (30)
('Graphic Designer', 30),
('Animator', 30),
('Video Producer', 30),
('Film Editor', 30),
('Entertainment UI/UX Designer', 30),
('Entertainment Marketing Manager', 30),
('Content Creator', 30),

-- Consulting (31)
('Consultant', 31),
('Management Consultant', 31),
('Strategy Consultant', 31),
('Consulting Business Analyst', 31),
('Consulting Data Analyst', 31),
('Consulting Project Manager', 31),

-- Telecommunications (32)
('Network Engineer', 32),
('Telecommunications Engineer', 32),
('Telecom Backend Developer', 32),
('Telecom DevOps Engineer', 32),
('Telecom Data Analyst', 32),
('RF Engineer', 32),

-- Marketing & Advertising (33)
('Marketing Manager', 33),
('Digital Marketing Specialist', 33),
('SEO Specialist', 33),
('Social Media Manager', 33),
('Copywriter', 33),
('Graphic Designer', 33),
('Advertising Sales Executive', 33),
('Brand Manager', 33),

-- E-commerce (34)
('E-commerce Manager', 34),
('Catalog Manager', 34),
('E-commerce Product Manager', 34),
('E-commerce Data Analyst', 34),
('E-commerce Frontend Developer', 34),
('Marketplace Specialist', 34),

-- Logistics & Supply Chain (35)
('Logistics Coordinator', 35),
('Warehouse Manager', 35),
('Supply Chain Manager', 35),
('Procurement Specialist', 35),
('Operations Executive', 35),
('Transportation Manager', 35),

-- Automotive (36)
('Automotive Engineer', 36),
('Vehicle Design Engineer', 36),
('Automotive Quality Engineer', 36),
('Automotive Project Manager', 36),
('Service Engineer', 36),

-- Banking (37)
('Banking Operations Executive', 37),
('Relationship Manager', 37),
('Credit Analyst', 37),
('Banking Risk Analyst', 37),
('Loan Officer', 37),

-- Insurance (38)
('Insurance Advisor', 38),
('Claims Analyst', 38),
('Underwriter', 38),
('Actuary', 38),
('Policy Administrator', 38),

-- Pharmaceuticals (39)
('Pharmacist', 39),
('Pharmaceutical Research Scientist', 39),
('Drug Safety Associate', 39),
('Regulatory Affairs Manager', 39),
('Quality Control Analyst', 39),

-- Biotechnology (40)
('Biotechnologist', 40),
('Research Scientist', 40),
('Lab Technician', 40),
('Clinical Data Manager', 40),
('Bioinformatics Analyst', 40),

-- Construction (41)
('Civil Engineer', 41),
('Architect', 41),
('Site Engineer', 41),
('Quantity Surveyor', 41),
('Construction Project Manager', 41),

-- Energy & Utilities (42)
('Energy Analyst', 42),
('Power Systems Engineer', 42),
('Utility Operations Manager', 42),
('Electrical Engineer', 42),
('Renewable Energy Engineer', 42),

-- Oil & Gas (43)
('Petroleum Engineer', 43),
('Drilling Engineer', 43),
('Reservoir Engineer', 43),
('HSE Officer', 43),
('Process Engineer', 43),

-- Agriculture (44)
('Agronomist', 44),
('Agricultural Engineer', 44),
('Farm Manager', 44),
('Soil Scientist', 44),
('Crop Analyst', 44),

-- Food & Beverage (45)
('Food Technologist', 45),
('Quality Assurance Manager', 45),
('Production Supervisor', 45),
('Food Safety Officer', 45),
('Supply Chain Manager', 45),

-- Hospitality (46)
('Hotel Manager', 46),
('Front Office Executive', 46),
('Housekeeping Manager', 46),
('Restaurant Manager', 46),
('Guest Relations Executive', 46),

-- Travel & Tourism (47)
('Travel Consultant', 47),
('Tour Manager', 47),
('Reservation Executive', 47),
('Destination Specialist', 47),
('Operations Coordinator', 47),

-- Media & Publishing (48)
('Editor', 48),
('Journalist', 48),
('Content Writer', 48),
('Publishing Manager', 48),
('Proofreader', 48),

-- Legal Services (49)
('Lawyer', 49),
('Legal Associate', 49),
('Paralegal', 49),
('Compliance Officer', 49),
('Contract Specialist', 49),

-- Government & Public Sector (50)
('Policy Analyst', 50),
('Public Administrator', 50),
('Program Officer', 50),
('Government Project Manager', 50),
('Research Officer', 50),

-- Non-Profit (51)
('Program Manager', 51),
('Fundraising Manager', 51),
('Community Outreach Coordinator', 51),
('Grant Writer', 51),
('Volunteer Coordinator', 51),

-- Human Resources (52)
('HR Executive', 52),
('HR Manager', 52),
('Recruiter', 52),
('Talent Acquisition Specialist', 52),
('Learning and Development Specialist', 52),

-- Cybersecurity (53)
('Cybersecurity Analyst', 53),
('Security Engineer', 53),
('Penetration Tester', 53),
('SOC Analyst', 53),
('Incident Response Specialist', 53),

-- Artificial Intelligence & Machine Learning (54)
('AI Engineer', 54),
('Machine Learning Engineer', 54),
('Prompt Engineer', 54),
('Research Scientist', 54),
('MLOps Engineer', 54),

-- Cloud Computing (55)
('Cloud Engineer', 55),
('Cloud Architect', 55),
('Site Reliability Engineer', 55),
('DevOps Engineer', 55),
('Infrastructure Engineer', 55),

-- Semiconductors (56)
('Semiconductor Engineer', 56),
('Chip Design Engineer', 56),
('Verification Engineer', 56),
('Process Engineer', 56),
('Test Engineer', 56),

-- Aerospace & Defense (57)
('Aerospace Engineer', 57),
('Avionics Engineer', 57),
('Systems Engineer', 57),
('Defense Analyst', 57),
('Quality Engineer', 57),

-- Mining & Metals (58)
('Mining Engineer', 58),
('Metallurgical Engineer', 58),
('Geologist', 58),
('Safety Officer', 58),
('Operations Manager', 58),

-- Textiles & Apparel (59)
('Textile Engineer', 59),
('Fashion Designer', 59),
('Production Merchandiser', 59),
('Quality Inspector', 59),
('Sourcing Manager', 59),

-- Consumer Goods (60)
('Brand Manager', 60),
('Category Manager', 60),
('Sales Manager', 60),
('Supply Chain Analyst', 60),
('Product Manager', 60),
-- Electronics (61)
('Electronics Engineer', 61),
('Embedded Systems Engineer', 61),
('Hardware Design Engineer', 61),
('PCB Design Engineer', 61),
('Electronics Test Engineer', 61),

-- Television & Broadcasting (62)
('Broadcast Engineer', 62),
('Video Editor', 62),
('TV Producer', 62),
('Camera Operator', 62),
('Broadcast Technician', 62),

-- Sports & Fitness (63)
('Fitness Trainer', 63),
('Sports Coach', 63),
('Sports Nutritionist', 63),
('Gym Manager', 63),
('Sports Analyst', 63),

-- Environmental Services (64)
('Environmental Engineer', 64),
('Sustainability Analyst', 64),
('Environmental Consultant', 64),
('Ecologist', 64),
('Compliance Specialist', 64),

-- Waste Management (65)
('Waste Management Specialist', 65),
('Recycling Coordinator', 65),
('Environmental Compliance Officer', 65),
('Operations Supervisor', 65),
('Safety Officer', 65),

-- Marine & Shipping (66)
('Marine Engineer', 66),
('Ship Operations Manager', 66),
('Logistics Coordinator', 66),
('Port Manager', 66),
('Naval Architect', 66),

-- Architecture & Planning (67)
('Architect', 67),
('Urban Planner', 67),
('Landscape Architect', 67),
('Draftsman', 67),
('Planning Consultant', 67),

-- Design Services (68)
('Graphic Designer', 68),
('UI/UX Designer', 68),
('Product Designer', 68),
('Interior Designer', 68),
('Creative Director', 68),

-- Research & Development (69)
('Research Scientist', 69),
('R&D Engineer', 69),
('Innovation Manager', 69),
('Lab Technician', 69),
('Prototype Engineer', 69),

-- Event Management (70)
('Event Manager', 70),
('Event Coordinator', 70),
('Wedding Planner', 70),
('Production Manager', 70),
('Sponsorship Manager', 70),

-- Gaming (71)
('Game Developer', 71),
('Game Designer', 71),
('Game Artist', 71),
('Level Designer', 71),
('QA Tester', 71),

-- Animation & VFX (72)
('Animator', 72),
('VFX Artist', 72),
('3D Modeler', 72),
('Compositor', 72),
('Motion Graphics Designer', 72),

-- EdTech (73)
('EdTech Product Manager', 73),
('Instructional Designer', 73),
('Learning Experience Designer', 73),
('Education Software Engineer', 73),
('Academic Content Developer', 73),

-- FinTech (74)
('FinTech Product Manager', 74),
('Financial Software Engineer', 74),
('Payments Analyst', 74),
('Risk Analyst', 74),
('Compliance Officer', 74),

-- HealthTech (75)
('HealthTech Product Manager', 75),
('Healthcare Software Engineer', 75),
('Clinical Data Analyst', 75),
('Medical Informatics Specialist', 75),
('Healthcare UX Designer', 75),

-- InsurTech (76)
('InsurTech Product Manager', 76),
('Insurance Data Analyst', 76),
('Insurance Software Engineer', 76),
('Underwriting Analyst', 76),
('Claims Automation Specialist', 76),

-- PropTech (77)
('PropTech Product Manager', 77),
('Real Estate Software Engineer', 77),
('Property Data Analyst', 77),
('GIS Analyst', 77),
('Real Estate UX Designer', 77),

-- AgriTech (78)
('AgriTech Product Manager', 78),
('Agricultural Data Analyst', 78),
('Precision Agriculture Engineer', 78),
('Farm Automation Specialist', 78),
('Agronomist', 78),

-- CleanTech (79)
('CleanTech Product Manager', 79),
('Renewable Energy Engineer', 79),
('Carbon Analyst', 79),
('Sustainability Consultant', 79),
('Energy Data Analyst', 79),

-- Robotics (80)
('Robotics Engineer', 80),
('Automation Engineer', 80),
('Control Systems Engineer', 80),
('ROS Developer', 80),
('Mechatronics Engineer', 80),

-- IoT (Internet of Things) (81)
('IoT Engineer', 81),
('Embedded Systems Engineer', 81),
('Firmware Engineer', 81),
('IoT Solutions Architect', 81),
('Sensor Integration Engineer', 81),

-- Blockchain (82)
('Blockchain Developer', 82),
('Smart Contract Engineer', 82),
('Web3 Developer', 82),
('Cryptography Engineer', 82),
('Tokenomics Analyst', 82),

-- Digital Marketing (83)
('Digital Marketing Manager', 83),
('SEO Specialist', 83),
('PPC Specialist', 83),
('Content Strategist', 83),
('Email Marketing Specialist', 83),

-- BPO & KPO (84)
('Customer Support Executive', 84),
('Process Associate', 84),
('Operations Analyst', 84),
('Quality Analyst', 84),
('Team Leader', 84),

-- Staffing & Recruitment (85)
('Recruiter', 85),
('Talent Acquisition Specialist', 85),
('Sourcing Specialist', 85),
('Recruitment Manager', 85),
('HR Consultant', 85),

-- Procurement (86)
('Procurement Specialist', 86),
('Category Buyer', 86),
('Vendor Manager', 86),
('Strategic Sourcing Manager', 86),
('Contract Manager', 86),

-- Import & Export (87)
('Import Export Manager', 87),
('Customs Compliance Specialist', 87),
('Trade Analyst', 87),
('Documentation Executive', 87),
('International Logistics Coordinator', 87),

-- Luxury Goods (88)
('Luxury Brand Manager', 88),
('Visual Merchandiser', 88),
('Retail Sales Consultant', 88),
('Product Specialist', 88),
('Store Manager', 88),

-- Jewelry (89)
('Jewelry Designer', 89),
('Gemologist', 89),
('Production Manager', 89),
('Sales Consultant', 89),
('Quality Inspector', 89),

-- Furniture & Home Decor (90)
('Furniture Designer', 90),
('Interior Designer', 90),
('Product Development Manager', 90),
('Visual Merchandiser', 90),
('Sales Consultant', 90),

-- Printing & Packaging (91)
('Packaging Engineer', 91),
('Print Production Manager', 91),
('Prepress Specialist', 91),
('Graphic Designer', 91),
('Quality Control Inspector', 91),

-- Music Industry (92)
('Music Producer', 92),
('Sound Engineer', 92),
('Artist Manager', 92),
('Music Marketing Manager', 92),
('A&R Manager', 92),

-- Film Production (93)
('Film Producer', 93),
('Director', 93),
('Screenwriter', 93),
('Cinematographer', 93),
('Production Coordinator', 93),

-- Social Media (94)
('Social Media Manager', 94),
('Content Creator', 94),
('Community Manager', 94),
('Influencer Marketing Specialist', 94),
('Social Media Analyst', 94),

-- Data Analytics (95)
('Data Analyst', 95),
('Business Intelligence Analyst', 95),
('Analytics Engineer', 95),
('Data Visualization Specialist', 95),
('Reporting Analyst', 95),

-- Venture Capital & Private Equity (96)
('Investment Associate', 96),
('Due Diligence Analyst', 96),
('Portfolio Manager', 96),
('Deal Sourcing Analyst', 96),
('Financial Modeling Analyst', 96),

-- Accounting & Auditing (97)
('Accountant', 97),
('Auditor', 97),
('Tax Consultant', 97),
('Forensic Accountant', 97),
('Internal Audit Manager', 97),

-- Corporate Training (98)
('Corporate Trainer', 98),
('Learning and Development Specialist', 98),
('Training Manager', 98),
('Instructional Designer', 98),
('Facilitator', 98),

-- Security Services (99)
('Security Officer', 99),
('Security Supervisor', 99),
('Risk Consultant', 99),
('Surveillance Operator', 99),
('Security Manager', 99),

-- Facilities Management (100)
('Facilities Manager', 100),
('Maintenance Supervisor', 100),
('Building Operations Manager', 100),
('Asset Manager', 100),
('Space Planner', 100),

-- Pet Care (101)
('Veterinary Assistant', 101),
('Pet Groomer', 101),
('Pet Trainer', 101),
('Veterinary Technician', 101),
('Pet Care Manager', 101),

-- Beauty & Cosmetics (102)
('Cosmetologist', 102),
('Beauty Consultant', 102),
('Makeup Artist', 102),
('Skincare Specialist', 102),
('Cosmetic Product Manager', 102),

-- Wellness & Mental Health (103)
('Mental Health Counselor', 103),
('Psychologist', 103),
('Wellness Coach', 103),
('Therapist', 103),
('Clinical Program Manager', 103),

-- Translation & Localization (104)
('Translator', 104),
('Interpreter', 104),
('Localization Specialist', 104),
('Localization Project Manager', 104),
('Language Quality Analyst', 104),

-- Open Source Software (105)
('Open Source Developer', 105),
('Community Manager', 105),
('Maintainer', 105),
('Developer Advocate', 105),
('Technical Writer', 105),

-- Mobile Applications (106)
('Mobile App Developer', 106),
('Android Developer', 106),
('iOS Developer', 106),
('React Native Developer', 106),
('Flutter Developer', 106),

-- SaaS (Software as a Service) (107)
('SaaS Product Manager', 107),
('Customer Success Manager', 107),
('Software Engineer', 107),
('DevOps Engineer', 107),
('Solutions Architect', 107),

-- Hardware (108)
('Hardware Engineer', 108),
('Embedded Systems Engineer', 108),
('Firmware Engineer', 108),
('PCB Design Engineer', 108),
('Hardware Test Engineer', 108),

-- Networking (109)
('Network Engineer', 109),
('Network Administrator', 109),
('Network Architect', 109),
('Systems Engineer', 109),
('NOC Engineer', 109),

-- Quantum Computing (110)
('Quantum Researcher', 110),
('Quantum Software Engineer', 110),
('Quantum Algorithm Developer', 110),
('Quantum Physicist', 110),
('Research Scientist', 110),

-- Space Technology (111)
('Space Systems Engineer', 111),
('Aerospace Engineer', 111),
('Satellite Engineer', 111),
('Mission Operations Engineer', 111),
('Propulsion Engineer', 111),

-- Renewable Energy (112)
('Renewable Energy Engineer', 112),
('Solar Engineer', 112),
('Wind Energy Technician', 112),
('Energy Analyst', 112),
('Project Manager', 112),

-- Drones (113)
('Drone Operator', 113),
('UAV Engineer', 113),
('Flight Test Engineer', 113),
('Drone Software Developer', 113),
('Payload Integration Engineer', 113),

-- 3D Printing (114)
('Additive Manufacturing Engineer', 114),
('3D Printing Technician', 114),
('CAD Designer', 114),
('Prototype Engineer', 114),
('Materials Engineer', 114);



INSERT INTO departments (name) VALUES
('Management'),
('Executive Office'),
('Strategy'),
('Corporate Planning'),
('Board Administration'),

('Software Development'),
('Custom Development'),
('Web Development'),
('Mobile Development'),
('DevOps'),
('Cloud Engineering'),
('Infrastructure'),
('Network Administration'),
('Database Administration'),
('Cybersecurity'),
('IT Support'),
('Technical Support'),
('QA / Testing'),
('Data Engineering'),
('Artificial Intelligence / Machine Learning'),
('Business Intelligence'),

('Designing Team'),
('UI/UX Design'),
('Graphic Design'),
('Product Design'),
('Video Production'),
('Content Creation'),

('Sales Team'),
('Business Development'),
('Account Management'),
('Inside Sales'),
('Field Sales'),
('Pre-Sales'),
('Customer Acquisition'),

('Digital Marketing'),
('Brand Marketing'),
('Performance Marketing'),
('SEO'),
('Social Media Marketing'),
('Product Marketing'),
('Public Relations'),
('Communications'),

('Human Resources'),
('HR Administration'),
('Talent Acquisition'),
('Recruitment'),
('Learning & Development'),
('Employee Relations'),
('Compensation & Benefits'),
('Payroll'),

('Operations'),
('Process Management'),
('Service Delivery'),
('Resource Management'),
('Administration'),

('Customer Support'),
('Customer Success'),
('Call Center'),
('Help Desk'),

('Finance'),
('Accounting'),
('Accounts Payable'),
('Accounts Receivable'),
('Treasury'),
('Taxation'),
('Audit'),
('Financial Planning & Analysis'),

('Legal'),
('Compliance'),
('Risk Management'),
('Corporate Governance'),

('Procurement'),
('Purchasing'),
('Supply Chain'),
('Logistics'),
('Inventory Management'),
('Vendor Management'),
('Warehouse'),

('Production'),
('Manufacturing'),
('Quality Control'),
('Maintenance'),
('Industrial Engineering'),

('Research and Development (R&D)'),
('Innovation Lab'),
('Product Engineering'),

('Data Science'),
('Analytics'),
('Reporting'),
('Data Governance'),

('Product Management'),
('Product Strategy'),
('Product Operations'),

('Nursing'),
('Medical Administration'),
('Laboratory'),
('Pharmacy'),
('Clinical Operations'),

('Academic Affairs'),
('Admissions'),
('Student Services'),
('Faculty Administration'),

('Underwriting'),
('Claims'),
('Loan Processing'),
('Credit Analysis'),

('Civil Engineering'),
('Site Operations'),
('Safety'),
('Project Management'),

('Physical Security'),
('Information Security'),

('Corporate Social Responsibility'),
('Environmental Health & Safety'),
('Sustainability'),

('Facilities'),
('Housekeeping'),

('Technical Writing'),
('Documentation'),
('Knowledge Management');




INSERT INTO department_jobs (name, department_id)
VALUES
-- Management
('General Manager', (SELECT id FROM departments WHERE name = 'Management')),
('Operations Manager', (SELECT id FROM departments WHERE name = 'Management')),
('Business Manager', (SELECT id FROM departments WHERE name = 'Management')),
('Assistant Manager', (SELECT id FROM departments WHERE name = 'Management')),
('Management Trainee', (SELECT id FROM departments WHERE name = 'Management')),

-- Executive Office
('Chief Executive Officer (CEO)', (SELECT id FROM departments WHERE name = 'Executive Office')),
('Chief Operating Officer (COO)', (SELECT id FROM departments WHERE name = 'Executive Office')),
('Chief Financial Officer (CFO)', (SELECT id FROM departments WHERE name = 'Executive Office')),
('Executive Assistant', (SELECT id FROM departments WHERE name = 'Executive Office')),
('Office Coordinator', (SELECT id FROM departments WHERE name = 'Executive Office')),

-- Strategy
('Strategy Manager', (SELECT id FROM departments WHERE name = 'Strategy')),
('Business Strategy Analyst', (SELECT id FROM departments WHERE name = 'Strategy')),
('Strategic Planner', (SELECT id FROM departments WHERE name = 'Strategy')),
('Corporate Strategist', (SELECT id FROM departments WHERE name = 'Strategy')),
('Growth Strategy Consultant', (SELECT id FROM departments WHERE name = 'Strategy')),

-- Corporate Planning
('Corporate Planning Manager', (SELECT id FROM departments WHERE name = 'Corporate Planning')),
('Business Planning Analyst', (SELECT id FROM departments WHERE name = 'Corporate Planning')),
('Planning Coordinator', (SELECT id FROM departments WHERE name = 'Corporate Planning')),
('Forecasting Analyst', (SELECT id FROM departments WHERE name = 'Corporate Planning')),
('Budget Planning Manager', (SELECT id FROM departments WHERE name = 'Corporate Planning')),

-- Board Administration
('Board Secretary', (SELECT id FROM departments WHERE name = 'Board Administration')),
('Governance Coordinator', (SELECT id FROM departments WHERE name = 'Board Administration')),
('Board Administrator', (SELECT id FROM departments WHERE name = 'Board Administration')),
('Compliance Secretary', (SELECT id FROM departments WHERE name = 'Board Administration')),
('Executive Governance Officer', (SELECT id FROM departments WHERE name = 'Board Administration')),

-- Software Development
('Software Engineer', (SELECT id FROM departments WHERE name = 'Software Development')),
('Senior Software Engineer', (SELECT id FROM departments WHERE name = 'Software Development')),
('Backend Developer', (SELECT id FROM departments WHERE name = 'Software Development')),
('Full Stack Developer', (SELECT id FROM departments WHERE name = 'Software Development')),
('Application Developer', (SELECT id FROM departments WHERE name = 'Software Development')),

-- Custom Development
('Custom Application Developer', (SELECT id FROM departments WHERE name = 'Custom Development')),
('Solutions Developer', (SELECT id FROM departments WHERE name = 'Custom Development')),
('Enterprise Developer', (SELECT id FROM departments WHERE name = 'Custom Development')),
('Technical Consultant', (SELECT id FROM departments WHERE name = 'Custom Development')),
('Integration Developer', (SELECT id FROM departments WHERE name = 'Custom Development')),

-- Web Development
('Frontend Developer', (SELECT id FROM departments WHERE name = 'Web Development')),
('Web Developer', (SELECT id FROM departments WHERE name = 'Web Development')),
('React Developer', (SELECT id FROM departments WHERE name = 'Web Development')),
('Angular Developer', (SELECT id FROM departments WHERE name = 'Web Development')),
('PHP Developer', (SELECT id FROM departments WHERE name = 'Web Development')),

-- Mobile Development
('Android Developer', (SELECT id FROM departments WHERE name = 'Mobile Development')),
('iOS Developer', (SELECT id FROM departments WHERE name = 'Mobile Development')),
('Flutter Developer', (SELECT id FROM departments WHERE name = 'Mobile Development')),
('React Native Developer', (SELECT id FROM departments WHERE name = 'Mobile Development')),
('Mobile App Developer', (SELECT id FROM departments WHERE name = 'Mobile Development')),

-- DevOps
('DevOps Engineer', (SELECT id FROM departments WHERE name = 'DevOps')),
('Site Reliability Engineer', (SELECT id FROM departments WHERE name = 'DevOps')),
('CI/CD Engineer', (SELECT id FROM departments WHERE name = 'DevOps')),
('Release Engineer', (SELECT id FROM departments WHERE name = 'DevOps')),
('Automation Engineer', (SELECT id FROM departments WHERE name = 'DevOps')),

-- Cloud Engineering
('Cloud Engineer', (SELECT id FROM departments WHERE name = 'Cloud Engineering')),
('AWS Engineer', (SELECT id FROM departments WHERE name = 'Cloud Engineering')),
('Azure Engineer', (SELECT id FROM departments WHERE name = 'Cloud Engineering')),
('Google Cloud Engineer', (SELECT id FROM departments WHERE name = 'Cloud Engineering')),
('Cloud Solutions Architect', (SELECT id FROM departments WHERE name = 'Cloud Engineering')),

-- Infrastructure
('Infrastructure Engineer', (SELECT id FROM departments WHERE name = 'Infrastructure')),
('Systems Engineer', (SELECT id FROM departments WHERE name = 'Infrastructure')),
('Infrastructure Architect', (SELECT id FROM departments WHERE name = 'Infrastructure')),
('Server Administrator', (SELECT id FROM departments WHERE name = 'Infrastructure')),
('Data Center Engineer', (SELECT id FROM departments WHERE name = 'Infrastructure')),

-- Network Administration
('Network Administrator', (SELECT id FROM departments WHERE name = 'Network Administration')),
('Network Engineer', (SELECT id FROM departments WHERE name = 'Network Administration')),
('NOC Engineer', (SELECT id FROM departments WHERE name = 'Network Administration')),
('Network Security Engineer', (SELECT id FROM departments WHERE name = 'Network Administration')),
('Wireless Network Engineer', (SELECT id FROM departments WHERE name = 'Network Administration')),

-- Database Administration
('Database Administrator', (SELECT id FROM departments WHERE name = 'Database Administration')),
('SQL Developer', (SELECT id FROM departments WHERE name = 'Database Administration')),
('Oracle DBA', (SELECT id FROM departments WHERE name = 'Database Administration')),
('PostgreSQL DBA', (SELECT id FROM departments WHERE name = 'Database Administration')),
('Database Engineer', (SELECT id FROM departments WHERE name = 'Database Administration')),

-- Cybersecurity
('Cybersecurity Analyst', (SELECT id FROM departments WHERE name = 'Cybersecurity')),
('Security Engineer', (SELECT id FROM departments WHERE name = 'Cybersecurity')),
('Penetration Tester', (SELECT id FROM departments WHERE name = 'Cybersecurity')),
('SOC Analyst', (SELECT id FROM departments WHERE name = 'Cybersecurity')),
('Information Security Analyst', (SELECT id FROM departments WHERE name = 'Cybersecurity')),

-- IT Support
('IT Support Specialist', (SELECT id FROM departments WHERE name = 'IT Support')),
('Desktop Support Engineer', (SELECT id FROM departments WHERE name = 'IT Support')),
('System Support Analyst', (SELECT id FROM departments WHERE name = 'IT Support')),
('IT Helpdesk Technician', (SELECT id FROM departments WHERE name = 'IT Support')),
('Technical Support Engineer', (SELECT id FROM departments WHERE name = 'IT Support')),

-- Technical Support
('Technical Support Executive', (SELECT id FROM departments WHERE name = 'Technical Support')),
('Support Engineer', (SELECT id FROM departments WHERE name = 'Technical Support')),
('Customer Technical Specialist', (SELECT id FROM departments WHERE name = 'Technical Support')),
('Product Support Analyst', (SELECT id FROM departments WHERE name = 'Technical Support')),
('Troubleshooting Specialist', (SELECT id FROM departments WHERE name = 'Technical Support')),

-- QA / Testing
('QA Engineer', (SELECT id FROM departments WHERE name = 'QA / Testing')),
('Software Tester', (SELECT id FROM departments WHERE name = 'QA / Testing')),
('Automation Test Engineer', (SELECT id FROM departments WHERE name = 'QA / Testing')),
('Manual Tester', (SELECT id FROM departments WHERE name = 'QA / Testing')),
('Quality Assurance Analyst', (SELECT id FROM departments WHERE name = 'QA / Testing')),

-- Data Engineering
('Data Engineer', (SELECT id FROM departments WHERE name = 'Data Engineering')),
('Big Data Engineer', (SELECT id FROM departments WHERE name = 'Data Engineering')),
('ETL Developer', (SELECT id FROM departments WHERE name = 'Data Engineering')),
('Data Pipeline Engineer', (SELECT id FROM departments WHERE name = 'Data Engineering')),
('Analytics Engineer', (SELECT id FROM departments WHERE name = 'Data Engineering')),

-- Artificial Intelligence / Machine Learning
('Machine Learning Engineer', (SELECT id FROM departments WHERE name = 'Artificial Intelligence / Machine Learning')),
('AI Engineer', (SELECT id FROM departments WHERE name = 'Artificial Intelligence / Machine Learning')),
('Deep Learning Engineer', (SELECT id FROM departments WHERE name = 'Artificial Intelligence / Machine Learning')),
('NLP Engineer', (SELECT id FROM departments WHERE name = 'Artificial Intelligence / Machine Learning')),
('Computer Vision Engineer', (SELECT id FROM departments WHERE name = 'Artificial Intelligence / Machine Learning')),

-- Business Intelligence
('BI Developer', (SELECT id FROM departments WHERE name = 'Business Intelligence')),
('Business Intelligence Analyst', (SELECT id FROM departments WHERE name = 'Business Intelligence')),
('Power BI Developer', (SELECT id FROM departments WHERE name = 'Business Intelligence')),
('Tableau Developer', (SELECT id FROM departments WHERE name = 'Business Intelligence')),
('Reporting Analyst', (SELECT id FROM departments WHERE name = 'Business Intelligence')),

-- Designing Team
('Creative Designer', (SELECT id FROM departments WHERE name = 'Designing Team')),
('Visual Designer', (SELECT id FROM departments WHERE name = 'Designing Team')),
('Design Lead', (SELECT id FROM departments WHERE name = 'Designing Team')),
('Art Director', (SELECT id FROM departments WHERE name = 'Designing Team')),
('Design Coordinator', (SELECT id FROM departments WHERE name = 'Designing Team')),

-- UI/UX Design
('UI Designer', (SELECT id FROM departments WHERE name = 'UI/UX Design')),
('UX Designer', (SELECT id FROM departments WHERE name = 'UI/UX Design')),
('Product Designer', (SELECT id FROM departments WHERE name = 'UI/UX Design')),
('UX Researcher', (SELECT id FROM departments WHERE name = 'UI/UX Design')),
('Interaction Designer', (SELECT id FROM departments WHERE name = 'UI/UX Design')),

-- Graphic Design
('Graphic Designer', (SELECT id FROM departments WHERE name = 'Graphic Design')),
('Senior Graphic Designer', (SELECT id FROM departments WHERE name = 'Graphic Design')),
('Brand Designer', (SELECT id FROM departments WHERE name = 'Graphic Design')),
('Illustrator', (SELECT id FROM departments WHERE name = 'Graphic Design')),
('Print Designer', (SELECT id FROM departments WHERE name = 'Graphic Design')),

-- Product Design
('Product Designer', (SELECT id FROM departments WHERE name = 'Product Design')),
('Industrial Designer', (SELECT id FROM departments WHERE name = 'Product Design')),
('Design Strategist', (SELECT id FROM departments WHERE name = 'Product Design')),
('Prototype Designer', (SELECT id FROM departments WHERE name = 'Product Design')),
('Concept Designer', (SELECT id FROM departments WHERE name = 'Product Design')),

-- Video Production
('Video Editor', (SELECT id FROM departments WHERE name = 'Video Production')),
('Motion Graphics Designer', (SELECT id FROM departments WHERE name = 'Video Production')),
('Videographer', (SELECT id FROM departments WHERE name = 'Video Production')),
('Post Production Specialist', (SELECT id FROM departments WHERE name = 'Video Production')),
('Animation Artist', (SELECT id FROM departments WHERE name = 'Video Production')),

-- Content Creation
('Content Writer', (SELECT id FROM departments WHERE name = 'Content Creation')),
('Copywriter', (SELECT id FROM departments WHERE name = 'Content Creation')),
('Content Strategist', (SELECT id FROM departments WHERE name = 'Content Creation')),
('Blog Writer', (SELECT id FROM departments WHERE name = 'Content Creation')),
('Technical Content Writer', (SELECT id FROM departments WHERE name = 'Content Creation')),

-- Sales Team
('Sales Executive', (SELECT id FROM departments WHERE name = 'Sales Team')),
('Sales Manager', (SELECT id FROM departments WHERE name = 'Sales Team')),
('Regional Sales Manager', (SELECT id FROM departments WHERE name = 'Sales Team')),
('Territory Sales Officer', (SELECT id FROM departments WHERE name = 'Sales Team')),
('Sales Representative', (SELECT id FROM departments WHERE name = 'Sales Team')),

-- Business Development
('Business Development Executive', (SELECT id FROM departments WHERE name = 'Business Development')),
('Business Development Manager', (SELECT id FROM departments WHERE name = 'Business Development')),
('Partnership Manager', (SELECT id FROM departments WHERE name = 'Business Development')),
('Growth Executive', (SELECT id FROM departments WHERE name = 'Business Development')),
('Market Development Manager', (SELECT id FROM departments WHERE name = 'Business Development')),

-- Account Management
('Account Manager', (SELECT id FROM departments WHERE name = 'Account Management')),
('Key Account Manager', (SELECT id FROM departments WHERE name = 'Account Management')),
('Client Relationship Manager', (SELECT id FROM departments WHERE name = 'Account Management')),
('Account Executive', (SELECT id FROM departments WHERE name = 'Account Management')),
('Customer Success Manager', (SELECT id FROM departments WHERE name = 'Account Management')),

-- Inside Sales
('Inside Sales Executive', (SELECT id FROM departments WHERE name = 'Inside Sales')),
('Inside Sales Representative', (SELECT id FROM departments WHERE name = 'Inside Sales')),
('Tele Sales Executive', (SELECT id FROM departments WHERE name = 'Inside Sales')),
('Lead Generation Executive', (SELECT id FROM departments WHERE name = 'Inside Sales')),
('Sales Development Representative', (SELECT id FROM departments WHERE name = 'Inside Sales')),

-- Field Sales
('Field Sales Executive', (SELECT id FROM departments WHERE name = 'Field Sales')),
('Territory Sales Executive', (SELECT id FROM departments WHERE name = 'Field Sales')),
('Area Sales Manager', (SELECT id FROM departments WHERE name = 'Field Sales')),
('Retail Sales Officer', (SELECT id FROM departments WHERE name = 'Field Sales')),
('Channel Sales Executive', (SELECT id FROM departments WHERE name = 'Field Sales')),

-- Pre-Sales
('Pre-Sales Consultant', (SELECT id FROM departments WHERE name = 'Pre-Sales')),
('Solutions Consultant', (SELECT id FROM departments WHERE name = 'Pre-Sales')),
('Technical Pre-Sales Engineer', (SELECT id FROM departments WHERE name = 'Pre-Sales')),
('Proposal Specialist', (SELECT id FROM departments WHERE name = 'Pre-Sales')),
('Demo Specialist', (SELECT id FROM departments WHERE name = 'Pre-Sales')),

-- Customer Acquisition
('Customer Acquisition Executive', (SELECT id FROM departments WHERE name = 'Customer Acquisition')),
('Growth Marketing Executive', (SELECT id FROM departments WHERE name = 'Customer Acquisition')),
('Lead Acquisition Specialist', (SELECT id FROM departments WHERE name = 'Customer Acquisition')),
('User Acquisition Manager', (SELECT id FROM departments WHERE name = 'Customer Acquisition')),
('Acquisition Analyst', (SELECT id FROM departments WHERE name = 'Customer Acquisition')),

-- Digital Marketing
('Digital Marketing Executive', (SELECT id FROM departments WHERE name = 'Digital Marketing')),
('Digital Marketing Manager', (SELECT id FROM departments WHERE name = 'Digital Marketing')),
('Online Marketing Specialist', (SELECT id FROM departments WHERE name = 'Digital Marketing')),
('Campaign Manager', (SELECT id FROM departments WHERE name = 'Digital Marketing')),
('Marketing Analyst', (SELECT id FROM departments WHERE name = 'Digital Marketing')),

-- Brand Marketing
('Brand Manager', (SELECT id FROM departments WHERE name = 'Brand Marketing')),
('Brand Executive', (SELECT id FROM departments WHERE name = 'Brand Marketing')),
('Brand Strategist', (SELECT id FROM departments WHERE name = 'Brand Marketing')),
('Marketing Communications Manager', (SELECT id FROM departments WHERE name = 'Brand Marketing')),
('Brand Analyst', (SELECT id FROM departments WHERE name = 'Brand Marketing')),

-- Performance Marketing
('Performance Marketing Executive', (SELECT id FROM departments WHERE name = 'Performance Marketing')),
('PPC Specialist', (SELECT id FROM departments WHERE name = 'Performance Marketing')),
('Paid Media Manager', (SELECT id FROM departments WHERE name = 'Performance Marketing')),
('Campaign Optimization Specialist', (SELECT id FROM departments WHERE name = 'Performance Marketing')),
('Growth Marketing Manager', (SELECT id FROM departments WHERE name = 'Performance Marketing')),

-- SEO
('SEO Executive', (SELECT id FROM departments WHERE name = 'SEO')),
('SEO Specialist', (SELECT id FROM departments WHERE name = 'SEO')),
('SEO Analyst', (SELECT id FROM departments WHERE name = 'SEO')),
('Search Engine Optimization Manager', (SELECT id FROM departments WHERE name = 'SEO')),
('Organic Growth Specialist', (SELECT id FROM departments WHERE name = 'SEO'));

INSERT INTO department_jobs (name, department_id)
VALUES
-- Social Media Marketing
('Social Media Executive', (SELECT id FROM departments WHERE name = 'Social Media Marketing')),
('Social Media Manager', (SELECT id FROM departments WHERE name = 'Social Media Marketing')),
('Community Manager', (SELECT id FROM departments WHERE name = 'Social Media Marketing')),
('Content Creator', (SELECT id FROM departments WHERE name = 'Social Media Marketing')),
('Influencer Marketing Specialist', (SELECT id FROM departments WHERE name = 'Social Media Marketing')),

-- Product Marketing
('Product Marketing Manager', (SELECT id FROM departments WHERE name = 'Product Marketing')),
('Go-to-Market Specialist', (SELECT id FROM departments WHERE name = 'Product Marketing')),
('Product Marketing Executive', (SELECT id FROM departments WHERE name = 'Product Marketing')),
('Market Research Analyst', (SELECT id FROM departments WHERE name = 'Product Marketing')),
('Product Positioning Specialist', (SELECT id FROM departments WHERE name = 'Product Marketing')),

-- Public Relations
('Public Relations Executive', (SELECT id FROM departments WHERE name = 'Public Relations')),
('PR Manager', (SELECT id FROM departments WHERE name = 'Public Relations')),
('Media Relations Specialist', (SELECT id FROM departments WHERE name = 'Public Relations')),
('Corporate Affairs Executive', (SELECT id FROM departments WHERE name = 'Public Relations')),
('Press Coordinator', (SELECT id FROM departments WHERE name = 'Public Relations')),

-- Communications
('Communications Manager', (SELECT id FROM departments WHERE name = 'Communications')),
('Corporate Communications Executive', (SELECT id FROM departments WHERE name = 'Communications')),
('Internal Communications Specialist', (SELECT id FROM departments WHERE name = 'Communications')),
('Communications Coordinator', (SELECT id FROM departments WHERE name = 'Communications')),
('Content Communications Specialist', (SELECT id FROM departments WHERE name = 'Communications')),

-- Human Resources
('HR Manager', (SELECT id FROM departments WHERE name = 'Human Resources')),
('HR Executive', (SELECT id FROM departments WHERE name = 'Human Resources')),
('HR Generalist', (SELECT id FROM departments WHERE name = 'Human Resources')),
('HR Business Partner', (SELECT id FROM departments WHERE name = 'Human Resources')),
('People Operations Specialist', (SELECT id FROM departments WHERE name = 'Human Resources')),

-- HR Administration
('HR Administrator', (SELECT id FROM departments WHERE name = 'HR Administration')),
('HR Coordinator', (SELECT id FROM departments WHERE name = 'HR Administration')),
('Personnel Administrator', (SELECT id FROM departments WHERE name = 'HR Administration')),
('HR Operations Executive', (SELECT id FROM departments WHERE name = 'HR Administration')),
('Employee Records Specialist', (SELECT id FROM departments WHERE name = 'HR Administration')),

-- Talent Acquisition
('Talent Acquisition Specialist', (SELECT id FROM departments WHERE name = 'Talent Acquisition')),
('Talent Acquisition Executive', (SELECT id FROM departments WHERE name = 'Talent Acquisition')),
('Talent Acquisition Manager', (SELECT id FROM departments WHERE name = 'Talent Acquisition')),
('Sourcing Specialist', (SELECT id FROM departments WHERE name = 'Talent Acquisition')),
('Candidate Experience Coordinator', (SELECT id FROM departments WHERE name = 'Talent Acquisition')),

-- Recruitment
('Recruiter', (SELECT id FROM departments WHERE name = 'Recruitment')),
('Recruitment Executive', (SELECT id FROM departments WHERE name = 'Recruitment')),
('Recruitment Consultant', (SELECT id FROM departments WHERE name = 'Recruitment')),
('Technical Recruiter', (SELECT id FROM departments WHERE name = 'Recruitment')),
('Senior Recruiter', (SELECT id FROM departments WHERE name = 'Recruitment')),

-- Learning & Development
('Learning and Development Specialist', (SELECT id FROM departments WHERE name = 'Learning & Development')),
('Training Manager', (SELECT id FROM departments WHERE name = 'Learning & Development')),
('Instructional Designer', (SELECT id FROM departments WHERE name = 'Learning & Development')),
('Corporate Trainer', (SELECT id FROM departments WHERE name = 'Learning & Development')),
('Training Coordinator', (SELECT id FROM departments WHERE name = 'Learning & Development')),

-- Employee Relations
('Employee Relations Specialist', (SELECT id FROM departments WHERE name = 'Employee Relations')),
('Employee Engagement Manager', (SELECT id FROM departments WHERE name = 'Employee Relations')),
('Labor Relations Officer', (SELECT id FROM departments WHERE name = 'Employee Relations')),
('HR Relations Executive', (SELECT id FROM departments WHERE name = 'Employee Relations')),
('Conflict Resolution Specialist', (SELECT id FROM departments WHERE name = 'Employee Relations')),

-- Compensation & Benefits
('Compensation and Benefits Analyst', (SELECT id FROM departments WHERE name = 'Compensation & Benefits')),
('Rewards Specialist', (SELECT id FROM departments WHERE name = 'Compensation & Benefits')),
('Benefits Administrator', (SELECT id FROM departments WHERE name = 'Compensation & Benefits')),
('Compensation Manager', (SELECT id FROM departments WHERE name = 'Compensation & Benefits')),
('Total Rewards Manager', (SELECT id FROM departments WHERE name = 'Compensation & Benefits')),

-- Payroll
('Payroll Executive', (SELECT id FROM departments WHERE name = 'Payroll')),
('Payroll Specialist', (SELECT id FROM departments WHERE name = 'Payroll')),
('Payroll Manager', (SELECT id FROM departments WHERE name = 'Payroll')),
('Compensation Processor', (SELECT id FROM departments WHERE name = 'Payroll')),
('Salary Administrator', (SELECT id FROM departments WHERE name = 'Payroll')),

-- Operations
('Operations Manager', (SELECT id FROM departments WHERE name = 'Operations')),
('Operations Executive', (SELECT id FROM departments WHERE name = 'Operations')),
('Business Operations Analyst', (SELECT id FROM departments WHERE name = 'Operations')),
('Operations Coordinator', (SELECT id FROM departments WHERE name = 'Operations')),
('Operations Supervisor', (SELECT id FROM departments WHERE name = 'Operations')),

-- Process Management
('Process Manager', (SELECT id FROM departments WHERE name = 'Process Management')),
('Business Process Analyst', (SELECT id FROM departments WHERE name = 'Process Management')),
('Process Improvement Specialist', (SELECT id FROM departments WHERE name = 'Process Management')),
('Lean Consultant', (SELECT id FROM departments WHERE name = 'Process Management')),
('Process Coordinator', (SELECT id FROM departments WHERE name = 'Process Management')),

-- Service Delivery
('Service Delivery Manager', (SELECT id FROM departments WHERE name = 'Service Delivery')),
('Service Delivery Executive', (SELECT id FROM departments WHERE name = 'Service Delivery')),
('Client Delivery Manager', (SELECT id FROM departments WHERE name = 'Service Delivery')),
('Delivery Coordinator', (SELECT id FROM departments WHERE name = 'Service Delivery')),
('Service Operations Analyst', (SELECT id FROM departments WHERE name = 'Service Delivery')),

-- Resource Management
('Resource Manager', (SELECT id FROM departments WHERE name = 'Resource Management')),
('Workforce Planner', (SELECT id FROM departments WHERE name = 'Resource Management')),
('Capacity Planning Analyst', (SELECT id FROM departments WHERE name = 'Resource Management')),
('Staffing Coordinator', (SELECT id FROM departments WHERE name = 'Resource Management')),
('Resource Allocation Specialist', (SELECT id FROM departments WHERE name = 'Resource Management')),

-- Administration
('Administrative Officer', (SELECT id FROM departments WHERE name = 'Administration')),
('Office Administrator', (SELECT id FROM departments WHERE name = 'Administration')),
('Administrative Assistant', (SELECT id FROM departments WHERE name = 'Administration')),
('Facility Coordinator', (SELECT id FROM departments WHERE name = 'Administration')),
('Office Manager', (SELECT id FROM departments WHERE name = 'Administration')),

-- Customer Support
('Customer Support Executive', (SELECT id FROM departments WHERE name = 'Customer Support')),
('Customer Service Representative', (SELECT id FROM departments WHERE name = 'Customer Support')),
('Support Associate', (SELECT id FROM departments WHERE name = 'Customer Support')),
('Customer Care Specialist', (SELECT id FROM departments WHERE name = 'Customer Support')),
('Service Desk Representative', (SELECT id FROM departments WHERE name = 'Customer Support')),

-- Customer Success
('Customer Success Manager', (SELECT id FROM departments WHERE name = 'Customer Success')),
('Customer Success Executive', (SELECT id FROM departments WHERE name = 'Customer Success')),
('Client Success Specialist', (SELECT id FROM departments WHERE name = 'Customer Success')),
('Onboarding Specialist', (SELECT id FROM departments WHERE name = 'Customer Success')),
('Retention Manager', (SELECT id FROM departments WHERE name = 'Customer Success')),

-- Call Center
('Call Center Executive', (SELECT id FROM departments WHERE name = 'Call Center')),
('Call Center Agent', (SELECT id FROM departments WHERE name = 'Call Center')),
('Telecaller', (SELECT id FROM departments WHERE name = 'Call Center')),
('Contact Center Supervisor', (SELECT id FROM departments WHERE name = 'Call Center')),
('Voice Process Associate', (SELECT id FROM departments WHERE name = 'Call Center')),

-- Help Desk
('Help Desk Technician', (SELECT id FROM departments WHERE name = 'Help Desk')),
('Service Desk Analyst', (SELECT id FROM departments WHERE name = 'Help Desk')),
('Help Desk Support Engineer', (SELECT id FROM departments WHERE name = 'Help Desk')),
('IT Help Desk Specialist', (SELECT id FROM departments WHERE name = 'Help Desk')),
('Support Desk Coordinator', (SELECT id FROM departments WHERE name = 'Help Desk')),

-- Finance
('Finance Manager', (SELECT id FROM departments WHERE name = 'Finance')),
('Financial Analyst', (SELECT id FROM departments WHERE name = 'Finance')),
('Finance Executive', (SELECT id FROM departments WHERE name = 'Finance')),
('Budget Analyst', (SELECT id FROM departments WHERE name = 'Finance')),
('Finance Controller', (SELECT id FROM departments WHERE name = 'Finance')),

-- Accounting
('Accountant', (SELECT id FROM departments WHERE name = 'Accounting')),
('Senior Accountant', (SELECT id FROM departments WHERE name = 'Accounting')),
('Accounting Executive', (SELECT id FROM departments WHERE name = 'Accounting')),
('General Ledger Accountant', (SELECT id FROM departments WHERE name = 'Accounting')),
('Accounting Manager', (SELECT id FROM departments WHERE name = 'Accounting')),

-- Accounts Payable
('Accounts Payable Executive', (SELECT id FROM departments WHERE name = 'Accounts Payable')),
('AP Specialist', (SELECT id FROM departments WHERE name = 'Accounts Payable')),
('Invoice Processing Executive', (SELECT id FROM departments WHERE name = 'Accounts Payable')),
('Vendor Payments Coordinator', (SELECT id FROM departments WHERE name = 'Accounts Payable')),
('Accounts Payable Manager', (SELECT id FROM departments WHERE name = 'Accounts Payable')),

-- Accounts Receivable
('Accounts Receivable Executive', (SELECT id FROM departments WHERE name = 'Accounts Receivable')),
('AR Specialist', (SELECT id FROM departments WHERE name = 'Accounts Receivable')),
('Billing Executive', (SELECT id FROM departments WHERE name = 'Accounts Receivable')),
('Collections Analyst', (SELECT id FROM departments WHERE name = 'Accounts Receivable')),
('Accounts Receivable Manager', (SELECT id FROM departments WHERE name = 'Accounts Receivable')),

-- Treasury
('Treasury Analyst', (SELECT id FROM departments WHERE name = 'Treasury')),
('Cash Manager', (SELECT id FROM departments WHERE name = 'Treasury')),
('Treasury Executive', (SELECT id FROM departments WHERE name = 'Treasury')),
('Liquidity Manager', (SELECT id FROM departments WHERE name = 'Treasury')),
('Treasurer', (SELECT id FROM departments WHERE name = 'Treasury')),

-- Taxation
('Tax Analyst', (SELECT id FROM departments WHERE name = 'Taxation')),
('Tax Consultant', (SELECT id FROM departments WHERE name = 'Taxation')),
('Tax Manager', (SELECT id FROM departments WHERE name = 'Taxation')),
('GST Specialist', (SELECT id FROM departments WHERE name = 'Taxation')),
('Corporate Tax Executive', (SELECT id FROM departments WHERE name = 'Taxation')),

-- Audit
('Internal Auditor', (SELECT id FROM departments WHERE name = 'Audit')),
('Audit Executive', (SELECT id FROM departments WHERE name = 'Audit')),
('Audit Manager', (SELECT id FROM departments WHERE name = 'Audit')),
('Compliance Auditor', (SELECT id FROM departments WHERE name = 'Audit')),
('Risk Auditor', (SELECT id FROM departments WHERE name = 'Audit')),

-- Financial Planning & Analysis
('FP&A Analyst', (SELECT id FROM departments WHERE name = 'Financial Planning & Analysis')),
('Financial Planning Analyst', (SELECT id FROM departments WHERE name = 'Financial Planning & Analysis')),
('Budgeting Manager', (SELECT id FROM departments WHERE name = 'Financial Planning & Analysis')),
('Forecasting Analyst', (SELECT id FROM departments WHERE name = 'Financial Planning & Analysis')),
('FP&A Manager', (SELECT id FROM departments WHERE name = 'Financial Planning & Analysis')),

-- Legal
('Legal Counsel', (SELECT id FROM departments WHERE name = 'Legal')),
('Legal Executive', (SELECT id FROM departments WHERE name = 'Legal')),
('Corporate Lawyer', (SELECT id FROM departments WHERE name = 'Legal')),
('Contract Specialist', (SELECT id FROM departments WHERE name = 'Legal')),
('Legal Manager', (SELECT id FROM departments WHERE name = 'Legal'));

INSERT INTO department_jobs (name, department_id)
VALUES
-- Product Management
('Product Manager', (SELECT id FROM departments WHERE name = 'Product Management')),
('Associate Product Manager', (SELECT id FROM departments WHERE name = 'Product Management')),
('Technical Product Manager', (SELECT id FROM departments WHERE name = 'Product Management')),
('Senior Product Manager', (SELECT id FROM departments WHERE name = 'Product Management')),
('Product Owner', (SELECT id FROM departments WHERE name = 'Product Management')),

-- Product Strategy
('Product Strategist', (SELECT id FROM departments WHERE name = 'Product Strategy')),
('Product Strategy Manager', (SELECT id FROM departments WHERE name = 'Product Strategy')),
('Market Strategy Analyst', (SELECT id FROM departments WHERE name = 'Product Strategy')),
('Go-to-Market Strategist', (SELECT id FROM departments WHERE name = 'Product Strategy')),
('Portfolio Strategy Manager', (SELECT id FROM departments WHERE name = 'Product Strategy')),

-- Product Operations
('Product Operations Manager', (SELECT id FROM departments WHERE name = 'Product Operations')),
('Product Operations Specialist', (SELECT id FROM departments WHERE name = 'Product Operations')),
('Product Analyst', (SELECT id FROM departments WHERE name = 'Product Operations')),
('Operations Program Manager', (SELECT id FROM departments WHERE name = 'Product Operations')),
('Product Coordinator', (SELECT id FROM departments WHERE name = 'Product Operations')),

-- Nursing
('Registered Nurse', (SELECT id FROM departments WHERE name = 'Nursing')),
('Staff Nurse', (SELECT id FROM departments WHERE name = 'Nursing')),
('Nurse Practitioner', (SELECT id FROM departments WHERE name = 'Nursing')),
('Charge Nurse', (SELECT id FROM departments WHERE name = 'Nursing')),
('Clinical Nurse Specialist', (SELECT id FROM departments WHERE name = 'Nursing')),

-- Medical Administration
('Medical Administrator', (SELECT id FROM departments WHERE name = 'Medical Administration')),
('Hospital Administrator', (SELECT id FROM departments WHERE name = 'Medical Administration')),
('Healthcare Operations Manager', (SELECT id FROM departments WHERE name = 'Medical Administration')),
('Medical Office Manager', (SELECT id FROM departments WHERE name = 'Medical Administration')),
('Patient Services Manager', (SELECT id FROM departments WHERE name = 'Medical Administration')),

-- Laboratory
('Lab Technician', (SELECT id FROM departments WHERE name = 'Laboratory')),
('Medical Laboratory Scientist', (SELECT id FROM departments WHERE name = 'Laboratory')),
('Pathology Technician', (SELECT id FROM departments WHERE name = 'Laboratory')),
('Lab Supervisor', (SELECT id FROM departments WHERE name = 'Laboratory')),
('Clinical Laboratory Technologist', (SELECT id FROM departments WHERE name = 'Laboratory')),

-- Pharmacy
('Pharmacist', (SELECT id FROM departments WHERE name = 'Pharmacy')),
('Clinical Pharmacist', (SELECT id FROM departments WHERE name = 'Pharmacy')),
('Pharmacy Technician', (SELECT id FROM departments WHERE name = 'Pharmacy')),
('Pharmacy Manager', (SELECT id FROM departments WHERE name = 'Pharmacy')),
('Retail Pharmacist', (SELECT id FROM departments WHERE name = 'Pharmacy')),

-- Clinical Operations
('Clinical Operations Manager', (SELECT id FROM departments WHERE name = 'Clinical Operations')),
('Clinical Coordinator', (SELECT id FROM departments WHERE name = 'Clinical Operations')),
('Clinical Research Associate', (SELECT id FROM departments WHERE name = 'Clinical Operations')),
('Patient Care Coordinator', (SELECT id FROM departments WHERE name = 'Clinical Operations')),
('Clinical Program Manager', (SELECT id FROM departments WHERE name = 'Clinical Operations')),

-- Academic Affairs
('Academic Affairs Manager', (SELECT id FROM departments WHERE name = 'Academic Affairs')),
('Academic Coordinator', (SELECT id FROM departments WHERE name = 'Academic Affairs')),
('Curriculum Specialist', (SELECT id FROM departments WHERE name = 'Academic Affairs')),
('Academic Dean Assistant', (SELECT id FROM departments WHERE name = 'Academic Affairs')),
('Education Program Manager', (SELECT id FROM departments WHERE name = 'Academic Affairs')),

-- Admissions
('Admissions Counselor', (SELECT id FROM departments WHERE name = 'Admissions')),
('Admissions Officer', (SELECT id FROM departments WHERE name = 'Admissions')),
('Enrollment Specialist', (SELECT id FROM departments WHERE name = 'Admissions')),
('Admissions Coordinator', (SELECT id FROM departments WHERE name = 'Admissions')),
('Student Recruitment Officer', (SELECT id FROM departments WHERE name = 'Admissions')),

-- Student Services
('Student Services Coordinator', (SELECT id FROM departments WHERE name = 'Student Services')),
('Academic Advisor', (SELECT id FROM departments WHERE name = 'Student Services')),
('Student Support Specialist', (SELECT id FROM departments WHERE name = 'Student Services')),
('Career Counselor', (SELECT id FROM departments WHERE name = 'Student Services')),
('Student Affairs Officer', (SELECT id FROM departments WHERE name = 'Student Services')),

-- Faculty Administration
('Faculty Administrator', (SELECT id FROM departments WHERE name = 'Faculty Administration')),
('Faculty Coordinator', (SELECT id FROM departments WHERE name = 'Faculty Administration')),
('Academic HR Specialist', (SELECT id FROM departments WHERE name = 'Faculty Administration')),
('Faculty Affairs Manager', (SELECT id FROM departments WHERE name = 'Faculty Administration')),
('Department Administrator', (SELECT id FROM departments WHERE name = 'Faculty Administration')),

-- Underwriting
('Underwriter', (SELECT id FROM departments WHERE name = 'Underwriting')),
('Senior Underwriter', (SELECT id FROM departments WHERE name = 'Underwriting')),
('Insurance Risk Analyst', (SELECT id FROM departments WHERE name = 'Underwriting')),
('Loan Underwriter', (SELECT id FROM departments WHERE name = 'Underwriting')),
('Underwriting Manager', (SELECT id FROM departments WHERE name = 'Underwriting')),

-- Claims
('Claims Adjuster', (SELECT id FROM departments WHERE name = 'Claims')),
('Claims Analyst', (SELECT id FROM departments WHERE name = 'Claims')),
('Claims Processor', (SELECT id FROM departments WHERE name = 'Claims')),
('Claims Manager', (SELECT id FROM departments WHERE name = 'Claims')),
('Insurance Claims Specialist', (SELECT id FROM departments WHERE name = 'Claims')),

-- Loan Processing
('Loan Processor', (SELECT id FROM departments WHERE name = 'Loan Processing')),
('Mortgage Processor', (SELECT id FROM departments WHERE name = 'Loan Processing')),
('Loan Documentation Specialist', (SELECT id FROM departments WHERE name = 'Loan Processing')),
('Loan Operations Executive', (SELECT id FROM departments WHERE name = 'Loan Processing')),
('Senior Loan Processor', (SELECT id FROM departments WHERE name = 'Loan Processing')),

-- Credit Analysis
('Credit Analyst', (SELECT id FROM departments WHERE name = 'Credit Analysis')),
('Senior Credit Analyst', (SELECT id FROM departments WHERE name = 'Credit Analysis')),
('Commercial Credit Analyst', (SELECT id FROM departments WHERE name = 'Credit Analysis')),
('Risk Assessment Analyst', (SELECT id FROM departments WHERE name = 'Credit Analysis')),
('Credit Manager', (SELECT id FROM departments WHERE name = 'Credit Analysis')),

-- Civil Engineering
('Civil Engineer', (SELECT id FROM departments WHERE name = 'Civil Engineering')),
('Structural Engineer', (SELECT id FROM departments WHERE name = 'Civil Engineering')),
('Design Engineer', (SELECT id FROM departments WHERE name = 'Civil Engineering')),
('Construction Engineer', (SELECT id FROM departments WHERE name = 'Civil Engineering')),
('Senior Civil Engineer', (SELECT id FROM departments WHERE name = 'Civil Engineering')),

-- Site Operations
('Site Engineer', (SELECT id FROM departments WHERE name = 'Site Operations')),
('Site Supervisor', (SELECT id FROM departments WHERE name = 'Site Operations')),
('Construction Supervisor', (SELECT id FROM departments WHERE name = 'Site Operations')),
('Field Operations Manager', (SELECT id FROM departments WHERE name = 'Site Operations')),
('Site Coordinator', (SELECT id FROM departments WHERE name = 'Site Operations')),

-- Safety
('Safety Officer', (SELECT id FROM departments WHERE name = 'Safety')),
('Safety Engineer', (SELECT id FROM departments WHERE name = 'Safety')),
('HSE Coordinator', (SELECT id FROM departments WHERE name = 'Safety')),
('Occupational Safety Specialist', (SELECT id FROM departments WHERE name = 'Safety')),
('Safety Manager', (SELECT id FROM departments WHERE name = 'Safety')),

-- Project Management
('Project Manager', (SELECT id FROM departments WHERE name = 'Project Management')),
('Program Manager', (SELECT id FROM departments WHERE name = 'Project Management')),
('Project Coordinator', (SELECT id FROM departments WHERE name = 'Project Management')),
('PMO Analyst', (SELECT id FROM departments WHERE name = 'Project Management')),
('Scrum Master', (SELECT id FROM departments WHERE name = 'Project Management')),

-- Physical Security
('Security Officer', (SELECT id FROM departments WHERE name = 'Physical Security')),
('Security Supervisor', (SELECT id FROM departments WHERE name = 'Physical Security')),
('Loss Prevention Manager', (SELECT id FROM departments WHERE name = 'Physical Security')),
('Security Operations Manager', (SELECT id FROM departments WHERE name = 'Physical Security')),
('Access Control Specialist', (SELECT id FROM departments WHERE name = 'Physical Security')),

-- Information Security
('Information Security Analyst', (SELECT id FROM departments WHERE name = 'Information Security')),
('Security Engineer', (SELECT id FROM departments WHERE name = 'Information Security')),
('SOC Analyst', (SELECT id FROM departments WHERE name = 'Information Security')),
('Security Architect', (SELECT id FROM departments WHERE name = 'Information Security')),
('Information Security Manager', (SELECT id FROM departments WHERE name = 'Information Security')),

-- Corporate Social Responsibility
('CSR Executive', (SELECT id FROM departments WHERE name = 'Corporate Social Responsibility')),
('CSR Manager', (SELECT id FROM departments WHERE name = 'Corporate Social Responsibility')),
('Community Relations Specialist', (SELECT id FROM departments WHERE name = 'Corporate Social Responsibility')),
('Social Impact Analyst', (SELECT id FROM departments WHERE name = 'Corporate Social Responsibility')),
('Sustainability Program Coordinator', (SELECT id FROM departments WHERE name = 'Corporate Social Responsibility')),

-- Environmental Health & Safety
('EHS Officer', (SELECT id FROM departments WHERE name = 'Environmental Health & Safety')),
('EHS Manager', (SELECT id FROM departments WHERE name = 'Environmental Health & Safety')),
('Environmental Specialist', (SELECT id FROM departments WHERE name = 'Environmental Health & Safety')),
('Health and Safety Coordinator', (SELECT id FROM departments WHERE name = 'Environmental Health & Safety')),
('Compliance Safety Officer', (SELECT id FROM departments WHERE name = 'Environmental Health & Safety')),

-- Sustainability
('Sustainability Analyst', (SELECT id FROM departments WHERE name = 'Sustainability')),
('Sustainability Manager', (SELECT id FROM departments WHERE name = 'Sustainability')),
('ESG Specialist', (SELECT id FROM departments WHERE name = 'Sustainability')),
('Environmental Consultant', (SELECT id FROM departments WHERE name = 'Sustainability')),
('Carbon Accounting Analyst', (SELECT id FROM departments WHERE name = 'Sustainability')),

-- Facilities
('Facilities Manager', (SELECT id FROM departments WHERE name = 'Facilities')),
('Facilities Coordinator', (SELECT id FROM departments WHERE name = 'Facilities')),
('Building Maintenance Supervisor', (SELECT id FROM departments WHERE name = 'Facilities')),
('Facilities Engineer', (SELECT id FROM departments WHERE name = 'Facilities')),
('Property Manager', (SELECT id FROM departments WHERE name = 'Facilities')),

-- Housekeeping
('Housekeeping Supervisor', (SELECT id FROM departments WHERE name = 'Housekeeping')),
('Housekeeping Manager', (SELECT id FROM departments WHERE name = 'Housekeeping')),
('Room Attendant', (SELECT id FROM departments WHERE name = 'Housekeeping')),
('Cleaning Staff', (SELECT id FROM departments WHERE name = 'Housekeeping')),
('Janitorial Supervisor', (SELECT id FROM departments WHERE name = 'Housekeeping')),

-- Technical Writing
('Technical Writer', (SELECT id FROM departments WHERE name = 'Technical Writing')),
('Documentation Specialist', (SELECT id FROM departments WHERE name = 'Technical Writing')),
('API Documentation Writer', (SELECT id FROM departments WHERE name = 'Technical Writing')),
('Content Developer', (SELECT id FROM departments WHERE name = 'Technical Writing')),
('Technical Editor', (SELECT id FROM departments WHERE name = 'Technical Writing')),

-- Documentation
('Documentation Executive', (SELECT id FROM departments WHERE name = 'Documentation')),
('Document Controller', (SELECT id FROM departments WHERE name = 'Documentation')),
('Records Management Specialist', (SELECT id FROM departments WHERE name = 'Documentation')),
('Document Coordinator', (SELECT id FROM departments WHERE name = 'Documentation')),
('Documentation Manager', (SELECT id FROM departments WHERE name = 'Documentation')),

-- Knowledge Management
('Knowledge Manager', (SELECT id FROM departments WHERE name = 'Knowledge Management')),
('Knowledge Analyst', (SELECT id FROM departments WHERE name = 'Knowledge Management')),
('Content Librarian', (SELECT id FROM departments WHERE name = 'Knowledge Management')),
('Knowledge Base Administrator', (SELECT id FROM departments WHERE name = 'Knowledge Management')),
('Information Architect', (SELECT id FROM departments WHERE name = 'Knowledge Management'));

INSERT INTO department_jobs (name, department_id)
VALUES
-- Compliance
('Compliance Officer', (SELECT id FROM departments WHERE name = 'Compliance')),
('Compliance Analyst', (SELECT id FROM departments WHERE name = 'Compliance')),
('Regulatory Affairs Specialist', (SELECT id FROM departments WHERE name = 'Compliance')),
('Compliance Manager', (SELECT id FROM departments WHERE name = 'Compliance')),
('Governance Risk and Compliance (GRC) Analyst', (SELECT id FROM departments WHERE name = 'Compliance')),

-- Risk Management
('Risk Analyst', (SELECT id FROM departments WHERE name = 'Risk Management')),
('Risk Manager', (SELECT id FROM departments WHERE name = 'Risk Management')),
('Enterprise Risk Specialist', (SELECT id FROM departments WHERE name = 'Risk Management')),
('Operational Risk Analyst', (SELECT id FROM departments WHERE name = 'Risk Management')),
('Credit Risk Manager', (SELECT id FROM departments WHERE name = 'Risk Management')),

-- Corporate Governance
('Corporate Governance Officer', (SELECT id FROM departments WHERE name = 'Corporate Governance')),
('Governance Analyst', (SELECT id FROM departments WHERE name = 'Corporate Governance')),
('Board Governance Specialist', (SELECT id FROM departments WHERE name = 'Corporate Governance')),
('Corporate Secretary', (SELECT id FROM departments WHERE name = 'Corporate Governance')),
('Governance Manager', (SELECT id FROM departments WHERE name = 'Corporate Governance')),

-- Procurement
('Procurement Executive', (SELECT id FROM departments WHERE name = 'Procurement')),
('Procurement Specialist', (SELECT id FROM departments WHERE name = 'Procurement')),
('Procurement Manager', (SELECT id FROM departments WHERE name = 'Procurement')),
('Strategic Sourcing Specialist', (SELECT id FROM departments WHERE name = 'Procurement')),
('Category Manager', (SELECT id FROM departments WHERE name = 'Procurement')),

-- Purchasing
('Purchasing Officer', (SELECT id FROM departments WHERE name = 'Purchasing')),
('Buyer', (SELECT id FROM departments WHERE name = 'Purchasing')),
('Purchasing Executive', (SELECT id FROM departments WHERE name = 'Purchasing')),
('Senior Buyer', (SELECT id FROM departments WHERE name = 'Purchasing')),
('Purchasing Manager', (SELECT id FROM departments WHERE name = 'Purchasing')),

-- Supply Chain
('Supply Chain Analyst', (SELECT id FROM departments WHERE name = 'Supply Chain')),
('Supply Chain Manager', (SELECT id FROM departments WHERE name = 'Supply Chain')),
('Supply Planner', (SELECT id FROM departments WHERE name = 'Supply Chain')),
('Demand Planner', (SELECT id FROM departments WHERE name = 'Supply Chain')),
('Supply Chain Coordinator', (SELECT id FROM departments WHERE name = 'Supply Chain')),

-- Logistics
('Logistics Coordinator', (SELECT id FROM departments WHERE name = 'Logistics')),
('Logistics Executive', (SELECT id FROM departments WHERE name = 'Logistics')),
('Transportation Manager', (SELECT id FROM departments WHERE name = 'Logistics')),
('Freight Specialist', (SELECT id FROM departments WHERE name = 'Logistics')),
('Logistics Manager', (SELECT id FROM departments WHERE name = 'Logistics')),

-- Inventory Management
('Inventory Analyst', (SELECT id FROM departments WHERE name = 'Inventory Management')),
('Inventory Controller', (SELECT id FROM departments WHERE name = 'Inventory Management')),
('Stock Manager', (SELECT id FROM departments WHERE name = 'Inventory Management')),
('Inventory Coordinator', (SELECT id FROM departments WHERE name = 'Inventory Management')),
('Materials Planner', (SELECT id FROM departments WHERE name = 'Inventory Management')),

-- Vendor Management
('Vendor Manager', (SELECT id FROM departments WHERE name = 'Vendor Management')),
('Supplier Relationship Manager', (SELECT id FROM departments WHERE name = 'Vendor Management')),
('Vendor Coordinator', (SELECT id FROM departments WHERE name = 'Vendor Management')),
('Supplier Performance Analyst', (SELECT id FROM departments WHERE name = 'Vendor Management')),
('Vendor Compliance Specialist', (SELECT id FROM departments WHERE name = 'Vendor Management')),

-- Warehouse
('Warehouse Supervisor', (SELECT id FROM departments WHERE name = 'Warehouse')),
('Warehouse Manager', (SELECT id FROM departments WHERE name = 'Warehouse')),
('Store Keeper', (SELECT id FROM departments WHERE name = 'Warehouse')),
('Warehouse Associate', (SELECT id FROM departments WHERE name = 'Warehouse')),
('Inventory Warehouse Coordinator', (SELECT id FROM departments WHERE name = 'Warehouse')),

-- Production
('Production Supervisor', (SELECT id FROM departments WHERE name = 'Production')),
('Production Manager', (SELECT id FROM departments WHERE name = 'Production')),
('Production Engineer', (SELECT id FROM departments WHERE name = 'Production')),
('Shift Supervisor', (SELECT id FROM departments WHERE name = 'Production')),
('Production Planner', (SELECT id FROM departments WHERE name = 'Production')),

-- Manufacturing
('Manufacturing Engineer', (SELECT id FROM departments WHERE name = 'Manufacturing')),
('Manufacturing Supervisor', (SELECT id FROM departments WHERE name = 'Manufacturing')),
('Manufacturing Manager', (SELECT id FROM departments WHERE name = 'Manufacturing')),
('Process Engineer', (SELECT id FROM departments WHERE name = 'Manufacturing')),
('Assembly Technician', (SELECT id FROM departments WHERE name = 'Manufacturing')),

-- Quality Control
('Quality Control Inspector', (SELECT id FROM departments WHERE name = 'Quality Control')),
('QC Analyst', (SELECT id FROM departments WHERE name = 'Quality Control')),
('Quality Engineer', (SELECT id FROM departments WHERE name = 'Quality Control')),
('Quality Control Manager', (SELECT id FROM departments WHERE name = 'Quality Control')),
('Testing Technician', (SELECT id FROM departments WHERE name = 'Quality Control')),

-- Maintenance
('Maintenance Technician', (SELECT id FROM departments WHERE name = 'Maintenance')),
('Maintenance Engineer', (SELECT id FROM departments WHERE name = 'Maintenance')),
('Maintenance Supervisor', (SELECT id FROM departments WHERE name = 'Maintenance')),
('Facility Maintenance Manager', (SELECT id FROM departments WHERE name = 'Maintenance')),
('Equipment Technician', (SELECT id FROM departments WHERE name = 'Maintenance')),

-- Industrial Engineering
('Industrial Engineer', (SELECT id FROM departments WHERE name = 'Industrial Engineering')),
('Process Improvement Engineer', (SELECT id FROM departments WHERE name = 'Industrial Engineering')),
('Lean Manufacturing Engineer', (SELECT id FROM departments WHERE name = 'Industrial Engineering')),
('Operations Excellence Engineer', (SELECT id FROM departments WHERE name = 'Industrial Engineering')),
('Methods Engineer', (SELECT id FROM departments WHERE name = 'Industrial Engineering')),

-- Research and Development (R&D)
('Research Scientist', (SELECT id FROM departments WHERE name = 'Research and Development (R&D)')),
('R&D Engineer', (SELECT id FROM departments WHERE name = 'Research and Development (R&D)')),
('Product Research Analyst', (SELECT id FROM departments WHERE name = 'Research and Development (R&D)')),
('Innovation Researcher', (SELECT id FROM departments WHERE name = 'Research and Development (R&D)')),
('R&D Manager', (SELECT id FROM departments WHERE name = 'Research and Development (R&D)')),

-- Innovation Lab
('Innovation Specialist', (SELECT id FROM departments WHERE name = 'Innovation Lab')),
('Innovation Manager', (SELECT id FROM departments WHERE name = 'Innovation Lab')),
('Prototype Engineer', (SELECT id FROM departments WHERE name = 'Innovation Lab')),
('Research Innovator', (SELECT id FROM departments WHERE name = 'Innovation Lab')),
('Innovation Program Lead', (SELECT id FROM departments WHERE name = 'Innovation Lab')),

-- Product Engineering
('Product Engineer', (SELECT id FROM departments WHERE name = 'Product Engineering')),
('Design Engineer', (SELECT id FROM departments WHERE name = 'Product Engineering')),
('Product Development Engineer', (SELECT id FROM departments WHERE name = 'Product Engineering')),
('Mechanical Design Engineer', (SELECT id FROM departments WHERE name = 'Product Engineering')),
('Product Engineering Manager', (SELECT id FROM departments WHERE name = 'Product Engineering')),

-- Data Science
('Data Scientist', (SELECT id FROM departments WHERE name = 'Data Science')),
('Senior Data Scientist', (SELECT id FROM departments WHERE name = 'Data Science')),
('Applied Scientist', (SELECT id FROM departments WHERE name = 'Data Science')),
('Research Data Scientist', (SELECT id FROM departments WHERE name = 'Data Science')),
('Machine Learning Scientist', (SELECT id FROM departments WHERE name = 'Data Science')),

-- Analytics
('Business Analyst', (SELECT id FROM departments WHERE name = 'Analytics')),
('Data Analyst', (SELECT id FROM departments WHERE name = 'Analytics')),
('Analytics Consultant', (SELECT id FROM departments WHERE name = 'Analytics')),
('Insights Analyst', (SELECT id FROM departments WHERE name = 'Analytics')),
('Analytics Manager', (SELECT id FROM departments WHERE name = 'Analytics')),

-- Reporting
('Reporting Analyst', (SELECT id FROM departments WHERE name = 'Reporting')),
('MIS Executive', (SELECT id FROM departments WHERE name = 'Reporting')),
('Report Developer', (SELECT id FROM departments WHERE name = 'Reporting')),
('Dashboard Analyst', (SELECT id FROM departments WHERE name = 'Reporting')),
('Reporting Manager', (SELECT id FROM departments WHERE name = 'Reporting')),

-- Data Governance
('Data Governance Analyst', (SELECT id FROM departments WHERE name = 'Data Governance')),
('Data Steward', (SELECT id FROM departments WHERE name = 'Data Governance')),
('Master Data Specialist', (SELECT id FROM departments WHERE name = 'Data Governance')),
('Data Quality Manager', (SELECT id FROM departments WHERE name = 'Data Governance')),
('Governance Lead', (SELECT id FROM departments WHERE name = 'Data Governance'));


ALTER TABLE departments
ADD COLUMN IF NOT EXISTS name_hi VARCHAR(255),
ADD COLUMN IF NOT EXISTS name_pa VARCHAR(255);


UPDATE departments
SET
    name_hi = CASE name
        WHEN 'Compliance' THEN 'अनुपालन'
        WHEN 'Risk Management' THEN 'जोखिम प्रबंधन'
        WHEN 'Corporate Governance' THEN 'कॉर्पोरेट प्रशासन'
        WHEN 'Procurement' THEN 'खरीद प्रबंधन'
        WHEN 'Purchasing' THEN 'क्रय'
        WHEN 'Supply Chain' THEN 'आपूर्ति श्रृंखला'
        WHEN 'Logistics' THEN 'लॉजिस्टिक्स'
        WHEN 'Inventory Management' THEN 'इन्वेंटरी प्रबंधन'
        WHEN 'Vendor Management' THEN 'विक्रेता प्रबंधन'
        WHEN 'Warehouse' THEN 'गोदाम'
        WHEN 'Production' THEN 'उत्पादन'
        WHEN 'Manufacturing' THEN 'विनिर्माण'
        WHEN 'Quality Control' THEN 'गुणवत्ता नियंत्रण'
        WHEN 'Maintenance' THEN 'रखरखाव'
        WHEN 'Industrial Engineering' THEN 'औद्योगिक इंजीनियरिंग'
        WHEN 'Research and Development (R&D)' THEN 'अनुसंधान और विकास (आर एंड डी)'
        WHEN 'Innovation Lab' THEN 'नवाचार प्रयोगशाला'
        WHEN 'Product Engineering' THEN 'उत्पाद इंजीनियरिंग'
        WHEN 'Data Science' THEN 'डेटा साइंस'
        WHEN 'Analytics' THEN 'विश्लेषिकी'
        WHEN 'Reporting' THEN 'रिपोर्टिंग'
        WHEN 'Data Governance' THEN 'डेटा गवर्नेंस'
        WHEN 'Product Management' THEN 'उत्पाद प्रबंधन'
        WHEN 'Product Strategy' THEN 'उत्पाद रणनीति'
        WHEN 'Product Operations' THEN 'उत्पाद संचालन'
        WHEN 'Medical Administration' THEN 'चिकित्सा प्रशासन'
        WHEN 'Laboratory' THEN 'प्रयोगशाला'
        WHEN 'Pharmacy' THEN 'फार्मेसी'
        WHEN 'Clinical Operations' THEN 'क्लिनिकल संचालन'
        WHEN 'Academic Affairs' THEN 'शैक्षणिक कार्य'
        WHEN 'Admissions' THEN 'प्रवेश'
        WHEN 'Student Services' THEN 'छात्र सेवाएँ'
        WHEN 'Faculty Administration' THEN 'संकाय प्रशासन'
        WHEN 'Underwriting' THEN 'अंडरराइटिंग'
        WHEN 'Claims' THEN 'दावे'
        WHEN 'Loan Processing' THEN 'ऋण प्रसंस्करण'
        WHEN 'Credit Analysis' THEN 'ऋण विश्लेषण'
        WHEN 'Civil Engineering' THEN 'सिविल इंजीनियरिंग'
        WHEN 'Site Operations' THEN 'साइट संचालन'
        WHEN 'Safety' THEN 'सुरक्षा'
        WHEN 'Project Management' THEN 'परियोजना प्रबंधन'
        WHEN 'Physical Security' THEN 'भौतिक सुरक्षा'
        WHEN 'Information Security' THEN 'सूचना सुरक्षा'
        WHEN 'Corporate Social Responsibility' THEN 'कॉर्पोरेट सामाजिक उत्तरदायित्व'
        WHEN 'Environmental Health & Safety' THEN 'पर्यावरण स्वास्थ्य और सुरक्षा'
        WHEN 'Sustainability' THEN 'स्थिरता'
        WHEN 'Facilities' THEN 'सुविधाएँ'
        WHEN 'Housekeeping' THEN 'गृह व्यवस्था'
        WHEN 'Technical Writing' THEN 'तकनीकी लेखन'
        WHEN 'Documentation' THEN 'दस्तावेज़ीकरण'
        WHEN 'Knowledge Management' THEN 'ज्ञान प्रबंधन'
        ELSE name_hi
    END,
    name_pa = CASE name
        WHEN 'Compliance' THEN 'ਅਨੁਪਾਲਨਾ'
        WHEN 'Risk Management' THEN 'ਜੋਖਿਮ ਪ੍ਰਬੰਧਨ'
        WHEN 'Corporate Governance' THEN 'ਕਾਰਪੋਰੇਟ ਪ੍ਰਸ਼ਾਸਨ'
        WHEN 'Procurement' THEN 'ਖਰੀਦ ਪ੍ਰਬੰਧਨ'
        WHEN 'Purchasing' THEN 'ਖਰੀਦ'
        WHEN 'Supply Chain' THEN 'ਸਪਲਾਈ ਚੇਨ'
        WHEN 'Logistics' THEN 'ਲੋਜਿਸਟਿਕਸ'
        WHEN 'Inventory Management' THEN 'ਇਨਵੈਂਟਰੀ ਪ੍ਰਬੰਧਨ'
        WHEN 'Vendor Management' THEN 'ਵਿਕਰੇਤਾ ਪ੍ਰਬੰਧਨ'
        WHEN 'Warehouse' THEN 'ਗੋਦਾਮ'
        WHEN 'Production' THEN 'ਉਤਪਾਦਨ'
        WHEN 'Manufacturing' THEN 'ਨਿਰਮਾਣ'
        WHEN 'Quality Control' THEN 'ਗੁਣਵੱਤਾ ਨਿਯੰਤਰਣ'
        WHEN 'Maintenance' THEN 'ਰਖ-ਰਖਾਵ'
        WHEN 'Industrial Engineering' THEN 'ਉਦਯੋਗਿਕ ਇੰਜੀਨੀਅਰਿੰਗ'
        WHEN 'Research and Development (R&D)' THEN 'ਖੋਜ ਅਤੇ ਵਿਕਾਸ (ਆਰ ਐਂਡ ਡੀ)'
        WHEN 'Innovation Lab' THEN 'ਨਵੀਨਤਾ ਪ੍ਰਯੋਗਸ਼ਾਲਾ'
        WHEN 'Product Engineering' THEN 'ਉਤਪਾਦ ਇੰਜੀਨੀਅਰਿੰਗ'
        WHEN 'Data Science' THEN 'ਡਾਟਾ ਸਾਇੰਸ'
        WHEN 'Analytics' THEN 'ਵਿਸ਼ਲੇਸ਼ਣ'
        WHEN 'Reporting' THEN 'ਰਿਪੋਰਟਿੰਗ'
        WHEN 'Data Governance' THEN 'ਡਾਟਾ ਗਵਰਨੈਂਸ'
        WHEN 'Product Management' THEN 'ਉਤਪਾਦ ਪ੍ਰਬੰਧਨ'
        WHEN 'Product Strategy' THEN 'ਉਤਪਾਦ ਰਣਨੀਤੀ'
        WHEN 'Product Operations' THEN 'ਉਤਪਾਦ ਸੰਚਾਲਨ'
        WHEN 'Medical Administration' THEN 'ਚਿਕਿਤਸਾ ਪ੍ਰਸ਼ਾਸਨ'
        WHEN 'Laboratory' THEN 'ਪ੍ਰਯੋਗਸ਼ਾਲਾ'
        WHEN 'Pharmacy' THEN 'ਫਾਰਮੇਸੀ'
        WHEN 'Clinical Operations' THEN 'ਕਲੀਨਿਕਲ ਸੰਚਾਲਨ'
        WHEN 'Academic Affairs' THEN 'ਅਕਾਦਮਿਕ ਮਾਮਲੇ'
        WHEN 'Admissions' THEN 'ਦਾਖਲੇ'
        WHEN 'Student Services' THEN 'ਵਿਦਿਆਰਥੀ ਸੇਵਾਵਾਂ'
        WHEN 'Faculty Administration' THEN 'ਫੈਕਲਟੀ ਪ੍ਰਸ਼ਾਸਨ'
        WHEN 'Underwriting' THEN 'ਅੰਡਰਰਾਈਟਿੰਗ'
        WHEN 'Claims' THEN 'ਦਾਅਵੇ'
        WHEN 'Loan Processing' THEN 'ਕਰਜ਼ ਪ੍ਰਕਿਰਿਆ'
        WHEN 'Credit Analysis' THEN 'ਕ੍ਰੈਡਿਟ ਵਿਸ਼ਲੇਸ਼ਣ'
        WHEN 'Civil Engineering' THEN 'ਸਿਵਲ ਇੰਜੀਨੀਅਰਿੰਗ'
        WHEN 'Site Operations' THEN 'ਸਾਈਟ ਸੰਚਾਲਨ'
        WHEN 'Safety' THEN 'ਸੁਰੱਖਿਆ'
        WHEN 'Project Management' THEN 'ਪ੍ਰੋਜੈਕਟ ਪ੍ਰਬੰਧਨ'
        WHEN 'Physical Security' THEN 'ਭੌਤਿਕ ਸੁਰੱਖਿਆ'
        WHEN 'Information Security' THEN 'ਜਾਣਕਾਰੀ ਸੁਰੱਖਿਆ'
        WHEN 'Corporate Social Responsibility' THEN 'ਕਾਰਪੋਰੇਟ ਸਮਾਜਿਕ ਜ਼ਿੰਮੇਵਾਰੀ'
        WHEN 'Environmental Health & Safety' THEN 'ਵਾਤਾਵਰਣ ਸਿਹਤ ਅਤੇ ਸੁਰੱਖਿਆ'
        WHEN 'Sustainability' THEN 'ਟਿਕਾਊਪਣ'
        WHEN 'Facilities' THEN 'ਸੁਵਿਧਾਵਾਂ'
        WHEN 'Housekeeping' THEN 'ਹਾਊਸਕੀਪਿੰਗ'
        WHEN 'Technical Writing' THEN 'ਤਕਨੀਕੀ ਲੇਖਨ'
        WHEN 'Documentation' THEN 'ਦਸਤਾਵੇਜ਼ੀਕਰਨ'
        WHEN 'Knowledge Management' THEN 'ਗਿਆਨ ਪ੍ਰਬੰਧਨ'
        ELSE name_pa
    END
WHERE name IN (
    'Compliance',
    'Risk Management',
    'Corporate Governance',
    'Procurement',
    'Purchasing',
    'Supply Chain',
    'Logistics',
    'Inventory Management',
    'Vendor Management',
    'Warehouse',
    'Production',
    'Manufacturing',
    'Quality Control',
    'Maintenance',
    'Industrial Engineering',
    'Research and Development (R&D)',
    'Innovation Lab',
    'Product Engineering',
    'Data Science',
    'Analytics',
    'Reporting',
    'Data Governance',
    'Product Management',
    'Product Strategy',
    'Product Operations',
    'Medical Administration',
    'Laboratory',
    'Pharmacy',
    'Clinical Operations',
    'Academic Affairs',
    'Admissions',
    'Student Services',
    'Faculty Administration',
    'Underwriting',
    'Claims',
    'Loan Processing',
    'Credit Analysis',
    'Civil Engineering',
    'Site Operations',
    'Safety',
    'Project Management',
    'Physical Security',
    'Information Security',
    'Corporate Social Responsibility',
    'Environmental Health & Safety',
    'Sustainability',
    'Facilities',
    'Housekeeping',
    'Technical Writing',
    'Documentation',
    'Knowledge Management'
);


-- Add Hindi and Punjabi columns to departments table
ALTER TABLE departments
ADD COLUMN IF NOT EXISTS name_hi VARCHAR(255),
ADD COLUMN IF NOT EXISTS name_pa VARCHAR(255);

-- Update all departments with Hindi and Punjabi translations
UPDATE departments
SET
    name_hi = CASE name
        WHEN 'Management' THEN 'प्रबंधन'
        WHEN 'Executive Office' THEN 'कार्यकारी कार्यालय'
        WHEN 'Strategy' THEN 'रणनीति'
        WHEN 'Corporate Planning' THEN 'कॉर्पोरेट योजना'
        WHEN 'Board Administration' THEN 'बोर्ड प्रशासन'
        WHEN 'Software Development' THEN 'सॉफ्टवेयर विकास'
        WHEN 'Custom Development' THEN 'कस्टम विकास'
        WHEN 'Web Development' THEN 'वेब विकास'
        WHEN 'Mobile Development' THEN 'मोबाइल विकास'
        WHEN 'DevOps' THEN 'डेवऑप्स'
        WHEN 'Cloud Engineering' THEN 'क्लाउड इंजीनियरिंग'
        WHEN 'Infrastructure' THEN 'इन्फ्रास्ट्रक्चर'
        WHEN 'Network Administration' THEN 'नेटवर्क प्रशासन'
        WHEN 'Database Administration' THEN 'डेटाबेस प्रशासन'
        WHEN 'Cybersecurity' THEN 'साइबर सुरक्षा'
        WHEN 'IT Support' THEN 'आईटी समर्थन'
        WHEN 'Technical Support' THEN 'तकनीकी समर्थन'
        WHEN 'QA / Testing' THEN 'गुणवत्ता आश्वासन / परीक्षण'
        WHEN 'Data Engineering' THEN 'डेटा इंजीनियरिंग'
        WHEN 'Artificial Intelligence / Machine Learning' THEN 'कृत्रिम बुद्धिमत्ता / मशीन लर्निंग'
        WHEN 'Business Intelligence' THEN 'व्यावसायिक बुद्धिमत्ता'
        WHEN 'Designing Team' THEN 'डिज़ाइन टीम'
        WHEN 'UI/UX Design' THEN 'यूआई/यूएक्स डिज़ाइन'
        WHEN 'Graphic Design' THEN 'ग्राफिक डिज़ाइन'
        WHEN 'Product Design' THEN 'उत्पाद डिज़ाइन'
        WHEN 'Video Production' THEN 'वीडियो निर्माण'
        WHEN 'Content Creation' THEN 'सामग्री निर्माण'
        WHEN 'Sales Team' THEN 'बिक्री टीम'
        WHEN 'Business Development' THEN 'व्यवसाय विकास'
        WHEN 'Account Management' THEN 'खाता प्रबंधन'
        WHEN 'Inside Sales' THEN 'इनसाइड सेल्स'
        WHEN 'Field Sales' THEN 'फील्ड सेल्स'
        WHEN 'Pre-Sales' THEN 'प्री-सेल्स'
        WHEN 'Customer Acquisition' THEN 'ग्राहक अधिग्रहण'
        WHEN 'Digital Marketing' THEN 'डिजिटल मार्केटिंग'
        WHEN 'Brand Marketing' THEN 'ब्रांड मार्केटिंग'
        WHEN 'Performance Marketing' THEN 'परफॉर्मेंस मार्केटिंग'
        WHEN 'SEO' THEN 'एसईओ'
        WHEN 'Social Media Marketing' THEN 'सोशल मीडिया मार्केटिंग'
        WHEN 'Product Marketing' THEN 'उत्पाद विपणन'
        WHEN 'Public Relations' THEN 'जनसंपर्क'
        WHEN 'Communications' THEN 'संचार'
        WHEN 'Human Resources' THEN 'मानव संसाधन'
        WHEN 'HR Administration' THEN 'एचआर प्रशासन'
        WHEN 'Talent Acquisition' THEN 'प्रतिभा अधिग्रहण'
        WHEN 'Recruitment' THEN 'भर्ती'
        WHEN 'Learning & Development' THEN 'प्रशिक्षण एवं विकास'
        WHEN 'Employee Relations' THEN 'कर्मचारी संबंध'
        WHEN 'Compensation & Benefits' THEN 'वेतन एवं लाभ'
        WHEN 'Payroll' THEN 'पेरोल'
        WHEN 'Operations' THEN 'संचालन'
        WHEN 'Process Management' THEN 'प्रक्रिया प्रबंधन'
        WHEN 'Service Delivery' THEN 'सेवा वितरण'
        WHEN 'Resource Management' THEN 'संसाधन प्रबंधन'
        WHEN 'Administration' THEN 'प्रशासन'
        WHEN 'Customer Support' THEN 'ग्राहक सहायता'
        WHEN 'Customer Success' THEN 'ग्राहक सफलता'
        WHEN 'Call Center' THEN 'कॉल सेंटर'
        WHEN 'Help Desk' THEN 'हेल्प डेस्क'
        WHEN 'Finance' THEN 'वित्त'
        WHEN 'Accounting' THEN 'लेखांकन'
        WHEN 'Accounts Payable' THEN 'देय खाते'
        WHEN 'Accounts Receivable' THEN 'प्राप्य खाते'
        WHEN 'Treasury' THEN 'कोषागार'
        WHEN 'Taxation' THEN 'कराधान'
        WHEN 'Audit' THEN 'लेखा परीक्षा'
        WHEN 'Financial Planning & Analysis' THEN 'वित्तीय योजना एवं विश्लेषण'
        WHEN 'Legal' THEN 'विधिक'
        ELSE name_hi
    END,
    name_pa = CASE name
        WHEN 'Management' THEN 'ਪ੍ਰਬੰਧਨ'
        WHEN 'Executive Office' THEN 'ਕਾਰਜਕਾਰੀ ਦਫ਼ਤਰ'
        WHEN 'Strategy' THEN 'ਰਣਨੀਤੀ'
        WHEN 'Corporate Planning' THEN 'ਕਾਰਪੋਰੇਟ ਯੋਜਨਾ'
        WHEN 'Board Administration' THEN 'ਬੋਰਡ ਪ੍ਰਸ਼ਾਸਨ'
        WHEN 'Software Development' THEN 'ਸਾਫਟਵੇਅਰ ਵਿਕਾਸ'
        WHEN 'Custom Development' THEN 'ਕਸਟਮ ਵਿਕਾਸ'
        WHEN 'Web Development' THEN 'ਵੈੱਬ ਵਿਕਾਸ'
        WHEN 'Mobile Development' THEN 'ਮੋਬਾਈਲ ਵਿਕਾਸ'
        WHEN 'DevOps' THEN 'ਡੈਵਓਪਸ'
        WHEN 'Cloud Engineering' THEN 'ਕਲਾਉਡ ਇੰਜੀਨੀਅਰਿੰਗ'
        WHEN 'Infrastructure' THEN 'ਇੰਫ੍ਰਾਸਟ੍ਰਕਚਰ'
        WHEN 'Network Administration' THEN 'ਨੈੱਟਵਰਕ ਪ੍ਰਸ਼ਾਸਨ'
        WHEN 'Database Administration' THEN 'ਡਾਟਾਬੇਸ ਪ੍ਰਸ਼ਾਸਨ'
        WHEN 'Cybersecurity' THEN 'ਸਾਈਬਰ ਸੁਰੱਖਿਆ'
        WHEN 'IT Support' THEN 'ਆਈਟੀ ਸਹਾਇਤਾ'
        WHEN 'Technical Support' THEN 'ਤਕਨੀਕੀ ਸਹਾਇਤਾ'
        WHEN 'QA / Testing' THEN 'ਗੁਣਵੱਤਾ ਭਰੋਸਾ / ਟੈਸਟਿੰਗ'
        WHEN 'Data Engineering' THEN 'ਡਾਟਾ ਇੰਜੀਨੀਅਰਿੰਗ'
        WHEN 'Artificial Intelligence / Machine Learning' THEN 'ਕ੍ਰਿਤ੍ਰਿਮ ਬੁੱਧਿਮਤਾ / ਮਸ਼ੀਨ ਲਰਨਿੰਗ'
        WHEN 'Business Intelligence' THEN 'ਵਪਾਰਕ ਬੁੱਧਿਮਤਾ'
        WHEN 'Designing Team' THEN 'ਡਿਜ਼ਾਇਨ ਟੀਮ'
        WHEN 'UI/UX Design' THEN 'ਯੂਆਈ/ਯੂਐਕਸ ਡਿਜ਼ਾਇਨ'
        WHEN 'Graphic Design' THEN 'ਗ੍ਰਾਫਿਕ ਡਿਜ਼ਾਇਨ'
        WHEN 'Product Design' THEN 'ਉਤਪਾਦ ਡਿਜ਼ਾਇਨ'
        WHEN 'Video Production' THEN 'ਵੀਡੀਓ ਉਤਪਾਦਨ'
        WHEN 'Content Creation' THEN 'ਸਮੱਗਰੀ ਨਿਰਮਾਣ'
        WHEN 'Sales Team' THEN 'ਵਿਕਰੀ ਟੀਮ'
        WHEN 'Business Development' THEN 'ਵਪਾਰ ਵਿਕਾਸ'
        WHEN 'Account Management' THEN 'ਖਾਤਾ ਪ੍ਰਬੰਧਨ'
        WHEN 'Inside Sales' THEN 'ਇਨਸਾਈਡ ਸੇਲਜ਼'
        WHEN 'Field Sales' THEN 'ਫੀਲਡ ਸੇਲਜ਼'
        WHEN 'Pre-Sales' THEN 'ਪ੍ਰੀ-ਸੇਲਜ਼'
        WHEN 'Customer Acquisition' THEN 'ਗਾਹਕ ਪ੍ਰਾਪਤੀ'
        WHEN 'Digital Marketing' THEN 'ਡਿਜ਼ਿਟਲ ਮਾਰਕੀਟਿੰਗ'
        WHEN 'Brand Marketing' THEN 'ਬ੍ਰਾਂਡ ਮਾਰਕੀਟਿੰਗ'
        WHEN 'Performance Marketing' THEN 'ਪਰਫਾਰਮੈਂਸ ਮਾਰਕੀਟਿੰਗ'
        WHEN 'SEO' THEN 'ਐਸਈਓ'
        WHEN 'Social Media Marketing' THEN 'ਸੋਸ਼ਲ ਮੀਡੀਆ ਮਾਰਕੀਟਿੰਗ'
        WHEN 'Product Marketing' THEN 'ਉਤਪਾਦ ਮਾਰਕੀਟਿੰਗ'
        WHEN 'Public Relations' THEN 'ਜਨ ਸੰਪਰਕ'
        WHEN 'Communications' THEN 'ਸੰਚਾਰ'
        WHEN 'Human Resources' THEN 'ਮਨੁੱਖੀ ਸਰੋਤ'
        WHEN 'HR Administration' THEN 'ਐਚਆਰ ਪ੍ਰਸ਼ਾਸਨ'
        WHEN 'Talent Acquisition' THEN 'ਪ੍ਰਤਿਭਾ ਪ੍ਰਾਪਤੀ'
        WHEN 'Recruitment' THEN 'ਭਰਤੀ'
        WHEN 'Learning & Development' THEN 'ਸਿਖਲਾਈ ਅਤੇ ਵਿਕਾਸ'
        WHEN 'Employee Relations' THEN 'ਕਰਮਚਾਰੀ ਸੰਬੰਧ'
        WHEN 'Compensation & Benefits' THEN 'ਮੁਆਵਜ਼ਾ ਅਤੇ ਲਾਭ'
        WHEN 'Payroll' THEN 'ਪੇਰੋਲ'
        WHEN 'Operations' THEN 'ਸੰਚਾਲਨ'
        WHEN 'Process Management' THEN 'ਪ੍ਰਕਿਰਿਆ ਪ੍ਰਬੰਧਨ'
        WHEN 'Service Delivery' THEN 'ਸੇਵਾ ਪ੍ਰਦਾਨਗੀ'
        WHEN 'Resource Management' THEN 'ਸਰੋਤ ਪ੍ਰਬੰਧਨ'
        WHEN 'Administration' THEN 'ਪ੍ਰਸ਼ਾਸਨ'
        WHEN 'Customer Support' THEN 'ਗਾਹਕ ਸਹਾਇਤਾ'
        WHEN 'Customer Success' THEN 'ਗਾਹਕ ਸਫਲਤਾ'
        WHEN 'Call Center' THEN 'ਕਾਲ ਸੈਂਟਰ'
        WHEN 'Help Desk' THEN 'ਹੈਲਪ ਡੈਸਕ'
        WHEN 'Finance' THEN 'ਵਿੱਤ'
        WHEN 'Accounting' THEN 'ਲੇਖਾਕਾਰੀ'
        WHEN 'Accounts Payable' THEN 'ਦੇਣਯੋਗ ਖਾਤੇ'
        WHEN 'Accounts Receivable' THEN 'ਪ੍ਰਾਪਤਯੋਗ ਖਾਤੇ'
        WHEN 'Treasury' THEN 'ਖ਼ਜ਼ਾਨਾ'
        WHEN 'Taxation' THEN 'ਕਰ ਪ੍ਰਣਾਲੀ'
        WHEN 'Audit' THEN 'ਆਡਿਟ'
        WHEN 'Financial Planning & Analysis' THEN 'ਵਿੱਤੀ ਯੋਜਨਾ ਅਤੇ ਵਿਸ਼ਲੇਸ਼ਣ'
        WHEN 'Legal' THEN 'ਕਾਨੂੰਨੀ'
        ELSE name_pa
    END;


    -- 1. Add Hindi and Punjabi columns to department_jobs
ALTER TABLE department_jobs
ADD COLUMN IF NOT EXISTS name_hi TEXT,
ADD COLUMN IF NOT EXISTS name_pa TEXT;

UPDATE department_jobs
SET
    name_hi = CASE name
        WHEN 'General Manager' THEN 'महाप्रबंधक'
        WHEN 'Operations Manager' THEN 'संचालन प्रबंधक'
        WHEN 'Business Manager' THEN 'व्यवसाय प्रबंधक'
        WHEN 'Assistant Manager' THEN 'सहायक प्रबंधक'
        WHEN 'Management Trainee' THEN 'प्रबंधन प्रशिक्षु'
        WHEN 'Chief Executive Officer (CEO)' THEN 'मुख्य कार्यकारी अधिकारी (सीईओ)'
        WHEN 'Chief Operating Officer (COO)' THEN 'मुख्य संचालन अधिकारी (सीओओ)'
        WHEN 'Chief Financial Officer (CFO)' THEN 'मुख्य वित्तीय अधिकारी (सीएफओ)'
        WHEN 'Executive Assistant' THEN 'कार्यकारी सहायक'
        WHEN 'Office Coordinator' THEN 'कार्यालय समन्वयक'
        WHEN 'Software Engineer' THEN 'सॉफ्टवेयर इंजीनियर'
        WHEN 'Senior Software Engineer' THEN 'वरिष्ठ सॉफ्टवेयर इंजीनियर'
        WHEN 'Backend Developer' THEN 'बैकएंड डेवलपर'
        WHEN 'Full Stack Developer' THEN 'फुल स्टैक डेवलपर'
        WHEN 'Application Developer' THEN 'एप्लिकेशन डेवलपर'
        WHEN 'Frontend Developer' THEN 'फ्रंटएंड डेवलपर'
        WHEN 'Web Developer' THEN 'वेब डेवलपर'
        WHEN 'React Developer' THEN 'रिएक्ट डेवलपर'
        WHEN 'Angular Developer' THEN 'एंगुलर डेवलपर'
        WHEN 'PHP Developer' THEN 'पीएचपी डेवलपर'
        WHEN 'Android Developer' THEN 'एंड्रॉइड डेवलपर'
        WHEN 'iOS Developer' THEN 'आईओएस डेवलपर'
        WHEN 'Flutter Developer' THEN 'फ्लटर डेवलपर'
        WHEN 'React Native Developer' THEN 'रिएक्ट नेटिव डेवलपर'
        WHEN 'Mobile App Developer' THEN 'मोबाइल ऐप डेवलपर'
        WHEN 'DevOps Engineer' THEN 'डेवऑप्स इंजीनियर'
        WHEN 'Site Reliability Engineer' THEN 'साइट विश्वसनीयता इंजीनियर'
        WHEN 'CI/CD Engineer' THEN 'सीआई/सीडी इंजीनियर'
        WHEN 'Release Engineer' THEN 'रिलीज इंजीनियर'
        WHEN 'Automation Engineer' THEN 'स्वचालन इंजीनियर'
        WHEN 'Cloud Engineer' THEN 'क्लाउड इंजीनियर'
        WHEN 'AWS Engineer' THEN 'एडब्ल्यूएस इंजीनियर'
        WHEN 'Azure Engineer' THEN 'एज़्योर इंजीनियर'
        WHEN 'Google Cloud Engineer' THEN 'गूगल क्लाउड इंजीनियर'
        WHEN 'Cloud Solutions Architect' THEN 'क्लाउड समाधान वास्तुकार'
        ELSE COALESCE(name_hi, name)
    END,

    name_pa = CASE name
        WHEN 'General Manager' THEN 'ਮਹਾਪ੍ਰਬੰਧਕ'
        WHEN 'Operations Manager' THEN 'ਓਪਰੇਸ਼ਨ ਮੈਨੇਜਰ'
        WHEN 'Business Manager' THEN 'ਕਾਰੋਬਾਰ ਮੈਨੇਜਰ'
        WHEN 'Assistant Manager' THEN 'ਸਹਾਇਕ ਮੈਨੇਜਰ'
        WHEN 'Management Trainee' THEN 'ਪ੍ਰਬੰਧਨ ਪ੍ਰਸ਼ਿਕਸ਼ੂ'
        WHEN 'Chief Executive Officer (CEO)' THEN 'ਮੁੱਖ ਕਾਰਜਕਾਰੀ ਅਧਿਕਾਰੀ (ਸੀਈਓ)'
        WHEN 'Chief Operating Officer (COO)' THEN 'ਮੁੱਖ ਸੰਚਾਲਨ ਅਧਿਕਾਰੀ (ਸੀਓਓ)'
        WHEN 'Chief Financial Officer (CFO)' THEN 'ਮੁੱਖ ਵਿੱਤੀ ਅਧਿਕਾਰੀ (ਸੀਐਫਓ)'
        WHEN 'Executive Assistant' THEN 'ਕਾਰਜਕਾਰੀ ਸਹਾਇਕ'
        WHEN 'Office Coordinator' THEN 'ਦਫ਼ਤਰ ਸਮਨਵਯਕ'
        WHEN 'Software Engineer' THEN 'ਸਾਫਟਵੇਅਰ ਇੰਜੀਨੀਅਰ'
        WHEN 'Senior Software Engineer' THEN 'ਸੀਨੀਅਰ ਸਾਫਟਵੇਅਰ ਇੰਜੀਨੀਅਰ'
        WHEN 'Backend Developer' THEN 'ਬੈਕਐਂਡ ਡਿਵੈਲਪਰ'
        WHEN 'Full Stack Developer' THEN 'ਫੁੱਲ ਸਟੈਕ ਡਿਵੈਲਪਰ'
        WHEN 'Application Developer' THEN 'ਐਪਲੀਕੇਸ਼ਨ ਡਿਵੈਲਪਰ'
        WHEN 'Frontend Developer' THEN 'ਫਰੰਟਐਂਡ ਡਿਵੈਲਪਰ'
        WHEN 'Web Developer' THEN 'ਵੈੱਬ ਡਿਵੈਲਪਰ'
        WHEN 'React Developer' THEN 'ਰਿਐਕਟ ਡਿਵੈਲਪਰ'
        WHEN 'Angular Developer' THEN 'ਐਂਗੂਲਰ ਡਿਵੈਲਪਰ'
        WHEN 'PHP Developer' THEN 'ਪੀਐਚਪੀ ਡਿਵੈਲਪਰ'
        WHEN 'Android Developer' THEN 'ਐਂਡਰਾਇਡ ਡਿਵੈਲਪਰ'
        WHEN 'iOS Developer' THEN 'ਆਈਓਐਸ ਡਿਵੈਲਪਰ'
        WHEN 'Flutter Developer' THEN 'ਫਲਟਰ ਡਿਵੈਲਪਰ'
        WHEN 'React Native Developer' THEN 'ਰਿਐਕਟ ਨੇਟਿਵ ਡਿਵੈਲਪਰ'
        WHEN 'Mobile App Developer' THEN 'ਮੋਬਾਈਲ ਐਪ ਡਿਵੈਲਪਰ'
        WHEN 'DevOps Engineer' THEN 'ਡੈਵਓਪਸ ਇੰਜੀਨੀਅਰ'
        WHEN 'Site Reliability Engineer' THEN 'ਸਾਈਟ ਭਰੋਸੇਯੋਗਤਾ ਇੰਜੀਨੀਅਰ'
        WHEN 'CI/CD Engineer' THEN 'ਸੀਆਈ/ਸੀਡੀ ਇੰਜੀਨੀਅਰ'
        WHEN 'Release Engineer' THEN 'ਰਿਲੀਜ਼ ਇੰਜੀਨੀਅਰ'
        WHEN 'Automation Engineer' THEN 'ਆਟੋਮੇਸ਼ਨ ਇੰਜੀਨੀਅਰ'
        WHEN 'Cloud Engineer' THEN 'ਕਲਾਉਡ ਇੰਜੀਨੀਅਰ'
        WHEN 'AWS Engineer' THEN 'ਏਡਬਲਯੂਐਸ ਇੰਜੀਨੀਅਰ'
        WHEN 'Azure Engineer' THEN 'ਐਜ਼ਰ ਇੰਜੀਨੀਅਰ'
        WHEN 'Google Cloud Engineer' THEN 'ਗੂਗਲ ਕਲਾਉਡ ਇੰਜੀਨੀਅਰ'
        WHEN 'Cloud Solutions Architect' THEN 'ਕਲਾਉਡ ਹੱਲ ਆਰਕੀਟੈਕਟ'
        ELSE COALESCE(name_pa, name)
    END
WHERE name IN (
    'General Manager',
    'Operations Manager',
    'Business Manager',
    'Assistant Manager',
    'Management Trainee',
    'Chief Executive Officer (CEO)',
    'Chief Operating Officer (COO)',
    'Chief Financial Officer (CFO)',
    'Executive Assistant',
    'Office Coordinator',
    'Software Engineer',
    'Senior Software Engineer',
    'Backend Developer',
    'Full Stack Developer',
    'Application Developer',
    'Frontend Developer',
    'Web Developer',
    'React Developer',
    'Angular Developer',
    'PHP Developer',
    'Android Developer',
    'iOS Developer',
    'Flutter Developer',
    'React Native Developer',
    'Mobile App Developer',
    'DevOps Engineer',
    'Site Reliability Engineer',
    'CI/CD Engineer',
    'Release Engineer',
    'Automation Engineer',
    'Cloud Engineer',
    'AWS Engineer',
    'Azure Engineer',
    'Google Cloud Engineer',
    'Cloud Solutions Architect'
);


-- added token utilization and cost colunm in assessment_session table
-- 1️⃣ Add the column to the assessment_sessions table (stores the session‑level running total)
ALTER TABLE assessment_sessions ADD COLUMN cost DOUBLE PRECISION NULL;

-- 2️⃣ Add the column to the assessment_results table (stores the final monetary cost for the completed assessment)
ALTER TABLE assessment_results ADD COLUMN cost DOUBLE PRECISION NULL;


-- 22 may 2026 change 
-- Scheduled Period column added in interviews table
 ALTER TABLE interviews ADD COLUMN scheduled_period VARCHAR(2);

-- Auto interview scheduling (provider settings + availability + interview extensions)
CREATE TABLE IF NOT EXISTS provider_interview_settings (
    provider_id VARCHAR(36) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    auto_schedule_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    slot_duration_minutes INTEGER NOT NULL DEFAULT 30,
    buffer_minutes INTEGER NOT NULL DEFAULT 0,
    timezone VARCHAR(64) NOT NULL DEFAULT 'UTC',
    lookahead_days INTEGER NOT NULL DEFAULT 14,
    min_notice_hours INTEGER NOT NULL DEFAULT 24,
    default_title VARCHAR(200) NOT NULL DEFAULT 'Interview',
    default_interviewer_name VARCHAR(200),
    default_agenda TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS provider_availability_windows (
    id VARCHAR(36) PRIMARY KEY,
    provider_id VARCHAR(36) NOT NULL REFERENCES provider_interview_settings(provider_id) ON DELETE CASCADE,
    day_of_week SMALLINT NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    CHECK (end_time > start_time)
);
CREATE INDEX IF NOT EXISTS idx_provider_availability_provider ON provider_availability_windows(provider_id);

ALTER TABLE interviews ADD COLUMN IF NOT EXISTS application_id VARCHAR(36) REFERENCES applications(id) ON DELETE SET NULL;
ALTER TABLE interviews ADD COLUMN IF NOT EXISTS source VARCHAR(20) NOT NULL DEFAULT 'manual';

CREATE UNIQUE INDEX IF NOT EXISTS uq_interviews_provider_scheduled_at ON interviews (provider_id, scheduled_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_interviews_application_auto
    ON interviews (application_id)
    WHERE application_id IS NOT NULL AND source = 'auto';