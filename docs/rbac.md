# RBAC - Users, Groups, and Permissions

SSP uses a group-based permission model designed for enterprise compliance (SOX, PCI DSS) while maintaining operational simplicity.

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PERMISSION MODEL                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Authenticated User                                                │
│         │                                                           │
│         ├── Baseline Access (implicit SystemRole: user)             │
│         │     • View Plugins list (cards only)                      │
│         │     • View Blueprints list (cards only)                    │
│         │     • View Projects list (own projects only)              │
│         │     • View Docs                                           │
│         │                                                           │
│         └── Group(s) ─────► SystemRole(s)                           │
│               │                                                     │
│               ├── SystemRoles                                       │
│               │     • admin                                         │
│               │     • operator                                      │
│               │     • auditor                                       │
│               │                                                     │
│               └── ProjectMembership(s) ─► project_role              │
│                     • owner                                         │
│                     • contributor                                   │
│                     • viewer                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Principles:**
- All permissions come from **Groups + SystemRoles** (no special "admin user" flag)
- Users access projects through Groups only (no individual project membership, for compatibility with AD-first workflows)
- Authenticated users have baseline read-only access for platform discovery (implicit `user` SystemRole)
- All access is traceable: User → Group → SystemRole/ProjectMembership
- Integrates seamlessly with SSO/LDAP systems

---

## Initial Setup

When Pathfinder is first installed:

1. **Unlock**: First user enters the unlock token from `secrets/initialUnlockToken`
2. **Create Account**: User creates their account (username, email, password)
3. **Automatic Setup**: Pathfinder automatically:
   - Creates a local group called `admins`
   - Attaches the `admin` SystemRole to this group
   - Adds the first user to the `admins` group
4. **Ready**: First user now has full system access and can:
   - Create more users and groups
   - Configure OIDC/LDAP integration
   - Create projects, integrations, blueprints, etc.

Roadmap item:
  - Create an option to use an IaC `yaml`/`toml` configuration file for setting up connection to AD/LDAP/SSO systems as source of truth for users and groups before the initial setup, rendering the unlock procedure and local admin group unnecessary. Allow mapping SystemRoles to external groups via IaC configuration.

### Session Management

- Sessions expire after 1 day by default
- "Remember me" checkbox extends session persistence to 7 days
- Sessions are invalidated on logout

---

## Users

### User Model

```
User:
  - id: UUID
  - username: string (unique, DNS-compatible)
  - email: string (unique)
  - full_name: string
  - status: enum (active, inactive)
  - source: enum (local, oidc, ldap)
  - external_id: string (nullable, for SSO sync)
  - last_login: datetime
  - created_at: datetime
  - updated_at: datetime
```

### Baseline Authenticated User

Every authenticated user (regardless of group membership) has implicit access to:

| Resource | Access |
|----------|--------|
| Plugins list | View available integration types (cards) |
| Blueprints list | View cards (name, description, tags) - no details |
| Projects list | View only projects where user has membership |
| Docs | Full read access |

This enables platform discovery without requiring any group assignment. All authenticated users implicitly have the `user` SystemRole.

---

## Groups

Groups are containers for users that can be assigned to projects. They enable:
- Bulk user management
- Seamless OIDC/LDAP synchronization (future)
- Clear audit trails

### Group Model

```
Group:
  - id: UUID
  - name: string (unique, DNS-compatible, max 63 chars)
  - description: text
  - source: enum (local, oidc, ldap)
  - external_id: string (nullable, for SSO sync)
  - system_roles: array of SystemRole names
  - status: enum (active, inactive)
  - created_at: datetime
  - updated_at: datetime
```

### Group Membership

```
GroupMembership:
  - group: FK Group
  - user: FK User
  - created_at: datetime
```

### Example Groups

```yaml
# Created automatically during initial setup
Group: admins
  description: "System administrators"
  source: local
  system_roles:
    - admin
  # Full system access

# Platform engineering team (from AD/OIDC)
Group: platform-operators
  description: "Platform operators with system-wide permissions"
  source: oidc
  external_id: "ssp-platform-operators"
  system_roles:
    - operator
  # Manages integrations and blueprints

# Development team owners (from AD/OIDC)
Group: team-a-owners
  description: "Team A senior developers"
  source: oidc
  external_id: "ssp-team-a-owners"
  system_roles: []  # No system roles
  # Assigned to team-a project with 'owner' project role

# Development team (from AD/OIDC)
Group: team-a-developers
  description: "Team A developers"
  source: oidc
  external_id: "ssp-team-a-developers"
  system_roles: []  # No system roles
  # Assigned to team-a project with 'contributor' project role

# Security/Compliance team
Group: security-auditors
  description: "Security and compliance team"
  source: oidc
  external_id: "ssp-security-auditors"
  system_roles:
    - auditor
  # Can view all projects read-only
```

