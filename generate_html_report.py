import os
import json

MD_FILE = "SYSTEM_HANDOVER.md"
HTML_FILE = "SYSTEM_HANDOVER.html"

def generate_html():
    if not os.path.exists(MD_FILE):
        print(f"Error: {MD_FILE} not found!")
        return

    with open(MD_FILE, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Escape backticks for JS string
    md_content_js = json.dumps(md_content)

    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rolevo System Handover</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max_width: 900px;
            margin: 0 auto;
            padding: 40px;
            color: #333;
        }
        @media print {
            body {
                max_width: 100%;
                padding: 0;
            }
            .no-print {
                display: none;
            }
        }
        h1, h2, h3 { color: #2c3e50; margin-top: 1.5em; }
        h1 { border-bottom: 2px solid #eee; padding-bottom: 10px; }
        h2 { border-bottom: 1px solid #eee; padding-bottom: 5px; }
        code { background: #f4f4f4; padding: 2px 5px; border-radius: 3px; font-family: Consolas, monospace; }
        pre { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
        pre code { background: none; padding: 0; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #f8f9fa; }
        img { max-width: 100%; }
        .mermaid { margin: 30px 0; text-align: center; }
        .alert { padding: 15px; margin: 20px 0; border-left: 5px solid #333; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="no-print" style="background: #e1f5fe; padding: 15px; border-radius: 5px; margin-bottom: 20px; border: 1px solid #b3e5fc; color: #01579b;">
        <strong>🖨️ Instructions:</strong> Right-click and select "Print", then choose "Save as PDF" to get the final PDF document.
    </div>

    <div id="content"></div>

    <script>
        const mdContent = MD_CONTENT_PLACEHOLDER;
        
        // Configure marked options
        marked.setOptions({
            highlight: function(code, lang) {
                if (lang === 'mermaid') {
                    return '<div class="mermaid">' + code + '</div>';
                }
                return code;
            }
        });

        const renderer = new marked.Renderer();
        const originalCode = renderer.code.bind(renderer);
        
        renderer.code = (code, language) => {
            if (language === 'mermaid') {
                return `<div class="mermaid">${code}</div>`;
            }
            return originalCode(code, language);
        };

        const htmlContent = marked.parse(mdContent, { renderer });
        document.getElementById('content').innerHTML = htmlContent;
        
        // Initialize mermaid after content is loaded
        setTimeout(() => {
            mermaid.initialize({ 
                startOnLoad: true, 
                theme: 'default',
                securityLevel: 'loose',
            });
            mermaid.init(undefined, document.querySelectorAll('.mermaid'));
        }, 100);
    </script>
</body>
</html>
    """

    final_html = html_template.replace("MD_CONTENT_PLACEHOLDER", md_content_js)

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(final_html)
    
    print(f"✅ Generated {HTML_FILE}")

if __name__ == "__main__":
    generate_html()
