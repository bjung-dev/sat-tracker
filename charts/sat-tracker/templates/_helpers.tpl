{{/*
Reusable snippets for the other templates. Files starting with "_" are not
turned into Kubernetes objects themselves.
*/}}

{{/*
Name for this release's objects. If the release is called "sat-tracker" we use
that; otherwise e.g. "chantilly" becomes "chantilly-sat-tracker". This lets
several copies live side by side without name clashes.
*/}}
{{- define "sat-tracker.fullname" -}}
{{- if eq .Release.Name .Chart.Name -}}
{{- .Chart.Name -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{/*
Labels used to find this release's pods. They must never change after the
first install, so they include only the chart name and the release name.
*/}}
{{- define "sat-tracker.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/* Full set of standard labels put on every object. */}}
{{- define "sat-tracker.labels" -}}
{{ include "sat-tracker.selectorLabels" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}