---

## System Roles

SystemRoles are predefined system-wide roles. They are **non-editable** in the current implementation (custom roles are on the roadmap).

### Available SystemRoles

| SystemRole | Permissions | Use Case |
|------------|-------------|----------|
| `admin` | Full system access: users, groups, projects, environments, integrations, blueprints, audit | Initial admin, platform team leads |
| `operator` | Manage integrations and blueprints: create, edit, delete connections; register, sync, delete blueprints | Platform/Ops team |
| `auditor` | View all audit logs; export access reports; view all projects (read-only) | Security/Compliance auditors |
| `user` | Baseline access (implicit for all authenticated users): view plugins, blueprints, own projects | All authenticated users |

---

## Project Roles

ProjectRoles are assigned when a Group is added to a Project:

| ProjectRole | Permissions |
|-------------|-------------|
| `owner` | Project-level control (settings, environments, services, prod deployments) |
| `contributor` | Create/edit services, deploy to non-production, view all |
| `viewer` | View-only access to project, services, deployments |

**Note:** Project/environment creation and deletion requires `admin` SystemRole.

---

## Project Membership

Projects are accessed through Groups only. A Group is assigned to a Project with a specific project role.

### ProjectMembership Model

```
ProjectMembership:
  - project: FK Project
  - group: FK Group
  - project_role: enum (owner, contributor, viewer)
  - added_by: string (username, denormalized)
  - created_at: datetime
```

### Example

```yaml
User: alice
  groups: [team-a-developers, senior-devs]

Group: team-a-developers
  projects:
    - team-a: contributor

Group: senior-devs
  projects:
    - team-a: owner
    - team-b: contributor

Alice's effective access:
  - team-a: owner (highest of contributor, owner)
  - team-b: contributor
```
---

### Export Formats

- **PDF**: Formatted permission matrix for external auditors
- **CSV**: Raw data for spreadsheet analysis
- **JSON**: Machine-readable for automated compliance tools

---

## Access Control Summary

### System-Level Permissions

| Action | admin | operator | auditor | user |
|--------|-------|----------|---------|------|
| Manage users/groups | ✓ | - | - | - |
| Create/delete projects | ✓ | - | - | - |
| Create/delete environments | ✓ | - | - | - |
| Manage connections | ✓ | ✓ | - | - |
| Manage blueprints | ✓ | ✓ | - | - |
| View audit logs | ✓ | - | ✓ | - |
| View all projects (read) | ✓ | - | ✓ | - |
| View plugins list | ✓ | ✓ | ✓ | ✓ |
| View blueprints list | ✓ | ✓ | ✓ | ✓ |
| View docs | ✓ | ✓ | ✓ | ✓ |

### Project-Level Permissions

| Action | owner | contributor | viewer |
|--------|-------|-------------|--------|
| View project | ✓ | ✓ | ✓ |
| Edit project settings | ✓ | - | - |
| Manage group memberships | ✓ | - | - |
| Edit environment settings | ✓ | - | - |
| Create services | ✓ | ✓ | - |
| Edit services | ✓ | ✓ | - |
| Delete services | ✓ | - | - |
| Deploy to non-prod | ✓ | ✓ | - |
| Deploy to production | ✓ | - | - |
| View deployments | ✓ | ✓ | ✓ |
| Rollback | ✓ | ✓ | - |

**Note:** Project/environment creation and deletion requires `admin` SystemRole.

---

## Audit Considerations

### What Gets Logged

All permission-related actions are logged:
- User login/logout
- Group membership changes
- Project membership changes (group assignment)
- SystemRole assignments
- Access attempts (successful and denied)

### Compliance Reports

Available exports for auditors:
1. **User Access Report**: All users with their effective permissions
2. **Project Access Report**: All users who can access a specific project
3. **Permission Changes Report**: Timeline of permission changes
4. **Login History Report**: User login activity
