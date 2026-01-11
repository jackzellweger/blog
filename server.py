#!/usr/bin/env python3
import http.server
import socket
import socketserver
import os
import time
from urllib.parse import unquote
import mimetypes
import mistune
import yaml
import re
from datetime import datetime

# Comment
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

    def parse_html_frontmatter(self, content):
        """Parse YAML frontmatter from HTML comment at start of file"""
        match = re.match(r'^\s*<!--\s*(.*?)\s*-->', content, re.DOTALL)
        if not match:
            return {}
        try:
            frontmatter = yaml.safe_load(match.group(1))
            return frontmatter if frontmatter else {}
        except yaml.YAMLError:
            return {}

    def do_GET(self):
        # Decode the path
        path = unquote(self.path)

        # Health check endpoint
        if path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
            return
        
        # Handle root path - show all posts
        if path == '/':
            self.serve_directory_listing()
            return
        
        # Handle tag filtering - check if path is a single word (tag)
        if path.count('/') == 1 and path.startswith('/') and not path.endswith('.md'):
            tag = path[1:]  # Remove leading slash
            if tag and not '.' in tag:  # Simple tag validation
                self.serve_directory_listing(filter_tag=tag)
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
                    html_content = mistune.html(content)
                    
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
                    if hasattr(e, 'errno') and e.errno == 32:  # EPIPE
                       self.send_error(500, f"Detected remote disconnect") # remote peer disconnected
                    else:
                        self.send_error(500, f"Error processing markdown: {e}")
                        return
            else:
                self.send_error(404, "Markdown file not found")
                return
        
        # For non-markdown files, try files directory first, then root directory
        file_locations = [fs_path, path[1:]]  # files/path and just path (without leading /)
        
        for file_path in file_locations:
            if os.path.exists(file_path):
                # Get the mime type
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type is None:
                    mime_type = 'application/octet-stream'
                
                try:
                    with open(file_path, 'rb') as f:
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
        
        self.send_error(404, "File not found")

    def get_file_info(self, filename):
        """Get file info including frontmatter date"""
        file_path = os.path.join('files', filename)
        
        # Get file modification time as fallback
        mod_time = os.path.getmtime(file_path)
        fallback_date = datetime.fromtimestamp(mod_time)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse frontmatter differently for HTML vs MD
            if filename.endswith('.html'):
                frontmatter = self.parse_html_frontmatter(content)
            else:
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
            title = frontmatter.get('title', re.sub(r'\.(md|html)$', '', filename))
            
            # Get tags from frontmatter (normalize to lowercase list)
            tags = frontmatter.get('tags', [])
            if isinstance(tags, str):
                tags = [tags.lower().strip()]
            elif isinstance(tags, list):
                tags = [tag.lower().strip() for tag in tags if isinstance(tag, str)]
            else:
                tags = []
            
            return {
                'filename': filename,
                'title': title,
                'date': parsed_date,
                'tags': tags,
                'frontmatter': frontmatter
            }

        except Exception:
            # If anything goes wrong, use file modification time
            return {
                'filename': filename,
                'title': re.sub(r'\.(md|html)$', '', filename),
                'date': fallback_date,
                'tags': [],
                'frontmatter': {}
            }

    def serve_directory_listing(self, filter_tag=None):
        """Generate and serve a directory listing of .md and .html files, optionally filtered by tag"""
        try:
            # Check if files directory exists
            if not os.path.exists('files'):
                self.send_error(404, "Files directory not found. Please create a 'files' directory.")
                return

            # Get all .md and .html files in files directory
            all_files = [f for f in os.listdir('files') if f.endswith('.md') or f.endswith('.html')]

            if not all_files:
                file_list_html = "No files found.<br>Create some .md or .html files in the 'files' directory to get started!"
            else:
                # Get file info and sort by date (most recent first)
                file_infos = [self.get_file_info(f) for f in all_files]
                
                # Filter by tag if specified
                if filter_tag:
                    filter_tag_lower = filter_tag.lower()
                    file_infos = [info for info in file_infos if filter_tag_lower in info['tags']]
                
                file_infos.sort(key=lambda x: x['date'], reverse=True)
                
                # Create HTML for file listing
                if not file_infos and filter_tag:
                    file_list_html = f"No posts found with tag '{filter_tag}'.<br><a href='/'>View all posts</a>"
                elif not file_infos:
                    file_list_html = "No files found.<br>Create some .md or .html files in the 'files' directory to get started!"
                else:
                    file_list_html = ""
                    for info in file_infos:
                        date_str = info['date'].strftime('%Y-%m-%d')
                        file_list_html += f'<a href="{info["filename"]}">{info["title"]}</a> - {date_str}<br>\n'
            
            # No image on front page
            image_html = ""
            
            # Generate page title
            if filter_tag:
                page_title = f"Jack Zellweger - {filter_tag.title()}"
                heading = f"Jack Zellweger - {filter_tag.title()}"
                count_text = f"{len(file_infos) if filter_tag else len(all_files)} post{'s' if (len(file_infos) if filter_tag else len(all_files)) != 1 else ''} found"
            else:
                page_title = "Jack Zellweger"
                heading = "Jack Zellweger"
                count_text = f"{len(all_files)} file{'s' if len(all_files) != 1 else ''} found"
            
            # Generate complete HTML page
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{page_title}</title>
    <style>
        body {{
            font-size: 20px;
        }}
        .header-container {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .header-container h1 {{
            margin: 0;
        }}
        .header-container img {{
            height: 2.5em;
        }}
        @media (max-width: 600px) {{
            body {{
                font-size: 22px;
            }}
        }}
    </style>
</head>
<body>
<div class="header-container">
    <img src="/john_building.svg" alt="John Building">
    <h1>{heading}</h1>
</div>
<hr>
{file_list_html}
<hr>
{image_html}
<p>{count_text}</p>
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
    PORT = int(os.environ.get('PORT', 3000))
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