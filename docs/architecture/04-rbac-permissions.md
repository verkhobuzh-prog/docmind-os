# RBAC + ABAC — DocMind OS

## Role hierarchy

```
Platform Admin (internal)
    └── Organization Owner
            └── Organization Admin
                    └── Workspace Admin
                            └── Member
                                    └── Viewer
                                            └── AI Agent (service account)
```

**Priority on conflict:** Owner > Admin > Member > Viewer > AI Agent

---

## Permissions matrix

| Resource / Action | Owner | Admin | Member | Viewer | AI Agent |
|-------------------|:-----:|:-----:|:------:|:------:|:--------:|
| org.settings.update | ✅ | ✅ | ❌ | ❌ | ❌ |
| org.billing.manage | ✅ | ❌ | ❌ | ❌ | ❌ |
| workspace.create | ✅ | ✅ | ❌ | ❌ | ❌ |
| workspace.delete | ✅ | ✅ | ❌ | ❌ | ❌ |
| member.invite | ✅ | ✅ | ❌ | ❌ | ❌ |
| member.remove | ✅ | ✅ | ❌ | ❌ | ❌ |
| document.upload | ✅ | ✅ | ✅ | ❌ | ✅* |
| document.read | ✅ | ✅ | ✅ | ✅ | ✅* |
| document.update | ✅ | ✅ | ✅ | ❌ | ❌ |
| document.delete | ✅ | ✅ | own | ❌ | ❌ |
| document.share | ✅ | ✅ | ✅ | ❌ | ❌ |
| chat.query | ✅ | ✅ | ✅ | ✅ | ✅* |
| search.semantic | ✅ | ✅ | ✅ | ✅ | ✅* |
| audit.read | ✅ | ✅ | ❌ | ❌ | ❌ |
| api_key.manage | ✅ | ✅ | ❌ | ❌ | ❌ |
| integration.connect | ✅ | ✅ | ❌ | ❌ | ❌ |

\* AI Agent: scoped to `agent_permissions` JSON per workspace; never billing/admin.

---

## ABAC attributes

| Attribute | Source | Use |
|-----------|--------|-----|
| `org_id` | JWT claim / membership | Tenant isolation |
| `workspace_id` | Request context | Resource scope |
| `user_id` | auth.uid() | Ownership |
| `document.classification` | metadata | confidential → restrict export |
| `org.plan` | organizations.plan | feature flags, quotas |
| `ip_country` | GeoIP | data residency |

```python
# Policy evaluation (Phase 2)
def can(user: User, action: str, resource: Resource) -> bool:
    if not rbac_allows(user.role, action):
        return False
    if resource.classification == "confidential" and action == "document.export":
        return user.role in ("owner", "admin")
    if org_quota_exceeded(user.org_id, action):
        return False
    return True
```

---

## JWT claims (Supabase custom)

```json
{
  "sub": "user-uuid",
  "org_id": "org-uuid",
  "workspace_ids": ["ws-1", "ws-2"],
  "role": "member",
  "plan": "pro"
}
```
