#!/usr/bin/env python3
import http.server
import socket
import socketserver
import os
import time
import markdown
from urllib.parse import unquote
import mimetypes
import yaml
import re
from datetime import datetime

class MarkdownHandler(http.server.SimpleHTTPRequestHandler):
    def parse_frontmatter(self, content):
        """Parse YAML frontmatter from markdown content"""
        # Check if content starts with frontmatter
        if not content.startswith('---'):
            return {}, content
        
        # Find the end of frontmatter
        parts = content.split('---', 2)
        if len(parts) < 3:
            return {}, content
        
        try:
            # Parse YAML frontmatter
            frontmatter = yaml.safe_load(parts[1].strip())
            if frontmatter is None:
                frontmatter = {}
            
            # Return frontmatter and content without frontmatter
            content_without_frontmatter = parts[2].lstrip('\n')
            return frontmatter, content_without_frontmatter
        except yaml.YAMLError:
            # If YAML parsing fails, return empty frontmatter and original content
            return {}, content

    def do_GET(self):
        # Decode the path
        path = unquote(self.path)
        
        # Handle root path - show directory listing
        if path == '/':
            self.serve_directory_listing()
            return
        elif not path.startswith('/'):
            path = '/' + path
            
        # Convert to filesystem path (now looking in 'files' directory)
        fs_path = 'files' + path
        
        # If it's a .md file, convert to HTML
        if path.endswith('.md'):
            if os.path.exists(fs_path):
                try:
                    with open(fs_path, 'r', encoding='utf-8') as f:
                        md_content = f.read()
                    
                    # Parse frontmatter
                    frontmatter, content = self.parse_frontmatter(md_content)
                    
                    # Convert markdown to HTML
                    html_content = markdown.markdown(content, extensions=['fenced_code', 'tables', 'extra'])
                    
                    # Get title from frontmatter or use filename
                    title = frontmatter.get('title', path.split('/')[-1].replace('.md', ''))
                    
                    # Wrap in basic HTML template
                    full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} - Jack Zellweger</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <style>
        @media (max-width: 600px) {{ 
            body {{ font-size: 18px; }}
            pre {{ overflow-x: auto; }}
            img {{ max-width: 100%; }}
        }}
    </style>
</head>
<body>
<a href="/">Home</a>
<hr>
{html_content}
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script>hljs.highlightAll();</script>
<script>
window.MathJax = {{
  tex: {{
    inlineMath: [['$', '$']],
    displayMath: [['$$', '$$']]
  }}
}};
</script>
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</body>
</html>
"""
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(full_html.encode('utf-8'))
                    return
                except Exception as e:
                    self.send_error(500, f"Error processing markdown: {e}")
                    return
            else:
                self.send_error(404, "Markdown file not found")
                return
        
        # For non-markdown files, serve them from the files directory
        if os.path.exists(fs_path):
            # Get the mime type
            mime_type, _ = mimetypes.guess_type(fs_path)
            if mime_type is None:
                mime_type = 'application/octet-stream'
            
            try:
                with open(fs_path, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', mime_type)
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            except Exception as e:
                self.send_error(500, f"Error serving file: {e}")
                return
        else:
            self.send_error(404, "File not found")

    def get_file_info(self, md_file):
        """Get file info including frontmatter date"""
        file_path = os.path.join('files', md_file)
        
        # Get file modification time as fallback
        mod_time = os.path.getmtime(file_path)
        fallback_date = datetime.fromtimestamp(mod_time)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            frontmatter, _ = self.parse_frontmatter(content)
            
            # Try to get date from frontmatter
            if 'date' in frontmatter:
                date_value = frontmatter['date']
                if isinstance(date_value, str):
                    # Try to parse date string
                    try:
                        # Common date formats
                        for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d', '%m/%d/%Y']:
                            try:
                                parsed_date = datetime.strptime(date_value, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            # If no format worked, use fallback
                            parsed_date = fallback_date
                    except:
                        parsed_date = fallback_date
                elif hasattr(date_value, 'year'):  # datetime or date object
                    # Convert date to datetime if needed
                    if hasattr(date_value, 'hour'):  # already datetime
                        parsed_date = date_value
                    else:  # date object, convert to datetime
                        parsed_date = datetime.combine(date_value, datetime.min.time())
                else:
                    parsed_date = fallback_date
            else:
                parsed_date = fallback_date
            
            # Get title from frontmatter or use filename
            title = frontmatter.get('title', md_file.replace('.md', ''))
            
            return {
                'filename': md_file,
                'title': title,
                'date': parsed_date,
                'frontmatter': frontmatter
            }
            
        except Exception:
            # If anything goes wrong, use file modification time
            return {
                'filename': md_file,
                'title': md_file.replace('.md', ''),
                'date': fallback_date,
                'frontmatter': {}
            }

    def serve_directory_listing(self):
        """Generate and serve a directory listing of all .md files in the files directory"""
        try:
            # Check if files directory exists
            if not os.path.exists('files'):
                self.send_error(404, "Files directory not found. Please create a 'files' directory.")
                return
                
            # Get all .md files in files directory
            md_files = [f for f in os.listdir('files') if f.endswith('.md')]
            
            if not md_files:
                file_list_html = "No markdown files found.<br>Create some .md files in the 'files' directory to get started!"
            else:
                # Get file info and sort by date (most recent first)
                file_infos = [self.get_file_info(f) for f in md_files]
                file_infos.sort(key=lambda x: x['date'], reverse=True)
                
                # Create HTML for file listing
                file_list_html = ""
                for info in file_infos:
                    date_str = info['date'].strftime('%Y-%m-%d')
                    file_list_html += f'<a href="{info["filename"]}">{info["title"]}</a> - {date_str}<br>\n'
            
            # Generate complete HTML page
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Jack Zellweger</title>
</head>
<body>
<h1>Jack Zellweger</h1>
<hr>
{file_list_html}
<hr>
<p>{len(md_files)} file{'s' if len(md_files) != 1 else ''} found</p>
</body>
</html>
"""
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error generating directory listing: {e}")

    def get_local_ip():
        """Get the local network IP address"""
        try:
            # Create a socket and connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # Connect to Google's DNS server (doesn't actually send data)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            return local_ip
        except Exception:
            # Fallback if the above fails
            return socket.gethostbyname(socket.gethostname())

if __name__ == "__main__":
    PORT = 3000
    HOST = "0.0.0.0"  # Bind to all interfaces
    
    # Create files directory if it doesn't exist
    if not os.path.exists('files'):
        os.makedirs('files')
        print("Created 'files' directory")
    
    with socketserver.ThreadingTCPServer((HOST, PORT), MarkdownHandler) as httpd:
        local_ip = MarkdownHandler.get_local_ip()
        print(f"Serving at http://localhost:{PORT}")
        print(f"Also accessible on local network at http://{local_ip}:{PORT}")
        print("Place your .md files in the 'files' directory")
        print("Use YAML frontmatter for dates:")
        print("---")
        print("title: My Post")
        print("date: YYYY-MM-DD")
        print("---")
        httpd.serve_forever()