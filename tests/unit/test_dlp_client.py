from __future__ import annotations

from src.dlp import dlp_client as dlp_client_module
from src.dlp.dlp_client import DlpClient


def test_local_encrypt_decrypt_round_trip() -> None:
    client = DlpClient(
        {
            "backend": "local",
            "field_name": "customer_ref",
            "common_alphabet": "ALPHA_NUMERIC",
            "local_key": "unit-test-key",
        }
    )

    original_value = "CUST001234"
    encrypted_value = client.encrypt_string(original_value)
    decrypted_value = client.decrypt_string(encrypted_value)

    assert encrypted_value is not None
    assert encrypted_value != original_value
    assert len(encrypted_value) == len(original_value)
    assert encrypted_value.isalnum()
    assert decrypted_value == original_value


def test_local_encrypt_decrypt_list_round_trip() -> None:
    client = DlpClient({"backend": "local", "local_key": "unit-test-key", "field_name": "customer_ref"})

    original_values = ["CUST001234", "ACCT998877", "USER554433"]
    encrypted_values = client.encrypt_values(original_values)
    decrypted_values = client.decrypt_values(encrypted_values)

    assert encrypted_values != original_values
    assert decrypted_values == original_values


def test_gcp_backend_builds_expected_requests(monkeypatch) -> None:
    captured_requests: dict[str, dict] = {}

    class FakeValue:
        def __init__(self, string_value: str) -> None:
            self.string_value = string_value

    class FakeRow:
        def __init__(self, string_value: str) -> None:
            self.values = [FakeValue(string_value)]

    class FakeTable:
        def __init__(self, values: list[str]) -> None:
            self.rows = [FakeRow(value) for value in values]

    class FakeItem:
        def __init__(self, values: list[str]) -> None:
            self.table = FakeTable(values)

    class FakeResponse:
        def __init__(self, values: list[str]) -> None:
            self.item = FakeItem(values)

    class FakeDlpServiceClient:
        def deidentify_content(self, request):
            captured_requests["deidentify"] = request
            return FakeResponse(["ENC123", "ENC456"])

        def reidentify_content(self, request):
            captured_requests["reidentify"] = request
            return FakeResponse(["RAW123", "RAW456"])

    class FakeDlpModule:
        DlpServiceClient = FakeDlpServiceClient

    monkeypatch.setattr(dlp_client_module, "dlp_v2", FakeDlpModule)

    client = DlpClient(
        dlp_config={
            "backend": "gcp",
            "field_name": "customer_ref",
            "common_alphabet": "ALPHA_NUMERIC",
            "kms_key_name": "projects/test/locations/global/keyRings/ring/cryptoKeys/key",
            "wrapped_key_base64": "d3JhcHBlZC1rZXk=",
        },
        gcp_config={"project_id": "test-project", "location": "global"},
    )

    assert client.encrypt_values(["A123", "B456"]) == ["ENC123", "ENC456"]
    assert client.decrypt_values(["E123", "E456"]) == ["RAW123", "RAW456"]
    assert captured_requests["deidentify"]["parent"] == "projects/test-project/locations/global"
    assert captured_requests["deidentify"]["deidentify_config"]["record_transformations"]["field_transformations"][0][
        "primitive_transformation"
    ]["crypto_replace_ffx_fpe_config"]["common_alphabet"] == "ALPHA_NUMERIC"
    assert captured_requests["reidentify"]["reidentify_config"]["record_transformations"]["field_transformations"][0]["fields"] == [
        {"name": "customer_ref"}
    ]
