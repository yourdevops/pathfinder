"""Docker plugin forms."""

from django import forms


class DockerConnectionForm(forms.Form):
    """Single-page form for Docker connection creation."""

    name = forms.CharField(
        max_length=63,
        label="Connection Name",
        help_text='Unique name for this connection (e.g., "docker-local", "docker-prod")',
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        label="Description",
        help_text="Optional description for this connection",
    )
    socket_path = forms.CharField(
        initial="/var/run/docker.sock",
        label="Docker Socket/Host",
        help_text="Unix socket path (e.g., /var/run/docker.sock) or TCP URL (e.g., tcp://localhost:2375)",
    )
    tls_enabled = forms.BooleanField(
        required=False, label="Enable TLS", help_text="Enable TLS for TCP connections"
    )
    tls_ca_cert = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "class": "font-mono text-xs"}),
        required=False,
        label="CA Certificate",
        help_text="CA certificate in PEM format (for TLS)",
    )
    tls_client_cert = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "class": "font-mono text-xs"}),
        required=False,
        label="Client Certificate",
        help_text="Client certificate in PEM format (for TLS)",
    )
    tls_client_key = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "class": "font-mono text-xs"}),
        required=False,
        label="Client Key",
        help_text="Client private key in PEM format (for TLS)",
    )

    def clean(self):
        cleaned_data = super().clean()
        tls_enabled = cleaned_data.get("tls_enabled")
        if tls_enabled:
            # If TLS enabled, require certificates
            if not cleaned_data.get("tls_ca_cert"):
                self.add_error(
                    "tls_ca_cert", "CA certificate required when TLS is enabled"
                )
            if not cleaned_data.get("tls_client_cert"):
                self.add_error(
                    "tls_client_cert", "Client certificate required when TLS is enabled"
                )
            if not cleaned_data.get("tls_client_key"):
                self.add_error(
                    "tls_client_key", "Client key required when TLS is enabled"
                )
        return cleaned_data
