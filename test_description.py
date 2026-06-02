"""
Test script to verify the generate_job_description function works correctly
"""
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from schemas.jobs import generate_job_description

def test_generate_description():
    # Test payload from the user's example
    payload = {
        "title": "Mern Developer",
        "exp_min": "1",
        "exp_max": "6",
        "sal_min": "1",
        "sal_max": "6",
        "salary_range": "1-6 LPA",
        "location": "Ludhiana, Punjab",
        "job_type": "wfh",
        "employment_type": "part_time",
        "shift": "night",
        "required_skills": [
            "MongoDB",
            "Express.js",
            "React.js",
            "Node.js",
            "JavaScript",
            "HTML",
            "CSS",
            "Git",
            "RESTful APIs",
            "Redux",
            "Mongoose",
            "Webpack",
            "Problem-solving",
            "Communication",
            "Teamwork"
        ],
        "perks": [
            "Flexible Working Hours",
            "Weekly Payout"
        ]
    }
    
    result = generate_job_description(payload)
    
    print("=== DESCRIPTION 1 ===")
    print(result["description_1"])
    print()
    print("=== DESCRIPTION 2 ===")
    print(result["description_2"])
    print()
    
    # Verify key components are present
    desc1 = result["description_1"]
    desc2 = result["description_2"]
    
    assert "Mern Developer" in desc1
    assert "1-6 years" in desc1 or "1-6" in desc1
    assert "1-6 LPA" in desc1
    assert "Ludhiana, Punjab" in desc1
    assert "wfh" in desc1
    assert "part_time" in desc1
    assert "night" in desc1
    
    assert "Mern Developer" in desc2
    assert "1 to 6 years" in desc2
    assert "MongoDB, Express.js" in desc2  # Skills should be included
    assert "Flexible Working Hours, Weekly Payout" in desc2  # Perks should be included
    
    print("All tests passed!")

if __name__ == "__main__":
    test_generate_description()