from xhtml2pdf import pisa
import os
import tempfile

html = """
<!DOCTYPE html>
<html>
<head>
<style>
    body { font-family: Helvetica, sans-serif; padding: 20px; }
    h1 { color: #2563eb; }
    .section { margin-bottom: 20px; }
    h2 { border-bottom: 1px solid #ccc; padding-bottom: 5px; }
</style>
</head>
<body>
    <h1>Professional Resume</h1>
    <div class="section">
        <h2>Experience</h2>
        <p><strong>Software Engineer</strong> | Tech Solutions</p>
        <p>Jan 2021 - Present</p>
    </div>
</body>
</html>
"""

def convert_html_to_pdf(source_html, output_filename):
    # open output file for writing (binary)
    result_file = open(output_filename, "w+b")

    # convert HTML to PDF
    pisa_status = pisa.CreatePDF(
            source_html,                # the HTML to convert
            dest=result_file)           # file handle to recieve result

    # close output file
    result_file.close()                 # close output file

    # return True on success and False on errors
    return pisa_status.err

if __name__ == "__main__":
    temp_dir = tempfile.gettempdir()
    test_pdf = os.path.join(temp_dir, "test_pisa_output.pdf")
    err = convert_html_to_pdf(html, test_pdf)
    if not err:
        print(f"Success! PDF created at: {test_pdf}")
    else:
        print(f"Error during PDF generation: {err}")
