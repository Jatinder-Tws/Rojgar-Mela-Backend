import pymupdf
import os
import tempfile

html = """
<html>
<body>
    <h1 style="color: blue;">Test Resume</h1>
    <p>This is a test of PDF generation using PyMuPDF Story.</p>
    <ul>
        <li>Skill 1</li>
        <li>Skill 2</li>
    </ul>
</body>
</html>
"""

def create_pdf(html_content, output_path):
    # Create a story from the HTML
    story = pymupdf.Story(html_content)
    
    # Create an empty PDF
    pdf = pymupdf.open()
    
    # Define page size (A4)
    mediabox = pymupdf.paper_rect("a4")
    
    # Write story to PDF
    while True:
        page = pdf.new_page(width=mediabox.width, height=mediabox.height)
        where = mediabox + (36, 36, -36, -36)  # margins
        more, _ = story.place(where)
        story.draw(page)
        if not more:
            break
            
    pdf.save(output_path)
    pdf.close()
    print(f"PDF saved to {output_path}")

# Use local temp file
temp_dir = tempfile.gettempdir()
test_py = os.path.join(temp_dir, "test_pdf_gen.py")
test_pdf = os.path.join(temp_dir, "test_output.pdf")

# We are already writing this to a file via the tool, so let's just use the current file's logic
if __name__ == "__main__":
    try:
        create_pdf(html, test_pdf)
        if os.path.exists(test_pdf):
            print(f"Success! PDF created at: {test_pdf}")
        else:
            print("Failed to create PDF file.")
    except Exception as e:
        print(f"Error during PDF generation: {e}")
