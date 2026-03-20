from flask import Flask, render_template, send_from_directory
import os

app = Flask(
    __name__,
    static_folder='static',      # serves /static/... correctly
    template_folder='.'          # index.html is in the same folder
)

# Serve the main page
@app.route('/')
def index():
    return render_template('index.html')

# Optional: explicit route to serve static files (Flask handles /static/ automatically)
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory(os.path.join(app.root_path, 'static'), path)

if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=5000)