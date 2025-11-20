import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_document_drafting_generate_template_api():
    url_template_create = f"{BASE_URL}/api/drafting/templates"
    url_generate = f"{BASE_URL}/api/drafting/generate/template"

    headers = {
        "Content-Type": "application/json"
    }

    # Sample template data to create a template for testing
    template_data = {
        "name": "Test Template",
        "description": "Template for testing document drafting generation",
        "content": "This is a legal template with placeholder {{client_name}}."
    }

    # Sample payload for generate template endpoint
    generate_payload = {
        "template_name": None,
        "parameters": {
            "client_name": "John Doe"
        }
    }

    template_id = None

    # Create a template first to ensure we have a template to generate from
    try:
        create_resp = requests.post(url_template_create, json=template_data, headers=headers, timeout=TIMEOUT)
        assert create_resp.status_code == 201 or create_resp.status_code == 200, f"Template creation failed: {create_resp.text}"
        created_template = create_resp.json()
        assert "name" in created_template and created_template["name"] == template_data["name"]
        assert "id" in created_template, "Template ID not found in creation response"

        # Extract template identifier
        template_id = created_template["id"]

        # Use the template name for generation as the API requires name
        generate_payload["template_name"] = template_data["name"]

        # Call the generate template endpoint
        gen_resp = requests.post(url_generate, json=generate_payload, headers=headers, timeout=TIMEOUT)
        assert gen_resp.status_code == 200, f"Document generation failed: {gen_resp.text}"

        gen_result = gen_resp.json()

        # Validate that generated document content is returned and contains expected replaced parameter
        assert isinstance(gen_result, dict), "Generated response is not a JSON object"
        assert "generated_document" in gen_result

        content = gen_result.get("generated_document")
        assert isinstance(content, str), "Generated document content is not a string"
        assert "John Doe" in content, "Generated document content does not contain replaced parameter value"

    finally:
        # Cleanup: Delete the created template if delete endpoint supported
        # No delete template endpoint documented; so skipping delete step
        pass

test_document_drafting_generate_template_api()
