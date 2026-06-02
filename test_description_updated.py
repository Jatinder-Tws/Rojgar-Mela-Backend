"""
Test script to verify the updated generate_description endpoint works correctly
"""
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ai_jobcreation_service import generate_job_descriptions

def test_generate_descriptions():
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
    
    # Since this is an async function, we need to handle it properly
    import asyncio
    
    async def run_test():
        result = await generate_job_descriptions(
            title=payload["title"],
            exp_min=payload["exp_min"],
            exp_max=payload["exp_max"],
            sal_min=payload["sal_min"],
            sal_max=payload["sal_max"],
            salary_range=payload["salary_range"],
            location=payload["location"],
            job_type=payload["job_type"],
            employment_type=payload["employment_type"],
            shift=payload["shift"],
            required_skills=payload["required_skills"],
            perks=payload["perks"]
        )
        
        print("=== DESCRIPTION 1 ===")
        print(result["description_1"])
        print()
        print("=== DESCRIPTION 2 ===")
        print(result["description_2"])
        print()
        
        # Verify key components are present
        desc1 = result["description_1"]
        desc2 = result["description_2"]
        
        # Basic checks - just make sure we got something back
        assert len(desc1) > 0, "Description 1 should not be empty"
        assert len(desc2) > 0, "Description 2 should not be empty"
        assert desc1 != desc2, "Descriptions should be different"
        
        print("All tests passed!")
        return result
    
    # Run the async test
    return asyncio.run(run_test())

if __name__ == "__main__":
    test_generate_descriptions()