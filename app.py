import re
import sqlite3
import pandas as pd
from flask import Flask, jsonify, request
from flasgger import LazyJSONEncoder, LazyString, Swagger, swag_from

app = Flask(__name__)
app.json_provider_class = LazyJSONEncoder 
app.json = LazyJSONEncoder(app)

swagger_template = dict(
    info = {
        'title' : LazyString(lambda: 'API Documentation for Data Processing and Modeling'),
        'version' : LazyString(lambda: '1.0.0'),
        'description' : LazyString(lambda: 'Dokumentasi API untuk Data Processing dan Modeling'),
    }, 
    host = LazyString(lambda: request.host)
)

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'docs',
            "route": '/docs.json'
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/"
}

swagger = Swagger(app, template=swagger_template, config=swagger_config)

conn = sqlite3.connect('database.db', check_same_thread=False)
df_new_kamusalay = pd.read_sql_query('SELECT * FROM newKamusAlay', conn)
df_abusive = pd.read_sql_query('SELECT * FROM abusive', conn)

def clean_text(text, df_new_kamusalay, df_abusive):
    for index, row in df_new_kamusalay.iterrows():
        slang = row['Typo_Slang']
        formal = row['Formal_Word']
        text = re.sub(r'\b{}\b'.format(re.escape(slang)), formal, text)
    
    text = re.sub('@[^\text]+', ' ', text)
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub('<.*?>', ' ', text)
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    text = re.sub('\n', ' ', text)
    text = text.lower()
    text = re.sub(r'\b[a-zA-Z]\b', ' ', text)
    
    for index, row in df_abusive.iterrows():
        abusive_word = row['Abusive_Word']
        replacement = row['Replacement_Word']
        text = re.sub(r'\b{}\b'.format(re.escape(abusive_word)), replacement, text)
    
    text = ' '.join(text.split())
    
    return text

@swag_from("docs/hello_world.yml", methods=['GET'])
@app.route('/', methods=['GET'])
def hello_world():
    json_response = {
        'status_code' : 200,
        'description' : "Menyapa Hello World",
        'data' : "Hello World",
    }
    response_data = jsonify(json_response)
    return response_data

@swag_from("docs/text.yml", methods=['GET'])
@app.route('/text', methods=['GET'])
def text():
    json_response = {
        'status_code' : 200,
        'description' : "Original Teks",
        'data' : "Halo, apa kabar semua?",
    }
    response_data = jsonify(json_response)
    return response_data

@swag_from("docs/text_clean.yml", methods=['GET'])
@app.route('/text-clean', methods=['GET'])
def text_clean():
    cleaned_text = clean_text("Halo, apa kabar semua?", df_new_kamusalay, df_abusive)
    json_response = {
        'status_code' : 200,
        'description' : "Original Teks",
        'data' : cleaned_text,
    }
    response_data = jsonify(json_response)
    return response_data

@swag_from("docs/text_processing.yml", methods=['POST'])
@app.route('/text-processing', methods=['POST'])
def text_processing():
    file = request.files.getlist('file')[0]
    df = pd.read_csv(file, encoding='latin-1')
    texts = df.Tweet.to_list()
    cleaned_text = [clean_text(Tweet, df_new_kamusalay, df_abusive) for Tweet in texts]
    df['Cleaned_Text'] = cleaned_text
    cleaned_file = 'cleaned_' + file.filename
    df.to_csv(cleaned_file, index=False)
    json_response = {
        'status_code': 200,
        'description': "Teks yang akan diproses",
        'cleaned_file': cleaned_file
    }
    response_data = jsonify(json_response)
    return response_data

if __name__ == '__main__':
    app.run(debug=True, port=8080, use_reloader=False)
