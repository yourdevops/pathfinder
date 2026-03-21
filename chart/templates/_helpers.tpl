{{/*
Expand the name of the chart.
*/}}
{{- define "pathfinder.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "pathfinder.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "pathfinder.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "pathfinder.labels" -}}
helm.sh/chart: {{ include "pathfinder.chart" . }}
{{ include "pathfinder.selectorLabels" . }}
app.kubernetes.io/version: {{ .Values.image.tag | default .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "pathfinder.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pathfinder.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "pathfinder.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "pathfinder.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
PostgreSQL fully qualified name
*/}}
{{- define "pathfinder.postgresql.fullname" -}}
{{- printf "%s-postgresql" (include "pathfinder.fullname" .) }}
{{- end }}

{{/*
App secret name (supports existingSecret)
*/}}
{{- define "pathfinder.secretName" -}}
{{- if .Values.secrets.existingSecret }}
{{- .Values.secrets.existingSecret }}
{{- else }}
{{- include "pathfinder.fullname" . }}
{{- end }}
{{- end }}

{{/*
PostgreSQL secret name (supports existingSecret)
*/}}
{{- define "pathfinder.postgresql.secretName" -}}
{{- if .Values.postgresql.auth.existingSecret }}
{{- .Values.postgresql.auth.existingSecret }}
{{- else }}
{{- include "pathfinder.postgresql.fullname" . }}
{{- end }}
{{- end }}

{{/*
Common environment variables shared by portal, worker, and scheduler
*/}}
{{- define "pathfinder.env" -}}
- name: DJANGO_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "pathfinder.secretName" . }}
      key: django-secret-key
- name: PTF_ENCRYPTION_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "pathfinder.secretName" . }}
      key: encryption-key
- name: DJANGO_DEBUG
  valueFrom:
    configMapKeyRef:
      name: {{ include "pathfinder.fullname" . }}
      key: django-debug
- name: DJANGO_ALLOWED_HOSTS
  valueFrom:
    configMapKeyRef:
      name: {{ include "pathfinder.fullname" . }}
      key: allowed-hosts
- name: CSRF_TRUSTED_ORIGINS
  valueFrom:
    configMapKeyRef:
      name: {{ include "pathfinder.fullname" . }}
      key: csrf-trusted-origins
{{- if .Values.postgresql.enabled }}
- name: DATABASE_HOST
  value: {{ include "pathfinder.postgresql.fullname" . }}
- name: DATABASE_PORT
  value: "5432"
- name: DATABASE_NAME
  value: {{ .Values.postgresql.auth.database | quote }}
- name: DATABASE_USER
  value: {{ .Values.postgresql.auth.username | quote }}
- name: DATABASE_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "pathfinder.postgresql.secretName" . }}
      key: postgresql-password
{{- end }}
{{- end }}
