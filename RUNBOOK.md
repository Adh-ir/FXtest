# Disaster Recovery Runbook

This document outlines recovery procedures for the Forex Rate Extractor application.

---

## 1. Secret Rotation (API Key Compromise)

If your Twelve Data API key is compromised:

1. **Revoke the old key** at [Twelve Data API Keys](https://twelvedata.com/account/api-keys)
2. **Generate a new key** from the same dashboard
3. **Clear browser cookies** or use incognito mode
4. **Re-enter the new key** in the application

**RTO**: ~1 minute

---

## 2. Application Rollback

To roll back to a previous version:

```bash
# List recent commits
git log --oneline -10

# Roll back to specific commit
git checkout <commit-hash>

# Rebuild container
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**RTO**: ~5 minutes

---

## 3. Container Recovery

If the container crashes:

- **Automatic recovery**: The `restart: unless-stopped` policy auto-restarts
- **Manual restart**:
  ```bash
  docker-compose restart app
  ```
- **Full rebuild**:
  ```bash
  docker-compose down
  docker-compose up -d --build
  ```

**RTO**: ~30 seconds (automatic), ~2 minutes (manual rebuild)

---

## 4. Health Check

Verify application health:

```bash
curl http://localhost:8501/_stcore/health
```

Expected response: `{"status": "ok"}`

---

## 5. Data Loss Scenarios

| Data Type | Recovery Method |
|-----------|-----------------|
| API Key | Re-enter from Twelve Data account |
| Uploaded files | User re-uploads (ephemeral by design) |
| Processed results | Regenerate from source files |
| Application code | `git checkout main` |

---

## 6. Contact Information

- **Twelve Data Support**: https://twelvedata.com/contact
- **GitHub Issues**: https://github.com/[your-repo]/issues

---

## 7. Monitoring Checklist

- [ ] Container health check passing (every 30s)
- [ ] Memory usage under 512MB limit
- [ ] CPU usage under 50% limit
- [ ] No CVEs in latest `pip-audit` run
