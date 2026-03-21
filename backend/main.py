from flask import Flask, render_template, request, Response, stream_with_context
import openai, os

# Set your OpenAI API key in environment
openai.api_key = os.environ.get("OPENAI_API_KEY")

app = Flask(__name__)

# --- Home page ---
@app.route("/")
def home():
    return render_template("index.html")

# --- Streaming GPT endpoint ---
@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    data = request.json
    message = data.get("message", "")
    chat_id = data.get("chat_id", "")

    def generate():
        try:
            # Streaming GPT-4.1-mini response
            response = openai.chat.completions.stream(
                model="gpt-4.1-mini",
                messages=[{"role":"user","content":message}],
                temperature=0.7,
            )
            for event in response:
                if event.type == "response.output_text.delta":
                    yield event.delta
        except Exception as e:
            yield f"Error: {str(e)}"

    return Response(stream_with_context(generate()), mimetype="text/plain")

if __name__ == "__main__":
    # Run Flask natively (WSGI)
    app.run(debug=True)