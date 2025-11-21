# AI Deployment Guide - Production Checklist

## Pre-Deployment Checklist

### 1. Get DeepSeek API Key

**Platform:** https://platform.deepseek.com

**Steps:**
1. Create account or sign in
2. Navigate to API Keys section
3. Generate new API key (starts with `sk-`)
4. **Important:** Look for V3.2 or V3 API access
5. Copy key immediately (won't be shown again)

**Cost Estimate:**
- V3.2-Exp: ~$0.07/M tokens (with caching)
- Per document: ~$0.0003-0.0005
- 1,000 documents: **$0.30-0.50 USD** (75% cheaper than V3)

---

## Deployment Steps

### Step 1: Update Environment Variables

**Production (.env):**
```bash
# AI Configuration
AI_API_KEY=sk-your-actual-deepseek-key-here
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-v3.2-exp
AI_TIMEOUT=30
```

**For Docker/Cloud:**
```bash
# GitHub Secrets (if using GitHub Actions)
gh secret set AI_API_KEY --body "sk-your-key"

# Vercel (if using Vercel)
vercel env add AI_API_KEY

# Docker Compose
# Add to docker-compose.yml environment section
```

---

### Step 2: Database Migration

**⚠️ CRITICAL: Use CONCURRENTLY for Zero Downtime**

The migration uses `CREATE INDEX CONCURRENTLY` which **must** run outside a transaction.

**Option A: Direct PostgreSQL (Recommended)**
```bash
# Connect to production database
psql -h your-prod-host -U justicia -d justicia_db

# Run migration (NOT in a transaction)
\i backend/migrations/add_ai_fields_to_documents.sql
```

**Option B: Docker PostgreSQL**
```bash
# Copy migration to container
docker cp backend/migrations/add_ai_fields_to_documents.sql cabineai-db:/tmp/

# Execute migration
docker exec -it cabineai-db psql -U justicia -d justicia_db -f /tmp/add_ai_fields_to_documents.sql
```

**Verify Migration:**
```sql
-- Check columns exist
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'documents' 
  AND column_name LIKE 'ai_%';

-- Check indexes (should show 3 indexes)
SELECT indexname 
FROM pg_indexes 
WHERE tablename = 'documents' 
  AND indexname LIKE 'idx_documents_ai%';
```

**Expected Output:**
```
 column_name       | data_type
-------------------+-----------
 ai_summary        | text
 ai_classification | varchar
 ai_metadata       | jsonb
 ai_processed      | boolean
 ai_processed_at   | timestamp
 ai_error          | text

 indexname
---------------------------------
 idx_documents_ai_classification
 idx_documents_ai_processed
 idx_documents_ai_metadata
```

---

### Step 3: Test AI Service

**Run Test Script:**
```bash
cd backend
python scripts/test_ai.py
```

**Expected Output:**
```
🧪 TESTING DEEPSEEK AI SERVICE
======================================================================

📋 Configuration:
   API Key: ✅ Configured
   Base URL: https://api.deepseek.com
   Model: deepseek-v3.2-exp
   Timeout: 30s
   Service Enabled: ✅ Yes

----------------------------------------------------------------------
📄 Testing: contrat_fr
----------------------------------------------------------------------

1️⃣ Classification:
   ✅ Result: Contrat

2️⃣ Metadata Extraction:
   ✅ Extracted:
      - parties: ['Ahmed BENALI', 'Fatima ALAMI']
      - dates: ['2024-01-01', '2023-12-15']
      - amounts: [{'value': 5000, 'currency': 'MAD'}]
      - language: fr
      - location: Casablanca

3️⃣ Summarization:
   ✅ Summary:
      Contrat de location entre M. Ahmed BENALI et Mme. Fatima ALAMI...

✅ AI SERVICE TEST COMPLETED
```

**If Test Fails:**
- Check `AI_API_KEY` is set correctly
- Verify network connectivity to api.deepseek.com
- Check API key has V3.2 access
- Review logs for specific error messages

---

### Step 4: Restart Services

**Docker Compose:**
```bash
# Restart all services
docker-compose restart

# Or restart specific services
docker-compose restart app1 app2 app3 celery-cpu celery-io
```

**Systemd (if not using Docker):**
```bash
sudo systemctl restart cabineai-backend
sudo systemctl restart cabineai-celery
```

**Verify Services:**
```bash
# Check Celery workers
docker-compose logs -f celery-cpu

# Should see:
# [INFO] AIService initialized with model: deepseek-v3.2-exp
```

---

### Step 5: End-to-End Test

**Upload Test Document:**

1. Log in to CabineAI
2. Upload a sample legal document (PDF)
3. Wait for OCR processing (~10-30s)
4. Check document in database:

```sql
SELECT 
    id,
    filename,
    ocr_processed,
    ai_processed,
    ai_classification,
    ai_summary,
    ai_error
FROM documents
ORDER BY created_at DESC
LIMIT 1;
```

**Expected Result:**
```
 id | filename        | ocr_processed | ai_processed | ai_classification | ai_summary                    | ai_error
----+-----------------+---------------+--------------+-------------------+-------------------------------+----------
 42 | contrat_2024.pdf| true          | true         | Contrat           | Contrat de location entre...  | null
```

**If AI Processing Failed:**
```sql
-- Check error
SELECT id, filename, ai_error 
FROM documents 
WHERE ai_processed = false 
  AND ai_error IS NOT NULL;
```

---

## Monitoring & Maintenance

### Key Metrics to Track

**1. AI Processing Success Rate:**
```sql
SELECT 
    COUNT(*) FILTER (WHERE ai_processed = true) as processed,
    COUNT(*) FILTER (WHERE ai_processed = false AND ai_error IS NOT NULL) as failed,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(*) FILTER (WHERE ai_processed = true) / COUNT(*), 2) as success_rate
FROM documents
WHERE ocr_processed = true;
```

**2. Classification Distribution:**
```sql
SELECT 
    ai_classification, 
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM documents 
WHERE ai_processed = true 
GROUP BY ai_classification 
ORDER BY count DESC;
```

**3. Rate Limit Errors:**
```sql
SELECT COUNT(*) 
FROM documents 
WHERE ai_error LIKE '%rate_limit%' OR ai_error LIKE '%429%';
```

**4. Average Processing Time:**
```sql
SELECT 
    AVG(EXTRACT(EPOCH FROM (ai_processed_at - created_at))) as avg_seconds,
    MIN(EXTRACT(EPOCH FROM (ai_processed_at - created_at))) as min_seconds,
    MAX(EXTRACT(EPOCH FROM (ai_processed_at - created_at))) as max_seconds
FROM documents
WHERE ai_processed = true;
```

---

### Rate Limit Management

**Current Configuration:**
- Exponential backoff: 60s → 120s → 240s
- Max retries: 3
- Soft time limit: 60s

**If Hitting Rate Limits Frequently:**

1. **Reduce Celery Concurrency:**
```bash
# In docker-compose.yml
celery-cpu:
  command: celery -A app.celery_app worker --concurrency=2 --loglevel=info
  # Reduce from default (CPU count) to 2-4 workers
```

2. **Add Rate Limiting to Celery:**
```python
# In celery_config.py
task_annotations = {
    'app.tasks.ocr_tasks.process_document_ocr': {
        'rate_limit': '10/m'  # Max 10 documents per minute
    }
}
```

3. **Contact DeepSeek for Higher Limits:**
- Email: support@deepseek.com
- Request production tier access

---

### Cost Monitoring

**Track API Usage:**
```sql
-- Daily AI processing volume
SELECT 
    DATE(ai_processed_at) as date,
    COUNT(*) as documents_processed,
    COUNT(*) * 0.0004 as estimated_cost_usd
FROM documents
WHERE ai_processed = true
GROUP BY DATE(ai_processed_at)
ORDER BY date DESC;
```

**Monthly Projection:**
```sql
SELECT 
    COUNT(*) as total_documents,
    COUNT(*) * 0.0004 as estimated_monthly_cost_usd
FROM documents
WHERE ai_processed = true
  AND ai_processed_at >= NOW() - INTERVAL '30 days';
```

---

## Troubleshooting

### Issue: "AI service not enabled"

**Symptoms:**
- Logs show: `AI service not enabled. Skipping classification.`
- `ai_processed` remains `false`

**Solution:**
```bash
# Check environment variable
echo $AI_API_KEY

# Should output: sk-...
# If empty, add to .env and restart
```

---

### Issue: "Rate limit exceeded (429)"

**Symptoms:**
- `ai_error` contains "429" or "rate_limit"
- Documents retry multiple times

**Solution:**
1. Check current rate limit usage in DeepSeek dashboard
2. Reduce Celery concurrency (see above)
3. Add task rate limiting
4. Request higher limits from DeepSeek

---

### Issue: "Timeout errors"

**Symptoms:**
- `ai_error` contains "timeout"
- Large documents fail consistently

**Solution:**
```bash
# Increase timeout in .env
AI_TIMEOUT=60  # Increase from 30s to 60s

# Restart services
docker-compose restart
```

---

### Issue: "Invalid JSON in metadata"

**Symptoms:**
- `ai_metadata` is `null`
- Logs show JSON parsing errors

**Solution:**
- This is handled gracefully (metadata will be null)
- Check if specific document types cause issues
- May need to tune prompts in `ai_service.py`

---

### Issue: "Classification always returns 'Autre'"

**Symptoms:**
- All documents classified as "Autre"
- Low classification accuracy

**Solution:**
1. Review sample documents in test script
2. Update system prompt in `ai_service.py` if needed
3. Add more specific categories for your use case
4. Consider fine-tuning prompts based on real data

---

## Rollback Plan

**If AI Integration Causes Issues:**

1. **Disable AI Processing (Quick Fix):**
```bash
# Remove AI_API_KEY from .env
AI_API_KEY=

# Restart services
docker-compose restart

# Documents will still be processed with OCR, AI will be skipped
```

2. **Revert Database Changes:**
```sql
-- Remove AI columns (if needed)
ALTER TABLE documents DROP COLUMN IF EXISTS ai_summary;
ALTER TABLE documents DROP COLUMN IF EXISTS ai_classification;
ALTER TABLE documents DROP COLUMN IF EXISTS ai_metadata;
ALTER TABLE documents DROP COLUMN IF EXISTS ai_processed;
ALTER TABLE documents DROP COLUMN IF EXISTS ai_processed_at;
ALTER TABLE documents DROP COLUMN IF EXISTS ai_error;

-- Drop indexes
DROP INDEX IF EXISTS idx_documents_ai_classification;
DROP INDEX IF EXISTS idx_documents_ai_processed;
DROP INDEX IF EXISTS idx_documents_ai_metadata;
```

3. **Revert Code Changes:**
```bash
# If using git
git revert <commit-hash>
git push

# Redeploy
```

---

## Success Criteria

✅ **Deployment Complete When:**
- [ ] DeepSeek API key obtained and configured
- [ ] Database migration completed successfully
- [ ] Test script passes all tests
- [ ] Services restarted without errors
- [ ] End-to-end test document processed with AI
- [ ] Monitoring queries return expected data
- [ ] No rate limit errors in first 24 hours

---

## Next Steps After Deployment

1. **Monitor for 24-48 hours:**
   - Check success rate (should be >95%)
   - Watch for rate limit errors
   - Review cost metrics

2. **Fine-tune based on real data:**
   - Analyze classification accuracy
   - Review metadata extraction quality
   - Adjust prompts if needed

3. **Add Frontend UI:**
   - Display AI classification in document list
   - Show metadata in document details
   - Add summary preview

4. **Implement batch re-processing:**
   - Create admin tool to re-process failed documents
   - Add bulk classification updates

---

## Support

**DeepSeek Support:**
- Documentation: https://platform.deepseek.com/docs
- Email: support@deepseek.com
- Discord: https://discord.gg/deepseek

**CabineAI Issues:**
- Check logs: `docker-compose logs -f celery-cpu`
- Database queries above for diagnostics
- Review walkthrough.md for implementation details
