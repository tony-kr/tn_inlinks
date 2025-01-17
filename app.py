from flask import Flask, request, send_file, render_template
import pandas as pd
import json
import re
import time
from bs4 import BeautifulSoup
import os
import shutil
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Define regions list
regions = ["US", "germany", "europe", "americas", "apac", "asia", "africa", "north america", "south america", "latin america",
        'United States America', 'United States', 'America', 'USA', 'Åland Islands', 'Afghanistan', 'Albania', 'Algeria', 
        'American Samoa', 'Andorra', 'Angola', 'Antigua and Barbuda', 'Argentina', 'Armenia',
        'Aruba', 'Australia', 'Austria', 'Azerbaijan', 'Bahamas', 'Bahrain',
        'Bangladesh', 'Barbados', 'Belarus', 'Belgium', 'Belize', 'Benin',
        'Bermuda', 'Bhutan', 'Bolivia', 'Bosnia and Herzegovina', 'Botswana',
        'Brazil', 'Virgin Islands', 'Brunei Darussalam', 'Bulgaria',
        'Burkina Faso', 'Burundi', 'Cabo Verde', 'Cambodia', 'Cameroon',
        'Canada', 'Cayman Islands', 'Central African Republic', 'Chad',
        'Chile', 'China', 'Colombia', 'Comoros', 'Congo',
        'Congo (the Democratic Republic of the)', 'Cook Islands', 'Costa Rica',
        "Côte d'Ivoire", 'Croatia', 'Cuba', 'Curaçao', 'Cyprus', 'Czechia',
        'Denmark', "Korea (the Democratic People's Republic of)", 'Djibouti',
        'Dominica', 'Dominican Republic', 'Ecuador', 'Egypt', 'El Salvador',
        'Equatorial Guinea', 'Eritrea', 'Estonia', 'Eswatini', 'Ethiopia',
        'Faroe Islands', 'Fiji', 'Finland', 'France', 'French Polynesia',
        'Micronesia', 'Gabon', 'Gambia', 'Georgia', 'Germany', 'Ghana',
        'Gibraltar', 'Greece', 'Greenland', 'Grenada', 'Guadeloupe', 'Guam',
        'Guinea', 'Guinea-Bissau', 'Guyana', 'Haiti', 'Honduras', 'Hong Kong',
        'Hungary', 'Iceland', 'India', 'Indonesia', 'Iran', 'Iraq', 'Ireland',
        'Isle of Man', 'Israel', 'Italy', 'Jamaica', 'Japan', 'Jordan',
        'Kazakhstan', 'Kenya', 'Kiribati', 'Korea', 'Kuwait', 'Kyrgyzstan',
        'Réunion', "Lao People's Democratic Republic", 'Latvia', 'Lebanon',
        'Lesotho', 'Liberia', 'Libya', 'Liechtenstein', 'Lithuania',
        'Luxembourg', 'Macao', 'Madagascar', 'Malawi', 'Malaysia', 'Maldives',
        'Mali', 'Malta', 'Marshall Islands', 'Martinique', 'Mauritania',
        'Mauritius', 'Mayotte', 'Mexico', 'Moldova', 'Monaco', 'Mongolia',
        'Montenegro', 'Montserrat', 'Morocco', 'Mozambique', 'Myanmar',
        'Namibia', 'Nauru', 'Nepal', 'Netherlands', 'New Caledonia',
        'New Zealand', 'Nicaragua', 'Niger', 'Nigeria',
        'Republic of North Macedonia', 'Northern Mariana Islands', 'Norway',
        'Oman', 'Pakistan', 'Palau', 'Palestine', 'Panama', 'Papua New Guinea',
        'Paraguay', 'Peru', 'Philippines', 'Poland', 'Portugal', 'Puerto Rico',
        'Qatar', 'Romania', 'Russian Federation', 'Russia', 'Rwanda',
        'Saint Kitts and Nevis', 'Saint Lucia',
        'Saint Vincent and the Grenadines', 'Samoa', 'San Marino',
        'Sao Tome and Principe', 'Saudi Arabia', 'Senegal', 'Serbia',
        'Seychelles', 'Sierra Leone', 'Singapore', 'Sint Maarten', 'Slovakia',
        'Slovenia', 'Solomon Islands', 'Somalia', 'South Africa',
        'South Sudan', 'Spain', 'Sri Lanka', 'Saint Martin', 'Sudan',
        'Suriname', 'Svalbard and Jan Mayen', 'Sweden', 'Switzerland',
        'Syrian Arab Republic', 'Turkey', 'Taiwan', 'Tajikistan', 'Tanzania',
        'Thailand', 'Timor-Leste', 'Togo', 'Tonga', 'Trinidad and Tobago',
        'Tunisia', 'Turkmenistan', 'Turks and Caicos Islands', 'Tuvalu',
        'Uganda', 'Ukraine', 'United Arab Emirates', 'UAE', 'United Kingdom',
        'UK', 'Uruguay', 'Uzbekistan', 'Wallis and Futuna', 'Vanuatu', 
        'Venezuela', 'Viet Nam', 'Yemen', 'Zambia', 'Zimbabwe']

