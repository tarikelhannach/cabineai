
# TestSprite AI Testing Report(MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** cabineai
- **Date:** 2025-11-20
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

#### Test TC001
- **Test Name:** test_user_login_api
- **Test Code:** [TC001_test_user_login_api.py](./TC001_test_user_login_api.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 38, in <module>
  File "<string>", line 25, in test_user_login_api
AssertionError: access_token is missing in response

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8fc77480-0afb-4f23-b239-ab2773f10ba3/49a68c73-9c99-481c-9d1d-3d7928276b88
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC002
- **Test Name:** test_document_upload_api
- **Test Code:** [TC002_test_document_upload_api.py](./TC002_test_document_upload_api.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 77, in <module>
  File "<string>", line 23, in test_document_upload_api
AssertionError: Case creation response missing 'id': {'status': 'ok'}

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8fc77480-0afb-4f23-b239-ab2773f10ba3/4d8921f5-d86a-46cc-ab34-919e1cd57f50
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC003
- **Test Name:** test_case_creation_api
- **Test Code:** [TC003_test_case_creation_api.py](./TC003_test_case_creation_api.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 36, in <module>
  File "<string>", line 19, in test_case_creation_api
AssertionError: Expected status code 201, got 200

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8fc77480-0afb-4f23-b239-ab2773f10ba3/ab5cf73b-cb65-48af-ab43-df201f251f83
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC004
- **Test Name:** test_chat_send_message_api
- **Test Code:** [TC004_test_chat_send_message_api.py](./TC004_test_chat_send_message_api.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 34, in <module>
  File "<string>", line 29, in test_chat_send_message_api
AssertionError: Response does not contain AI-generated response

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8fc77480-0afb-4f23-b239-ab2773f10ba3/7511b214-41bb-4704-ac0c-1fc0ec36e03d
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC005
- **Test Name:** test_ai_document_classification_api
- **Test Code:** [TC005_test_ai_document_classification_api.py](./TC005_test_ai_document_classification_api.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 99, in <module>
  File "<string>", line 67, in test_ai_document_classification_api
AssertionError: Failed to obtain auth token

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8fc77480-0afb-4f23-b239-ab2773f10ba3/cd5c15df-aadc-4a47-ae82-6cb2532379cc
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC006
- **Test Name:** test_document_drafting_generate_template_api
- **Test Code:** [TC006_test_document_drafting_generate_template_api.py](./TC006_test_document_drafting_generate_template_api.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 64, in <module>
  File "<string>", line 36, in test_document_drafting_generate_template_api
AssertionError

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8fc77480-0afb-4f23-b239-ab2773f10ba3/140a1d3e-b9de-4903-93f2-64d11113d7ac
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC007
- **Test Name:** test_search_documents_api
- **Test Code:** [TC007_test_search_documents_api.py](./TC007_test_search_documents_api.py)
- **Test Error:** Traceback (most recent call last):
  File "<string>", line 20, in test_search_documents_api
  File "/var/task/requests/models.py", line 1024, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 404 Client Error: Not Found for url: http://localhost:8000/api/search/documents?q=contract+termination

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 44, in <module>
  File "<string>", line 22, in test_search_documents_api
AssertionError: Request to search documents API failed: 404 Client Error: Not Found for url: http://localhost:8000/api/search/documents?q=contract+termination

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8fc77480-0afb-4f23-b239-ab2773f10ba3/8dfe2b61-716b-47ef-a783-3e356ab58d04
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC008
- **Test Name:** test_user_creation_api
- **Test Code:** [TC008_test_user_creation_api.py](./TC008_test_user_creation_api.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 61, in <module>
  File "<string>", line 38, in test_user_creation_api
AssertionError: Response missing user id

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8fc77480-0afb-4f23-b239-ab2773f10ba3/7ac76011-98de-4e86-9ffa-10ae1b825b68
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC009
- **Test Name:** test_billing_create_checkout_session_api
- **Test Code:** [TC009_test_billing_create_checkout_session_api.py](./TC009_test_billing_create_checkout_session_api.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 49, in <module>
  File "<string>", line 36, in test_billing_create_checkout_session_api
AssertionError: Response missing 'id' field: {'status': 'ok'}

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8fc77480-0afb-4f23-b239-ab2773f10ba3/6b8b442a-3153-4867-a0fb-6611105b0b10
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test TC010
- **Test Name:** test_audit_logs_retrieval_api
- **Test Code:** [TC010_test_audit_logs_retrieval_api.py](./TC010_test_audit_logs_retrieval_api.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 40, in <module>
  File "<string>", line 17, in test_audit_logs_retrieval_api
AssertionError: Expected status code 200, got 404

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8fc77480-0afb-4f23-b239-ab2773f10ba3/b1aeb1b4-4a2e-4819-8675-0444d83edfb6
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---


## 3️⃣ Coverage & Matching Metrics

- **0.00** of tests passed

| Requirement        | Total Tests | ✅ Passed | ❌ Failed  |
|--------------------|-------------|-----------|------------|
| ...                | ...         | ...       | ...        |
---


## 4️⃣ Key Gaps / Risks
{AI_GNERATED_KET_GAPS_AND_RISKS}
---