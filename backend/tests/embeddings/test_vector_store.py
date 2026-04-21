from __future__ import annotations

from storage.vector_store import DEFAULT_GRPC_OPTIONS, VectorStore


def test_vector_store_passes_conservative_grpc_options_to_client(monkeypatch):
    captured: dict[str, object] = {}

    def fake_init(self, host="localhost:50051", **kwargs):
        captured["host"] = host
        captured["grpc_options"] = kwargs.get("grpc_options")
        self._host = host
        self._client = None

    monkeypatch.setattr(
        "storage.vector_store.ConservativeVectorAIClient.__init__",
        fake_init,
    )
    monkeypatch.setattr(
        "storage.vector_store.ConservativeVectorAIClient.connect",
        lambda self: captured.__setitem__("connected", True),
    )
    monkeypatch.setattr(
        "storage.vector_store.ConservativeVectorAIClient.close",
        lambda self: captured.__setitem__("closed", True),
    )

    store = VectorStore()
    store.connect()
    store.close()

    assert captured["host"] == "localhost:50051"
    assert captured["grpc_options"] == DEFAULT_GRPC_OPTIONS
    assert captured["connected"] is True
    assert captured["closed"] is True