def process_content(tasks_text, filename, df_keywords):
    """Combined processing function that does what the API used to do"""
    start_time = time.time()
    soup = BeautifulSoup(tasks_text, 'html.parser')
    tasks_text = soup.get_text()
    
    try:
        h2 = soup.h2.text.lower()
    except AttributeError:
        h2 = ""
    
    output = []
    seen_keywords = set()
    tasks_lower = tasks_text.lower()
    
    for item in df_keywords['Keyword'].tolist():
        if item in seen_keywords or item in h2:
            continue
        
        escaped_item = ' '.join(re.escape(word) for word in item.split())
        pattern = rf"\b{escaped_item}s?\b" if ' ' not in item else rf"\b{escaped_item}\b"
        
        try:
            if re.search(pattern, tasks_lower):
                url = df_keywords.loc[df_keywords['Keyword'] == item, "URL in TN"].values[0]
                output.append({"keyword": item, "url": url})
                seen_keywords.add(item)
        except re.error:
            continue
    
    return {
        "input": tasks_text,
        "filename": filename,
        "output": output
    }

def create_zip(output_dir):
    """Create a zip file from the output directory"""
    zip_path = f"{output_dir}.zip"
    shutil.make_archive(output_dir, 'zip', output_dir)
    return zip_path

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    try:
        # Create unique session ID for this processing
        session_id = str(uuid.uuid4())
        session_upload_dir = os.path.join(UPLOAD_FOLDER, session_id)
        session_output_dir = os.path.join(OUTPUT_FOLDER, session_id)
        os.makedirs(session_upload_dir, exist_ok=True)
        os.makedirs(session_output_dir, exist_ok=True)

        # Save uploaded files
        uploaded_csv = request.files['csv']
        uploaded_excel = request.files['excel']

        if not uploaded_csv or not uploaded_excel:
            return 'Please upload both CSV and Excel files', 400

        csv_path = os.path.join(session_upload_dir, secure_filename(uploaded_csv.filename))
        excel_path = os.path.join(session_upload_dir, secure_filename(uploaded_excel.filename))
        
        uploaded_csv.save(csv_path)
        uploaded_excel.save(excel_path)

        # Read master data
        df_keywords = pd.read_excel(excel_path)
        df_keywords['Keyword'] = df_keywords['Keyword'].str.lower().str.strip()
        
        # Read input CSV
        df_input = pd.read_csv(csv_path)
        
        # Process each row
        for index, row in df_input.iterrows():
            result = process_content(row["CONTENT"], row["SKU"], df_keywords)
            
            # Filter regions
            filtered_output = [
                item for item in result['output'] 
                if not any(f"\\b{re.escape(region.lower())}\\b" in item['url'].lower() 
                          for region in regions)
            ]
            
            result['output'] = filtered_output
            
            # Save output
            output_path = os.path.join(session_output_dir, f"{row['SKU']}.json")
            with open(output_path, "w") as f:
                json.dump(result, f)
        
        # Create zip file
        zip_path = create_zip(session_output_dir)
        
        # Clean up uploaded files and output directory
        shutil.rmtree(session_upload_dir)
        shutil.rmtree(session_output_dir)
        
        # Send zip file
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name='output.zip'
        )

    except Exception as e:
        return str(e), 500

    finally:
        # Clean up zip file
        if 'zip_path' in locals():
            os.remove(zip_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
