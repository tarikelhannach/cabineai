import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_search_documents_api():
    """
    Verify that the /api/search/documents endpoint performs a full-text search over documents
    and returns relevant search results based on query parameters.
    """

    # Example query parameter for full-text search
    query_params = {
        "q": "contract termination"
    }
    url = f"{BASE_URL}/api/search/documents"

    try:
        response = requests.get(url, params=query_params, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request to search documents API failed: {e}"

    # Validate response
    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not a valid JSON"

    # Assuming the response is a JSON object with a list of documents in a key named "results"
    assert "results" in data, "Response JSON does not contain 'results' key"
    assert isinstance(data["results"], list), "'results' is not a list"

    # Check that at least 1 search result is returned (assuming indexed test data exists)
    assert len(data["results"]) > 0, "No search results returned for valid query"

    # Each item should have relevant fields, for example: id, title, snippet
    for doc in data["results"]:
        assert isinstance(doc, dict), "Each search result should be a dict"
        assert "id" in doc, "Document in results missing 'id'"
        assert "title" in doc, "Document in results missing 'title'"
        assert "snippet" in doc, "Document in results missing 'snippet'"

test_search_documents_api()