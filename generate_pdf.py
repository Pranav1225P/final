import os
from fpdf import FPDF

class ProjectPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Campus AI Lost & Found System - Complete Documentation', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf():
    pdf = ProjectPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Files to include
    project_files = [
        ('app.py', 'c:/Users/PRANAV/.gemini/antigravity/playground/glacial-protostar/app.py'),
        ('init_db.py', 'c:/Users/PRANAV/.gemini/antigravity/playground/glacial-protostar/init_db.py'),
        ('requirements.txt', 'c:/Users/PRANAV/.gemini/antigravity/playground/glacial-protostar/requirements.txt'),
        ('Procfile', 'c:/Users/PRANAV/.gemini/antigravity/playground/glacial-protostar/Procfile'),
        ('nixpacks.toml', 'c:/Users/PRANAV/.gemini/antigravity/playground/glacial-protostar/nixpacks.toml'),
        ('style.css', 'c:/Users/PRANAV/.gemini/antigravity/playground/glacial-protostar/static/css/style.css'),
        ('chat.js', 'c:/Users/PRANAV/.gemini/antigravity/playground/glacial-protostar/static/js/chat.js'),
        ('login.html', 'c:/Users/PRANAV/.gemini/antigravity/playground/glacial-protostar/templates/login.html'),
        ('chatbot.html', 'c:/Users/PRANAV/.gemini/antigravity/playground/glacial-protostar/templates/chatbot.html'),
        ('my_reports.html', 'c:/Users/PRANAV/.gemini/antigravity/playground/glacial-protostar/templates/my_reports.html')
    ]
    
    brain_dir = 'C:/Users/PRANAV/.gemini/antigravity/brain/658018f4-17ab-496a-ae5c-a6f09cf3796d'
    brain_files = [
        ('task.md', os.path.join(brain_dir, 'task.md')),
        ('implementation_plan.md', os.path.join(brain_dir, 'implementation_plan.md')),
        ('walkthrough.md', os.path.join(brain_dir, 'walkthrough.md')),
        ('deployment_guide.md', os.path.join(brain_dir, 'deployment_guide.md')),
        ('port_forwarding_guide.md', os.path.join(brain_dir, 'port_forwarding_guide.md'))
    ]
    
    all_files = brain_files + project_files
    
    for title, path in all_files:
        if os.path.exists(path):
            pdf.set_font('Arial', 'B', 12)
            pdf.set_text_color(70, 130, 180) # Steel blue-ish
            pdf.cell(0, 10, f'File: {title}', 0, 1, 'L')
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Courier', '', 9)
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Handle characters that might cause issues with standard fonts
                    safe_content = content.encode('ascii', 'replace').decode('ascii')
                    pdf.multi_cell(0, 5, safe_content)
            except Exception as e:
                pdf.cell(0, 10, f'Error reading file: {e}', 0, 1)
            
            pdf.ln(10)
        else:
            print(f"Warning: File not found {path}")

    output_path = 'c:/Users/PRANAV/.gemini/antigravity/playground/glacial-protostar/Campus_AI_Project_Documentation.pdf'
    pdf.output(output_path)
    print(f"PDF generated successfully at: {output_path}")

if __name__ == '__main__':
    create_pdf()
