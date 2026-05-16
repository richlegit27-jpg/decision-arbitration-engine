from attachment_compat import attachment_compat, extract_attachments_from_json

def register_attachment_compat(app):
    app.register_blueprint(attachment_compat)
    app.extract_attachments_from_json = extract_attachments_from_json
    return app