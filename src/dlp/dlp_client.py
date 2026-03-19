from __future__ import annotations

import base64
import hashlib
import logging
import string
from typing import Any, Sequence

try:
    from google.cloud import dlp_v2
except ImportError:  # pragma: no cover
    dlp_v2 = None


class DlpClientError(RuntimeError):
    """Raised when the DLP client is misconfigured."""


class LocalFormatPreservingCipher:
    """Local reversible demo cipher that preserves length and character classes."""

    _DIGITS = string.digits
    _LOWER = string.ascii_lowercase
    _UPPER = string.ascii_uppercase

    def __init__(self, key_material: str) -> None:
        self.key_material = key_material or "spark-local-demo-key"

    def encrypt(self, value: str | None) -> str | None:
        return self._transform(value=value, decrypt=False)

    def decrypt(self, value: str | None) -> str | None:
        return self._transform(value=value, decrypt=True)

    def _transform(self, value: str | None, decrypt: bool) -> str | None:
        if value is None:
            return None

        transformed: list[str] = []
        length = len(value)
        for position, character in enumerate(value):
            alphabet = self._resolve_alphabet(character)
            if not alphabet:
                transformed.append(character)
                continue

            original_index = alphabet.index(character)
            offset = self._offset(position=position, length=length, alphabet_size=len(alphabet))
            new_index = (original_index - offset) % len(alphabet) if decrypt else (original_index + offset) % len(alphabet)
            transformed.append(alphabet[new_index])

        return "".join(transformed)

    def _offset(self, position: int, length: int, alphabet_size: int) -> int:
        digest = hashlib.sha256(f"{self.key_material}|{position}|{length}".encode("utf-8")).digest()
        if alphabet_size <= 1:
            return 0
        return 1 + (digest[0] % (alphabet_size - 1))

    def _resolve_alphabet(self, character: str) -> str:
        if character.isdigit():
            return self._DIGITS
        if character.islower():
            return self._LOWER
        if character.isupper():
            return self._UPPER
        return ""


class DlpClient:
    """Config-driven client for local demo encryption or Google DLP table FPE."""

    def __init__(self, dlp_config: dict[str, Any], gcp_config: dict[str, Any] | None = None, logger: logging.Logger | None = None) -> None:
        self.dlp_config = dlp_config or {}
        self.gcp_config = gcp_config or {}
        self.logger = logger or logging.getLogger(__name__)
        self.backend = self.dlp_config.get("backend", "local").lower()
        self.local_cipher = LocalFormatPreservingCipher(self.dlp_config.get("local_key", "spark-local-demo-key"))
        self._google_client = None

        if self.backend == "local":
            self.logger.warning(
                "Using the local reversible demo cipher. This is for local development only and is not a substitute for Google DLP FPE."
            )

    def encrypt_string(self, value: str | None) -> str | None:
        if self.backend == "gcp":
            return self.encrypt_values([value])[0]
        return self.local_cipher.encrypt(value)

    def decrypt_string(self, value: str | None) -> str | None:
        if self.backend == "gcp":
            return self.decrypt_values([value])[0]
        return self.local_cipher.decrypt(value)

    def encrypt_values(self, values: Sequence[str | None]) -> list[str | None]:
        if self.backend == "gcp":
            return self._transform_values_with_google_dlp(values=values, operation="encrypt")
        return [self.local_cipher.encrypt(value) for value in values]

    def decrypt_values(self, values: Sequence[str | None]) -> list[str | None]:
        if self.backend == "gcp":
            return self._transform_values_with_google_dlp(values=values, operation="decrypt")
        return [self.local_cipher.decrypt(value) for value in values]

    def _transform_values_with_google_dlp(self, values: Sequence[str | None], operation: str) -> list[str | None]:
        active_values = [(index, value) for index, value in enumerate(values) if value not in (None, "")]
        transformed = list(values)
        if not active_values:
            return transformed

        project_id = self.gcp_config.get("project_id") or self.dlp_config.get("project_id")
        location = self.gcp_config.get("location") or self.dlp_config.get("location") or "global"
        if not project_id:
            raise DlpClientError("Missing project_id for backend=gcp.")

        request_item = self._build_table_item([str(value) for _, value in active_values])
        request_key = "deidentify_config" if operation == "encrypt" else "reidentify_config"
        request = {
            "parent": f"projects/{project_id}/locations/{location}",
            request_key: self._build_record_transformations(),
            "item": request_item,
        }

        client = self._get_google_client()
        if operation == "encrypt":
            response = client.deidentify_content(request=request)
        else:
            response = client.reidentify_content(request=request)

        response_values = self._extract_response_values(response)
        for (index, _), transformed_value in zip(active_values, response_values):
            transformed[index] = transformed_value

        return transformed

    def _get_google_client(self):
        if dlp_v2 is None:
            raise DlpClientError("google-cloud-dlp is not installed, so backend=gcp cannot be used.")
        if self._google_client is None:
            self._google_client = dlp_v2.DlpServiceClient()
        return self._google_client

    def _build_record_transformations(self) -> dict[str, Any]:
        return {
            "record_transformations": {
                "field_transformations": [
                    {
                        "primitive_transformation": {
                            "crypto_replace_ffx_fpe_config": self._build_ffx_config(),
                        },
                        "fields": [{"name": self.dlp_config.get("field_name", "sensitive_value")}],
                    }
                ]
            }
        }

    def _build_ffx_config(self) -> dict[str, Any]:
        ffx_config: dict[str, Any] = {
            "crypto_key": self._build_crypto_key(),
        }

        custom_alphabet = self.dlp_config.get("custom_alphabet")
        if custom_alphabet:
            ffx_config["custom_alphabet"] = custom_alphabet
        else:
            ffx_config["common_alphabet"] = self.dlp_config.get("common_alphabet", "ALPHA_NUMERIC")

        return ffx_config

    def _build_crypto_key(self) -> dict[str, Any]:
        unwrapped_key_base64 = self.dlp_config.get("unwrapped_key_base64")
        if unwrapped_key_base64:
            return {
                "unwrapped": {
                    "key": base64.b64decode(unwrapped_key_base64),
                }
            }

        wrapped_key_base64 = self.dlp_config.get("wrapped_key_base64")
        kms_key_name = self.dlp_config.get("kms_key_name")
        if wrapped_key_base64 and kms_key_name:
            return {
                "kms_wrapped": {
                    "wrapped_key": base64.b64decode(wrapped_key_base64),
                    "crypto_key_name": kms_key_name,
                }
            }

        raise DlpClientError(
            "For backend=gcp provide either dlp.unwrapped_key_base64 or both dlp.wrapped_key_base64 and dlp.kms_key_name."
        )

    def _build_table_item(self, values: Sequence[str]) -> dict[str, Any]:
        field_name = self.dlp_config.get("field_name", "sensitive_value")
        return {
            "table": {
                "headers": [{"name": field_name}],
                "rows": [{"values": [{"string_value": value}]} for value in values],
            }
        }

    def _extract_response_values(self, response: Any) -> list[str]:
        item = self._get_field(response, "item")
        table = self._get_field(item, "table")
        rows = self._get_field(table, "rows") or []

        extracted_values: list[str] = []
        for row in rows:
            row_values = self._get_field(row, "values") or []
            if not row_values:
                extracted_values.append("")
                continue
            extracted_values.append(self._get_field(row_values[0], "string_value") or "")

        return extracted_values

    def _get_field(self, value: Any, field_name: str) -> Any:
        if value is None:
            return None
        if isinstance(value, dict):
            return value.get(field_name)
        return getattr(value, field_name, None)
