from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import logging
import os
import traceback
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

# Ensure the template directory is correctly set
template_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(template_dir, 'templates')

app = Flask(__name__, 
            template_folder=template_dir,
            static_folder=template_dir)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def home():
    return render_template('scrapper.html')

@app.route('/scraper')
def scraper():
    return render_template('scrapper.html')

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    try:
        # Get the paragraphs from the request
        data = request.get_json()
        paragraphs = data.get('paragraphs', [])
        url = data.get('url', 'Unknown Source')

        # Create a PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        
        # Create styles
        styles = getSampleStyleSheet()
        story = []

        # Add title
        title = Paragraph(f"Web Scraping Results from {url}", styles['Title'])
        story.append(title)
        story.append(Paragraph("<br/><br/>", styles['Normal']))

        # Add paragraphs
        for paragraph in paragraphs:
            story.append(Paragraph(paragraph, styles['Normal']))
            story.append(Paragraph("<br/>", styles['Normal']))

        # Build PDF
        doc.build(story)

        # Move to the beginning of the BytesIO buffer
        buffer.seek(0)

        # Send the file
        return send_file(
            buffer, 
            as_attachment=True, 
            download_name='web_scraper_results.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        logger.error(f"PDF generation error: {traceback.format_exc()}")
        return jsonify({
            "status": "error", 
            "message": f"Failed to generate PDF: {str(e)}"
        }), 500

@app.route('/scrape', methods=['POST'])
def scrape_paragraphs():
    try:
        # Get the URL from the request
        data = request.get_json()
        
        # Log the received data for debugging
        logger.info(f"Received data: {data}")
        
        # Validate URL
        url = data.get('url')
        if not url:
            return jsonify({
                "status": "error",
                "message": "No URL provided"
            }), 400

        # Ensure URL has a scheme
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Send a GET request to the URL
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Increased timeout to 30 seconds
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            return jsonify({
                "status": "error",
                "message": f"Failed to fetch the website: {str(e)}"
            }), 500

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract all paragraph texts
        paragraphs = []
        
        # Find all <p> tags, extract text, and concatenate
        for p in soup.find_all('p'):
            # Clean up the text
            text = p.get_text(strip=True)
            
            # Only add non-empty paragraphs
            if text:
                paragraphs.append(text)

        # Return JSON response
        return jsonify({
            "status": "success",
            "url": url,
            "total_paragraphs": len(paragraphs),
            "paragraphs": paragraphs
        })

    except Exception as e:
        # Log the full traceback for server-side debugging
        logger.error(f"Unexpected error: {traceback.format_exc()}")
        
        # Return a clean JSON error response
        return jsonify({
            "status": "error", 
            "message": f"An unexpected error occurred: {str(e)}"
        }), 500

# Allow running on specific port
def run_app():
    app.run(debug=True, host='0.0.0.0', port=5004)

if __name__ == '__main__':
    run_app()