import pdfplumber
# from docx import Document

def extract_text(file):
    if file.filename.endswith(".pdf"):
        with pdfplumber.open(file.file) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)

    # elif file.filename.endswith(".docx"):
    #     doc = Document(file.file)
    #     return "\n".join([p.text for p in doc.paragraphs])

def build_resume_text(parsed_json: dict) -> str:
    text = f"""
        Name: {parsed_json.get('name')}
        Email: {parsed_json.get('email')}
        Phone: {parsed_json.get('phone')}

        Summary:
        {parsed_json.get('summary')}

        Skills:
        {", ".join(parsed_json.get('skills', []))}

        Experience:
        """

    for exp in parsed_json.get("experience", []):
        text += f"""
        - {exp.get('title')} at {exp.get('company')}
        {exp.get('start_date')} - {exp.get('end_date')}
        {exp.get('description')}
        """

        text += "\nEducation:\n"

        for edu in parsed_json.get("education", []):
            text += f"""
        - {edu.get('degree')} in {edu.get('field')}
        {edu.get('institution')} ({edu.get('graduation_date')})
        """
    print(text)

    return text
