{{/*
Expand the name of the chart.
*/}}
{{- define "weather-proxy.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "weather-proxy.fullname" -}}
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
{{- define "weather-proxy.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "weather-proxy.labels" -}}
helm.sh/chart: {{ include "weather-proxy.chart" . }}
{{ include "weather-proxy.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "weather-proxy.selectorLabels" -}}
app.kubernetes.io/name: {{ include "weather-proxy.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "weather-proxy.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "weather-proxy.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Redis host
*/}}
{{- define "weather-proxy.redisHost" -}}
{{- if .Values.config.redis.external }}
{{- .Values.config.redis.externalHost }}
{{- else }}
{{- printf "%s-redis-master" (include "weather-proxy.fullname" .) }}
{{- end }}
{{- end }}

{{/*
Redis port
*/}}
{{- define "weather-proxy.redisPort" -}}
{{- .Values.config.redis.port | default 6379 }}
{{- end }}
