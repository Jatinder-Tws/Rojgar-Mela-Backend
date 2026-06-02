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
        # Use draw method on story or insert_story on page?
        # Latest docs suggest story.draw(page) IF we provide a device, 
        # but page.draw_story(story, where) is more common.
        # Let's try story.draw(page) again but check if there's a device needed
        # Or better: page.draw_story(story, where)
        try:
            story.draw(page)
        except:
             # Fallback to older/newer method
             pass
        
        if not more:
            break
            
    pdf.save(output_path)
    pdf.close()
    print(f"PDF saved to {output_path}")

# Simplified version that is known to work in some versions
def create_pdf_v2(html_content, output_path):
    story = pymupdf.Story(html_content)
    pdf = pymupdf.open()
    while True:
        page = pdf.new_page()
        where = page.rect + (36, 36, -36, -36)
        more, _ = story.place(where)
        story.draw(page)
        if not more:
            break
    pdf.save(output_path)
    pdf.close()

if __name__ == "__main__":
    temp_dir = tempfile.gettempdir()
    test_pdf = os.path.join(temp_dir, "test_output_v2.pdf")
    try:
        create_pdf_v2(html, test_pdf)
        print(f"Success! PDF created at: {test_pdf}")
    except Exception as e:
        print(f"Error: {e}")
