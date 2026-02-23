# Projects

Projects are the primary organizational unit in Pathfinder. They group related Services and define shared configuration.

## Project Model

```
Project:
  - name: string (unique, DNS-compatible, max 20 chars)
  - description: text
  - env_vars: array of { key, value, lock, description }
  - status: enum (active, inactive, archived)
  - created_by: string (username, denormalized)
  - created_at, updated_at: datetime
```

---

## Project Features

### Membership

Projects are accessed through **Groups** (not individual users). A Group is assigned to a Project with a project role.

```
ProjectMembership:
  - project: FK Project
  - group: FK Group
  - project_role: enum (owner, contributor, viewer)
  - added_by: string (username, denormalized)
  - created_at: datetime
```

**Project Roles:**
- **owner**: Project control (settings, environments, services, prod deploy)
- **contributor**: Create/edit services, deploy to non-production
- **viewer**: Read-only access

**Access Resolution:**
- Users with `admin` and `operator` SystemRole have automatic owner access to all projects
- Users access projects via their Group memberships
- If a user is in multiple groups with different roles, highest role wins

See [rbac.md](rbac.md) for full permission model documentation.

### Environments

- Each Project has one or more Environments (dev, stg, prod)
- Environments are created within a Project context
- See [environments.md](environments.md) for Environment model details

### Services

- Services belong to exactly one Project
- Service names are unique within a Project
- See [services.md](services.md) for Service model and lifecycle details

---

## Environment Variables

Project is the top level of the variable cascade. Variables defined here are inherited by Services and Environments. See [Environment Variables](env-vars.md) for variable shape, cascade rules, and override logic.

`PTF_PROJECT` is system-injected (locked) with the project name as its value.

---

## Access Control

| Action | admin | owner | contributor | viewer |
|--------|-------|-------|-------------|--------|
| View project | ✓ | ✓ | ✓ | ✓ |
| Edit project settings | ✓ | ✓ | - | - |
| Delete project | ✓ | - | - | - |
| Manage group memberships | ✓ | ✓ | - | - |
| Create environments | ✓ | - | - | - |
| Delete environments | ✓ | - | - | - |
| Edit environment settings | ✓ | ✓ | - | - |
| Create services | ✓ | ✓ | ✓ | - |
| Delete services | ✓ | ✓ | - | - |
| Deploy to non-prod | ✓ | ✓ | ✓ | - |
| Deploy to production | ✓ | ✓ | - | - |

**Notes:**
- `admin` and `operator` SystemRoles grant owner access to all projects
- Only `admin` and `operator` can create/delete projects and environments
- Project owners can manage within the project, but cannot delete the project itself
- Project deletion requires removing all services first
- Deactivating a project prevents new deployments but keeps existing services running

See [rbac.md](rbac.md) for full permission model and audit export documentation.
